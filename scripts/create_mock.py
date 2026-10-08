"""공식 실적이 아닌 산술·UI 검증용 CSV를 재생성한다."""
import csv
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from revenue_agent.schema import COLUMNS

rows = []
# 삼성전자 실제 매출과 무관한 모의 데이터. 단위: 백만원.
values = [100000, 110000, 121000, 133100, 140000, 126000, 151200, 166320, 158000, 173800]
for year, value in zip(range(2015, 2025), values):
    rows.append(dict(company_name='삼성전자 (모의 데이터)', stock_code='005930', corp_code='00126380',
        fiscal_year=year, period_start=f'{year}-01-01', period_end=f'{year}-12-31', revenue=value,
        unit='백만원', currency='KRW', fs_div='CFS', report_type='annual',
        publication_date=f'{year+1}-03-15', receipt_no='', source_url='https://example.com/mock-not-real',
        is_correction=False, retrieved_at='2026-10-06T00:00:00+00:00', value_basis='current',
        source_fiscal_year=year, point_in_time_verified=False, first_annual_report=False,
        comparability_notes='모의 수치·모의 공시일: 실제 투자 분석에 사용 금지', comparability_reviewed=False,
        is_mock=True, evidence_note='공식 자료가 아닌 계산·화면 확인용 모의 데이터'))
root = Path(__file__).resolve().parents[1]
for name, records in [('mock_revenue.csv', rows), ('manual_template.csv', [])]:
    with (root / 'data' / name).open('w', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(records)
