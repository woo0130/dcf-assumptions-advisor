from pathlib import Path

import pandas as pd
import pytest

from revenue_agent.recommendation import (
    build_capital_ratio_scenario_table,
    capital_ratio_metadata,
    capital_ratio_statistics,
    evaluate_capex_assumptions,
    evaluate_nwc_assumptions,
)


ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def capital_data():
    return pd.read_csv(ROOT / 'data/samsung_nwc_capex.csv')


def test_nwc_distribution_uses_operating_balance_definition(capital_data):
    stats = capital_ratio_statistics(capital_data, 2025, 'nwc_ratio')
    latest = stats['snapshot'].iloc[-1]

    assert stats['count'] == 11
    assert latest['nwc_krw'] == pytest.approx(
        latest['trade_receivables_krw'] + latest['inventories_krw'] - latest['trade_payables_krw']
    )
    assert stats['mean'] == pytest.approx(23.4034563)
    assert stats['median'] == pytest.approx(23.0813288)
    assert stats['lower'] == pytest.approx(20.5697197)
    assert stats['upper'] == pytest.approx(26.3800267)
    assert stats['stddev'] == pytest.approx(3.9762455)
    assert stats['volatility_category'] == '보통'


def test_capex_distribution_includes_ppe_and_intangible_cash_outflows(capital_data):
    stats = capital_ratio_statistics(capital_data, 2025, 'capex_ratio')
    latest = stats['snapshot'].iloc[-1]

    assert latest['capex_krw'] == pytest.approx(
        latest['ppe_acquisition_krw'] + latest['intangible_acquisition_krw']
    )
    assert stats['mean'] == pytest.approx(16.2400517)
    assert stats['median'] == pytest.approx(17.0061759)
    assert stats['lower'] == pytest.approx(13.0948698)
    assert stats['upper'] == pytest.approx(17.8416292)
    assert stats['trend_change_pp'] == pytest.approx(-7.7449281)


@pytest.mark.parametrize(
    ('evaluator', 'metric', 'assumption'),
    [
        (evaluate_nwc_assumptions, 'nwc_ratio', 15.0),
        (evaluate_capex_assumptions, 'capex_ratio', 12.0),
    ],
)
def test_outside_range_is_adjust_and_cashflow_scenarios_are_inverted(
    capital_data, evaluator, metric, assumption,
):
    result = evaluator(capital_data, 2025, assumption)
    scenarios = build_capital_ratio_scenario_table(result, origin_year=2025, metric=metric)

    assert result.verdict == 'adjust'
    assert result.confidence == 'medium'
    assert result.bear_case == pytest.approx(result.suggested_range[1])
    assert result.bull_case == pytest.approx(result.suggested_range[0])
    assert len(scenarios) == 4
    assert result.provider_status['peer'] == 'unconnected'
    assert any('예측 백테스트가 아닙니다' in warning for warning in result.data_warnings)


def test_capital_ratio_review_excludes_disclosures_after_cutoff(capital_data):
    stats = capital_ratio_statistics(capital_data, 2022, 'nwc_ratio')
    metadata = capital_ratio_metadata(capital_data, 2022)

    assert stats['count'] == 8
    assert stats['snapshot']['fiscal_year'].max() == 2022
    assert metadata['cutoff_date'] == pd.Timestamp('2023-03-07')
    assert 2023 not in stats['snapshot']['fiscal_year'].tolist()


def test_multi_year_capex_keeps_each_user_input(capital_data):
    assumptions = {2026: 14.0, 2027: 15.0, 2028: 16.0}
    result = evaluate_capex_assumptions(capital_data, 2025, assumptions)
    scenarios = build_capital_ratio_scenario_table(result, origin_year=2025, metric='capex_ratio')

    user = scenarios[scenarios['시나리오'] == '사용자 입력']
    assert user['CapEx/매출액 (%)'].tolist() == [14.0, 15.0, 16.0]
    assert any('지속성이 검증되지 않았습니다' in warning for warning in result.data_warnings)


def test_negative_capex_ratio_is_rejected(capital_data):
    with pytest.raises(ValueError, match='0% 이상'):
        evaluate_capex_assumptions(capital_data, 2025, -1.0)
