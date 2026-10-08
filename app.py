from datetime import date
import json
import os
from pathlib import Path

import pandas as pd
import streamlit as st
from dotenv import load_dotenv

from revenue_agent.backtest import RETROSPECTIVE, run_backtest, summarize
from revenue_agent.collect import DartClient, DartError
from revenue_agent.recommendation import (
    CAPITAL_RATIO_CONFIG,
    MockPeerBenchmarkProvider,
    RecommendationError,
    available_origin_years,
    build_capital_ratio_scenario_table,
    build_method_candidates,
    build_operating_margin_scenario_table,
    build_scenario_table,
    capital_ratio_metadata,
    capital_ratio_statistics,
    evaluate_capex_assumptions,
    evaluate_nwc_assumptions,
    evaluate_operating_margin_assumptions,
    evaluate_user_assumptions,
    evaluation_metadata,
    operating_margin_metadata,
    operating_margin_statistics,
)
from revenue_agent.reporting import (
    build_dcf_scenario_export,
    build_integrated_markdown_report,
    build_markdown_report,
    combine_dcf_scenario_exports,
)
from revenue_agent.schema import DataError, normalize, read_csv
from revenue_agent.ui_sections import (
    build_assumption_position,
    build_capital_ratio_position,
    build_capital_ratio_scenario_display,
    build_dcf_scenario_display,
    build_operating_margin_position,
    build_operating_margin_scenario_display,
    build_reviewer_interpretation,
    csv_bytes,
    data_context_message,
    render_backtest_tab,
    render_downloads_tab,
    render_evidence_tab,
    render_method_definitions,
    render_performance_tab,
)


ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / '.env', override=False)
st.set_page_config(page_title='DCF 가정 리뷰어', layout='wide')
st.title('내 DCF 가정, 데이터로 검토받으세요')
st.write('기업의 과거 실적과 비교 기준을 바탕으로 입력한 매출 성장률·영업이익률·NWC·CapEx 가정을 검토하고, '
         'DCF에 바로 적용할 수 있는 보수·기본·낙관 시나리오를 제안합니다.')
st.caption('현재 검토 범위: 연간 연결 매출 성장률·영업이익률·NWC/매출액·CapEx/매출액 · 투자 의견이나 미래 실적 보장이 아닙니다.')


# 1단계: 자료 확인 및 입력
st.divider()
st.header('1. 분석할 기업 자료를 확인하세요')
source = st.radio('데이터 입력 방식', ['CSV', 'OpenDART'], horizontal=True)
raw = None
api_raw = None
collection_warnings: list[str] = []
csv_choice = None

if source == 'CSV':
    csv_choice = st.selectbox('재무자료 선택', [
        '공식 원문 대조 자료 (2015~2025)', '직접 업로드', '모의 데이터 (2015~2024)',
    ])
    uploaded = st.file_uploader('매출 CSV 업로드', type=['csv']) if csv_choice == '직접 업로드' else None
    try:
        if uploaded is not None:
            raw = read_csv(uploaded)
        elif csv_choice == '모의 데이터 (2015~2024)':
            raw = read_csv(ROOT / 'data/mock_revenue.csv')
        elif csv_choice == '공식 원문 대조 자료 (2015~2025)':
            raw = read_csv(ROOT / 'data/samsung_official_revenue.csv')
    except DataError as exc:
        st.error(str(exc))

    with st.expander('CSV 서식·모의 자료·공식 대조 근거', expanded=False):
        st.caption('같은 연도의 여러 공시 버전을 별도 행으로 보존합니다. 종목코드 앞자리 0을 유지하세요.')
        source_cols = st.columns(3)
        source_cols[0].download_button('수동 입력 CSV 서식', (ROOT / 'data/manual_template.csv').read_bytes(),
                                       'manual_template.csv', 'text/csv')
        source_cols[1].download_button('모의 데이터 CSV', (ROOT / 'data/mock_revenue.csv').read_bytes(),
                                       'mock_revenue.csv', 'text/csv')
        source_cols[2].download_button('공식 대조 근거 JSON', (ROOT / 'data/official_evidence.json').read_bytes(),
                                       'official_evidence.json', 'application/json')
