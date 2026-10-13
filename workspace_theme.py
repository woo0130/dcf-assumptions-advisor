"""KIC RESEARCH-inspired local research workspace presentation layer."""
from html import escape
import streamlit as st

STEPS = ['기업 선택', '계정 입력', '계정 분석', '관련 이슈', '가설 제공', '미래 가이던스']
CSS = '''<style>
:root {--forest:#1C3527;--sand:#FAF9F5;--line:#DBDFD2;--muted:#7D8779;--gold:#B5A77A;}
.stApp, [data-testid="stAppViewContainer"], [data-testid="stMain"] {background:var(--sand);color:var(--forest);}
[data-testid="stHeader"] {background:var(--sand);}
[data-testid="stMainBlockContainer"] {max-width:1440px;padding:2.5rem 3rem 3rem;}
[data-testid="stSidebar"] {background:var(--forest);border-right:1px solid #385040;}
[data-testid="stSidebar"] *, [data-testid="stSidebar"] label {color:#EAEBDD;}
[data-testid="stSidebar"] [data-baseweb="select"] * {color:var(--forest);}
[data-testid="stSidebar"] button {background:#324838!important;color:#FAF9F5!important;border-color:#61725B!important;}
h1,h2,h3 {color:var(--forest)!important;letter-spacing:-.035em;font-weight:500!important;}
h1 {font-size:2.6rem!important;} h2 {font-size:1.65rem!important;} h3 {font-size:1.12rem!important;}
[data-testid="stCaptionContainer"] {color:var(--muted);}
[data-testid="stVerticalBlockBorderWrapper"] > div {border-color:var(--line)!important;border-radius:3px!important;box-shadow:none!important;}
[data-testid="stMetric"] {background:#FFFFFF;border:1px solid var(--line);padding:1.1rem 1.2rem;min-height:128px;border-radius:3px;box-shadow:none;}
[data-testid="stMetricLabel"] {color:var(--muted);font-size:.8rem;}
[data-testid="stMetricValue"] {color:var(--forest);font-size:2rem;letter-spacing:-.04em;}
[data-testid="stMetricDelta"] {color:#677D55;font-size:.8rem;}
.stButton button, .stDownloadButton button {border:1px solid #CCD3C0;border-radius:3px;box-shadow:none;color:var(--forest);background:#FFFFFF;min-height:42px;}
.stButton button[kind="primary"], .stDownloadButton button[kind="primary"] {background:var(--forest);color:#FFFFFF;border-color:var(--forest);}
.stButton button:disabled {opacity:.45;} .stButton button:hover {border-color:#738764;background:#EDF0E6;}
.stButton button[kind="primary"]:hover {background:#304D38;color:white;}
[data-baseweb="input"], [data-baseweb="select"] > div, [data-baseweb="textarea"] {border-color:var(--line)!important;border-radius:3px;background:#FFFFFF;box-shadow:none!important;}
[data-testid="stAlert"] {border:1px solid var(--line);border-radius:3px;box-shadow:none;}
[data-testid="stTabs"] [data-baseweb="tab-list"] {gap:1.5rem;border-bottom:1px solid var(--line);}
[data-testid="stTabs"] [aria-selected="true"] {color:var(--forest);font-weight:600;}
[data-baseweb="tab-highlight"] {background:#738764;}
[data-testid="stExpander"] {background:#FFFFFF;border:1px solid var(--line);border-radius:3px;}
hr {border-color:var(--line)!important;}
.ws-top {display:flex;justify-content:space-between;color:#8C947D;font-size:.65rem;letter-spacing:.18em;padding-bottom:1.4rem;}
.ws-stepper {display:grid;grid-template-columns:repeat(6,1fr);border-top:1px solid var(--line);border-bottom:1px solid var(--line);margin-bottom:2rem;}
.ws-step {padding:1rem .3rem;display:flex;align-items:center;gap:.55rem;color:#939A8D;font-size:.76rem;border-bottom:2px solid transparent;}
.ws-step.active {color:var(--forest);border-bottom-color:#70815C;}
.ws-step.done {color:#6D7C5E;}
.ws-num {border:1px solid var(--line);border-radius:50%;width:25px;height:25px;display:inline-flex;align-items:center;justify-content:center;font-size:.65rem;}
.active .ws-num {background:var(--forest);color:white;border-color:var(--forest);}
.ws-hero {display:flex;justify-content:space-between;align-items:center;margin-bottom:1.7rem;gap:1rem;}
.ws-eyebrow {font-size:.63rem;letter-spacing:.18em;color:#8B967B;margin-bottom:.6rem;}
.ws-hero h1 {margin:0;line-height:1.3;} .ws-hero p {color:#7C8677;font-size:.88rem;margin:.7rem 0 0;}
.ws-count {font-family:Georgia,serif;color:#CCD2BC;font-size:3.1rem;white-space:nowrap;} .ws-count small {font-family:Arial,sans-serif;font-size:.7rem;}
.ws-brand {font-family:Georgia,serif;font-size:2.5rem;line-height:1.2;color:#F1E9C7;}
.ws-brand small {display:block;font-family:Arial,sans-serif;font-size:.6rem;letter-spacing:.35em;margin-top:.4rem;color:#CDBE87;}
.ws-motto {font-family:Georgia,serif;font-size:1.8rem;font-weight:300;line-height:1.3;color:#E9E2BB;padding-top:2rem;}
.ws-motto em {color:#BDAB74;}
.ws-context {border:1px solid var(--line);background:#F0F3E9;padding:.8rem 1rem;margin-bottom:1.4rem;color:#697A59;font-size:.82rem;}
.ws-card {background:#FFFFFF;border:1px solid var(--line);padding:1.3rem;border-radius:3px;min-height:126px;}
.ws-card-label {font-size:.72rem;color:#87917D;} .ws-card-value {font-size:2rem;color:var(--forest);margin:.45rem 0;letter-spacing:-.04em;}
.ws-card-detail {font-size:.75rem;color:#7F8978;line-height:1.5;}
@media(max-width:900px) {[data-testid="stMainBlockContainer"] {padding:1.5rem 1rem;} .ws-stepper {grid-template-columns:repeat(3,1fr);} .ws-step {font-size:.7rem;} .ws-count {font-size:2rem;} .ws-hero h1 {font-size:1.9rem!important;}}
</style>'''


