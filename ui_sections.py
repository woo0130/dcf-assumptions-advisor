"""Streamlit의 상세 백테스트·공시 근거 영역."""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import streamlit as st

from .forecast import METHODS
from .recommendation import (
    CAPITAL_RATIO_CONFIG,
    RecommendationResult,
    capital_ratio_statistics,
    evaluation_metadata,
    operating_margin_statistics,
)
from .review import comparative_checks, segment_diagnostics, trace_case


def csv_bytes(frame: pd.DataFrame) -> bytes:
    return frame.to_csv(index=False).encode('utf-8-sig')


def build_reviewer_interpretation(
    result: RecommendationResult,
    metric: str = 'revenue_growth',
) -> str:
    """사용자의 가정을 먼저 언급하는 한 줄 리뷰 문구를 만든다."""
    if isinstance(result.user_assumption, dict):
        values = list(result.user_assumption.values())
        assumption_label = f'입력한 {len(values)}개년 가정'
        repeat_label = '입력한 가정을'
    else:
        value = float(result.user_assumption)
        assumption_label = f'{value:.1f}%'
        repeat_label = f'{assumption_label}를'

    lower, upper = result.suggested_range
    values = list(result.user_assumption.values()) if isinstance(result.user_assumption, dict) else [float(result.user_assumption)]
    within_range = all(lower <= value <= upper for value in values)

    if metric == 'operating_margin':
        if within_range:
            opening = f'{assumption_label}는 기업의 과거 영업이익률 중앙 범위 안에 있습니다.'
        else:
            opening = f'{assumption_label}는 기업의 과거 영업이익률 중앙 범위를 벗어납니다.'
        if result.verdict == 'retain':
            return f'{opening} 기본 시나리오로 유지할 수 있지만 업황과 사업 구성 변화도 함께 점검하세요.'
        if result.verdict == 'caution':
            return f'{opening} 과거 변동성이 높으므로 {repeat_label} 단독 적용하기보다 보수 시나리오를 병행하세요.'
        if result.verdict == 'adjust':
            return f'{opening} 권고 범위로 조정하거나 범위를 벗어나는 별도 근거를 문서화하는 것이 적절합니다.'
        return f'{opening} 유효 표본이 부족해 채택 여부를 확정하기 어렵습니다.'

    if metric in CAPITAL_RATIO_CONFIG:
        label = str(CAPITAL_RATIO_CONFIG[metric]['label'])
        if within_range:
            opening = f'{assumption_label}는 기업의 과거 {label} 중앙 범위 안에 있습니다.'
        else:
            opening = f'{assumption_label}는 기업의 과거 {label} 중앙 범위를 벗어납니다.'
        cashflow_note = '비율이 높을수록 FCFF의 현금 유출 부담이 커집니다.'
        if result.verdict == 'retain':
            return f'{opening} 기본 시나리오로 유지할 수 있지만 {cashflow_note}'
        if result.verdict == 'caution':
            return f'{opening} 과거 변동성이 높으므로 {repeat_label} 단독 적용하지 말고 상단 보수 시나리오를 함께 검토하세요.'
        if result.verdict == 'adjust':
            return f'{opening} 권고 범위로 조정하거나 범위를 벗어나는 투자·운전자본 계획을 문서화하세요. {cashflow_note}'
        return f'{opening} 유효 표본이 부족해 채택 여부를 확정하기 어렵습니다.'

    if within_range:
        opening = f'{assumption_label}는 과거 성장률 범위 안에 있어 과도한 가정은 아닙니다.'
    else:
        opening = f'{assumption_label}는 과거 성장률 범위를 벗어나 추가 근거 또는 조정이 필요합니다.'

    if result.verdict == 'caution':
        return (f'{opening} 다만 과거 백테스트에서 성장률 기반 예측이 매출 유지 기준보다 나빴기 때문에, '
                f'{repeat_label} 그대로 채택하기보다 보수 시나리오와 함께 사용하는 것이 적절합니다.')
    if result.verdict == 'adjust':
        return f'{opening} 아래 권고 범위와 보수·기본·낙관 시나리오를 함께 검토하세요.'
    if result.verdict == 'retain':
        return (f'{opening} 시간순 최종 평가에서도 선택 방식이 매출 유지 기준보다 나았지만, '
                '미래 실적을 보장하는 판정은 아닙니다.')
    return f'{opening} 검증 표본이 부족하므로 현재 자료만으로 채택 여부를 확정하기 어렵습니다.'


