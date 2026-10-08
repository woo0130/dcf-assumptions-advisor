from dataclasses import fields
from pathlib import Path

import pandas as pd
import pytest

from revenue_agent.backtest import run_backtest
from revenue_agent.recommendation import (
    PeerBenchmark,
    PeerBenchmarkProvider,
    RecommendationError,
    RecommendationResult,
    available_origin_years,
    build_scenario_table,
    evaluate_user_assumptions,
    evaluation_metadata,
)
from revenue_agent.schema import normalize, read_csv


ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def official():
    data = normalize(read_csv(ROOT / 'data/samsung_official_revenue.csv')).data
    return data, run_backtest(data)


def test_recommendation_result_contract():
    assert {field.name for field in fields(RecommendationResult)} == {
        'verdict', 'confidence', 'user_assumption', 'suggested_range',
        'base_case', 'bear_case', 'bull_case', 'supporting_evidence',
        'conflicting_evidence', 'data_warnings', 'provider_status',
    }


def test_2025_single_year_assumption_is_caution_and_keeps_bad_cagr_evidence(official):
    data, results = official
    before = results.copy(deep=True)
    decision = evaluate_user_assumptions(data, results, 2025, 5.0)

    assert isinstance(decision, RecommendationResult)
    assert decision.verdict == 'caution'
    assert decision.confidence == 'low'
    assert decision.user_assumption == 5.0
    assert decision.suggested_range == pytest.approx((0.8913539, 14.8665070))
    assert decision.bear_case == pytest.approx(0.8913539)
    assert decision.base_case == pytest.approx(5.4363768)
    assert decision.bull_case == pytest.approx(14.8665070)
    assert decision.provider_status == {
        'company': 'active', 'latest_disclosure': 'partial', 'peer': 'unconnected',
    }
    assert any('15.56%' in item and '13.49%' in item and '-2.07%p' in item
               for item in decision.conflicting_evidence)
    assert any('동종기업' in item for item in decision.data_warnings)
    pd.testing.assert_frame_equal(before, results)


def test_2025_multi_year_assumptions_and_compounded_scenarios(official):
    data, results = official
    assumptions = {2026: 5.0, 2027: 4.0, 2028: 3.0, 2029: 2.0, 2030: 1.0}
    decision = evaluate_user_assumptions(data, results, 2025, assumptions)
    meta = evaluation_metadata(data, 2025)
    scenarios = build_scenario_table(
        decision, current_revenue_krw=meta['current_revenue_krw'], origin_year=2025,
    )

    assert decision.verdict == 'caution'
    assert decision.user_assumption == assumptions
    assert list(decision.base_case) == list(range(2026, 2031))
    assert all(value == pytest.approx(5.4363768) for value in decision.base_case.values())
    assert len(scenarios) == 20
    user = scenarios[scenarios['시나리오'] == '사용자 입력']
    expected = meta['current_revenue_krw']
    for growth in assumptions.values():
        expected *= 1 + growth / 100
    assert user.iloc[-1]['예측 매출 (원)'] == pytest.approx(expected)
    assert any('1년 예측만 검증' in item for item in decision.data_warnings)


def test_outside_range_requests_adjustment(official):
    data, results = official
    decision = evaluate_user_assumptions(data, results, 2025, 50.0)
    assert decision.verdict == 'adjust'
    assert decision.confidence == 'low'
    assert any('2026년' in item and '범위를 벗어' in item for item in decision.conflicting_evidence)


def test_historical_review_does_not_use_later_actuals(official):
    data, results = official
    decision = evaluate_user_assumptions(data, results, 2022, 5.0)
    assert decision.verdict == 'insufficient'
    assert any('7개 미만' in item for item in decision.conflicting_evidence)
    assert any('2023-03-07' in item for item in decision.supporting_evidence)


def test_peer_provider_interface_is_wired(official):
    class MockPeer(PeerBenchmarkProvider):
        @property
        def status(self):
            return 'mocked'

        def get_benchmark(self, **kwargs):
            assert kwargs['forecast_years'] == [2026]
            return PeerBenchmark((2.0, 8.0), 5.0, ['모의 Peer 근거'], [], ['모의 자료'])

    data, results = official
    decision = evaluate_user_assumptions(data, results, 2025, 5.0, peer_provider=MockPeer())
    assert decision.provider_status['peer'] == 'mocked'
    assert '모의 Peer 근거' in decision.supporting_evidence
    assert '모의 자료' in decision.data_warnings


def test_input_contract(official):
    data, results = official
    assert available_origin_years(data) == list(range(2015, 2026))
    with pytest.raises(RecommendationError, match='3~5개년'):
        evaluate_user_assumptions(data, results, 2025, {2026: 5.0, 2027: 4.0})
    with pytest.raises(RecommendationError, match='연속'):
        evaluate_user_assumptions(data, results, 2025, {2026: 5.0, 2028: 4.0, 2029: 3.0})
    with pytest.raises(RecommendationError, match='-100%'):
        evaluate_user_assumptions(data, results, 2025, -100.0)
