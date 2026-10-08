"""OpenDART annual CFS snapshots. API amounts are never claimed to be historical vintages."""
from datetime import date, datetime, timezone
import re
import time

import pandas as pd
import requests

from .schema import COLUMNS

CORP_CODE = '00126380'
STOCK_CODE = '005930'
API_BASE = 'https://opendart.fss.or.kr/api/'
REVENUE_IDS = {'ifrs-full_Revenue', 'ifrs_Revenue'}
REVENUE_NAMES = {'매출액', '수익(매출액)', '매출', '영업수익'}


class DartError(RuntimeError):
    pass


class DartClient:
    def __init__(self, api_key: str, session=None):
        if not api_key or not api_key.strip():
            raise DartError('OpenDART 키가 없습니다. 로컬 .env 또는 Streamlit secrets에 DART_API_KEY를 설정하거나 CSV를 사용하세요.')
        self._key = api_key.strip()
        self._session = session or requests.Session()

    def _get(self, endpoint, params, allow_empty=False):
        payload = None
        for attempt in range(3):
            try:
                response = self._session.get(API_BASE + endpoint, params={**params, 'crtfc_key': self._key}, timeout=(10, 40))
                if response.status_code in (429, 500, 502, 503, 504):
                    if attempt < 2:
                        time.sleep(attempt + 1)
                        continue
                    raise DartError('OpenDART 서버 오류 또는 HTTP 호출 제한입니다. 잠시 후 다시 시도하세요.')
                response.raise_for_status()
                payload = response.json()
                if not isinstance(payload, dict):
                    raise DartError('OpenDART 응답 형식이 올바르지 않습니다.')
                break
            except (requests.RequestException, ValueError):
                # 예외/요청 URL에는 키가 포함될 수 있으므로 원문을 출력하지 않는다.
                raise DartError('OpenDART 연결 또는 응답 처리 실패: 네트워크 허용 도메인과 연결을 확인하세요.') from None
        status = payload.get('status')
        if status == '013' and allow_empty:
            return {'status': '013', 'list': []}
        messages = {'010': '등록되지 않은 OpenDART 키입니다.', '011': '사용이 중지된 OpenDART 키입니다.',
                    '012': '접근할 수 없는 IP입니다.', '020': 'OpenDART API 호출 한도를 초과했습니다.',
                    '100': 'OpenDART 요청 인자가 올바르지 않습니다.', '800': 'OpenDART 점검 중입니다.',
                    '900': 'OpenDART 서버 오류입니다.'}
        if status != '000':
            raise DartError(messages.get(status, 'OpenDART가 정상 데이터를 반환하지 않았습니다.'))
        return payload

    def filings(self, start_year, end_year):
        records = []
        # 기업 지정 시 기간 제한 없이 조회 가능. 정정 전후 모두 요청한다.
        for page in range(1, 1001):
            payload = self._get('list.json', {'corp_code': CORP_CODE,
                'bgn_de': f'{start_year}0101', 'end_de': f'{end_year}1231',
                'pblntf_ty': 'A', 'last_reprt_at': 'N', 'page_count': 100, 'page_no': page}, allow_empty=True)
            records.extend(payload.get('list', []))
            if page >= int(payload.get('total_page', 1)):
                return records
        raise DartError('공시 목록 페이지 수가 예상 범위를 넘었습니다. 조회 기간을 줄이세요.')

    def collect(self, start_year, end_year):
        if not 2015 <= start_year <= end_year < date.today().year:
            raise DartError('연도는 2015년부터 직전 완료 회계연도 사이로 지정하세요.')
        filings = self.filings(start_year + 1, date.today().year)
        by_receipt = {r['rcept_no']: r for r in filings}
        raw, rows, warnings = [], [], []
        fetched = datetime.now(timezone.utc).isoformat()
        for year in range(start_year, end_year + 1):
            payload = self._get('fnlttSinglAcntAll.json', {'corp_code': CORP_CODE, 'bsns_year': year,
                                'reprt_code': '11011', 'fs_div': 'CFS'}, allow_empty=True)
            # 응답만 보관. 키·요청 URL·세션 헤더는 보관하지 않는다.
            raw.append({'requested_fiscal_year': year, 'response': payload})
            accounts = payload.get('list', [])
            income = [a for a in accounts if a.get('sj_div') in ('IS', 'CIS')]
            candidates = [a for a in income if a.get('account_id') in REVENUE_IDS]
            if not candidates:
                candidates = [a for a in income if a.get('account_nm', '').replace(' ', '') in REVENUE_NAMES]
            if not candidates:
                warnings.append(f'{year}: 연결 손익계산서 매출 계정을 확보하지 못했습니다. 임의 대체하지 않습니다.')
                continue
            identities = {(a.get('thstrm_amount'), a.get('rcept_no'), a.get('currency', 'KRW')) for a in candidates}
            if len(identities) != 1:
                warnings.append(f'{year}: 매출 계정 후보가 충돌합니다. 공식 보고서에서 확인해야 합니다.')
                continue
            a = candidates[0]
            receipt = a.get('rcept_no', '')
            filing = by_receipt.get(receipt)
            if not filing or '사업보고서' not in filing.get('report_nm', ''):
                warnings.append(f'{year}: 재무 수치의 접수번호를 연간 사업보고서 공시일과 대조하지 못해 제외했습니다.')
                continue
            if f'{year}.12' not in filing['report_nm'].replace(' ', ''):
                warnings.append(f'{year}: 보고서 회계기간이 12월 결산과 일치하지 않아 제외했습니다.')
                continue
            pub = datetime.strptime(filing['rcept_dt'], '%Y%m%d').date().isoformat()
            # 전체 재무제표 API는 기간 시작/종료를 주지 않는 경우가 있다.
            # 사업보고서 제목과 reprt_code=11011로 연도를 매핑하되, 기간 원문 미검증을 명시한다.
            period_text = a.get('thstrm_dt', '')
            if period_text:
                dates = re.findall(r'(\d{4})[.\-/](\d{2})[.\-/](\d{2})', period_text.replace(' ', ''))
                if len(dates) != 2 or dates != [(str(year), '01', '01'), (str(year), '12', '31')]:
                    warnings.append(f'{year}: API 매출 대상 기간이 표준 연간 기간과 다르거나 불명확하여 제외했습니다.')
                    continue
            amendments = [f for f in filings if '사업보고서' in f.get('report_nm', '') and
                          f'{year}.12' in f['report_nm'].replace(' ', '') and '정정' in f['report_nm']]
            notes = '기간·합병·분할·중단영업·재작성 원문 미검토'
            if amendments:
                notes += '; 관련 정정공시 존재: ' + ', '.join(f['rcept_no'] for f in amendments)
            rows.append(dict(company_name='삼성전자', stock_code=STOCK_CODE, corp_code=CORP_CODE,
                fiscal_year=year, period_start=f'{year}-01-01', period_end=f'{year}-12-31',
                revenue=a.get('thstrm_amount', ''), unit='원', currency=a.get('currency') or 'KRW',
                fs_div='CFS', report_type='annual', publication_date=pub, receipt_no=receipt,
                source_url=f'https://dart.fss.or.kr/dsaf001/main.do?rcpNo={receipt}',
                is_correction='정정' in filing['report_nm'], retrieved_at=fetched, value_basis='current',
                source_fiscal_year=year, point_in_time_verified=False, first_annual_report=False,
                comparability_notes=notes, comparability_reviewed=False, is_mock=False,
                evidence_note=f'OpenDART 11011/CFS 당기; 계정 {a.get("account_id", "")}; {filing["report_nm"]}; API 현재 응답, 과거 원문 미검증'))
        return pd.DataFrame(rows, columns=COLUMNS), {'filings': filings, 'financial_responses': raw, 'retrieved_at': fetched}, warnings
