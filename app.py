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
    RecommendationError,
    available_origin_years,
    build_method_candidates,
    build_scenario_table,
    evaluate_user_assumptions,
    evaluation_metadata,
)
from revenue_agent.schema import DataError, normalize, read_csv
from revenue_agent.ui_sections import (
    build_assumption_position,
    build_dcf_scenario_display,
    build_reviewer_interpretation,
    csv_bytes,
    data_context_message,
    render_backtest_tab,
    render_downloads_tab,
    render_evidence_tab,
    render_method_definitions,
    render_performance_tab,
)


from revenue_agent.ui_review_updates import (
    render_peer_notice, render_uncertainty_notice, render_net_debt_information,
    prepare_scenario_display,
)

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / '.env', override=False)
st.set_page_config(page_title='DCF 가정 리뷰어', layout='wide')
st.title('내 DCF 가정, 데이터로 검토받으세요')
st.write('기업의 과거 실적과 시간순 백테스트를 바탕으로 입력한 매출 성장률이 합리적인지 검토하고, '
         '과거 분포에 따른 보수·기준·낙관 참고 시나리오와 불확실성을 확인합니다.')
st.caption('현재 검토 범위: 연간 연결 매출 · 금액 표시: 조원(KRW) · 투자 의견이나 미래 실적 보장이 아닙니다.')


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
render_net_debt_information(str(data.iloc[0]['company_name']))

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


# 2단계: 질문형 가정 입력
st.divider()
st.header('2. 검토할 매출 성장률을 입력하세요')
origin_years = available_origin_years(data)
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
    st.subheader(f'{company_name}의 {target_year}년 매출 성장률을 몇 %로 가정하셨나요?')
    single_assumption = st.number_input(
        '내 DCF 매출 성장률 (%)', min_value=-99.9, max_value=300.0,
        value=6.0, step=0.5, format='%.1f',
    )

    use_multi_year = False
    multi_assumptions: dict[int, float] = {}
    with st.expander('3~5개년 직접 입력', expanded=False):
        use_multi_year = st.checkbox('다년도 가정으로 검토하기', value=False)
        if use_multi_year:
            horizon = st.slider('예측 연수', min_value=3, max_value=5, value=5, step=1)
            assumption_frame = pd.DataFrame({
                '예측 연도': list(range(target_year, target_year + horizon)),
                '성장률 (%)': [6.0] * horizon,
            })
            edited = st.data_editor(
                assumption_frame,
                hide_index=True,
                num_rows='fixed',
                disabled=['예측 연도'],
                key=f'assumptions_{assumption_origin}_{horizon}',
                column_config={
                    '성장률 (%)': st.column_config.NumberColumn(
                        min_value=-99.9, max_value=300.0, step=0.5, format='%.1f%%',
                    ),
                },
            )
            multi_assumptions = {
                int(row['예측 연도']): float(row['성장률 (%)']) for _, row in edited.iterrows()
            }
            st.caption('현재 백테스트는 1년 예측만 검증합니다. 2~5년차는 참고 시나리오로 구분합니다.')

    current_assumptions: float | dict[int, float] = multi_assumptions if use_multi_year else float(single_assumption)
    data_identity = (
        company_name,
        int(data['fiscal_year'].min()),
        int(data['fiscal_year'].max()),
        len(data),
        bool(mock),
    )
    if st.button('가정 검토하기', type='primary', width='stretch'):
        st.session_state['submitted_review'] = {
            'data_identity': data_identity,
            'origin_year': int(assumption_origin),
            'assumptions': current_assumptions,
        }

submitted = st.session_state.get('submitted_review')
if not submitted or submitted.get('data_identity') != data_identity:
    st.info('성장률을 입력한 뒤 **가정 검토하기**를 누르면 판정과 DCF 적용 시나리오가 표시됩니다.')
    st.stop()

submitted_origin = int(submitted['origin_year'])
submitted_assumptions = submitted['assumptions']
try:
    recommendation = evaluate_user_assumptions(data, results, submitted_origin, submitted_assumptions)
    metadata = evaluation_metadata(data, submitted_origin)
    scenarios = build_scenario_table(
        recommendation,
        current_revenue_krw=metadata['current_revenue_krw'],
        origin_year=submitted_origin,
    )
    candidates = build_method_candidates(data, submitted_origin)
    positions = build_assumption_position(data, submitted_origin, submitted_assumptions)
except RecommendationError as exc:
    st.error(str(exc))
    st.stop()