else:
    st.info('OpenDART API 응답은 조회 시점 자료이므로 정정 전 원문이 확인되지 않으면 회고적 비교로 표시합니다.')
    left, right = st.columns(2)
    start_year = left.number_input('시작 회계연도', min_value=2015, max_value=date.today().year - 1,
                                   value=max(2015, date.today().year - 10), step=1)
    end_year = right.number_input('마지막 회계연도', min_value=2015, max_value=date.today().year - 1,
                                  value=date.today().year - 1, step=1)
    st.caption('키는 환경변수 DART_API_KEY, 로컬 .env 또는 Streamlit secrets에 설정합니다.')
    if st.button('연간 연결 매출 수집', type='primary'):
        st.session_state.pop('dart_data', None)
        key = os.environ.get('DART_API_KEY', '')
        if not key:
            try:
                key = str(st.secrets.get('DART_API_KEY', ''))
            except (FileNotFoundError, st.errors.StreamlitSecretNotFoundError):
                key = ''
        try:
            with st.spinner('공시 목록과 연결 매출을 대조하고 있습니다…'):
                collected = DartClient(key).collect(int(start_year), int(end_year))
            st.session_state['dart_data'] = (int(start_year), int(end_year), collected)
        except DartError as exc:
            st.error(str(exc))
    stored = st.session_state.get('dart_data')
    if stored and stored[:2] == (int(start_year), int(end_year)):
        raw, api_raw, collection_warnings = stored[2]

for warning in collection_warnings:
    st.warning(warning)
if raw is None:
    st.info('CSV를 선택·업로드하거나 OpenDART 수집을 실행하세요.')
    st.stop()

try:
    normalized = normalize(raw)
except DataError as exc:
    st.error(str(exc))
    st.stop()
data = normalized.data
if data.empty:
    st.error('정규화 후 사용할 수 있는 연간 연결 자료가 없습니다.')
    st.stop()

mock = bool(data['is_mock'].iloc[0])
st.success('✓ ' + data_context_message(data))
context_cols = st.columns(4)
context_cols[0].metric('기업', str(data.iloc[0]['company_name']))
context_cols[1].metric('회계연도 수', f"{data['fiscal_year'].nunique()}개년")
context_cols[2].metric('재무 기준', '연간 연결')
context_cols[3].metric('통화', 'KRW')

with st.expander('데이터 검증 상태와 원본 다운로드', expanded=False):
    if mock:
        st.error('모의 데이터입니다. 실제 기업 실적·공시일이 아닙니다.')
    elif data['point_in_time_verified'].all():
        st.success('입력 자료의 당시 공시 원문 확인 표시가 활성화되어 있습니다.')
    else:
        st.warning(RETROSPECTIVE + ' — 엄밀한 과거 시점 백테스트가 아닙니다.')
    for warning in normalized.warnings:
        st.warning(warning)
    if not normalized.rejected.empty:
        st.warning(f'정규화 과정에서 {len(normalized.rejected)}개 행을 제외했습니다.')
        st.dataframe(normalized.rejected, hide_index=True)
        st.download_button('제외 행 CSV', csv_bytes(normalized.rejected), 'rejected_rows.csv', 'text/csv')
    st.download_button('원본 매출 CSV', csv_bytes(raw), 'raw_revenue.csv', 'text/csv')
    if api_raw is not None:
        st.download_button('OpenDART 원본 응답 JSON (키 제외)',
                           json.dumps(api_raw, ensure_ascii=False, indent=2),
                           'opendart_response.json', 'application/json')

results = run_backtest(data)
summary, common, split = summarize(results)
margin_data = pd.read_csv(ROOT / 'data/samsung_operating_margin.csv')
capital_data = pd.read_csv(ROOT / 'data/samsung_nwc_capex.csv')
peer_provider = MockPeerBenchmarkProvider(ROOT / 'data/peer_benchmark_mock.csv')

