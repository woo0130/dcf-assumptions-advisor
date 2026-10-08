import copy
import json
from pathlib import Path

import pandas as pd
import pytest
import requests

from revenue_agent.backtest import PIT, RETROSPECTIVE, run_backtest, summarize
from revenue_agent.collect import DartClient, DartError
from revenue_agent.forecast import predict
from revenue_agent.schema import DataError, normalize, read_csv

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def raw():
    return read_csv(ROOT / 'data/mock_revenue.csv')


def verified(raw):
    result = raw.copy()
    result['is_mock'] = 'false'
    result['point_in_time_verified'] = 'true'
    result['first_annual_report'] = 'true'
    result['comparability_reviewed'] = 'true'
    result['comparability_notes'] = ''
    result['evidence_note'] = '테스트용 가상 원문 확인 (실제 데이터 아님)'
    return result


@pytest.mark.parametrize('method', ['last_growth', 'cagr3', 'mean3'])
def test_hand_calculation_ten_percent(method):
    value, reason = predict({2020: 100, 2021: 110, 2022: 121, 2023: 133.1}, 2023, method)
    assert not reason
    assert value == pytest.approx(146.41)


def test_arithmetic_is_not_cagr():
    values = {2020: 100, 2021: 120, 2022: 90, 2023: 108}
    assert predict(values, 2023, 'mean3')[0] == pytest.approx(113.4)  # (20%-25%+20%)/3 = 5%
    assert predict(values, 2023, 'cagr3')[0] == pytest.approx(108 * 1.08 ** (1/3))
    assert predict(values, 2023, 'last_growth')[0] == pytest.approx(129.6)
    assert predict(values, 2023, 'flat')[0] == 108


@pytest.mark.parametrize('value', [0, -1, float('nan'), float('inf')])
def test_invalid_input(value):
    assert predict({2020: value, 2021: 100}, 2021, 'last_growth')[0] is None


def test_missing_intermediate_year():
    value, reason = predict({2020: 100, 2022: 121, 2023: 133.1}, 2023, 'cagr3')
    assert value is None and '2021' in reason


@pytest.mark.parametrize('unit,amount', [('원', '100000000'), ('천원', '100000'), ('백만원', '100'), ('억원', '1')])
def test_unit_conversion(raw, unit, amount):
    raw = raw.iloc[:1].copy()
    raw.loc[0, ['unit', 'revenue']] = [unit, amount]
    result = normalize(raw)
    assert result.data.iloc[0]['revenue_krw'] == 100000000
    assert result.rejected.empty


@pytest.mark.parametrize('column,value', [('fs_div', 'OFS'), ('report_type', 'quarter'),
    ('period_start', '2015-07-01'), ('period_end', '2015-09-30'), ('currency', 'USD'),
    ('unit', '달러'), ('retrieved_at', '2026-01-01'), ('is_mock', 'yes'), ('revenue', 'NaN'),
    ('publication_date', '2015-12-31'), ('stock_code', '5930')])
def test_reject_bad_records(raw, column, value):
    raw = raw.iloc[:1].copy()
    raw.loc[0, column] = value
    result = normalize(raw)
    assert result.data.empty and len(result.rejected) == 1


def test_mixed_mock_rejected(raw):
    raw.loc[0, 'is_mock'] = 'false'
    with pytest.raises(DataError, match='함께'):
        normalize(raw)


def test_conflicting_same_date(raw):
    duplicate = raw.iloc[:1].copy()
    duplicate.loc[0, 'revenue'] = '999'
    with pytest.raises(DataError, match='서로 다른'):
        normalize(pd.concat([raw, duplicate]))


def test_future_correction_not_used_and_first_actual_preserved(raw):
    raw = verified(raw)
    initial = normalize(raw).data
    before = run_backtest(initial)
    correction = raw[raw['fiscal_year'] == '2018'].copy()
    correction['publication_date'] = '2021-06-01'
    correction['revenue'] = '999999'
    correction['is_correction'] = 'true'
    correction['first_annual_report'] = 'false'
    corrected = normalize(pd.concat([raw, correction])).data
    after = run_backtest(corrected)
    a = after[(after['origin_year'] == 2018) & (after['method'] == 'cagr3')].iloc[0]
    b = before[(before['origin_year'] == 2018) & (before['method'] == 'cagr3')].iloc[0]
    assert a['forecast_krw'] == b['forecast_krw']
    assert all(pd.Timestamp(v['publication_date']) <= a['cutoff_date'] for v in json.loads(a['input_vintages']))
    target = after[(after['target_year'] == 2018) & (after['method'] == 'flat')].iloc[0]
    assert target['actual_krw'] == 133100 * 1000000
    assert target['actual_basis'] == '최초 연간 정기보고서 원문 확인'
    assert a['analysis_basis'] == PIT


def test_later_comparative_is_not_available_early(raw):
    raw = verified(raw)
    comparison = raw[raw['fiscal_year'] == '2017'].copy()
    comparison['publication_date'] = '2020-03-15'
    comparison['source_fiscal_year'] = '2019'
    comparison['value_basis'] = 'comparative'
    comparison['first_annual_report'] = 'false'
    comparison['revenue'] = '900000'
    data = normalize(pd.concat([raw, comparison])).data
    results = run_backtest(data)
    early = results[(results['origin_year'] == 2018) & (results['method'] == 'cagr3')].iloc[0]
    late = results[(results['origin_year'] == 2019) & (results['method'] == 'cagr3')].iloc[0]
    assert next(v for v in json.loads(early['input_vintages']) if v['year'] == 2017)['revenue_krw'] == 121000000000
    assert next(v for v in json.loads(late['input_vintages']) if v['year'] == 2017)['revenue_krw'] == 900000000000


