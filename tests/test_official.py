import json
from pathlib import Path

import pytest

from revenue_agent.backtest import PIT, run_backtest, summarize
from revenue_agent.official import EvidenceError, parse_dart_revenue
from revenue_agent.schema import normalize, read_csv

ROOT = Path(__file__).resolve().parents[1]


def test_official_csv_and_saved_crosschecks():
    evidence = json.loads((ROOT / 'data/official_evidence.json').read_text())
    data = normalize(read_csv(ROOT / 'data/samsung_official_revenue.csv'))
    assert data.rejected.empty
    assert len(data.data) == 30
    assert len(evidence['checks']) == 11
    assert not data.data['is_mock'].any()
    annual = data.data[data.data['value_basis'] == 'current'].set_index('fiscal_year')
    assert annual.index.tolist() == list(range(2015, 2026))
    # 직접 확인한 공식 PDF Revenue 행의 대조 값.
    expected = {2015: 200653482, 2016: 201866745, 2017: 239575376,
                2018: 243771415, 2019: 230400881, 2020: 236806988,
                2021: 279604799, 2022: 302231360, 2023: 258935494,
                2024: 300870903, 2025: 333605938}
    assert annual['revenue_krw'].to_dict() == {y: amount * 1e6 for y, amount in expected.items()}
    for check in evidence['checks']:
        year = check['report_year']
        assert check['revenue_million_krw'][str(year)] == expected[year]
        assert annual.loc[year, 'receipt_no'] == check['receipt_no']
    results = run_backtest(data.data)
    scored = results[results['status'] == '평가 완료']
    assert set(scored['analysis_basis']) == {PIT}
    assert (results['input_max_publication_date'] <= results['cutoff_date']).all()
    assert (scored['actual_publication_date'] > scored['cutoff_date']).all()
    _, common, split = summarize(results)
    assert common == list(range(2019, 2026))
    assert split['selected_method'] == '최근 3년 CAGR 유지'
    assert split['test_mape_pct'] == pytest.approx(15.5631976124)
    assert split['baseline_test_mape_pct'] == pytest.approx(13.4904027363)
    assert not split['beats_baseline']


def test_dart_parser_rejects_quarter_or_wrong_unit():
    evidence = json.loads((ROOT / 'data/official_evidence.json').read_text())
    html = (ROOT / 'tests/fixtures/2025_dart_statement.html').read_text()
    values, _ = parse_dart_revenue(html, 2025)
    assert values == {2025: 333605938, 2024: 300870903, 2023: 258935494}
    for broken in [html.replace('2025.01.01', '2025.07.01'), html.replace('백만원', '천원')]:
        with pytest.raises(EvidenceError):
            parse_dart_revenue(broken, 2025)