METRIC_LABEL_TO_KEY = {
    '매출 성장률': 'revenue_growth',
    '영업이익률': 'operating_margin',
    '순운전자본(NWC)': 'nwc_ratio',
    '설비투자(CapEx)': 'capex_ratio',
}
METRIC_NAMES = {
    'revenue_growth': '매출 성장률',
    'operating_margin': '영업이익률',
    'nwc_ratio': '매출액 대비 NWC 비율',
    'capex_ratio': '매출액 대비 CapEx 비율',
}
METRIC_DEFAULTS = {'revenue_growth': 6.0, 'operating_margin': 12.0, 'nwc_ratio': 15.0, 'capex_ratio': 12.0}
review_metric_label = st.radio(
    '검토 항목', list(METRIC_LABEL_TO_KEY), horizontal=True,
    help='매출은 예측 백테스트, 나머지 항목은 기준일 당시 과거 분포·변동성으로 검토합니다.',
)
review_metric = METRIC_LABEL_TO_KEY[review_metric_label]
supplemental_available = source == 'CSV' and csv_choice == '공식 원문 대조 자료 (2015~2025)'
if review_metric != 'revenue_growth':
    if not supplemental_available:
        st.warning('현재 영업이익률·NWC·CapEx 검토는 기본 제공 삼성전자 공식 대조 자료에만 연결되어 있습니다.')
        st.stop()
    if review_metric == 'operating_margin':
        st.success('✓ 삼성전자 2015~2025년 연결 영업이익률 데이터를 확인했습니다.')
        st.caption('영업이익률 = 연결 영업이익 ÷ 연결 매출. 각 연도의 최초 연간 공시 당기 값을 사용합니다.')
    elif review_metric == 'nwc_ratio':
        st.success('✓ 삼성전자 2015~2025년 연결 NWC 구성 계정을 확인했습니다.')
        st.caption('NWC = 매출채권 + 재고자산 − 매입채무, NWC 비율 = NWC ÷ 연결 매출 × 100')
        st.caption('DCF 현금흐름에는 이 비율로 산정한 연도별 NWC 잔액의 증감(ΔNWC)을 사용합니다.')
    else:
        st.success('✓ 삼성전자 2015~2025년 연결 CapEx 현금유출 데이터를 확인했습니다.')
        st.caption('CapEx = 유형자산 취득 + 무형자산 취득 현금유출, CapEx 비율 = CapEx ÷ 연결 매출 × 100')


# 2단계: 질문형 가정 입력
st.divider()
metric_name = METRIC_NAMES[review_metric]
st.header(f'2. 검토할 {metric_name}을 입력하세요')
origin_years = (
    available_origin_years(data)
    if review_metric == 'revenue_growth'
    else sorted(int(year) for year in (
        margin_data if review_metric == 'operating_margin' else capital_data
    )['fiscal_year'].unique())
)
if not origin_years:
    st.warning('가정 기준일을 만들 수 있는 당기 연간 매출이 없습니다.')
    st.stop()