def test_metrics_common_years_and_small_sample(raw):
    results = run_backtest(normalize(raw).data)
    summary, common, split = summarize(results)
    assert common == list(range(2019, 2025))
    assert summary['공통 표본 수'].tolist() == [6, 6, 6, 6]
    assert summary['전체 유효 표본 수'].tolist() == [8, 6, 6, 9]
    assert not split['available']
    assert set(results['analysis_basis']) == {RETROSPECTIVE}
    row = results[(results['target_year'] == 2016) & (results['method'] == 'flat')].iloc[0]
    assert row['error_krw'] == -10000 * 1e6
    assert row['ape_pct'] == pytest.approx(100 / 11)
    assert row['signed_pct_error'] == pytest.approx(-100 / 11)
    assert row['days_until_actual'] == 365
    assert summary.loc[summary['method'] == 'flat', '기준 대비 MAPE 개선 (%p)'].iloc[0] == 0


def test_zero_actual_is_not_scored(raw):
    raw.loc[raw['fiscal_year'] == '2018', 'revenue'] = '0'
    results = run_backtest(normalize(raw).data)
    row = results[(results['target_year'] == 2018) & (results['method'] == 'flat')].iloc[0]
    assert row['status'] == '평가 불가'
    assert pd.isna(row['ape_pct'])
    assert row['absolute_error_krw'] > 0


def test_chronological_selection_does_not_read_holdout(raw):
    extra = raw.iloc[-1:].copy()
    extra['fiscal_year'] = '2025'
    extra['source_fiscal_year'] = '2025'
    extra['period_start'] = '2025-01-01'
    extra['period_end'] = '2025-12-31'
    extra['publication_date'] = '2026-03-15'
    extra['revenue'] = '191180'
    extended = pd.concat([raw, extra], ignore_index=True)
    r = run_backtest(normalize(extended).data)
    _, _, split = summarize(r)
    assert split['available']
    assert split['selection_years'] == [2019, 2020, 2021, 2022]
    assert split['test_years'] == [2023, 2024, 2025]
    changed = r.copy()
    changed.loc[changed['target_year'].isin(split['test_years']), 'ape_pct'] = 9999
    _, _, other = summarize(changed)
    assert other['selected_method'] == split['selected_method']
    assert other['selection_mape_pct'] == split['selection_mape_pct']


def test_missing_required_columns():
    with pytest.raises(DataError, match='필수 열'):
        normalize(pd.DataFrame({'revenue': [10]}))


class Response:
    status_code = 200
    def __init__(self, payload):
        self.payload = payload
    def raise_for_status(self):
        pass
    def json(self):
        return copy.deepcopy(self.payload)


class Session:
    def __init__(self, payloads):
        self.payloads = iter(payloads)
    def get(self, *args, **kwargs):
        return Response(next(self.payloads))


def test_api_no_key():
    with pytest.raises(DartError, match='키가 없습니다'):
        DartClient('')


@pytest.mark.parametrize('status,message', [('010', '등록되지'), ('020', '호출 한도'), ('800', '점검')])
def test_api_errors(status, message):
    client = DartClient('secret-example', Session([{'status': status, 'message': 'secret-example'}]))
    with pytest.raises(DartError, match=message) as exc:
        client._get('list.json', {})
    assert 'secret-example' not in str(exc.value)


def test_api_transport_error_redacts_key():
    class Failed:
        def get(self, *args, **kwargs):
            raise requests.ConnectionError('https://host/?crtfc_key=secret-example')
    with pytest.raises(DartError) as exc:
        DartClient('secret-example', Failed())._get('list.json', {})
    assert 'secret-example' not in str(exc.value)
    assert exc.value.__suppress_context__


def test_api_receipt_and_annual_account_mapping():
    filings = {'status': '000', 'total_page': 1, 'list': [{'rcept_no': '20240315000001',
        'rcept_dt': '20240315', 'report_nm': '사업보고서 (2023.12)'}]}
    financial = {'status': '000', 'list': [{'rcept_no': '20240315000001',
        'sj_div': 'IS', 'account_id': 'ifrs-full_Revenue', 'thstrm_amount': '100000000', 'currency': 'KRW'}]}
    raw, audit, warnings = DartClient('secret-example', Session([filings, financial])).collect(2023, 2023)
    assert not warnings
    assert raw.iloc[0]['publication_date'] == '2024-03-15'
    assert raw.iloc[0]['value_basis'] == 'current'
    assert not raw.iloc[0]['point_in_time_verified']
    assert not raw.iloc[0]['first_annual_report']
    assert 'secret-example' not in json.dumps(audit)
    assert len(normalize(raw).data) == 1


def test_api_empty_and_ambiguous_accounts():
    filings = {'status': '013'}
    financial = {'status': '000', 'list': [
        {'sj_div': 'IS', 'account_id': 'ifrs-full_Revenue', 'thstrm_amount': '100'},
        {'sj_div': 'CIS', 'account_id': 'ifrs-full_Revenue', 'thstrm_amount': '200'}]}
    raw, _, warnings = DartClient('secret-example', Session([filings, financial])).collect(2023, 2023)
    assert raw.empty and '충돌' in warnings[0]


def test_comparative_publication_cannot_be_backdated(raw):
    row = raw.iloc[:1].copy()
    row['value_basis'] = 'comparative'
    row['source_fiscal_year'] = '2024'
    # 2015년 매출을 2024년 보고서에서 가져왔는데 2016년 공시일을 붙인 잘못된 입력.
    result = normalize(row)
    assert result.data.empty
    assert '소급' in result.rejected.iloc[0]['reason']