def apply_theme():
    st.markdown(CSS, unsafe_allow_html=True)


def render_sidebar():
    with st.sidebar:
        st.markdown('<div class="ws-brand">KIC<small>RESEARCH</small></div>', unsafe_allow_html=True)
        st.caption('공모전 프로토타입 · DCF ASSUMPTIONS ADVISOR')
        st.divider()
        st.caption('YOUR RESEARCH')
        step = st.selectbox('분석 워크스페이스', range(6), index=None if 'workspace_nav' in st.session_state else 0,
                            format_func=lambda i: f'{i+1:02d}  {STEPS[i]}', key='workspace_nav')
        st.session_state['workspace_step'] = step
        if st.button('새로운 분석 시작', key='workspace_reset', use_container_width=True):
            for key in ['workspace_context', 'submitted_review', 'dart_data']:
                st.session_state.pop(key, None)
            # Widget changes are applied on the next run before widget creation.
            st.session_state['workspace_requested_step'] = 0
            st.rerun()
        st.divider()
        st.markdown('<div class="ws-motto">Clarity<br>before<br><em>conviction.</em></div>', unsafe_allow_html=True)
        st.caption('공시부터 계산 근거까지, 검토 과정을 확인합니다.')
    return step


def render_header(step):
    st.markdown('<div class="ws-top"><span>THE RESEARCH WORKSPACE</span><span>DCF / FINANCIAL RESEARCH</span></div>', unsafe_allow_html=True)
    chunks = []
    for i, label in enumerate(STEPS):
        cls = 'active' if i == step else ''
        # Only selection/data loading is confirmed; navigation does not imply completion.
        chunks.append(f'<div class="ws-step {cls}"><span class="ws-num">{i+1:02d}</span>{escape(label)}</div>')
    st.markdown('<div class="ws-stepper">'+''.join(chunks)+'</div>', unsafe_allow_html=True)
    headings = [
        ('숫자를 넘어, 기업의 맥락을 읽다.', '삼성전자 연간 연결 매출 자료를 선택하고 검토를 시작하세요.'),
        ('좋은 분석은, 좋은 질문에서.', '매출 성장률 가정과 기준 회계연도를 입력하세요.'),
        ('변화의 흐름을 읽습니다.', '과거 매출 추이와 예측 방식의 성능을 확인하세요.'),
        ('숫자에 맥락을 더합니다.', '공시 출처와 비교 가능성에 영향을 주는 사항을 확인하세요.'),
        ('가능한 가정을 비교합니다.', '과거 분포 기반 참고 시나리오와 한계를 검토하세요.'),
        ('다음 공시에서, 무엇을 볼까요?', '검토를 이어갈 확인 질문을 정리합니다.'),
    ]
    title, detail = headings[step]
    st.markdown(f'<div class="ws-hero"><div><div class="ws-eyebrow">STEP {step+1:02d} · RESEARCH</div><h1>{escape(title)}</h1><p>{escape(detail)}</p></div><div class="ws-count">{step+1:02d} <small>/ 06</small></div></div>', unsafe_allow_html=True)


def context_strip(context):
    data = context['data']
    company = str(data.iloc[0]['company_name'])
    years = f"{int(data.fiscal_year.min())}–{int(data.fiscal_year.max())}"
    st.markdown(f'<div class="ws-context">{escape(company)}　 /　 {years}　 /　 연간 연결재무제표　 /　 KRW</div>', unsafe_allow_html=True)


def metric_card(label, value, detail):
    st.markdown(f'<div class="ws-card"><div class="ws-card-label">{escape(label)}</div><div class="ws-card-value">{escape(value)}</div><div class="ws-card-detail">{escape(detail)}</div></div>', unsafe_allow_html=True)


def render_navigation(step, ready):
    st.divider()
    left, mid, right = st.columns([1, 3, 1])
    with left:
        if st.button('← 이전 단계', disabled=step == 0, use_container_width=True, key='workspace_previous'):
            st.session_state['workspace_requested_step'] = step - 1
            st.rerun()
    with mid:
        st.caption('과거 분포 기반 참고 분석 · 최근 공시 근거 확인 후 사용하세요.')
    with right:
        if st.button('다음 단계 →', type='primary', disabled=step == 5 or not ready, use_container_width=True, key='workspace_next'):
            st.session_state['workspace_requested_step'] = step + 1
            st.rerun()