def build_assumption_position(
    data: pd.DataFrame,
    origin_year: int,
    assumptions: float | dict[int, float],
) -> pd.DataFrame:
    """기준일 당시 성장률 분포에서 사용자 가정의 위치와 최근 성장률 차이를 계산한다."""
    metadata = evaluation_metadata(data, int(origin_year))
    cutoff = metadata['cutoff_date']
    snapshot = data[
        (data['publication_date'] <= cutoff) & (data['fiscal_year'] <= int(origin_year))
    ].sort_values('publication_date').drop_duplicates('fiscal_year', keep='last').sort_values('fiscal_year')
    revenue = snapshot.set_index('fiscal_year')['revenue_krw'].astype(float)
    growths: list[float] = []
    for year in revenue.index:
        if year - 1 in revenue.index and revenue.loc[year - 1] > 0 and revenue.loc[year] > 0:
            growths.append((revenue.loc[year] / revenue.loc[year - 1] - 1) * 100)
    history = pd.Series(growths, dtype=float)
    if history.empty:
        return pd.DataFrame()

    values = assumptions if isinstance(assumptions, dict) else {int(origin_year) + 1: float(assumptions)}
    recent = float(history.iloc[-1])
    return pd.DataFrame([
        {
            '예측 연도': int(year),
            '입력 성장률 (%)': float(value),
            '과거 분포 백분위 (%)': float((history <= float(value)).mean() * 100),
            '최근 실적 성장률 (%)': recent,
            '최근 성장률 대비 (%p)': float(value) - recent,
        }
        for year, value in values.items()
    ])


def build_operating_margin_position(
    data: pd.DataFrame,
    origin_year: int,
    assumptions: float | dict[int, float],
) -> pd.DataFrame:
    """기업 과거 영업이익률 분포에서 사용자 가정의 위치를 계산한다."""
    stats = operating_margin_statistics(data, int(origin_year))
    history = stats['snapshot']['operating_margin_pct'].astype(float)
    values = assumptions if isinstance(assumptions, dict) else {int(origin_year) + 1: float(assumptions)}
    return pd.DataFrame([
        {
            '예측 연도': int(year),
            '입력 영업이익률 (%)': float(value),
            '과거 분포 백분위 (%)': float((history <= float(value)).mean() * 100),
            '최근 영업이익률 (%)': float(stats['latest']),
            '최근 마진 대비 (%p)': float(value) - float(stats['latest']),
        }
        for year, value in values.items()
    ])


def build_capital_ratio_position(
    data: pd.DataFrame,
    origin_year: int,
    assumptions: float | dict[int, float],
    metric: str,
) -> pd.DataFrame:
    """기업 과거 NWC·CapEx 비율 분포에서 사용자 가정의 위치를 계산한다."""
    if metric not in CAPITAL_RATIO_CONFIG:
        raise ValueError(f'지원하지 않는 자본효율 지표입니다: {metric}')
    stats = capital_ratio_statistics(data, int(origin_year), metric)
    column = str(CAPITAL_RATIO_CONFIG[metric]['column'])
    value_label = str(CAPITAL_RATIO_CONFIG[metric]['value_column'])
    history = stats['snapshot'][column].astype(float)
    values = assumptions if isinstance(assumptions, dict) else {int(origin_year) + 1: float(assumptions)}
    return pd.DataFrame([
        {
            '예측 연도': int(year),
            f'입력 {value_label}': float(value),
            '과거 분포 백분위 (%)': float((history <= float(value)).mean() * 100),
            f'최근 {value_label}': float(stats['latest']),
            '최근 비율 대비 (%p)': float(value) - float(stats['latest']),
        }
        for year, value in values.items()
    ])


def build_dcf_scenario_display(
    scenarios: pd.DataFrame,
    recommendation: RecommendationResult,
) -> pd.DataFrame:
    """사용자 입력을 제외한 DCF 적용용 보수·기본·낙관 시나리오를 정리한다."""
    descriptions = {
        '보수': '업황 둔화·기준 매출 유지에 가까운 경우',
        '기본': '기업 과거 성장률 중앙값 기준',
        '낙관': '과거 상단 성장 구간 재현',
    }
    display = scenarios[scenarios['시나리오'].isin(descriptions)].copy()
    display['예측 매출 (조원)'] = display['예측 매출 (원)'] / 1e12
    display['적용 해석'] = display['시나리오'].map(descriptions)
    if not isinstance(recommendation.user_assumption, dict):
        display = display.rename(columns={'성장률 (%)': '권고 성장률 (%)'})
        return display[['시나리오', '권고 성장률 (%)', '예측 매출 (조원)', '적용 해석']]
    return display[['시나리오', '예측 연도', '성장률 (%)', '예측 매출 (조원)', '적용 해석']]


