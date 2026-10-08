"""가정 리뷰 결과의 Markdown 및 DCF 모델 연동용 내보내기."""
from __future__ import annotations

from datetime import date
from typing import Iterable, Literal

import pandas as pd

from .recommendation import RecommendationResult


Metric = Literal['revenue_growth', 'operating_margin', 'nwc_ratio', 'capex_ratio']

METRIC_LABELS: dict[Metric, str] = {
    'revenue_growth': '매출 성장률',
    'operating_margin': '영업이익률',
    'nwc_ratio': 'NWC/매출액',
    'capex_ratio': 'CapEx/매출액',
}


def _format_assumption(value: float | dict[int, float]) -> str:
    if isinstance(value, dict):
        return ', '.join(f'{year}: {rate:.2f}%' for year, rate in sorted(value.items()))
    return f'{float(value):.2f}%'


def build_markdown_report(
    *,
    metric: Metric,
    company_name: str,
    origin_year: int,
    cutoff_date: date | pd.Timestamp,
    result: RecommendationResult,
    interpretation: str,
) -> str:
    metric_label = METRIC_LABELS[metric]
    verdict_labels = {
        'retain': '유지 가능',
        'adjust': '조정 검토',
        'caution': '주의해서 사용',
        'insufficient': '근거 부족',
    }
    confidence_labels = {'high': '높음', 'medium': '보통', 'low': '낮음'}
    cutoff = pd.Timestamp(cutoff_date).date().isoformat()
    lines = [
        f'# {company_name} DCF {metric_label} 가정 검토',
        '',
        '## 결론',
        '',
        f'- 정보 기준일: {cutoff}',
        f'- 기준 회계연도: {origin_year}',
        f'- 입력 가정: {_format_assumption(result.user_assumption)}',
        f'- 판정: {verdict_labels[result.verdict]} (`{result.verdict}`)',
        f'- 신뢰도: {confidence_labels[result.confidence]} (`{result.confidence}`)',
        f'- 권고 범위: {result.suggested_range[0]:.2f}% ~ {result.suggested_range[1]:.2f}%',
        f'- 보수 / 기본 / 낙관: {_format_assumption(result.bear_case)} / '
        f'{_format_assumption(result.base_case)} / {_format_assumption(result.bull_case)}',
        '',
        '## 한 줄 해석',
        '',
        interpretation,
        '',
        '## 찬성 근거',
        '',
    ]
    lines.extend(f'- {item}' for item in result.supporting_evidence)
    lines.extend(['', '## 주의·충돌 근거', ''])
    lines.extend(f'- {item}' for item in result.conflicting_evidence)
    if not result.conflicting_evidence:
        lines.append('- 확인된 충돌 근거 없음')
    lines.extend(['', '## 데이터 경고', ''])
    lines.extend(f'- {item}' for item in result.data_warnings)
    lines.extend(['', '## 데이터 공급자 상태', ''])
    lines.extend(f'- {name}: {status}' for name, status in result.provider_status.items())
    lines.extend([
        '',
        '> 본 보고서는 DCF 가정 검토 참고자료이며 투자 의견이나 미래 실적 보장이 아닙니다.',
        '',
    ])
    return '\n'.join(lines)


def build_dcf_scenario_export(
    *,
    metric: Metric,
    company_name: str,
    cutoff_date: date | pd.Timestamp,
    result: RecommendationResult,
    scenario_table: pd.DataFrame,
) -> pd.DataFrame:
    """Excel Power Query에서도 바로 읽을 수 있는 공통 long-form 스키마."""
    cutoff = pd.Timestamp(cutoff_date).date().isoformat()
    rows = []
    for _, row in scenario_table.iterrows():
        scenario = str(row['시나리오'])
        year = int(row['예측 연도'])
        exported = {
            'company_name': company_name,
            'information_cutoff': cutoff,
            'forecast_year': year,
            'scenario': scenario,
            'review_metric': metric,
            'revenue_growth_pct': pd.NA,
            'operating_margin_pct': pd.NA,
            'nwc_to_revenue_pct': pd.NA,
            'capex_to_revenue_pct': pd.NA,
            'forecast_revenue_krw': pd.NA,
            'forecast_operating_profit_krw': pd.NA,
            'forecast_nwc_krw': pd.NA,
            'forecast_capex_krw': pd.NA,
            'verdict': result.verdict,
            'confidence': result.confidence,
            'peer_status': result.provider_status.get('peer', 'unconnected'),
        }
        if metric == 'revenue_growth':
            exported['revenue_growth_pct'] = float(row['성장률 (%)'])
            exported['forecast_revenue_krw'] = float(row['예측 매출 (원)'])
        elif metric == 'operating_margin':
            exported['operating_margin_pct'] = float(row['영업이익률 (%)'])
        elif metric == 'nwc_ratio':
            exported['nwc_to_revenue_pct'] = float(row['NWC/매출액 (%)'])
        elif metric == 'capex_ratio':
            exported['capex_to_revenue_pct'] = float(row['CapEx/매출액 (%)'])
        rows.append(exported)
    return pd.DataFrame(rows)


def combine_dcf_scenario_exports(exports: Iterable[pd.DataFrame]) -> pd.DataFrame:
    """여러 검토 항목의 공통 스키마 CSV를 한 표로 결합한다."""
    frames = [frame.copy() for frame in exports if not frame.empty]
    if not frames:
        return pd.DataFrame()
    expected = frames[0].columns.tolist()
    if any(frame.columns.tolist() != expected for frame in frames[1:]):
        raise ValueError('통합할 DCF 시나리오 CSV의 열 구조가 서로 다릅니다.')
    return pd.concat(frames, ignore_index=True)


def build_integrated_markdown_report(reports: dict[str, str]) -> str:
    """현재 세션에서 검토한 핵심 가정의 Markdown 보고서를 하나로 묶는다."""
    ordered = [metric for metric in METRIC_LABELS if metric in reports]
    sections = [
        '# DCF 핵심 가정 통합 검토 리포트',
        '',
        f"검토 완료 항목: {', '.join(METRIC_LABELS[metric] for metric in ordered) or '없음'}",
        '',
    ]
    for metric in ordered:
        sections.extend(['---', '', reports[metric], ''])
    return '\n'.join(sections)
