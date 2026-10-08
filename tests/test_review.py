import hashlib
import json
from pathlib import Path

import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

from revenue_agent.schema import normalize, read_csv
from revenue_agent.backtest import run_backtest, summarize
from revenue_agent.review import trace_case, segment_diagnostics, comparative_checks

ROOT = Path(__file__).resolve().parents[1]


def original():
    data = normalize(read_csv(ROOT / 'data/samsung_official_revenue.csv')).data
    return data, run_backtest(data)


def test_original_data_methods_and_holdout_are_unchanged():
    lock = json.loads((ROOT / 'docs/review/original_lock.json').read_text())
    assert hashlib.sha256((ROOT / 'data/samsung_official_revenue.csv').read_bytes()).hexdigest() == lock['source_sha256']
    for name, expected in lock['method_files_sha256'].items():
        assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == expected
    _, results = original()
    _, common, split = summarize(results)
    assert common == lock['common_years']
    assert split == lock['selection']
    assert not split['beats_baseline']


def test_2023_input_dates_vintages_and_actual_are_separate():
    data, results = original()
    before = results.copy(deep=True)
    inputs, case, timely = trace_case(data, results)
    assert timely
    assert inputs['year'].tolist() == [2019, 2020, 2021, 2022]
    assert inputs['publication_date'].tolist() == ['2022-03-08', '2023-03-07', '2023-03-07', '2023-03-07']
    assert inputs['receipt_no'].tolist() == ['20220308000798'] + ['20230307000542'] * 3
    assert inputs['value_basis'].tolist() == ['comparative'] * 3 + ['current']
    assert (case['cutoff_date'] == pd.Timestamp('2023-03-07')).all()
    assert (case['actual_publication_date'] == pd.Timestamp('2024-03-12')).all()
    assert (case['actual_krw'] == 258935494000000).all()
    assert case.loc[case.method == 'cagr3', 'ape_pct'].iloc[0] == pytest.approx(27.7712281493)
    pd.testing.assert_frame_equal(before, results)


def test_segments_report_all_methods_without_reselection():
    _, results = original()
    protocol = json.loads((ROOT / 'docs/review/review_protocol.json').read_text())
    before = results.copy(deep=True)
    diagnostics = segment_diagnostics(results, protocol)
    assert len(diagnostics) == len(protocol['segments']) * 4
    counts = diagnostics.groupby('segment_id')['표본 수'].first().to_dict()
    assert counts == {'original': 7, 'ifrs15_transition': 3, 'ifrs15_after': 4,
                      'locked_holdout': 3, 'emagin': 1, 'dowoo_sale': 1, 'major_2025': 1}
    holdout = diagnostics[diagnostics.segment_id == 'locked_holdout'].set_index('method')
    assert holdout.loc['cagr3', '유지 대비 개선 (%p)'] == pytest.approx(-2.0727948761)
    pd.testing.assert_frame_equal(before, results)


def test_restatement_review_has_nineteen_comparatives_and_year_coverage():
    data, _ = original()
    checks = comparative_checks(data)
    assert len(checks) == 19
    assert (checks['차이 (원)'] == 0).all()
    assert 2025 not in checks['회계연도'].values
    review = json.loads((ROOT / 'data/comparability_review.json').read_text())
    assert [r['year'] for r in review['years']] == list(range(2015, 2026))
    assert review['post_hoc'] and not review['original_csv_modified']
    assert all(r['unconfirmed'] and r['sources'] for r in review['years'])


def test_review_screen_is_only_attached_to_official_bundle():
    app = AppTest.from_file(str(ROOT / 'app.py')).run(timeout=30)
    assert not app.exception
    next(button for button in app.button if button.label == '가정 검토하기').click().run(timeout=30)
    assert any('2023년 예측 한 건' in x.value for x in app.subheader)
    assert any('모든 사용 입력' in x.value for x in app.success)
    app.selectbox[0].set_value('모의 데이터 (2015~2024)').run(timeout=30)
    assert not app.exception
    assert not any('2023년 예측 한 건' in x.value for x in app.subheader)
