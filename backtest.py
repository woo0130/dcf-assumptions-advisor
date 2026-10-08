"""공시일 기준 expanding-window, 공통 평가 연도 및 시간순 선택/평가."""
import json

import pandas as pd

from .forecast import METHODS, predict

RETROSPECTIVE = '최신 재무자료 기반의 회고적 비교'
PIT = '과거 시점 백테스트 (입력 원문 검증 표시 기준)'


def _annual_actual(rows):
    rows = rows[rows['value_basis'] == 'current'].sort_values('publication_date')
    first = rows[rows['first_annual_report'] & rows['point_in_time_verified']]
    return first.iloc[0] if not first.empty else (rows.iloc[0] if not rows.empty else None)


def run_backtest(data: pd.DataFrame) -> pd.DataFrame:
    if data.empty:
        return pd.DataFrame()
    results = []
    for year in sorted(data['fiscal_year'].unique()):
        origin = _annual_actual(data[data['fiscal_year'] == year])
        if origin is None:
            continue
        cutoff = origin['publication_date']
        # 중요: 예측 입력은 이 필터를 통과한 vintage에서만 선택한다.
        available = data[(data['publication_date'] <= cutoff) & (data['fiscal_year'] <= year)]
        snapshot = available.sort_values('publication_date').drop_duplicates('fiscal_year', keep='last').set_index('fiscal_year')
        actual = _annual_actual(data[data['fiscal_year'] == year + 1])
        for method, (_, _, lookback) in METHODS.items():
            prediction, reason = predict(snapshot['revenue_krw'].to_dict(), year, method)
            used = snapshot.loc[snapshot.index.isin(range(year - lookback, year + 1))]
            strict = bool(len(used) == lookback + 1 and used['point_in_time_verified'].all())
            actual_verified = actual is not None and bool(actual['first_annual_report'] and actual['point_in_time_verified'])
            row = {
                'origin_year': int(year), 'target_year': int(year + 1), 'method': method,
                'method_name': METHODS[method][0], 'cutoff_date': cutoff,
                'target_period_start': pd.Timestamp(year + 1, 1, 1),
                'target_period_end': pd.Timestamp(year + 1, 12, 31),
                'forecast_krw': prediction, 'actual_krw': None,
                'actual_publication_date': pd.NaT, 'days_until_actual': None,
                'days_until_period_end': (pd.Timestamp(year + 1, 12, 31) - cutoff).days,
                'forecast_period': '다음 회계연도 1월~12월 (1년)',
                'status': '계산 불가' if reason else '실적 미확보', 'reason': reason,
                'analysis_basis': PIT if strict and actual_verified and not bool(origin['is_mock']) else RETROSPECTIVE,
                'is_mock': bool(origin['is_mock']), 'actual_basis': '',
                'actual_receipt_no': '', 'actual_source_url': '', 'actual_is_correction': None,
                'error_krw': None, 'absolute_error_krw': None, 'ape_pct': None, 'signed_pct_error': None,
                'input_max_publication_date': used['publication_date'].max(),
                'input_vintages': json.dumps([
                    {'year': int(y), 'publication_date': r['publication_date'].date().isoformat(),
                     'revenue_krw': int(r['revenue_krw']), 'receipt_no': r['receipt_no'],
                     'source_url': r['source_url'], 'value_basis': r['value_basis'],
                     'point_in_time_verified': bool(r['point_in_time_verified'])}
                    for y, r in used.iterrows()], ensure_ascii=False),
            }
            if not reason and (cutoff >= pd.Timestamp(year + 1, 12, 31)):
                row.update(status='계산 대상 외', reason='예측 기준일이 대상 연도 말 이후입니다.')
            elif actual is not None:
                actual_value = float(actual['revenue_krw'])
                row.update(actual_krw=actual_value, actual_publication_date=actual['publication_date'],
                           days_until_actual=(actual['publication_date'] - cutoff).days,
                           actual_basis='최초 연간 정기보고서 원문 확인' if actual_verified else '최초 원문 미검증: 확보된 당기 값',
                           actual_receipt_no=actual['receipt_no'], actual_source_url=actual['source_url'],
                           actual_is_correction=bool(actual['is_correction']))
                if not reason:
                    if actual['publication_date'] <= cutoff:
                        row.update(status='계산 대상 외', reason='대상 실제 실적이 예측 기준일 이전 또는 같은 날 공개되었습니다.')
                    elif actual_value <= 0:
                        row.update(status='평가 불가', reason='실제 매출이 0·음수여서 백분율 평가에서 제외합니다.',
                                   error_krw=prediction - actual_value, absolute_error_krw=abs(prediction - actual_value))
                    else:
                        error = prediction - actual_value
                        row.update(status='평가 완료', error_krw=error, absolute_error_krw=abs(error),
                                   ape_pct=abs(error) / actual_value * 100, signed_pct_error=error / actual_value * 100)
            results.append(row)
    return pd.DataFrame(results)


