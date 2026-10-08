"""기존 결과를 변경하지 않는 사후 주석 진단과 예측 추적."""
import json

import pandas as pd

from .forecast import METHODS


def trace_case(data: pd.DataFrame, results: pd.DataFrame, target_year: int = 2023):
    case = results[results['target_year'] == target_year].copy()
    if case.empty:
        raise ValueError('해당 평가 연도 결과가 없습니다.')
    inputs = []
    seen = set()
    all_in_time = True
    for _, row in case.iterrows():
        for item in json.loads(row['input_vintages']):
            all_in_time &= pd.Timestamp(item['publication_date']) <= row['cutoff_date']
            key = (item['year'], item['receipt_no'], item['publication_date'])
            if key in seen:
                continue
            seen.add(key)
            current = data[(data['fiscal_year'] == item['year']) & (data['value_basis'] == 'current')]
            earliest = current['publication_date'].min()
            inputs.append({**item, 'first_current_publication_date': earliest,
                           'revenue_trillion_krw': item['revenue_krw'] / 1e12})
    input_frame = pd.DataFrame(inputs).sort_values('year').reset_index(drop=True)
    return input_frame, case, bool(all_in_time)


def segment_diagnostics(results: pd.DataFrame, protocol: dict):
    """기존 공통 평가 집합을 고정하고, 명시된 모든 구간·방식을 재선택 없이 요약."""
    valid = results[(results['status'] == '평가 완료') & results['target_year'].isin(protocol['original_common_years'])]
    rows = []
    for segment in protocol['segments']:
        requested = set(segment['years'])
        per_method = {m: set(valid.loc[valid['method'] == m, 'target_year']) & requested for m in METHODS}
        common = sorted(set.intersection(*per_method.values()))
        part = valid[valid['target_year'].isin(common)]
        baseline = part.loc[part['method'] == 'flat', 'ape_pct'].mean()
        for method, (name, _, _) in METHODS.items():
            values = part[part['method'] == method]
            mape = values['ape_pct'].mean()
            rows.append({'segment_id': segment['id'], '구간': segment['label'],
                         '평가 연도': ', '.join(map(str, common)), '방식': name, 'method': method,
                         '표본 수': len(values), 'MAPE (%)': mape,
                         '평균 부호 백분율오차 (%)': values['signed_pct_error'].mean(),
                         '유지 대비 개선 (%p)': baseline - mape,
                         '분할 근거': segment['basis'], '해석': '사후 진단·재선택 없음; 소표본'})
    return pd.DataFrame(rows)


def comparative_checks(data: pd.DataFrame):
    rows = []
    for _, row in data[data['value_basis'] == 'comparative'].iterrows():
        current = data[(data['fiscal_year'] == row['fiscal_year']) & (data['value_basis'] == 'current')]
        original = current.sort_values('publication_date').iloc[0]
        rows.append({'회계연도': int(row['fiscal_year']), '원래 공시일': original['publication_date'],
                     '비교표시 공시일': row['publication_date'], '비교표시 보고서 연도': int(row['source_fiscal_year']),
                     '최초 매출 (원)': int(original['revenue_krw']), '비교표시 매출 (원)': int(row['revenue_krw']),
                     '차이 (원)': int(row['revenue_krw'] - original['revenue_krw'])})
    return pd.DataFrame(rows)
