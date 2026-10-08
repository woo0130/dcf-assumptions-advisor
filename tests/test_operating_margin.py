from pathlib import Path

import pandas as pd
import pytest

from revenue_agent.recommendation import (
    MockPeerBenchmarkProvider,
    build_operating_margin_scenario_table,
    evaluate_operating_margin_assumptions,
    operating_margin_metadata,
    operating_margin_statistics,
)


ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def margin_data():
    return pd.read_csv(ROOT / 'data/samsung_operating_margin.csv')


@pytest.fixture
def peer():
    return MockPeerBenchmarkProvider(ROOT / 'data/peer_benchmark_mock.csv')


def test_operating_margin_distribution_and_volatility(margin_data):
    stats = operating_margin_statistics(margin_data, 2025)

    assert stats['count'] == 11
    assert stats['mean'] == pytest.approx(14.6137001)
    assert stats['median'] == pytest.approx(14.3521275)
    assert stats['lower'] == pytest.approx(12.5609425)
    assert stats['upper'] == pytest.approx(16.8331977)
    assert stats['stddev'] == pytest.approx(5.8113186)
    assert stats['volatility_category'] == '보통'
    assert stats['latest'] == pytest.approx(13.0696268)


def test_operating_margin_assumption_and_mock_peer_are_integrated(margin_data, peer):
    result = evaluate_operating_margin_assumptions(margin_data, 2025, 14.0, peer_provider=peer)

    assert result.verdict == 'retain'
    assert result.confidence == 'medium'
    assert result.base_case == pytest.approx(14.3521275)
    assert result.bear_case == pytest.approx(12.5609425)
    assert result.bull_case == pytest.approx(16.8331977)
    assert result.provider_status == {
        'company': 'active', 'latest_disclosure': 'partial', 'peer': 'active',
    }
    assert any('Mock Peer' in item and '백분위' in item for item in result.supporting_evidence)
    assert any('비검증 Mock' in item for item in result.data_warnings)


def test_operating_margin_outside_range_is_adjust(margin_data, peer):
    result = evaluate_operating_margin_assumptions(margin_data, 2025, 30.0, peer_provider=peer)

    assert result.verdict == 'adjust'
    assert any('2026년' in item and '범위를 벗어' in item for item in result.conflicting_evidence)


def test_historical_margin_review_excludes_later_years(margin_data):
    stats = operating_margin_statistics(margin_data, 2022)
    metadata = operating_margin_metadata(margin_data, 2022)

    assert stats['count'] == 8
    assert stats['snapshot']['fiscal_year'].max() == 2022
    assert metadata['cutoff_date'] == pd.Timestamp('2023-03-07')
    assert 2023 not in stats['snapshot']['fiscal_year'].tolist()


def test_multi_year_margin_scenarios_keep_each_year(margin_data, peer):
    assumptions = {2026: 14.0, 2027: 13.5, 2028: 13.0}
    result = evaluate_operating_margin_assumptions(margin_data, 2025, assumptions, peer_provider=peer)
    scenarios = build_operating_margin_scenario_table(result, origin_year=2025)

    assert result.verdict == 'retain'
    assert len(scenarios) == 12
    user = scenarios[scenarios['시나리오'] == '사용자 입력']
    assert user['영업이익률 (%)'].tolist() == [14.0, 13.5, 13.0]
    assert any('지속성이 검증되지 않았습니다' in item for item in result.data_warnings)


def test_mock_peer_has_active_status_but_explicit_mock_source(peer):
    benchmark = peer.get_benchmark(
        company_name='삼성전자', as_of_date=pd.Timestamp('2026-03-10'),
        forecast_years=[2026], metric='revenue_growth', user_values=[6.0],
    )

    assert peer.status == 'active'
    assert benchmark is not None
    assert benchmark.sample_size == 10
    assert benchmark.user_percentile is not None
    assert benchmark.source_label == 'SK하이닉스·TSMC 비검증 Mock 샘플'