# 3단계: 결론과 DCF 적용 제안
VERDICT_LABELS = {
    'retain': '유지 가능', 'adjust': '조정 검토', 'caution': '주의해서 사용', 'insufficient': '근거 부족',
}
CONFIDENCE_LABELS = {'high': '높음', 'medium': '보통', 'low': '낮음'}
STATUS_LABELS = {'active': '활성', 'partial': '일부 적용', 'mocked': '모의', 'unconnected': '미연결'}

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
    '과거 성장률 참고 구간 (Q25~Q75)',
    f'{recommendation.suggested_range[0]:.1f}% ~ {recommendation.suggested_range[1]:.1f}%',
)
verdict_cards[3].metric('과거 성장률 중앙값 (Base Estimate)', base_metric)
verdict_cards[4].metric('신뢰도', CONFIDENCE_LABELS[recommendation.confidence])
st.caption(f"정보 기준일 {metadata['cutoff_date'].date().isoformat()} · 기준 매출 "
           f"{metadata['current_revenue_krw'] / 1e12:,.2f}조원")

interpretation = build_reviewer_interpretation(recommendation)
if recommendation.verdict == 'retain':
    st.success('**한 줄 리뷰:** ' + interpretation)
elif recommendation.verdict in {'adjust', 'caution'}:
    st.warning('**한 줄 리뷰:** ' + interpretation)
else:
    st.info('**한 줄 리뷰:** ' + interpretation)

render_uncertainty_notice(recommendation)
st.subheader('과거 분포 기반 참고 시나리오')
scenario_display = prepare_scenario_display(build_dcf_scenario_display(scenarios, recommendation))
scenario_config = {
    '참고 성장률 (%)': st.column_config.NumberColumn(format='%.1f%%'),
    '성장률 (%)': st.column_config.NumberColumn(format='%.1f%%'),
    '예측 매출 (조원)': st.column_config.NumberColumn(format='%.3f'),
}
st.dataframe(scenario_display, hide_index=True, column_config=scenario_config, width='stretch')
st.caption('보수(Q25)·기준(중앙값)·낙관(Q75)은 과거 분포의 위치입니다. 미래 예측 확률이나 권고값을 뜻하지 않습니다.')

export = prepare_scenario_display(scenarios)
export['예측 매출 (조원)'] = export['예측 매출 (원)'] / 1e12
export.insert(0, '기업', metadata['company_name'])
export.insert(1, '정보 기준일', metadata['cutoff_date'].date().isoformat())
export['verdict'] = recommendation.verdict
export['confidence'] = recommendation.confidence
download_left, download_right = st.columns(2)
download_left.download_button('가정 시나리오 CSV 다운로드', csv_bytes(export),
                              'revenue_assumption_scenarios.csv', 'text/csv')
download_right.download_button(
    '검토 리포트 JSON 다운로드',
    json.dumps(recommendation.to_dict(), ensure_ascii=False, indent=2),
    'revenue_assumption_review.json',
    'application/json',
)


# 4단계: 판단 근거와 상세 분석
st.divider()
st.header('4. 왜 이렇게 판단했나요?')
if not positions.empty:
    if len(positions) == 1:
        position = positions.iloc[0]
        position_cards = st.columns(2)
        position_cards[0].metric('과거 성장률 분포 내 위치', f"{position['과거 분포 백분위 (%)']:.0f}백분위")
        position_cards[1].metric(
            '최근 실적 성장률과 차이',
            f"{position['최근 성장률 대비 (%p)']:+.1f}%p",
            help=f"최근 실적 성장률은 {position['최근 실적 성장률 (%)']:.1f}%입니다.",
        )
    else:
        st.subheader('연도별 가정의 과거 분포 위치')
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

render_peer_notice(metadata['company_name'], recommendation.provider_status.get('peer', 'unconnected'))
st.subheader('아직 연결되지 않았거나 제한적인 근거')
provider_names = {'company': '기업 실적 검증', 'latest_disclosure': '최신 공시 근거', 'peer': 'Peer 벤치마크'}
provider_table = pd.DataFrame([
    {'근거': provider_names.get(name, name), '현재 상태': STATUS_LABELS.get(status, status)}
    for name, status in recommendation.provider_status.items()
])
st.dataframe(provider_table, hide_index=True, width='stretch')
for item in recommendation.data_warnings:
    st.warning(item)

with st.expander('왜 이런 결론이 나왔나요? (상세 분석)', expanded=False):
    st.caption('아래 내용은 판정의 계산 근거를 확인하려는 사용자를 위한 고급 분석입니다.')
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
