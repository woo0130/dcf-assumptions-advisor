from pathlib import Path

import pandas as pd

from revenue_agent.backtest import run_backtest
from revenue_agent.recommendation import (
    MockPeerBenchmarkProvider,
    build_operating_margin_scenario_table,
    build_scenario_table,
    evaluate_operating_margin_assumptions,
    evaluate_user_assumptions,
    evaluation_metadata,
    operating_margin_metadata,
    build_capital_ratio_scenario_table,
    capital_ratio_metadata,
    evaluate_capex_assumptions,
    evaluate_nwc_assumptions,
)
from revenue_agent.reporting import (
    build_dcf_scenario_export,
    build_integrated_markdown_report,
    build_markdown_report,
    combine_dcf_scenario_exports,
)
from revenue_agent.schema import normalize, read_csv
from revenue_agent.ui_sections import build_reviewer_interpretation


ROOT = Path(__file__).resolve().parents[1]


def test_markdown_report_contains_decision_interpretation_and_evidence():
    margins = pd.read_csv(ROOT / 'data/samsung_operating_margin.csv')
    peer = MockPeerBenchmarkProvider(ROOT / 'data/peer_benchmark_mock.csv')
    result = evaluate_operating_margin_assumptions(margins, 2025, 14.0, peer_provider=peer)
    meta = operating_margin_metadata(margins, 2025)
    interpretation = build_reviewer_interpretation(result, 'operating_margin')
    report = build_markdown_report(
        metric='operating_margin', company_name='삼성전자', origin_year=2025,
        cutoff_date=meta['cutoff_date'], result=result, interpretation=interpretation,
    )

    assert '# 삼성전자 DCF 영업이익률 가정 검토' in report
    assert '- 입력 가정: 14.00%' in report
    assert '- 판정: 유지 가능 (`retain`)' in report
    assert '## 한 줄 해석' in report and interpretation in report
    assert '## 찬성 근거' in report
    assert '## 주의·충돌 근거' in report
    assert '비검증 Mock' in report


def test_dcf_exports_have_one_common_excel_schema_for_both_metrics():
    revenue = normalize(read_csv(ROOT / 'data/samsung_official_revenue.csv')).data
    revenue_result = evaluate_user_assumptions(revenue, run_backtest(revenue), 2025, 6.0)
    revenue_meta = evaluation_metadata(revenue, 2025)
    revenue_scenarios = build_scenario_table(
        revenue_result, current_revenue_krw=revenue_meta['current_revenue_krw'], origin_year=2025,
    )
    revenue_export = build_dcf_scenario_export(
        metric='revenue_growth', company_name='삼성전자', cutoff_date=revenue_meta['cutoff_date'],
        result=revenue_result, scenario_table=revenue_scenarios,
    )

    margins = pd.read_csv(ROOT / 'data/samsung_operating_margin.csv')
    margin_result = evaluate_operating_margin_assumptions(margins, 2025, 14.0)
    margin_meta = operating_margin_metadata(margins, 2025)
    margin_scenarios = build_operating_margin_scenario_table(margin_result, origin_year=2025)
    margin_export = build_dcf_scenario_export(
        metric='operating_margin', company_name='삼성전자', cutoff_date=margin_meta['cutoff_date'],
        result=margin_result, scenario_table=margin_scenarios,
    )

    assert revenue_export.columns.tolist() == margin_export.columns.tolist()
    assert revenue_export['revenue_growth_pct'].notna().all()
    assert revenue_export['forecast_revenue_krw'].notna().all()
    assert revenue_export['operating_margin_pct'].isna().all()
    assert margin_export['operating_margin_pct'].notna().all()
    assert margin_export['revenue_growth_pct'].isna().all()
    assert set(revenue_export['scenario']) == {'사용자 입력', '보수', '기본', '낙관'}


def test_capital_ratio_reports_and_exports_share_four_assumption_schema():
    data = pd.read_csv(ROOT / 'data/samsung_nwc_capex.csv')
    meta = capital_ratio_metadata(data, 2025)
    frames = []
    reports = {}
    for metric, evaluator, assumption, expected_column in [
        ('nwc_ratio', evaluate_nwc_assumptions, 23.0, 'nwc_to_revenue_pct'),
        ('capex_ratio', evaluate_capex_assumptions, 17.0, 'capex_to_revenue_pct'),
    ]:
        result = evaluator(data, 2025, assumption)
        scenarios = build_capital_ratio_scenario_table(result, origin_year=2025, metric=metric)
        frame = build_dcf_scenario_export(
            metric=metric, company_name='삼성전자', cutoff_date=meta['cutoff_date'],
            result=result, scenario_table=scenarios,
        )
        report = build_markdown_report(
            metric=metric, company_name='삼성전자', origin_year=2025,
            cutoff_date=meta['cutoff_date'], result=result,
            interpretation=build_reviewer_interpretation(result, metric),
        )
        assert frame[expected_column].notna().all()
        assert {'revenue_growth_pct', 'operating_margin_pct', 'nwc_to_revenue_pct', 'capex_to_revenue_pct'} <= set(frame)
        frames.append(frame)
        reports[metric] = report

    combined = combine_dcf_scenario_exports(frames)
    markdown = build_integrated_markdown_report(reports)
    assert len(combined) == 8
    assert set(combined['review_metric']) == {'nwc_ratio', 'capex_ratio'}
    assert '# DCF 핵심 가정 통합 검토 리포트' in markdown
    assert 'NWC/매출액' in markdown and 'CapEx/매출액' in markdown