def build_operating_margin_scenario_display(
    scenarios: pd.DataFrame,
    recommendation: RecommendationResult,
) -> pd.DataFrame:
    descriptions = {
        '보수': '과거 영업이익률 하단 구간 적용',
        '기본': '기업 과거 영업이익률 중앙값 기준',
        '낙관': '과거 영업이익률 상단 구간 재현',
    }
    display = scenarios[scenarios['시나리오'].isin(descriptions)].copy()
    display['적용 해석'] = display['시나리오'].map(descriptions)
    if not isinstance(recommendation.user_assumption, dict):
        display = display.rename(columns={'영업이익률 (%)': '권고 영업이익률 (%)'})
        return display[['시나리오', '권고 영업이익률 (%)', '적용 해석']]
    return display[['시나리오', '예측 연도', '영업이익률 (%)', '적용 해석']]


def build_capital_ratio_scenario_display(
    scenarios: pd.DataFrame,
    recommendation: RecommendationResult,
    metric: str,
) -> pd.DataFrame:
    if metric not in CAPITAL_RATIO_CONFIG:
        raise ValueError(f'지원하지 않는 자본효율 지표입니다: {metric}')
    value_column = str(CAPITAL_RATIO_CONFIG[metric]['value_column'])
    short_label = 'NWC' if metric == 'nwc_ratio' else 'CapEx'
    descriptions = {
        '보수': f'과거 {short_label} 비율 상단: FCFF 현금 유출 부담 확대',
        '기본': f'기업 과거 {short_label} 비율 중앙값 기준',
        '낙관': f'과거 {short_label} 비율 하단: FCFF 현금 유출 부담 완화',
    }
    display = scenarios[scenarios['시나리오'].isin(descriptions)].copy()
    display['적용 해석'] = display['시나리오'].map(descriptions)
    if not isinstance(recommendation.user_assumption, dict):
        renamed = f'권고 {value_column}'
        display = display.rename(columns={value_column: renamed})
        return display[['시나리오', renamed, '적용 해석']]
    return display[['시나리오', '예측 연도', value_column, '적용 해석']]


def data_context_message(data: pd.DataFrame) -> str:
    """자료 선택 직후 보여주는 한 문장 요약."""
    years = sorted(int(year) for year in data['fiscal_year'].unique())
    company = str(data.iloc[0]['company_name'])
    return f'{company} {years[0]}~{years[-1]}년 연결 매출 데이터를 확인했습니다.'


def render_method_definitions() -> None:
    st.write('Rₜ는 회계연도 t의 매출입니다. 3년 방식은 t−3부터 t까지 4개 연속 연도 매출이 필요합니다.')
    for name, formula, _ in METHODS.values():
        st.markdown(f'**{name}**: {formula}')
    st.write('오차 = 예측−실제, APE = |오차|/실제×100, MAPE = 평균 APE입니다. '
             '기준 대비 개선(%p) = 매출 유지 MAPE−해당 방식 MAPE이며 양수면 개선입니다.')


