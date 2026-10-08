from pathlib import Path

import pandas as pd
import pytest

from revenue_agent.backtest import run_backtest
from revenue_agent.recommendation import (
    build_operating_margin_scenario_table,
    build_scenario_table,
    evaluate_operating_margin_assumptions,
    evaluate_user_assumptions,
    evaluation_metadata,
)
from revenue_agent.schema import normalize, read_csv
from revenue_agent.ui_sections import (
    build_assumption_position,
    build_dcf_scenario_display,
    build_operating_margin_position,
    build_operating_margin_scenario_display,
    build_reviewer_interpretation,
    data_context_message,
)


ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def official_review():
    data = normalize(read_csv(ROOT / 'data/samsung_official_revenue.csv')).data
    result = evaluate_user_assumptions(data, run_backtest(data), 2025, 6.0)
    return data, result


def test_reviewer_copy_leads_with_user_assumption(official_review):
    _, result = official_review
    text = build_reviewer_interpretation(result)

    assert text == (
        '6.0%는 과거 성장률 범위 안에 있어 과도한 가정은 아닙니다. '
        '다만 과거 백테스트에서 성장률 기반 예측이 매출 유지 기준보다 나빴기 때문에, '
        '6.0%를 그대로 채택하기보다 보수 시나리오와 함께 사용하는 것이 적절합니다.'
    )


def test_assumption_position_uses_as_of_growth_distribution(official_review):
    data, _ = official_review
    position = build_assumption_position(data, 2025, 6.0).iloc[0]

    assert position['예측 연도'] == 2026
    assert position['입력 성장률 (%)'] == 6.0
    assert position['과거 분포 백분위 (%)'] == 50.0
    assert position['최근 실적 성장률 (%)'] == pytest.approx(10.89, abs=.01)
    assert position['최근 성장률 대비 (%p)'] == pytest.approx(-4.89, abs=.01)


def test_dcf_scenario_display_excludes_user_row_and_explains_cases(official_review):
    data, result = official_review
    metadata = evaluation_metadata(data, 2025)
    scenarios = build_scenario_table(
        result, current_revenue_krw=metadata['current_revenue_krw'], origin_year=2025,
    )
    display = build_dcf_scenario_display(scenarios, result)

    assert display['시나리오'].tolist() == ['보수', '기본', '낙관']
    assert display['적용 해석'].tolist() == [
        '업황 둔화·기준 매출 유지에 가까운 경우',
        '기업 과거 성장률 중앙값 기준',
        '과거 상단 성장 구간 재현',
    ]
    assert '사용자 입력' not in display['시나리오'].tolist()
    assert data_context_message(data) == '삼성전자 2015~2025년 연결 매출 데이터를 확인했습니다.'


def test_operating_margin_copy_position_and_scenario_display():
    data = pd.read_csv(ROOT / 'data/samsung_operating_margin.csv')
    result = evaluate_operating_margin_assumptions(data, 2025, 14.0)
    interpretation = build_reviewer_interpretation(result, 'operating_margin')
    position = build_operating_margin_position(data, 2025, 14.0).iloc[0]
    scenarios = build_operating_margin_scenario_table(result, origin_year=2025)
    display = build_operating_margin_scenario_display(scenarios, result)

    assert '과거 영업이익률 중앙 범위 안' in interpretation
    assert position['과거 분포 백분위 (%)'] == pytest.approx(45.4545, abs=.001)
    assert position['최근 영업이익률 (%)'] == pytest.approx(13.0696, abs=.001)
    assert display['시나리오'].tolist() == ['보수', '기본', '낙관']
    assert display['적용 해석'].tolist() == [
        '과거 영업이익률 하단 구간 적용',
        '기업 과거 영업이익률 중앙값 기준',
        '과거 영업이익률 상단 구간 재현',
    ]