with st.container(border=True):
    assumption_origin = st.selectbox(
        '가정 기준 회계연도', origin_years, index=len(origin_years) - 1,
        help='이 연도의 연간 실적 공시일을 정보 기준일로 사용합니다.',
    )
    company_name = str(data.iloc[0]['company_name'])
    target_year = int(assumption_origin) + 1
    st.subheader(f'{company_name}의 {target_year}년 {metric_name}을 몇 %로 가정하셨나요?')
    single_assumption = st.number_input(
        f'내 DCF {metric_name} (%)', min_value=-99.9 if review_metric in {'revenue_growth', 'operating_margin'} else 0.0,
        max_value=300.0 if review_metric == 'revenue_growth' else 100.0,
        value=METRIC_DEFAULTS[review_metric],
        step=0.5, format='%.1f',
    )

    use_multi_year = False
    multi_assumptions: dict[int, float] = {}
    with st.expander('3~5개년 직접 입력', expanded=False):
        use_multi_year = st.checkbox('다년도 가정으로 검토하기', value=False)
        if use_multi_year:
            horizon = st.slider('예측 연수', min_value=3, max_value=5, value=5, step=1)
            assumption_frame = pd.DataFrame({
                '예측 연도': list(range(target_year, target_year + horizon)),
                f'{metric_name} (%)': [METRIC_DEFAULTS[review_metric]] * horizon,
            })
            edited = st.data_editor(
                assumption_frame,
                hide_index=True,
                num_rows='fixed',
                disabled=['예측 연도'],
                key=f'assumptions_{assumption_origin}_{horizon}',
                column_config={
                    f'{metric_name} (%)': st.column_config.NumberColumn(
                        min_value=-99.9 if review_metric in {'revenue_growth', 'operating_margin'} else 0.0,
                        max_value=300.0 if review_metric == 'revenue_growth' else 100.0,
                        step=0.5, format='%.1f%%',
                    ),
                },
            )
            multi_assumptions = {
                int(row['예측 연도']): float(row[f'{metric_name} (%)']) for _, row in edited.iterrows()
            }
            if review_metric == 'revenue_growth':
                st.caption('현재 매출 백테스트는 1년 예측만 검증합니다. 2~5년차는 참고 시나리오로 구분합니다.')
            else:
                st.caption(f'2~5년차 {metric_name}은 과거 분포를 연장한 참고 시나리오이며 지속성이 검증되지 않았습니다.')

    current_assumptions: float | dict[int, float] = multi_assumptions if use_multi_year else float(single_assumption)
    data_identity = (
        company_name,
        int(data['fiscal_year'].min()),
        int(data['fiscal_year'].max()),
        len(data),
        bool(mock),
        review_metric,
    )
    history_scope = data_identity[:-1]
    if st.session_state.get('review_history_scope') != history_scope:
        st.session_state['review_history_scope'] = history_scope
        st.session_state.pop('review_history', None)
    if st.button('가정 검토하기', type='primary', width='stretch'):
        st.session_state['submitted_review'] = {
            'data_identity': data_identity,
            'origin_year': int(assumption_origin),
            'assumptions': current_assumptions,
            'review_metric': review_metric,
        }

submitted = st.session_state.get('submitted_review')
if not submitted or submitted.get('data_identity') != data_identity or submitted.get('review_metric') != review_metric:
    st.info(f'{metric_name}을 입력한 뒤 **가정 검토하기**를 누르면 판정과 DCF 적용 시나리오가 표시됩니다.')
    st.stop()

submitted_origin = int(submitted['origin_year'])
submitted_assumptions = submitted['assumptions']
try:
    peer_benchmark = None
    ratio_stats = None
    if review_metric == 'revenue_growth':
        recommendation = evaluate_user_assumptions(
            data, results, submitted_origin, submitted_assumptions, peer_provider=peer_provider,
        )
        metadata = evaluation_metadata(data, submitted_origin)
        scenarios = build_scenario_table(
            recommendation,
            current_revenue_krw=metadata['current_revenue_krw'],
            origin_year=submitted_origin,
        )
        candidates = build_method_candidates(data, submitted_origin)
        positions = build_assumption_position(data, submitted_origin, submitted_assumptions)
        margin_stats = None
        peer_metric = 'revenue_growth'
    elif review_metric == 'operating_margin':
        recommendation = evaluate_operating_margin_assumptions(
            margin_data, submitted_origin, submitted_assumptions, peer_provider=peer_provider,
        )
        metadata = operating_margin_metadata(margin_data, submitted_origin)
        scenarios = build_operating_margin_scenario_table(recommendation, origin_year=submitted_origin)
        candidates = pd.DataFrame()
        positions = build_operating_margin_position(margin_data, submitted_origin, submitted_assumptions)
        margin_stats = operating_margin_statistics(margin_data, submitted_origin)
        peer_metric = 'operating_margin'
    else:
        evaluator = evaluate_nwc_assumptions if review_metric == 'nwc_ratio' else evaluate_capex_assumptions
        recommendation = evaluator(capital_data, submitted_origin, submitted_assumptions)
        metadata = capital_ratio_metadata(capital_data, submitted_origin)
        scenarios = build_capital_ratio_scenario_table(
            recommendation, origin_year=submitted_origin, metric=review_metric,
        )
        candidates = pd.DataFrame()
        positions = build_capital_ratio_position(
            capital_data, submitted_origin, submitted_assumptions, review_metric,
        )
        margin_stats = None
        ratio_stats = capital_ratio_statistics(capital_data, submitted_origin, review_metric)
        peer_metric = None
    if peer_metric is not None:
        assumption_values = (
            list(recommendation.user_assumption.values())
            if isinstance(recommendation.user_assumption, dict)
            else [float(recommendation.user_assumption)]
        )
        peer_benchmark = peer_provider.get_benchmark(
            company_name=metadata['company_name'], as_of_date=metadata['cutoff_date'],
            forecast_years=list(range(submitted_origin + 1, submitted_origin + 1 + len(assumption_values))),
            metric=peer_metric, user_values=assumption_values,
        )
