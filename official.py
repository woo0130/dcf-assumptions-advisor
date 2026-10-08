"""공식 DART 원문과 삼성전자 감사 PDF를 대조하는 CSV 작성 보조 함수.
OpenDART API와 별개로, 키 없는 공식 자료 CSV의 재현에만 사용한다.
"""
from html import unescape
from html.parser import HTMLParser
from io import BytesIO
import re
from urllib.parse import urlencode


class EvidenceError(ValueError):
    pass


class _Text(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []
    def handle_data(self, data):
        self.parts.append(data)


def plain_text(html):
    parser = _Text()
    parser.feed(html)
    return re.sub(r'\s+', ' ', unescape(' '.join(parser.parts))).strip()


def parse_filing_list(html):
    filings = []
    for tr in re.findall(r'<tr\b[^>]*>(.*?)</tr>', html, re.S | re.I):
        receipt = re.search(r'rcpNo=(\d{14})', tr)
        if not receipt:
            continue
        text = plain_text(tr)
        year = re.search(r'사업보고서\s*\((\d{4})\.12\)', text)
        pub = re.search(r'\b(20\d{2})\.(\d{2})\.(\d{2})\b', text)
        if not year or not pub or '00126380' not in tr or '삼성전자' not in text:
            raise EvidenceError('공시 목록의 기업·보고서 연도·공시일을 확인하지 못했습니다.')
        filings.append({'fiscal_year': int(year[1]), 'receipt_no': receipt[1],
            'publication_date': '-'.join(pub.groups()), 'is_correction': '정정' in text,
            'filing_list_text': text})
    total = re.search(r'총\s*([\d,]+)건', plain_text(html))
    if not total or int(total[1].replace(',', '')) != len(filings):
        raise EvidenceError('공시 목록의 전체 건수를 확인하지 못했거나 페이지가 잘렸습니다.')
    return filings


def statement_url(main_html, receipt):
    nodes = [dict(re.findall(r"node\d\['(\w+)'\]\s*=\s*\"([^\"]*)\"", chunk))
             for chunk in re.split(r'var node\d = \{\};', main_html)]
    node = next((n for n in nodes if n.get('text') == '2-2. 연결 손익계산서'), None)
    if node is None:
        node = next((n for n in nodes if n.get('text') == '2. 연결재무제표'), None)
    if node is None or node.get('rcpNo') != receipt:
        raise EvidenceError('요청 접수번호의 연결 손익계산서 원문을 찾지 못했습니다.')
    keys = ['rcpNo', 'dcmNo', 'eleId', 'offset', 'length', 'dtd']
    if any(not node.get(k) for k in keys):
        raise EvidenceError('DART 원문 주소 인자가 누락되었습니다.')
    return 'https://dart.fss.or.kr/report/viewer.do?' + urlencode({k: node[k] for k in keys})


def parse_dart_revenue(html, year):
    text = plain_text(html)
    start = text.find('연결 손익계산서')
    if start < 0:
        raise EvidenceError('연결 손익계산서 제목을 확인하지 못했습니다.')
    block = text[start:]
    end = block.find('매출원가')
    if end < 0:
        raise EvidenceError('연결 손익계산서 매출 행을 확인하지 못했습니다.')
    block = block[:end]
    if not re.search(r'단위\s*:\s*백만원', block):
        raise EvidenceError('공식 표의 백만원 단위를 확인하지 못했습니다.')
    periods = re.findall(r'(\d{4})\.01\.01\s*부터\s*(\d{4})\.12\.31\s*까지', block)
    if periods != [(str(year - i), str(year - i)) for i in range(3)]:
        raise EvidenceError('당기·전기·전전기 연간 기간이 예상과 다릅니다.')
    revenue = re.search(r'(?:수익\s*\(\s*매출액\s*\)|매출액|영업수익)\s*(?:\(주\s*\d+\))?\s*(.*)', block)
    if revenue is None:
        raise EvidenceError('매출액 행을 찾지 못했습니다.')
    amounts = re.findall(r'\d{1,3}(?:,\d{3})+', revenue[1])
    if len(amounts) != 3:
        raise EvidenceError('매출액의 3개 연도 열을 확정하지 못했습니다.')
    return {year - i: int(amount.replace(',', '')) for i, amount in enumerate(amounts)}, block


def parse_pdf_revenue(payload, year):
    from pypdf import PdfReader  # 문서 검증용 선택 의존성
    reader = PdfReader(BytesIO(payload))
    for page_no, page in enumerate(reader.pages[:16], start=1):
        text = page.extract_text() or ''
        if not any(title in text for title in ('CONSOLIDATED STATEMENTS OF PROFIT OR LOSS', 'CONSOLIDATED STATEMENTS OF INCOME')):
            continue
        if 'millions of Korean won' not in text or not re.search(rf'{year}\s+{year-1}\s+{year}\s+{year-1}', text):
            raise EvidenceError('PDF 연결 표의 통화·단위·연도 순서를 확인하지 못했습니다.')
        line = next((line.strip() for line in text.splitlines() if line.strip().startswith('Revenue ')), '')
        amounts = re.findall(r'\d{1,3}(?:,\d{3})+', line)
        if len(amounts) != 4:
            raise EvidenceError('PDF 매출의 KRW·USD 열을 확인하지 못했습니다.')
        return {year: int(amounts[0].replace(',', '')), year-1: int(amounts[1].replace(',', ''))}, page_no, line
    raise EvidenceError('PDF 연결 손익계산서 매출을 찾지 못했습니다.')
