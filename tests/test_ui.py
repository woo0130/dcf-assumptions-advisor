from pathlib import Path

from streamlit.testing.v1 import AppTest


APP = str(Path(__file__).resolve().parents[1] / 'app.py')


def _button(app: AppTest, label: str):
    return next(button for button in app.button if button.label == label)


def test_reviewer_landing_page_leads_with_data_and_question():
    app = AppTest.from_file(APP).run(timeout=30)

    assert not app.exception
    assert not app.error
    assert app.title[0].value == '내 DCF 가정, 데이터로 검토받으세요'
    assert [item.value for item in app.header] == [
        '1. 분석할 기업 자료를 확인하세요',
        '2. 검토할 매출 성장률을 입력하세요',
    ]
    assert any('삼성전자 2015~2025년 연결 매출 데이터를 확인했습니다' in item.value
               for item in app.success)
    assert any('삼성전자의 2026년 매출 성장률을 몇 %로 가정하셨나요?' in item.value
               for item in app.subheader)
    assert app.number_input[0].label == '내 DCF 매출 성장률 (%)'
    assert app.number_input[0].value == 6.0
    assert any(button.label == '가정 검토하기' for button in app.button)
    assert not any(metric.label == '판정 결과' for metric in app.metric)
    assert any('가정 검토하기' in item.value for item in app.info)


def test_official_six_percent_review_shows_immediate_verdict_and_scenarios():
    app = AppTest.from_file(APP).run(timeout=30)
    _button(app, '가정 검토하기').click().run(timeout=30)

    assert not app.exception
    assert any(item.value == '3. 검토 결과와 DCF 적용 제안' for item in app.header)
    assert any(item.value == '4. 왜 이렇게 판단했나요?' for item in app.header)
    assert any(metric.label == '입력한 가정' and metric.value == '6.0%' for metric in app.metric)
    assert any(metric.label == '판정 결과' and metric.value == '주의해서 사용' for metric in app.metric)
    assert any(metric.label == '과거 기반 권고 범위' and metric.value == '0.9% ~ 14.9%'
               for metric in app.metric)
    assert any(metric.label == '기본 시나리오' and metric.value == '5.4%' for metric in app.metric)
    assert any(metric.label == '신뢰도' and metric.value == '낮음' for metric in app.metric)
    assert any('6.0%는 과거 성장률 범위 안' in item.value and '6.0%를 그대로 채택' in item.value
               for item in app.warning)
    assert any(metric.label == '기업 과거 매출 성장률 분포 내 위치' and metric.value == '50백분위'
               for metric in app.metric)
    assert any('동종기업 비교: 활성화됨' in item.value for item in app.caption)
    assert any('비검증 Mock' in item.value for item in app.warning)
    assert any('15.56%' in item.value and '13.49%' in item.value for item in app.markdown)


def test_csv_mock_workflow_is_clearly_labelled():
    app = AppTest.from_file(APP).run(timeout=30)
    app.selectbox[0].set_value('모의 데이터 (2015~2024)').run(timeout=30)

    assert not app.exception
    assert any('삼성전자 (모의 데이터) 2015~2024년 연결 매출 데이터를 확인했습니다' in item.value
               for item in app.success)
    assert any('모의 데이터입니다' in item.value for item in app.error)
    _button(app, '가정 검토하기').click().run(timeout=30)
    assert not app.exception
    assert any(metric.label == '판정 결과' for metric in app.metric)
    assert any('7개 미만' in item.value for item in list(app.markdown) + list(app.warning))


def test_missing_api_key_is_actionable(monkeypatch):
    monkeypatch.delenv('DART_API_KEY', raising=False)
    app = AppTest.from_file(APP).run(timeout=30)
    app.radio[0].set_value('OpenDART').run(timeout=30)
    _button(app, '연간 연결 매출 수집').click().run(timeout=30)

    assert not app.exception
    assert any('키가 없습니다' in item.value for item in app.error)