except RecommendationError as exc:
    st.error(str(exc))
    st.stop()


# 3단계: 결론과 DCF 적용 제안
VERDICT_LABELS = {
    'retain': '유지 가능', 'adjust': '조정 검토', 'caution': '주의해서 사용', 'insufficient': '근거 부족',
}
CONFIDENCE_LABELS = {'high': '높음', 'medium': '보통', 'low': '낮음'}
STATUS_LABELS = {'active': '활성화됨', 'partial': '일부 적용', 'mocked': '모의', 'unconnected': '미연결'}

st.divider()
st.header('3. 검토 결과와 DCF 적용 제안')
if isinstance(recommendation.user_assumption, dict):
    assumption_metric = f'{len(recommendation.user_assumption)}개년 입력'
    base_values = list(recommendation.base_case.values())
    base_metric = f'{base_values[0]:.1f}%/년'
else:
    assumption_metric = f'{float(recommendation.user_assumption):.1f}%'
    base_metric = f'{float(recommendation.base_case):.1f}%'

verdict_cards = st.columns(5)
verdict_cards[0].metric('입력한 가정', assumption_metric)
verdict_cards[1].metric('판정 결과', VERDICT_LABELS[recommendation.verdict])
verdict_cards[2].metric(
    '과거 기반 권고 범위',
    f'{recommendation.suggested_range[0]:.1f}% ~ {recommendation.suggested_range[1]:.1f}%',
)
verdict_cards[3].metric('기본 시나리오', base_metric)
verdict_cards[4].metric('신뢰도', CONFIDENCE_LABELS[recommendation.confidence])
if review_metric == 'revenue_growth':
    st.caption(f"정보 기준일 {metadata['cutoff_date'].date().isoformat()} · 기준 매출 "
               f"{metadata['current_revenue_krw'] / 1e12:,.2f}조원")
elif review_metric == 'operating_margin':
    st.caption(f"정보 기준일 {metadata['cutoff_date'].date().isoformat()} · 최근 영업이익률 "
               f"{metadata['current_operating_margin_pct']:.2f}%")
else:
    current_key = 'current_nwc_ratio_pct' if review_metric == 'nwc_ratio' else 'current_capex_ratio_pct'
    st.caption(f"정보 기준일 {metadata['cutoff_date'].date().isoformat()} · 최근 {metric_name} "
               f"{metadata[current_key]:.2f}%")

interpretation = build_reviewer_interpretation(recommendation, review_metric)
if recommendation.verdict == 'retain':
    st.success('**한 줄 리뷰:** ' + interpretation)
elif recommendation.verdict in {'adjust', 'caution'}:
    st.warning('**한 줄 리뷰:** ' + interpretation)
else:
    st.info('**한 줄 리뷰:** ' + interpretation)

st.subheader('DCF에 적용할 3대 시나리오')
if review_metric == 'revenue_growth':
    scenario_display = build_dcf_scenario_display(scenarios, recommendation)
elif review_metric == 'operating_margin':
    scenario_display = build_operating_margin_scenario_display(scenarios, recommendation)
else:
    scenario_display = build_capital_ratio_scenario_display(scenarios, recommendation, review_metric)
scenario_config = {
    '권고 성장률 (%)': st.column_config.NumberColumn(format='%.1f%%'),
    '성장률 (%)': st.column_config.NumberColumn(format='%.1f%%'),
    '권고 영업이익률 (%)': st.column_config.NumberColumn(format='%.1f%%'),
    '영업이익률 (%)': st.column_config.NumberColumn(format='%.1f%%'),
    '권고 NWC/매출액 (%)': st.column_config.NumberColumn(format='%.1f%%'),
    'NWC/매출액 (%)': st.column_config.NumberColumn(format='%.1f%%'),
    '권고 CapEx/매출액 (%)': st.column_config.NumberColumn(format='%.1f%%'),
    'CapEx/매출액 (%)': st.column_config.NumberColumn(format='%.1f%%'),
    '예측 매출 (조원)': st.column_config.NumberColumn(format='%.3f'),
}
st.dataframe(scenario_display, hide_index=True, column_config=scenario_config, width='stretch')
st.caption('보수·기본·낙관은 정답이 아니라 현재 데이터에서 DCF 민감도를 점검하기 위한 적용 범위입니다.')