def summarize(results: pd.DataFrame):
    if results.empty:
        return pd.DataFrame(), [], {'available': False, 'reason': '평가 가능한 자료가 없습니다.'}
    valid = results[results['status'] == '평가 완료']
    year_sets = {m: set(valid.loc[valid['method'] == m, 'target_year']) for m in METHODS}
    common = sorted(set.intersection(*year_sets.values()))
    records = []
    baseline = valid[(valid['method'] == 'flat') & valid['target_year'].isin(common)]['ape_pct'].mean()
    for method, (name, _, _) in METHODS.items():
        all_rows = valid[valid['method'] == method]
        rows = all_rows[all_rows['target_year'].isin(common)]
        mape = rows['ape_pct'].mean()
        records.append({'method': method, '방식': name, '전체 유효 표본 수': len(all_rows),
                        '전체 유효 연도': ', '.join(map(str, sorted(year_sets[method]))),
                        '공통 표본 수': len(rows), 'MAPE (%)': mape,
                        '평균 부호 백분율오차 (%)': rows['signed_pct_error'].mean(),
                        '평균 절대오차 (원)': rows['absolute_error_krw'].mean(),
                        '기준 대비 MAPE 개선 (%p)': baseline - mape if len(rows) else None,
                        '기준 대비 개선': bool(mape < baseline) if len(rows) else None})
    # 최소 4개 선택 연도 + 3개 최종 평가 연도. 통계적 신뢰를 보장하는 기준은 아니다.
    split = {'available': False, 'reason': '공통 평가 연도가 7개 미만입니다. 신뢰할 만한 추천을 할 수 없습니다.'}
    if len(common) >= 7:
        n_select = max(4, int(len(common) * .6))
        n_select = min(n_select, len(common) - 3)
        train, test = common[:n_select], common[n_select:]
        candidates = valid[(valid['method'] != 'flat') & valid['target_year'].isin(train)]
        scores = candidates.groupby('method')['ape_pct'].mean()
        chosen = scores.idxmin()
        # 선택에 쓴 실제 값의 공개일이 첫 최종평가 예측 기준일을 넘으면 선택 누출이다.
        selection_ready = candidates['actual_publication_date'].max()
        first_test_cutoff = valid[valid['target_year'].isin(test)]['cutoff_date'].min()
        if selection_ready > first_test_cutoff:
            split = {'available': False, 'reason': '선택 기간 실적이 첫 최종 평가 기준일까지 공개되지 않아 방식 선택을 중단합니다.'}
        else:
            holdout = valid[valid['target_year'].isin(test)]
            score = holdout.loc[holdout['method'] == chosen, 'ape_pct'].mean()
            base = holdout.loc[holdout['method'] == 'flat', 'ape_pct'].mean()
            split = {'available': True, 'selected_method': METHODS[chosen][0], 'selection_years': train,
                     'test_years': test, 'selection_mape_pct': float(scores[chosen]),
                     'test_mape_pct': float(score), 'baseline_test_mape_pct': float(base),
                     'improvement_pp': float(base - score), 'beats_baseline': bool(score < base),
                     'reason': '탐색적 선택 결과입니다. 작은 단일 기업 표본으로 통계적 신뢰나 산업 전체 우월성을 주장할 수 없습니다.'}
    return pd.DataFrame(records), common, split
