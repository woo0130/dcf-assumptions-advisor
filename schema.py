from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from urllib.parse import urlparse

import pandas as pd

COLUMNS = [
    'company_name', 'stock_code', 'corp_code', 'fiscal_year', 'period_start',
    'period_end', 'revenue', 'unit', 'currency', 'fs_div', 'report_type',
    'publication_date', 'receipt_no', 'source_url', 'is_correction',
    'retrieved_at', 'value_basis', 'source_fiscal_year', 'point_in_time_verified',
    'first_annual_report', 'comparability_notes', 'comparability_reviewed',
    'is_mock', 'evidence_note',
]
BOOLS = ['is_correction', 'point_in_time_verified', 'first_annual_report',
         'comparability_reviewed', 'is_mock']
UNITS = {'원': 1, '천원': 1000, '백만원': 1000000, '억원': 100000000}


class DataError(ValueError):
    pass


@dataclass
class Normalized:
    data: pd.DataFrame
    rejected: pd.DataFrame
    warnings: list[str]


def read_csv(file) -> pd.DataFrame:
    try:
        return pd.read_csv(file, dtype=str, keep_default_na=False, encoding='utf-8-sig')
    except (ValueError, UnicodeError, pd.errors.ParserError) as exc:
        raise DataError('CSV를 읽지 못했습니다. UTF-8 CSV 형식을 확인하세요.') from exc


def _boolean(value):
    text = str(value).strip().lower()
    if text not in ('true', 'false'):
        raise DataError('논리값은 true 또는 false여야 합니다.')
    return text == 'true'