dcf_export = build_dcf_scenario_export(
    metric=review_metric,
    company_name=metadata['company_name'],
    cutoff_date=metadata['cutoff_date'],
    result=recommendation,
    scenario_table=scenarios,
)
markdown_report = build_markdown_report(
    metric=review_metric,
    company_name=metadata['company_name'],
    origin_year=submitted_origin,
    cutoff_date=metadata['cutoff_date'],
    result=recommendation,
    interpretation=interpretation,
)
review_history = st.session_state.setdefault('review_history', {})
review_history[review_metric] = {
    'result': recommendation.to_dict(),
    'markdown': markdown_report,
    'dcf_export': dcf_export,
}
integrated_csv = combine_dcf_scenario_exports([
    item['dcf_export'] for item in review_history.values()
])
integrated_markdown = build_integrated_markdown_report({
    metric: item['markdown'] for metric, item in review_history.items()
})
integrated_json = {
    'reviewed_metrics': list(review_history),
    'results': {metric: item['result'] for metric, item in review_history.items()},
}
download_left, download_middle, download_right = st.columns(3)
download_left.download_button(
    'DCF 통합 시나리오 CSV 다운로드', csv_bytes(integrated_csv),
    'dcf_four_assumptions_scenarios.csv', 'text/csv',
)
download_middle.download_button(
    '통합 검토 리포트 Markdown 다운로드', integrated_markdown.encode('utf-8-sig'),
    'dcf_assumptions_review.md', 'text/markdown',
)
download_right.download_button(
    '통합 검토 리포트 JSON 다운로드',
    json.dumps(integrated_json, ensure_ascii=False, indent=2),
    'dcf_assumptions_review.json',
    'application/json',
)
st.caption(f"현재 세션 통합 파일에 {len(review_history)}개 검토 항목이 포함되었습니다. 각 항목을 전환해 검토하면 누적됩니다.")


# 4단계: 판단 근거와 상세 분석
st.divider()
st.header('4. 왜 이렇게 판단했나요?')
if not positions.empty:
    if len(positions) == 1:
        position = positions.iloc[0]
        position_cards = st.columns(3)
        position_cards[0].metric(
            f'기업 과거 {metric_name} 분포 내 위치',
            f"{position['과거 분포 백분위 (%)']:.0f}백분위",
        )
        if review_metric == 'revenue_growth':
            position_cards[1].metric(
                '최근 실적 성장률과 차이',
                f"{position['최근 성장률 대비 (%p)']:+.1f}%p",
                help=f"최근 실적 성장률은 {position['최근 실적 성장률 (%)']:.1f}%입니다.",
            )
        elif review_metric == 'operating_margin':
            position_cards[1].metric(
                '최근 영업이익률과 차이',
                f"{position['최근 마진 대비 (%p)']:+.1f}%p",
                help=f"최근 영업이익률은 {position['최근 영업이익률 (%)']:.1f}%입니다.",
            )
        else:
            recent_column = f"최근 {CAPITAL_RATIO_CONFIG[review_metric]['value_column']}"
            position_cards[1].metric(
                '최근 비율과 차이',
                f"{position['최근 비율 대비 (%p)']:+.1f}%p",
                help=f"최근 비율은 {position[recent_column]:.1f}%입니다.",
            )
        peer_value = '자료 없음' if peer_benchmark is None or peer_benchmark.user_percentile is None else f'{peer_benchmark.user_percentile:.0f}백분위'
        position_cards[2].metric('동종기업 분포 내 위치', peer_value)
        if peer_benchmark is not None:
            st.caption('동종기업 위치는 SK하이닉스·TSMC 비검증 Mock 샘플에 대한 보조 지표입니다.')
        else:
            st.caption(f'{metric_name}의 동종기업 비교 데이터는 아직 연결되지 않았습니다.')
    else:
        st.subheader(f'연도별 {metric_name} 가정의 과거 분포 위치')
        st.dataframe(
            positions,
            hide_index=True,
            column_config={
                '입력 성장률 (%)': st.column_config.NumberColumn(format='%.1f%%'),
                '과거 분포 백분위 (%)': st.column_config.NumberColumn(format='%.0f'),
                '최근 실적 성장률 (%)': st.column_config.NumberColumn(format='%.1f%%'),
                '최근 성장률 대비 (%p)': st.column_config.NumberColumn(format='%+.1f'),
            },
            width='stretch',
        )
        if peer_benchmark is not None and peer_benchmark.user_percentile is not None:
            st.metric('다년도 평균 가정의 동종기업 분포 내 위치', f'{peer_benchmark.user_percentile:.0f}백분위')
            st.caption('동종기업 위치는 SK하이닉스·TSMC 비검증 Mock 샘플에 대한 보조 지표입니다.')

