"""키 없이 공식 DART 원문과 삼성전자 IR PDF를 교차 대조하여 입력 CSV를 재현.
네트워크 접근 및 requirements-dev.txt(pypdf)가 필요하다. HTML 변경 시 실패하도록 설계.
"""
import argparse
import csv
from datetime import datetime, timezone
import hashlib
import json
import logging
from pathlib import Path
import sys

import requests

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from revenue_agent.official import EvidenceError, parse_filing_list, statement_url, parse_dart_revenue, parse_pdf_revenue
from revenue_agent.schema import COLUMNS, normalize
import pandas as pd


def main():
    parser = argparse.ArgumentParser(description='공식 원문 대조 및 삼성전자 실제 CSV 생성')
    parser.add_argument('--start-year', type=int, default=2015)
    parser.add_argument('--end-year', type=int, default=2025)
    parser.add_argument('--output-dir', type=Path, default=Path('.local/official-build'))
    args = parser.parse_args()
    if not 2015 <= args.start_year <= args.end_year < datetime.now().year:
        parser.error('2015년 이후 완료 회계연도를 지정하세요.')
    args.output_dir.mkdir(parents=True, exist_ok=True)
    session = requests.Session()
    retrieved = datetime.now(timezone.utc).isoformat()
    evidence = {'retrieved_at': retrieved, 'documents': [], 'checks': [], 'filings': []}
    logging.getLogger('pypdf').setLevel(logging.ERROR)

    def get(url, filename, params=None):
        target = args.output_dir / filename
        resolved_url = requests.Request('GET', url, params=params).prepare().url
        if target.exists():
            # 재실행은 확보한 원문을 재사용한다. 새 조회는 새 출력 폴더에서 수행한다.
            payload = target.read_bytes()
        else:
            response = session.get(url, params=params, timeout=(10, 45))
            response.raise_for_status()
            payload = response.content
            target.write_bytes(payload)
        evidence['documents'].append({'file': filename, 'url': resolved_url,
            'sha256': hashlib.sha256(payload).hexdigest(),
            'retrieved_at': datetime.fromtimestamp(target.stat().st_mtime, timezone.utc).isoformat()})
        return payload

    try:
        filings = []
        for start in range(args.start_year + 1, datetime.now().year + 1, 5):
            end = min(start + 4, datetime.now().year)
            payload = get('https://dart.fss.or.kr/dsab001/searchCorp.ax', f'filings_{start}_{end}.html',
                {'currentPage': 1, 'maxResults': 100, 'maxLinks': 10, 'sort': 'date', 'series': 'asc',
                 'textCrpCik': '00126380', 'textCrpNm': '삼성전자', 'pageGubun': 'corp',
                 'startDate': f'{start}0101', 'endDate': f'{end}1231', 'publicType': 'A001'})
            filings.extend(parse_filing_list(payload.decode('utf-8')))
        filings = [f for f in filings if args.start_year <= f['fiscal_year'] <= args.end_year]
        evidence['filings'] = filings
        rows = []
        for year in range(args.start_year, args.end_year + 1):
            year_filings = sorted([f for f in filings if f['fiscal_year'] == year], key=lambda f: (f['publication_date'], f['receipt_no']))
            initial = [f for f in year_filings if not f['is_correction']]
            if not initial:
                raise EvidenceError(f'{year}: 최초 비정정 사업보고서를 찾지 못했습니다.')
            first_receipt = initial[0]['receipt_no']
            pdf_url = f'https://images.samsung.com/is/content/samsung/assets/global/ir/docs/{year}_con_quarter04_all.pdf'
            pdf = get(pdf_url, f'{year}_official.pdf')
            pdf_values, pdf_page, pdf_line = parse_pdf_revenue(pdf, year)
            for filing in year_filings:
                receipt = filing['receipt_no']
                main = get('https://dart.fss.or.kr/dsaf001/main.do', f'{receipt}_main.html', {'rcpNo': receipt}).decode('utf-8')
                url = statement_url(main, receipt)
                statement = get(url, f'{receipt}_statement.html').decode('utf-8')
                dart_values, excerpt = parse_dart_revenue(statement, year)
                # IR PDF는 최신일 수 있다. 값이 다르면 원문을 바꾸지 않고 보수적으로 중단해 수동 검토한다.
                for y, expected in pdf_values.items():
                    if dart_values[y] != expected:
                        raise EvidenceError(f'{year} 보고서 {y}년: DART와 IR 금액이 다릅니다. 정정·재작성 검토 필요.')
                evidence['checks'].append({'report_year': year, 'receipt_no': receipt,
                    'publication_date': filing['publication_date'], 'dart_source_url': url,
                    'pdf_source_url': pdf_url, 'pdf_page': pdf_page, 'pdf_revenue_line': pdf_line,
                    'dart_excerpt': excerpt, 'revenue_million_krw': dart_values,
                    'crosscheck': '당기와 비교 전기 KRW 매출 모두 일치'})
                for value_year, amount in dart_values.items():
                    if value_year < args.start_year:
                        continue
                    note = '사업결합·중단영업·회계정책 등 주석 전체 검토 미완료'
                    if value_year == 2017:
                        note += '; 2017년 Harman 인수로 연결 범위 변화 (2017 감사 PDF p.101, 주석 35)'
                    if value_year == 2018:
                        note += '; 2018년 IFRS 15 최초 적용·비교기간 미재작성 (2018 감사 PDF p.31~32)'
                    rows.append(dict(company_name='삼성전자', stock_code='005930', corp_code='00126380',
                        fiscal_year=value_year, period_start=f'{value_year}-01-01', period_end=f'{value_year}-12-31',
                        revenue=amount, unit='백만원', currency='KRW', fs_div='CFS', report_type='annual',
                        publication_date=filing['publication_date'], receipt_no=receipt, source_url=url,
                        is_correction=filing['is_correction'], retrieved_at=retrieved,
                        value_basis='current' if value_year == year else 'comparative', source_fiscal_year=year,
                        point_in_time_verified=True, first_annual_report=value_year == year and receipt == first_receipt,
                        comparability_notes=note, comparability_reviewed=False, is_mock=False,
                        evidence_note=f'DART 고정 접수번호 원문 연결 손익계산서 매출액·연간기간·백만원 확인; 최초/정정 목록 대조; '
                            f'당기/전기는 공식 감사 PDF p.{pdf_page} Revenue와 교차 일치 ({pdf_url}); '
                            '전전기는 DART 원문만 확인; 원문 SHA-256은 official_evidence.json 참조'))
            print(f'{year}: DART 원문 및 IR PDF p.{pdf_page} 매출 대조 통과', flush=True)
        normalized = normalize(pd.DataFrame(rows))
        if not normalized.rejected.empty:
            raise EvidenceError('생성 CSV에 정규화 거부 행이 있습니다.')
        with (args.output_dir / 'samsung_official_revenue.csv').open('w', newline='', encoding='utf-8-sig') as file:
            writer = csv.DictWriter(file, fieldnames=COLUMNS)
            writer.writeheader()
            writer.writerows(rows)
        (args.output_dir / 'official_evidence.json').write_text(json.dumps(evidence, ensure_ascii=False, indent=2), encoding='utf-8')
        print(f'완료: {len(rows)}개 공시 버전 행, {args.start_year}~{args.end_year}. 비교 가능성 주석 검토는 별도 필요.')
    except (requests.RequestException, EvidenceError, ValueError) as exc:
        parser.exit(1, f'공식 자료 대조 중단: {exc}\n')


if __name__ == '__main__':
    main()
