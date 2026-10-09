"""Presentation additions; independent of revenue recommendation calculations."""
import math
import pandas as pd
import streamlit as st


def prepare_scenario_display(frame):
    result = frame.copy().rename(columns={'권고 성장률 (%)': '참고 성장률 (%)'})
    if '시나리오' in result:
        result['시나리오'] = result['시나리오'].replace({'기본': '기준'})
    return result


def render_peer_notice(company_name, status='unconnected'):
    st.subheader('동종기업 비교 (Peer Benchmarking)')
    if status == 'unconnected':
        st.info(f'동종기업 비교는 현재 미지원이며, {company_name} 자체 과거 실적을 기준으로 분석합니다.')
    else:
        st.caption('과거 성장률 참고 구간은 기업 자체 실적에서 계산합니다. 동종기업 근거는 별도로 확인하세요.')


def render_uncertainty_notice(recommendation):
    st.info('참고 구간은 과거 연도별 성장률의 Q25~Q75, 기준값은 중앙값입니다. '
            '통계적 신뢰구간이나 미래 예측구간이 아니며, 중앙값은 미래 성장률의 정답이 아닙니다. '
            '백테스트 오차·동종기업 전망은 이 구간 계산에 반영되지 않습니다.')
    st.caption('보수·기준·낙관은 과거 분포 기반 민감도 시나리오입니다. '
               '최근 사업 변화와 공시 근거를 확인한 후 가정을 선택하세요.')
    if recommendation.verdict == 'insufficient':
        st.warning('평가 근거가 부족합니다. 아래 수치는 과거 분포 참고값이며 적용 권고를 보류합니다.')
    if isinstance(recommendation.base_case, dict):
        st.warning('다년도 시나리오는 동일한 과거 분위수를 매년 반복 적용합니다. '
                   '2~5년차 성장률과 누적 예측 오차는 검증되지 않았습니다.')


def calculate_net_debt(borrowings, bonds, leases, cash):
    values = [borrowings, bonds, leases, cash]
    if any(not math.isfinite(float(x)) or float(x) < 0 for x in values):
        raise ValueError('금액은 유한한 0 이상의 값이어야 합니다.')
    debt = float(borrowings) + float(bonds) + float(leases)
    return debt, debt - float(cash)


def render_net_debt_information(company_name):
    with st.expander('기업 기본정보: 순부채 구성', expanded=True):
        st.caption('단순 순부채 = 차입금 + 사채 + 리스부채 − 현금및현금성자산. '
                   '매출 가정 판정·백테스트·신뢰도 산출에 반영하지 않습니다. '
                   '단기금융상품은 현금에 포함하지 않습니다.')
        confirmed = st.checkbox('같은 기업·결산일의 연결 금액과 출처를 확인하여 직접 입력', key='net_debt_confirmed')
        if not confirmed:
            st.dataframe(pd.DataFrame({'항목': ['차입금', '사채', '리스부채', '이자발생부채 합계', '현금및현금성자산', '순부채 / 순현금'],
                                       '금액': ['자료 미확보'] * 6}), hide_index=True)
            st.info('첨부 매출 CSV에는 부채·현금 자료가 없습니다. 미확보 금액은 0으로 간주하지 않습니다.')
            return
        st.caption(f'입력 기업: {company_name} · 연결 기준 · 유동·비유동 합산 · 금액 단위: 억원')
        period = st.date_input('순부채 결산일', key='net_debt_period')
        source = st.text_input('공시 / 출처 URL 또는 문서명', key='net_debt_source')
        st.caption('차입금 입력에서 사채와 리스부채를 제외하여 중복 합산을 방지하세요.')
        amounts = [st.number_input(label + ' (억원)', min_value=0.0, value=None, step=1.0, key='net_debt_' + key)
                   for label, key in [('차입금', 'borrowings'), ('사채', 'bonds'), ('리스부채', 'leases'), ('현금및현금성자산', 'cash')]]
        if not source.strip() or any(value is None for value in amounts):
            st.info('네 항목 모두와 출처를 입력하면 합계와 순부채를 표시합니다. 실제 0원인 항목은 0을 입력하세요.')
            return
        try:
            debt, net = calculate_net_debt(*amounts)
        except ValueError as exc:
            st.error(str(exc))
            return
        label = '순현금' if net < 0 else '순부채'
        rows = [('차입금', amounts[0]), ('사채', amounts[1]), ('리스부채', amounts[2]),
                ('이자발생부채 합계', debt), ('현금및현금성자산', amounts[3]), (label, abs(net))]
        st.dataframe(pd.DataFrame(rows, columns=['항목', '금액 (억원)']), hide_index=True)
        st.caption(f'사용자 입력 자료 · 결산일 {period.isoformat()} · 출처: {source}')