evidence_left, evidence_right = st.columns(2)
with evidence_left:
    st.subheader('이 가정을 지지하는 근거')
    if recommendation.supporting_evidence:
        for item in recommendation.supporting_evidence:
            st.markdown(f'- {item}')
    else:
        st.caption('확인된 찬성 근거가 없습니다.')
with evidence_right:
    st.subheader('주의하거나 충돌하는 근거')
    if recommendation.conflicting_evidence:
        for item in recommendation.conflicting_evidence:
            st.markdown(f'- {item}')
    else:
        st.caption('확인된 충돌 근거가 없습니다.')

st.subheader('아직 연결되지 않았거나 제한적인 근거')
provider_names = {'company': '기업 실적 검증', 'latest_disclosure': '최신 공시 근거', 'peer': '동종기업 비교'}
provider_table = pd.DataFrame([
    {'근거': provider_names.get(name, name), '현재 상태': STATUS_LABELS.get(status, status)}
    for name, status in recommendation.provider_status.items()
])
st.dataframe(provider_table, hide_index=True, width='stretch')
if recommendation.provider_status.get('peer') == 'active':
    st.caption('동종기업 비교: 활성화됨 · 현재 공급자는 SK하이닉스·TSMC 비검증 Mock 샘플입니다.')
for item in recommendation.data_warnings:
    st.warning(item)