def normalize(raw: pd.DataFrame) -> Normalized:
    missing = sorted(set(COLUMNS) - set(raw.columns))
    if missing:
        raise DataError('필수 열 누락: ' + ', '.join(missing))
    if raw.empty:
        raise DataError('입력 데이터가 비어 있습니다.')
    if len(raw) > 10000:
        raise DataError('이번 단계는 기업 1개, 최대 10,000개 관측값만 지원합니다.')
    accepted, rejected, warnings = [], [], []
    for i, record in enumerate(raw.to_dict('records'), start=2):
        r = {k: str(record[k]).strip() for k in COLUMNS}
        try:
            for key in BOOLS:
                r[key] = _boolean(r[key])
            if r['stock_code'] != '005930' or r['corp_code'] != '00126380':
                raise DataError('이번 단계 대상은 삼성전자(005930 / 00126380)입니다. 코드를 문자열로 보존하세요.')
            if not r['company_name']:
                raise DataError('기업명이 필요합니다.')
            if r['fs_div'] != 'CFS' or r['report_type'] != 'annual':
                raise DataError('연간 연결(CFS / annual) 자료만 허용합니다.')
            if r['currency'] != 'KRW' or r['unit'] not in UNITS:
                raise DataError('지원 통화는 KRW, 단위는 원·천원·백만원·억원입니다.')
            r['fiscal_year'] = int(r['fiscal_year'])
            r['source_fiscal_year'] = int(r['source_fiscal_year'])
            for key in ('period_start', 'period_end', 'publication_date'):
                r[key] = pd.Timestamp(r[key])
                if pd.isna(r[key]) or r[key].tzinfo is not None or r[key] != r[key].normalize():
                    raise DataError('회계기간·공시일은 YYYY-MM-DD 날짜여야 합니다.')
            y = r['fiscal_year']
            if r['period_start'] != pd.Timestamp(y, 1, 1) or r['period_end'] != pd.Timestamp(y, 12, 31):
                raise DataError('삼성전자 1월~12월 연간 자료와 기간이 다릅니다. 분기·결산기간 변경은 제외합니다.')
            if r['publication_date'] <= r['period_end']:
                raise DataError('공시일은 해당 연간 실적 기간 종료일 이후여야 합니다.')
            r['retrieved_at'] = pd.Timestamp(r['retrieved_at'])
            if pd.isna(r['retrieved_at']) or r['retrieved_at'].tzinfo is None:
                raise DataError('조회 시각은 시간대가 있는 ISO 8601 형식이어야 합니다.')
            if r['retrieved_at'].date() < r['publication_date'].date():
                raise DataError('조회 시각이 공시일보다 이릅니다.')
            if r['value_basis'] not in ('current', 'comparative'):
                raise DataError('value_basis는 current 또는 comparative여야 합니다.')
            if r['value_basis'] == 'current' and r['source_fiscal_year'] != y:
                raise DataError('당기 값과 보고서 대상 연도가 다릅니다.')
            if r['value_basis'] == 'comparative' and r['source_fiscal_year'] <= y:
                raise DataError('비교표시 값은 이후 연도 보고서에서 가져와야 합니다.')
            if r['publication_date'] <= pd.Timestamp(r['source_fiscal_year'], 12, 31):
                raise DataError('공시일이 원본 연간 보고서의 대상 기간 종료일 이후여야 합니다. 비교표시 공시일을 소급할 수 없습니다.')
            if r['first_annual_report'] and (r['is_correction'] or r['value_basis'] != 'current'):
                raise DataError('최초 연간 보고서 표시는 정정·비교표시 행과 함께 사용할 수 없습니다.')
            if r['point_in_time_verified'] and not r['evidence_note']:
                raise DataError('당시 수치 검증에는 원문·페이지 등 evidence_note 근거가 필요합니다.')
            if urlparse(r['source_url']).scheme != 'https' or not urlparse(r['source_url']).netloc:
                raise DataError('출처는 HTTPS 원문 링크여야 합니다.')
            if r['receipt_no'] and (len(r['receipt_no']) != 14 or not r['receipt_no'].isdigit()):
                raise DataError('DART 접수번호는 14자리입니다. 공식 IR은 빈 값이 가능합니다.')
            amount = Decimal(r['revenue'].replace(',', '')) * UNITS[r['unit']]
            if not amount.is_finite() or amount != amount.to_integral_value() or abs(amount) > Decimal('1e20'):
                raise DataError('매출은 유한한 원 단위 정수(절댓값 1e20 이하)로 환산되어야 합니다.')
            r['revenue_krw'] = int(amount)
            r['available_date'] = r['publication_date']
            accepted.append(r)
        except (ValueError, TypeError, InvalidOperation, OverflowError) as exc:
            rejected.append({**record, 'csv_row': i, 'reason': str(exc)})
    data = pd.DataFrame(accepted)
    if not data.empty:
        if data['is_mock'].nunique() > 1:
            raise DataError('실제 데이터와 모의 데이터를 함께 분석할 수 없습니다.')
        keys = ['fiscal_year', 'publication_date']
        for _, group in data.groupby(keys):
            if group['revenue_krw'].nunique() > 1:
                raise DataError('같은 연도·공시일에 서로 다른 매출이 있습니다. 원문을 대조해 충돌을 해결하세요.')
        data = data.drop_duplicates(COLUMNS).sort_values(['fiscal_year', 'publication_date']).reset_index(drop=True)
        if not data['point_in_time_verified'].all():
            warnings.append('당시 원문 수치가 검증되지 않은 행이 있습니다. 최신 재무자료 기반의 회고적 비교로만 해석하세요.')
        if not data['comparability_reviewed'].all():
            warnings.append('합병·분할·중단영업·재작성 등 비교 가능성에 대한 원문 검토가 완료되지 않았습니다.')
        if (data['revenue_krw'] <= 0).any():
            warnings.append('0·음수 매출이 있어 관련 예측 또는 백분율 평가를 제외합니다.')
        years = set(data['fiscal_year'])
        gaps = sorted(set(range(min(years), max(years) + 1)) - years)
        if gaps:
            warnings.append(f'누락 연도 {gaps}: 보간하거나 임의로 채우지 않습니다.')
        for note in data.loc[data['comparability_notes'] != '', 'comparability_notes'].unique():
            warnings.append('비교 가능성 주의: ' + note)
    if rejected:
        warnings.append(f'기간·단위·출처 등 검증에서 {len(rejected)}개 행을 제외했습니다. 제외 사유를 확인하세요.')
    return Normalized(data, pd.DataFrame(rejected), warnings)