def render_backtest_tab(data: pd.DataFrame, results: pd.DataFrame) -> None:
    years = sorted(data['fiscal_year'].unique())
    company = str(data.iloc[0]['company_name'])
    st.subheader('기업·기간·자료 기준')
    st.write(f'{company} · {years[0]}~{years[-1]}년 중 {len(years)}개 회계연도 · 연간 연결(CFS) · 원화(KRW) · '
             f'공시 버전 {len(data)}개 · 조회 시각(UTC) {data["retrieved_at"].max().tz_convert("UTC")}')
    latest = data.sort_values('publication_date').drop_duplicates('fiscal_year', keep='last')
    trend = latest.set_index('fiscal_year')['revenue_krw'].astype(float).div(1e8).rename('매출 (억원)')
    st.subheader('과거 매출 추이')
    st.line_chart(trend)

    st.subheader('연도별 예측·실제·오차')
    if results.empty:
        st.warning('당기 연간 실적 행이 없어 예측 기준일을 설정하지 못했습니다.')
        return
    display = results.copy()
    for col, label in [('forecast_krw', '예측 (억원)'), ('actual_krw', '실제 (억원)'),
                       ('error_krw', '오차 (억원)'), ('absolute_error_krw', '절대오차 (억원)')]:
        display[label] = pd.to_numeric(display[col], errors='coerce') / 1e8
    display = display.rename(columns={
        'origin_year': '기준 연도', 'target_year': '평가 연도', 'method_name': '방식',
        'cutoff_date': '예측 기준일', 'ape_pct': 'APE (%)', 'actual_publication_date': '실적 공시일',
        'status': '상태', 'reason': '계산·평가 불가 사유', 'analysis_basis': '분석 기준',
    })
    st.dataframe(display[['기준 연도', '평가 연도', '방식', '예측 기준일', '예측 (억원)', '실제 (억원)',
                          '오차 (억원)', '절대오차 (억원)', 'APE (%)', '실적 공시일', '상태',
                          '계산·평가 불가 사유', '분석 기준']], hide_index=True)
    evaluated = results[results['status'] == '평가 완료']
    if not evaluated.empty:
        chart = evaluated.pivot(index='target_year', columns='method_name', values='forecast_krw') / 1e8
        chart['실제 매출'] = evaluated.drop_duplicates('target_year').set_index('target_year')['actual_krw'] / 1e8
        st.line_chart(chart)
        st.caption('그래프 단위: 억원. 계산 가능한 방식별 연도가 다를 수 있습니다.')


def render_performance_tab(summary: pd.DataFrame, common: list[int], split: dict, mock: bool) -> None:
    st.subheader('MAPE·과대/과소 예측 경향')
    st.write('동일한 공통 평가 연도: ' + (', '.join(map(str, common)) if common else '없음'))
    st.caption('네 방식 모두 유효한 공통 연도에서 성능을 비교합니다.')
    if not summary.empty:
        st.dataframe(summary.drop(columns='method'), hide_index=True)
    st.subheader('시간순 방식 선택과 최종 평가')
    if split['available']:
        st.write(f'선택 기간: {split["selection_years"]} / 최종 평가 기간: {split["test_years"]}')
        st.write(f'선택 기간에서 고른 방식: {split["selected_method"]} (선택 MAPE {split["selection_mape_pct"]:.2f}%)')
        st.markdown(f'**최종 평가:** 선택 방식 {split["test_mape_pct"]:.2f}% / 매출 유지 {split["baseline_test_mape_pct"]:.2f}% / '
                    f'개선 {split["improvement_pp"]:.2f}%p / 기준보다 우수: {"예" if split["beats_baseline"] else "아니요"}')
    st.warning(split['reason'])
    if mock:
        st.caption('모의 데이터 방식 선택은 계산 시연이며 실제 기업 추천이 아닙니다.')