with st.expander('왜 이런 결론이 나왔나요? (상세 분석)', expanded=False):
    st.caption('아래 내용은 판정의 계산 근거를 확인하려는 사용자를 위한 고급 분석입니다.')
    if review_metric == 'revenue_growth':
        method_tab, backtest_tab, performance_tab, evidence_tab, download_tab = st.tabs([
            '계산식·현재 후보', '예측 오차표·그래프', 'MAPE 분석', '공시·비교 가능성', '원본 다운로드',
        ])
        with method_tab:
            render_method_definitions()
            st.subheader('현재 기준일의 네 방식 후보')
            candidate_display = candidates.copy()
            candidate_display['예측 매출 (조원)'] = candidate_display['예측 매출 (원)'] / 1e12
            st.dataframe(
                candidate_display[['방식', '성장률 (%)', '예측 매출 (조원)', '상태', '사유', '계산식']],
                hide_index=True,
            )
        with backtest_tab:
            render_backtest_tab(data, results)
        with performance_tab:
            render_performance_tab(summary, common, split, mock)
        with evidence_tab:
            render_evidence_tab(data, results, source=source, csv_choice=csv_choice, root=ROOT)
        with download_tab:
            render_downloads_tab(data, results, summary, split)
    elif review_metric == 'operating_margin':
        distribution_tab, source_tab, rule_tab = st.tabs(['분포·변동성', '연도별 공식 자료', '판정 기준'])
        with distribution_tab:
            stat_cards = st.columns(4)
            stat_cards[0].metric('과거 평균', f"{margin_stats['mean']:.2f}%")
            stat_cards[1].metric('과거 중앙값', f"{margin_stats['median']:.2f}%")
            stat_cards[2].metric('표준편차', f"{margin_stats['stddev']:.2f}%p")
            stat_cards[3].metric('변동성 범주', margin_stats['volatility_category'])
            trend = margin_stats['snapshot'].set_index('fiscal_year')['operating_margin_pct']
            st.line_chart(trend)
            st.caption('영업이익률 = 연결 영업이익 ÷ 연결 매출 × 100')
        with source_tab:
            source_display = margin_stats['snapshot'].copy()
            source_display['영업이익률 (%)'] = source_display['operating_margin_pct']
            st.dataframe(
                source_display[[
                    'fiscal_year', 'publication_date', 'revenue_krw', 'operating_profit_krw',
                    '영업이익률 (%)', 'receipt_no', 'source_url', 'evidence_note',
                ]],
                hide_index=True,
            )
            st.download_button(
                '영업이익률 원본 CSV 다운로드', csv_bytes(margin_data),
                'samsung_operating_margin.csv', 'text/csv',
            )
        with rule_tab:
            st.write('권고 범위는 기준일까지 공개된 연간 영업이익률의 25%~75% 분위수입니다.')
            st.write('기본 시나리오는 중앙값, 보수·낙관 시나리오는 각각 25%·75% 분위수입니다.')
            st.write('표준편차가 3%p 미만이면 변동성 낮음, 3~7%p는 보통, 7%p 이상은 높음으로 분류합니다.')
            st.warning('이 평가는 분포 검토이며 영업이익률 예측 성능을 백테스트한 결과가 아닙니다.')
    else:
        distribution_tab, source_tab, rule_tab = st.tabs(['분포·추세', '연도별 공식 자료', '판정 기준'])
        ratio_config = CAPITAL_RATIO_CONFIG[review_metric]
        ratio_column = str(ratio_config['column'])
        value_column = str(ratio_config['value_column'])
        with distribution_tab:
            stat_cards = st.columns(4)
            stat_cards[0].metric('과거 평균', f"{ratio_stats['mean']:.2f}%")
            stat_cards[1].metric('과거 중앙값', f"{ratio_stats['median']:.2f}%")
            stat_cards[2].metric('표준편차', f"{ratio_stats['stddev']:.2f}%p")
            stat_cards[3].metric('변동성 범주', ratio_stats['volatility_category'])
            trend = ratio_stats['snapshot'].set_index('fiscal_year')[ratio_column]
            st.line_chart(trend)
            if review_metric == 'capex_ratio' and ratio_stats['trend_change_pp'] is not None:
                st.caption(f"최근 비율은 2년 전보다 {ratio_stats['trend_change_pp']:+.2f}%p 변했습니다.")
            st.caption(str(ratio_config['definition']) + ' · 같은 연도 연결 매출로 나눈 비율')
        with source_tab:
            source_display = ratio_stats['snapshot'].copy()
            source_display[value_column] = source_display[ratio_column]
            component_columns = (
                ['trade_receivables_krw', 'inventories_krw', 'trade_payables_krw', 'nwc_krw']
                if review_metric == 'nwc_ratio'
                else ['ppe_acquisition_krw', 'intangible_acquisition_krw', 'capex_krw']
            )
            st.dataframe(
                source_display[[
                    'fiscal_year', 'publication_date', 'revenue_krw', *component_columns,
                    value_column, 'receipt_no', 'source_url', 'comparability_note', 'evidence_note',
                ]],
                hide_index=True,
            )
            st.download_button(
                'NWC·CapEx 원본 CSV 다운로드', csv_bytes(capital_data),
                'samsung_nwc_capex.csv', 'text/csv',
            )
        with rule_tab:
            st.write(f"{ratio_config['definition']}으로 계산합니다.")
            st.write(f'권고 범위는 기준일까지 공개된 연간 {metric_name}의 25%~75% 분위수입니다.')
            st.write('기본 시나리오는 중앙값입니다. 비율 상승은 FCFF 부담이므로 보수는 75%, 낙관은 25% 분위수입니다.')
            st.write('표준편차가 2%p 미만이면 변동성 낮음, 2~5%p는 보통, 5%p 이상은 높음으로 분류합니다.')
            st.warning(f'이 평가는 분포 검토이며 {metric_name}의 예측 성능을 백테스트한 결과가 아닙니다.')