def test_multi_year_editor_is_hidden_until_enabled_and_reviews_five_years():
    app = AppTest.from_file(APP).run(timeout=30)
    assert len(app.slider) == 0
    assert len(app.dataframe) == 0

    app.checkbox[0].set_value(True).run(timeout=30)
    assert not app.exception
    assert app.slider[0].min == 3 and app.slider[0].max == 5 and app.slider[0].value == 5
    assert len(app.dataframe) == 1
    _button(app, '가정 검토하기').click().run(timeout=30)

    assert not app.exception
    assert any(metric.label == '입력한 가정' and metric.value == '5개년 입력' for metric in app.metric)
    assert any('1년 예측만 검증' in item.value for item in app.warning)


def test_operating_margin_reviewer_flow_and_peer_position():
    app = AppTest.from_file(APP).run(timeout=30)
    app.radio[1].set_value('영업이익률').run(timeout=30)

    assert not app.exception
    assert any(item.value == '2. 검토할 영업이익률을 입력하세요' for item in app.header)
    assert app.number_input[0].label == '내 DCF 영업이익률 (%)'
    assert app.number_input[0].value == 12.0
    assert any('연결 영업이익률 데이터를 확인했습니다' in item.value for item in app.success)

    _button(app, '가정 검토하기').click().run(timeout=30)

    assert not app.exception
    assert any(metric.label == '판정 결과' and metric.value == '조정 검토' for metric in app.metric)
    assert any(metric.label == '과거 기반 권고 범위' and metric.value == '12.6% ~ 16.8%'
               for metric in app.metric)
    assert any(metric.label == '기본 시나리오' and metric.value == '14.4%' for metric in app.metric)
    assert any(metric.label == '동종기업 분포 내 위치' and metric.value == '10백분위'
               for metric in app.metric)
    assert any(metric.label == '표준편차' and metric.value == '5.81%p' for metric in app.metric)
    assert any('분포·변동성 검토' in item.value for item in app.warning)
    assert any('동종기업 비교: 활성화됨' in item.value for item in app.caption)


def test_nwc_reviewer_flow_uses_cashflow_direction():
    app = AppTest.from_file(APP).run(timeout=30)
    app.radio[1].set_value('순운전자본(NWC)').run(timeout=30)

    assert not app.exception
    assert any(item.value == '2. 검토할 매출액 대비 NWC 비율을 입력하세요' for item in app.header)
    assert any('삼성전자의 2026년 매출액 대비 NWC 비율을 몇 %로 가정하셨나요?' in item.value
               for item in app.subheader)
    assert app.number_input[0].value == 15.0
    _button(app, '가정 검토하기').click().run(timeout=30)

    assert not app.exception
    assert any(metric.label == '판정 결과' and metric.value == '조정 검토' for metric in app.metric)
    assert any(metric.label == '과거 기반 권고 범위' and metric.value == '20.6% ~ 26.4%'
               for metric in app.metric)
    assert any(metric.label == '기본 시나리오' and metric.value == '23.1%' for metric in app.metric)
    assert any('비율이 높을수록 FCFF' in item.value for item in app.warning)
    assert any('동종기업 비교 데이터는 아직 연결되지 않았습니다' in item.value for item in app.caption)


def test_capex_reviewer_flow_and_integrated_downloads():
    app = AppTest.from_file(APP).run(timeout=30)
    app.radio[1].set_value('설비투자(CapEx)').run(timeout=30)

    assert not app.exception
    assert any('삼성전자의 2026년 매출액 대비 CapEx 비율을 몇 %로 가정하셨나요?' in item.value
               for item in app.subheader)
    assert app.number_input[0].value == 12.0
    _button(app, '가정 검토하기').click().run(timeout=30)

    assert not app.exception
    assert any(metric.label == '과거 기반 권고 범위' and metric.value == '13.1% ~ 17.8%'
               for metric in app.metric)
    assert any(metric.label == '기본 시나리오' and metric.value == '17.0%' for metric in app.metric)
    labels = [button.label for button in app.get('download_button')]
    assert 'DCF 통합 시나리오 CSV 다운로드' in labels
    assert '통합 검토 리포트 Markdown 다운로드' in labels
    assert '통합 검토 리포트 JSON 다운로드' in labels