def render_evidence_tab(
    data: pd.DataFrame,
    results: pd.DataFrame,
    *,
    source: str,
    csv_choice: str | None,
    root: Path,
) -> None:
    st.subheader('공시·기간·정정·당기/비교표시')
    st.dataframe(data.rename(columns={
        'fiscal_year': '회계연도', 'publication_date': '공시일', 'receipt_no': '접수번호',
        'source_url': '출처 링크', 'revenue_krw': '매출 (원)', 'is_correction': '정정 여부',
        'value_basis': '당기/비교표시', 'comparability_notes': '비교 가능성 주의',
    }), hide_index=True)

    if not (source == 'CSV' and csv_choice == '공식 원문 대조 자료 (2015~2025)'):
        st.info('고정 공식 주석 검토는 기본 제공 삼성전자 자료에만 연결됩니다.')
        return

    st.subheader('검토: 2023년 예측 한 건 추적')
    st.info('원래 매출·계산식·방식 선택·최종 평가를 보존했습니다. 주석 구간 분석은 사후 진단입니다.')
    trace_inputs, trace_results, inputs_in_time = trace_case(data, results, 2023)
    st.write('예측 기준일: 2023-03-07 · 실제 최초 공시: 2024-03-12')
    input_display = trace_inputs[['year', 'revenue_trillion_krw', 'publication_date', 'value_basis', 'receipt_no']].rename(columns={
        'year': '입력 회계연도', 'revenue_trillion_krw': '매출 (조원)', 'publication_date': '사용한 공시일',
        'value_basis': '원문 구분', 'receipt_no': '사용한 접수번호',
    })
    input_display['원문 구분'] = input_display['원문 구분'].map({'current': '당기', 'comparative': '비교표시'})
    st.dataframe(input_display, hide_index=True)
    case_display = trace_results[['method_name', 'forecast_krw', 'actual_krw', 'error_krw', 'ape_pct']].copy()
    for key in ['forecast_krw', 'actual_krw', 'error_krw']:
        case_display[key] /= 1e12
    case_display = case_display.rename(columns={
        'method_name': '방식', 'forecast_krw': '예측 (조원)', 'actual_krw': '실제 (조원)',
        'error_krw': '오차 (조원)', 'ape_pct': 'APE (%)',
    })
    st.dataframe(case_display, hide_index=True)
    if inputs_in_time:
        st.success('확인: 모든 사용 입력의 공시일 ≤ 2023-03-07. 2023년 실제 매출은 평가에만 사용했습니다.')
    else:
        st.error('입력 공시일 위반이 발견되었습니다.')

    st.subheader('공식 주석의 비교 가능성')
    review = json.loads((root / 'data/comparability_review.json').read_text(encoding='utf-8'))
    st.caption('2026-10-07 사후 검토 · 공식 감사 PDF의 지정 주석 검토이며 전체 주석 전수 감사는 아닙니다.')
    reviewed_rows = [{
        '연도': row['year'], '사업결합·연결 범위': row['business_combinations'],
        '매각·중단영업': row['disposals_and_discontinued'], '회계정책': row['accounting_policy'],
        '매출 재작성 점검': row['restatement'], '미확인 사항': row['unconfirmed'],
    } for row in review['years']]
    st.dataframe(pd.DataFrame(reviewed_rows), hide_index=True)
    st.warning('인수·매각 순매출 효과가 모두 공개되지 않아 동일 범위 유기적 매출을 재구성하지 않았습니다.')

    st.subheader('원래 결과와 별도 구간 진단')
    protocol = json.loads((root / 'docs/review/review_protocol.json').read_text(encoding='utf-8'))
    diagnostics = segment_diagnostics(results, protocol)
    matrix = diagnostics.pivot(index='구간', columns='방식', values='MAPE (%)')
    matrix = matrix.reindex([part['label'] for part in protocol['segments']])
    matrix.insert(0, '평가 연도', [str(part['years'][0]) if len(part['years']) == 1
                               else f"{part['years'][0]}~{part['years'][-1]}" for part in protocol['segments']])
    matrix.insert(1, '방식당 표본 수', diagnostics.drop_duplicates('구간').set_index('구간')['표본 수'])
    st.dataframe(matrix)
    st.warning('최초 선택 CAGR 고정: 2023~2025년 MAPE 15.56%, 매출 유지 13.49%. 구간별 재선택은 하지 않습니다.')
    st.download_button('2023년 사용 입력 CSV', csv_bytes(trace_inputs), 'case_2023_inputs.csv', 'text/csv')
    st.download_button('2023년 예측 상세 CSV', csv_bytes(trace_results), 'case_2023_results.csv', 'text/csv')
    st.download_button('별도 구간 진단 CSV', csv_bytes(diagnostics), 'segment_diagnostics.csv', 'text/csv')
    st.download_button('공식 주석 검토 JSON', json.dumps(review, ensure_ascii=False, indent=2),
                       'comparability_review.json', 'application/json')
    st.download_button('매출 비교표시 대조 CSV', csv_bytes(comparative_checks(data)),
                       'comparative_checks.csv', 'text/csv')


def render_downloads_tab(data: pd.DataFrame, results: pd.DataFrame, summary: pd.DataFrame, split: dict) -> None:
    st.subheader('원본 분석 자료')
    st.download_button('정규화 데이터 CSV (원)', csv_bytes(data), 'normalized_revenue.csv', 'text/csv')
    st.download_button('백테스트 결과 CSV', csv_bytes(results), 'backtest_results.csv', 'text/csv')
    st.download_button('성능 요약 CSV', csv_bytes(summary), 'performance_summary.csv', 'text/csv')
    st.download_button('시간순 선택·평가 JSON', json.dumps(split, ensure_ascii=False, indent=2),
                       'selection_evaluation.json', 'application/json')
    st.subheader('데이터 경고와 한계')
    st.write('공시일 필터만으로 모든 정정·재작성 누출이 해결되지는 않습니다. 합병·분할·중단영업·재작성 메모가 있는 '
             '연도는 포함한 상태로 경고합니다. 현재 서비스는 매출 성장률과 영업이익률 가정을 검토하며 FCFF·WACC·'
             '영구성장률·가치평가는 포함하지 않습니다.')
