"""DCF 매출 가정 리뷰어의 규칙 기반 의사결정 계층.

기존 예측·백테스트 결과는 변경하지 않는다. 선택한 기준일 당시 공개된
재무 수치와 그때까지 발표된 실제 실적만 평가에 사용한다.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass
import math
from pathlib import Path
from typing import Literal, TypeAlias

import pandas as pd

from .backtest import summarize
from .forecast import METHODS, predict


AssumptionValue: TypeAlias = float | dict[int, float]
Verdict: TypeAlias = Literal['retain', 'adjust', 'caution', 'insufficient']
Confidence: TypeAlias = Literal['high', 'medium', 'low']
CapitalRatioMetric: TypeAlias = Literal['nwc_ratio', 'capex_ratio']


class RecommendationError(ValueError):
    """가정 검토 결과를 만들 수 없는 입력에 사용한다."""


@dataclass(frozen=True)
class RecommendationResult:
    verdict: Verdict
    confidence: Confidence
    user_assumption: AssumptionValue
    suggested_range: tuple[float, float]
    base_case: AssumptionValue
    bear_case: AssumptionValue
    bull_case: AssumptionValue
    supporting_evidence: list[str]
    conflicting_evidence: list[str]
    data_warnings: list[str]
    provider_status: dict[str, str]

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class PeerBenchmark:
    """향후 동종기업 공급자가 반환할 최소 계약."""

    suggested_range: tuple[float, float]
    base_case: float
    supporting_evidence: list[str]
    conflicting_evidence: list[str]
    data_warnings: list[str]
    user_percentile: float | None = None
    sample_size: int = 0
    source_label: str = ''


class PeerBenchmarkProvider(ABC):
    """동종기업·산업 성장률 기준을 연결하기 위한 확장 인터페이스."""

    @property
    @abstractmethod
    def status(self) -> str:
        """active, partial, mocked, unconnected 중 공급자 상태를 반환한다."""

    @abstractmethod
    def get_benchmark(
        self,
        *,
        company_name: str,
        as_of_date: pd.Timestamp,
        forecast_years: list[int],
        metric: str = 'revenue_growth',
        user_values: list[float] | None = None,
    ) -> PeerBenchmark | None:
        """기준일 현재 비교 가능한 동종기업 성장률·이익률 근거를 반환한다."""


class UnavailablePeerBenchmarkProvider(PeerBenchmarkProvider):
    @property
    def status(self) -> str:
        return 'unconnected'

    def get_benchmark(self, **_: object) -> None:
        return None


class MockPeerBenchmarkProvider(PeerBenchmarkProvider):
    """제품 흐름 검증용 동종기업 샘플 공급자.

    연결 상태는 active지만 값은 공식 실시간 공급자가 아닌 mock이다. 이 구분은
    모든 반환 결과의 경고와 source_label에 보존한다.
    """

    def __init__(self, source: str | Path | pd.DataFrame):
        self._data = pd.read_csv(source) if not isinstance(source, pd.DataFrame) else source.copy()

    @property
    def status(self) -> str:
        return 'active'

    def get_benchmark(
        self,
        *,
        company_name: str,
        as_of_date: pd.Timestamp,
        forecast_years: list[int],
        metric: str = 'revenue_growth',
        user_values: list[float] | None = None,
    ) -> PeerBenchmark | None:
        columns = {
            'revenue_growth': ('revenue_growth_pct', '매출 성장률'),
            'operating_margin': ('operating_margin_pct', '영업이익률'),
        }
        if metric not in columns:
            raise RecommendationError(f'지원하지 않는 Peer 지표입니다: {metric}')
        column, label = columns[metric]
        required = {'company_name', 'fiscal_year', column}
        if not required.issubset(self._data.columns):
            raise RecommendationError(f'Peer 샘플에 필수 열이 없습니다: {sorted(required)}')
        # 연간 수치는 통상 다음 해에 확정되므로 기준일의 연도보다 앞선 회계연도만 사용한다.
        available = self._data[pd.to_numeric(self._data['fiscal_year'], errors='coerce') < as_of_date.year]
        values = pd.to_numeric(available[column], errors='coerce').dropna().astype(float)
        if values.empty:
            return None
        lower, base, upper = (float(values.quantile(q)) for q in (.25, .5, .75))
        percentile = None
        if user_values:
            percentiles = [float((values <= value).mean() * 100) for value in user_values]
            percentile = float(sum(percentiles) / len(percentiles))
        peers = ', '.join(sorted(str(name) for name in available['company_name'].dropna().unique()))
        percentile_text = '' if percentile is None else f' 사용자 가정은 Peer 표본의 약 {percentile:.0f}백분위입니다.'
        return PeerBenchmark(
            suggested_range=(lower, upper),
            base_case=base,
            supporting_evidence=[
                f'Mock Peer({peers}) {label} {len(values)}개 표본의 중앙 50%는 '
                f'{lower:.2f}%~{upper:.2f}%입니다.{percentile_text}',
            ],
            conflicting_evidence=[],
            data_warnings=['Peer 값은 UI·연동 검증용 비검증 Mock 샘플이며 투자 판단 근거로 사용할 수 없습니다.'],
            user_percentile=percentile,
            sample_size=len(values),
            source_label='SK하이닉스·TSMC 비검증 Mock 샘플',
        )


def available_origin_years(data: pd.DataFrame) -> list[int]:
    if data.empty:
        return []
    rows = data[data['value_basis'] == 'current']
    return sorted(int(year) for year in rows['fiscal_year'].unique())


def _origin_row(data: pd.DataFrame, origin_year: int) -> pd.Series:
    rows = data[(data['fiscal_year'] == origin_year) & (data['value_basis'] == 'current')].sort_values('publication_date')
    verified = rows[rows['first_annual_report'] & rows['point_in_time_verified']]
    if not verified.empty:
        return verified.iloc[0]
    if not rows.empty:
        return rows.iloc[0]
    raise RecommendationError(f'{origin_year}년 당기 연간 매출 공시가 없습니다.')


def evaluation_metadata(data: pd.DataFrame, origin_year: int) -> dict:
    origin = _origin_row(data, int(origin_year))
    return {
        'company_name': str(origin['company_name']),
        'origin_year': int(origin_year),
        'cutoff_date': pd.Timestamp(origin['publication_date']),
        'current_revenue_krw': float(origin['revenue_krw']),
    }


def _snapshot(data: pd.DataFrame, origin_year: int, cutoff: pd.Timestamp) -> pd.DataFrame:
    available = data[(data['publication_date'] <= cutoff) & (data['fiscal_year'] <= origin_year)]
    return available.sort_values('publication_date').drop_duplicates('fiscal_year', keep='last').sort_values('fiscal_year')


def _historical_growths(snapshot: pd.DataFrame) -> pd.Series:
    revenue = snapshot.set_index('fiscal_year')['revenue_krw'].astype(float).sort_index()
    growths = []
    for year in revenue.index:
        if year - 1 in revenue.index and revenue.loc[year - 1] > 0 and revenue.loc[year] > 0:
            growths.append((revenue.loc[year] / revenue.loc[year - 1] - 1) * 100)
    return pd.Series(growths, dtype=float)


def _as_of_results(results: pd.DataFrame, cutoff: pd.Timestamp) -> pd.DataFrame:
    if results.empty:
        return results.copy()
    dates = pd.to_datetime(results['actual_publication_date'], errors='coerce')
    return results[dates.notna() & (dates <= cutoff)].copy()


def _normalize_assumptions(
    origin_year: int,
    assumptions: AssumptionValue,
    *,
    metric_label: str = '성장률',
) -> tuple[AssumptionValue, list[int], list[float]]:
    if isinstance(assumptions, dict):
        normalized = {int(year): float(growth) for year, growth in assumptions.items()}
        years = sorted(normalized)
        if len(years) not in {1, 3, 4, 5}:
            raise RecommendationError('다년도 가정은 3~5개년이어야 합니다. 단일 연도는 숫자 하나로 입력하세요.')
        expected = list(range(origin_year + 1, origin_year + 1 + len(years)))
        if years != expected:
            raise RecommendationError(f'예측 연도는 연속되어야 합니다: {expected}')
        values = [normalized[year] for year in years]
        output: AssumptionValue = normalized
    else:
        output = float(assumptions)
        years = [origin_year + 1]
        values = [float(assumptions)]
    if any(not math.isfinite(value) or value <= -100 for value in values):
        raise RecommendationError(f'모든 {metric_label}은 유한한 값이며 -100%보다 커야 합니다.')
    return output, years, values


def _case_value(value: float, years: list[int], multi_year: bool) -> AssumptionValue:
    return {year: value for year in years} if multi_year else value


def build_method_candidates(data: pd.DataFrame, origin_year: int) -> pd.DataFrame:
    meta = evaluation_metadata(data, origin_year)
    snapshot = _snapshot(data, origin_year, meta['cutoff_date'])
    revenue_map = snapshot.set_index('fiscal_year')['revenue_krw'].to_dict()
    current_revenue = meta['current_revenue_krw']
    rows = []
    for method, (name, formula, _) in METHODS.items():
        forecast, reason = predict(revenue_map, int(origin_year), method)
        rows.append({
            'method': method,
            '방식': name,
            '계산식': formula,
            '성장률 (%)': None if forecast is None else (forecast / current_revenue - 1) * 100,
            '예측 매출 (원)': forecast,
            '상태': '계산 불가' if reason else '참고 후보',
            '사유': reason,
        })
    return pd.DataFrame(rows)


def evaluate_user_assumptions(
    data: pd.DataFrame,
    results: pd.DataFrame,
    origin_year: int,
    user_assumptions: AssumptionValue,
    *,
    peer_provider: PeerBenchmarkProvider | None = None,
) -> RecommendationResult:
    """단일 또는 3~5개년 사용자 성장률을 기준일 현재 정보로 평가한다."""
    normalized, forecast_years, values = _normalize_assumptions(int(origin_year), user_assumptions)
    multi_year = isinstance(normalized, dict)
    meta = evaluation_metadata(data, int(origin_year))
    cutoff = meta['cutoff_date']
    snapshot = _snapshot(data, int(origin_year), cutoff)
    growths = _historical_growths(snapshot)
    if growths.empty:
        raise RecommendationError('연속된 과거 매출이 없어 성장률 범위를 계산할 수 없습니다.')

    lower = float(growths.quantile(.25))
    base = float(growths.quantile(.5))
    upper = float(growths.quantile(.75))
    result_range = (lower, upper)
    within_range = [lower <= value <= upper for value in values]

    supporting = [
        f"정보 기준일 {cutoff.date().isoformat()}까지 공개된 매출만 사용했습니다.",
        f'연속된 과거 성장률 {len(growths)}개의 중앙 50% 범위는 {lower:.2f}%~{upper:.2f}%입니다.',
    ]
    conflicting: list[str] = []
    warnings: list[str] = []
    if all(within_range):
        supporting.append('사용자 가정이 모든 예측 연도에서 기업 과거 성장률의 중앙 범위 안에 있습니다.')
    else:
        outside = [str(year) for year, ok in zip(forecast_years, within_range) if not ok]
        conflicting.append(f"{', '.join(outside)}년 사용자 가정이 기업 과거 성장률의 중앙 범위를 벗어납니다.")

    verified = bool(snapshot['point_in_time_verified'].all())
    reviewed = bool(snapshot['comparability_reviewed'].all())
    provider_status = {
        'company': 'active' if verified else 'partial',
        'latest_disclosure': 'partial',
        'peer': 'unconnected',
    }
    if verified:
        supporting.append('기업 매출 입력의 당시 공시 원문 확인 표시가 활성화되어 있습니다.')
    else:
        warnings.append('일부 기업 매출 입력의 당시 공시 원문이 검증되지 않았습니다.')
    if not reviewed:
        warnings.append('사업결합·매각·회계정책에 따른 비교 가능성 검토가 완전하지 않습니다.')
    if multi_year:
        warnings.append('현재 백테스트는 1년 예측만 검증했습니다. 2~5년차 시나리오는 같은 과거 분포를 연장한 참고값입니다.')

    peer = peer_provider or UnavailablePeerBenchmarkProvider()
    provider_status['peer'] = peer.status
    benchmark = peer.get_benchmark(
        company_name=meta['company_name'], as_of_date=cutoff, forecast_years=forecast_years,
        metric='revenue_growth', user_values=values,
    )
    if benchmark is None:
        warnings.append('동종기업·산업 기준은 아직 연결되지 않았습니다.')
    else:
        supporting.extend(benchmark.supporting_evidence)
        conflicting.extend(benchmark.conflicting_evidence)
        warnings.extend(benchmark.data_warnings)

    as_of = _as_of_results(results, cutoff)
    _, common, split = summarize(as_of)
    supporting.append(f'기준일까지 네 방식의 공통 검증 연도는 {len(common)}개입니다.')

    if not split.get('available'):
        verdict = 'insufficient'
        confidence = 'low'
        conflicting.append(split['reason'])
    else:
        selected_mape = float(split['test_mape_pct'])
        baseline_mape = float(split['baseline_test_mape_pct'])
        improvement = float(split['improvement_pp'])
        comparison = (
            f"선택 방식의 최종 MAPE는 {selected_mape:.2f}%, 매출 유지 기준은 "
            f'{baseline_mape:.2f}%로 개선 폭은 {improvement:.2f}%p입니다.'
        )
        if split['beats_baseline']:
            supporting.append(comparison)
        else:
            conflicting.append(comparison)

        if not all(within_range):
            verdict = 'adjust'
        elif not split['beats_baseline']:
            verdict = 'caution'
        else:
            verdict = 'retain'

        if not split['beats_baseline']:
            confidence = 'low'
        elif len(split['test_years']) >= 5 and reviewed and verified and peer.status == 'active':
            confidence = 'high'
        else:
            confidence = 'medium'

    return RecommendationResult(
        verdict=verdict,
        confidence=confidence,
        user_assumption=normalized,
        suggested_range=result_range,
        base_case=_case_value(base, forecast_years, multi_year),
        bear_case=_case_value(lower, forecast_years, multi_year),
        bull_case=_case_value(upper, forecast_years, multi_year),
        supporting_evidence=supporting,
        conflicting_evidence=conflicting,
        data_warnings=warnings,
        provider_status=provider_status,
    )


def _prepare_operating_margin_data(data: pd.DataFrame) -> pd.DataFrame:
    required = {
        'company_name', 'fiscal_year', 'publication_date', 'revenue_krw',
        'operating_profit_krw', 'point_in_time_verified', 'is_mock',
    }
    missing = sorted(required - set(data.columns))
    if missing:
        raise RecommendationError(f'영업이익률 데이터 필수 열이 없습니다: {missing}')
    prepared = data.copy()
    prepared['fiscal_year'] = pd.to_numeric(prepared['fiscal_year'], errors='coerce')
    prepared['publication_date'] = pd.to_datetime(prepared['publication_date'], errors='coerce')
    prepared['revenue_krw'] = pd.to_numeric(prepared['revenue_krw'], errors='coerce')
    prepared['operating_profit_krw'] = pd.to_numeric(prepared['operating_profit_krw'], errors='coerce')
    prepared = prepared.dropna(subset=['fiscal_year', 'publication_date', 'revenue_krw', 'operating_profit_krw'])
    prepared = prepared[prepared['revenue_krw'] > 0].copy()
    prepared['fiscal_year'] = prepared['fiscal_year'].astype(int)
    prepared['operating_margin_pct'] = prepared['operating_profit_krw'] / prepared['revenue_krw'] * 100
    if prepared.empty:
        raise RecommendationError('사용할 수 있는 영업이익률 데이터가 없습니다.')
    return prepared.sort_values(['fiscal_year', 'publication_date'])


def operating_margin_metadata(data: pd.DataFrame, origin_year: int) -> dict:
    prepared = _prepare_operating_margin_data(data)
    rows = prepared[prepared['fiscal_year'] == int(origin_year)].sort_values('publication_date')
    if rows.empty:
        raise RecommendationError(f'{origin_year}년 영업이익률 자료가 없습니다.')
    origin = rows.iloc[0]
    return {
        'company_name': str(origin['company_name']),
        'origin_year': int(origin_year),
        'cutoff_date': pd.Timestamp(origin['publication_date']),
        'current_revenue_krw': float(origin['revenue_krw']),
        'current_operating_profit_krw': float(origin['operating_profit_krw']),
        'current_operating_margin_pct': float(origin['operating_margin_pct']),
    }


def operating_margin_statistics(data: pd.DataFrame, origin_year: int) -> dict:
    prepared = _prepare_operating_margin_data(data)
    meta = operating_margin_metadata(prepared, int(origin_year))
    snapshot = prepared[
        (prepared['publication_date'] <= meta['cutoff_date'])
        & (prepared['fiscal_year'] <= int(origin_year))
    ].sort_values('publication_date').drop_duplicates('fiscal_year', keep='last').sort_values('fiscal_year')
    margins = snapshot['operating_margin_pct'].astype(float)
    if margins.empty:
        raise RecommendationError('기준일까지 공개된 영업이익률이 없습니다.')
    volatility = float(margins.std(ddof=1)) if len(margins) > 1 else 0.0
    category = '낮음' if volatility < 3 else ('보통' if volatility < 7 else '높음')
    return {
        'count': int(len(margins)),
        'mean': float(margins.mean()),
        'median': float(margins.median()),
        'lower': float(margins.quantile(.25)),
        'upper': float(margins.quantile(.75)),
        'minimum': float(margins.min()),
        'maximum': float(margins.max()),
        'stddev': volatility,
        'volatility_category': category,
        'latest': float(margins.iloc[-1]),
        'snapshot': snapshot,
    }


def evaluate_operating_margin_assumptions(
    data: pd.DataFrame,
    origin_year: int,
    user_assumptions: AssumptionValue,
    *,
    peer_provider: PeerBenchmarkProvider | None = None,
) -> RecommendationResult:
    """과거 영업이익률 분포와 변동성으로 단일·다년도 가정을 평가한다."""
    normalized, forecast_years, values = _normalize_assumptions(
        int(origin_year), user_assumptions, metric_label='영업이익률',
    )
    multi_year = isinstance(normalized, dict)
    prepared = _prepare_operating_margin_data(data)
    meta = operating_margin_metadata(prepared, int(origin_year))
    stats = operating_margin_statistics(prepared, int(origin_year))
    lower, base, upper = stats['lower'], stats['median'], stats['upper']
    within_range = [lower <= value <= upper for value in values]

    supporting = [
        f"정보 기준일 {meta['cutoff_date'].date().isoformat()}까지 공개된 영업이익률만 사용했습니다.",
        f"과거 {stats['count']}개년 평균은 {stats['mean']:.2f}%, 중앙값은 {base:.2f}%입니다.",
        f"중앙 50% 범위는 {lower:.2f}%~{upper:.2f}%이고 변동성은 "
        f"{stats['stddev']:.2f}%p({stats['volatility_category']})입니다.",
    ]
    conflicting: list[str] = []
    warnings = ['영업이익률 평가는 분포·변동성 검토이며 미래 마진의 정답이나 예측 백테스트가 아닙니다.']
    if all(within_range):
        supporting.append('사용자 영업이익률 가정이 모든 예측 연도에서 기업 과거 중앙 범위 안에 있습니다.')
    else:
        outside = [str(year) for year, ok in zip(forecast_years, within_range) if not ok]
        conflicting.append(f"{', '.join(outside)}년 영업이익률 가정이 기업 과거 중앙 범위를 벗어납니다.")
    if stats['volatility_category'] == '높음':
        conflicting.append('과거 영업이익률 변동성이 높아 단일 마진 가정의 지속 가능성에 주의가 필요합니다.')

    verified = bool(stats['snapshot']['point_in_time_verified'].astype(bool).all())
    provider_status = {
        'company': 'active' if verified else 'partial',
        'latest_disclosure': 'partial',
        'peer': 'unconnected',
    }
    if verified:
        supporting.append('영업이익과 매출의 당시 연간 공시 원문 확인 표시가 활성화되어 있습니다.')
    else:
        warnings.append('일부 영업이익률 입력의 당시 공시 원문이 검증되지 않았습니다.')
    if multi_year:
        warnings.append('2~5년차 영업이익률은 동일한 과거 분포를 연장한 시나리오이며 지속성이 검증되지 않았습니다.')

    peer = peer_provider or UnavailablePeerBenchmarkProvider()
    provider_status['peer'] = peer.status
    benchmark = peer.get_benchmark(
        company_name=meta['company_name'], as_of_date=meta['cutoff_date'],
        forecast_years=forecast_years, metric='operating_margin', user_values=values,
    )
    if benchmark is None:
        warnings.append('동종기업·산업 영업이익률 기준은 아직 연결되지 않았습니다.')
    else:
        supporting.extend(benchmark.supporting_evidence)
        conflicting.extend(benchmark.conflicting_evidence)
        warnings.extend(benchmark.data_warnings)

    if stats['count'] < 5:
        verdict: Verdict = 'insufficient'
        confidence: Confidence = 'low'
        conflicting.append('유효한 연간 영업이익률이 5개 미만이어서 판정을 확정하지 않습니다.')
    elif not all(within_range):
        verdict = 'adjust'
        confidence = 'low' if stats['volatility_category'] == '높음' else 'medium'
    elif stats['volatility_category'] == '높음':
        verdict = 'caution'
        confidence = 'low'
    else:
        verdict = 'retain'
        confidence = 'medium'

    return RecommendationResult(
        verdict=verdict,
        confidence=confidence,
        user_assumption=normalized,
        suggested_range=(lower, upper),
        base_case=_case_value(base, forecast_years, multi_year),
        bear_case=_case_value(lower, forecast_years, multi_year),
        bull_case=_case_value(upper, forecast_years, multi_year),
        supporting_evidence=supporting,
        conflicting_evidence=conflicting,
        data_warnings=warnings,
        provider_status=provider_status,
    )


def build_operating_margin_scenario_table(
    recommendation: RecommendationResult,
    *,
    origin_year: int,
) -> pd.DataFrame:
    cases = {
        '사용자 입력': recommendation.user_assumption,
        '보수': recommendation.bear_case,
        '기본': recommendation.base_case,
        '낙관': recommendation.bull_case,
    }
    rows = []
    for name, assumptions in cases.items():
        values = assumptions if isinstance(assumptions, dict) else {origin_year + 1: float(assumptions)}
        for year in sorted(values):
            rows.append({
                '시나리오': name,
                '예측 연도': int(year),
                '영업이익률 (%)': float(values[year]),
            })
    return pd.DataFrame(rows)


CAPITAL_RATIO_CONFIG = {
    'nwc_ratio': {
        'label': '매출액 대비 NWC 비율',
        'column': 'nwc_to_revenue_pct',
        'value_column': 'NWC/매출액 (%)',
        'definition': 'NWC = 매출채권 + 재고자산 − 매입채무',
    },
    'capex_ratio': {
        'label': '매출액 대비 CapEx 비율',
        'column': 'capex_to_revenue_pct',
        'value_column': 'CapEx/매출액 (%)',
        'definition': 'CapEx = 유형자산 취득 + 무형자산 취득 현금유출',
    },
}


def _prepare_capital_ratio_data(data: pd.DataFrame) -> pd.DataFrame:
    required = {
        'company_name', 'fiscal_year', 'publication_date', 'revenue_krw',
        'trade_receivables_krw', 'inventories_krw', 'trade_payables_krw',
        'ppe_acquisition_krw', 'intangible_acquisition_krw',
        'point_in_time_verified', 'is_mock',
    }
    missing = sorted(required - set(data.columns))
    if missing:
        raise RecommendationError(f'NWC·CapEx 데이터 필수 열이 없습니다: {missing}')
    prepared = data.copy()
    numeric = [
        'fiscal_year', 'revenue_krw', 'trade_receivables_krw', 'inventories_krw',
        'trade_payables_krw', 'ppe_acquisition_krw', 'intangible_acquisition_krw',
    ]
    for column in numeric:
        prepared[column] = pd.to_numeric(prepared[column], errors='coerce')
    prepared['publication_date'] = pd.to_datetime(prepared['publication_date'], errors='coerce')
    prepared = prepared.dropna(subset=numeric + ['publication_date'])
    prepared = prepared[prepared['revenue_krw'] > 0].copy()
    if prepared.empty:
        raise RecommendationError('사용할 수 있는 NWC·CapEx 데이터가 없습니다.')
    prepared['fiscal_year'] = prepared['fiscal_year'].astype(int)
    prepared['nwc_krw'] = (
        prepared['trade_receivables_krw'] + prepared['inventories_krw']
        - prepared['trade_payables_krw']
    )
    prepared['capex_krw'] = prepared['ppe_acquisition_krw'] + prepared['intangible_acquisition_krw']
    prepared['nwc_to_revenue_pct'] = prepared['nwc_krw'] / prepared['revenue_krw'] * 100
    prepared['capex_to_revenue_pct'] = prepared['capex_krw'] / prepared['revenue_krw'] * 100
    return prepared.sort_values(['fiscal_year', 'publication_date'])


def capital_ratio_metadata(data: pd.DataFrame, origin_year: int) -> dict:
    prepared = _prepare_capital_ratio_data(data)
    rows = prepared[prepared['fiscal_year'] == int(origin_year)].sort_values('publication_date')
    if rows.empty:
        raise RecommendationError(f'{origin_year}년 NWC·CapEx 자료가 없습니다.')
    origin = rows.iloc[0]
    return {
        'company_name': str(origin['company_name']),
        'origin_year': int(origin_year),
        'cutoff_date': pd.Timestamp(origin['publication_date']),
        'current_revenue_krw': float(origin['revenue_krw']),
        'current_nwc_krw': float(origin['nwc_krw']),
        'current_capex_krw': float(origin['capex_krw']),
        'current_nwc_ratio_pct': float(origin['nwc_to_revenue_pct']),
        'current_capex_ratio_pct': float(origin['capex_to_revenue_pct']),
    }


def capital_ratio_statistics(
    data: pd.DataFrame,
    origin_year: int,
    metric: CapitalRatioMetric,
) -> dict:
    if metric not in CAPITAL_RATIO_CONFIG:
        raise RecommendationError(f'지원하지 않는 자본효율 지표입니다: {metric}')
    prepared = _prepare_capital_ratio_data(data)
    meta = capital_ratio_metadata(prepared, int(origin_year))
    snapshot = prepared[
        (prepared['publication_date'] <= meta['cutoff_date'])
        & (prepared['fiscal_year'] <= int(origin_year))
    ].sort_values('publication_date').drop_duplicates('fiscal_year', keep='last').sort_values('fiscal_year')
    values = snapshot[CAPITAL_RATIO_CONFIG[metric]['column']].astype(float)
    if values.empty:
        raise RecommendationError('기준일까지 공개된 자본효율 비율이 없습니다.')
    volatility = float(values.std(ddof=1)) if len(values) > 1 else 0.0
    category = '낮음' if volatility < 2 else ('보통' if volatility < 5 else '높음')
    return {
        'count': int(len(values)),
        'mean': float(values.mean()),
        'median': float(values.median()),
        'lower': float(values.quantile(.25)),
        'upper': float(values.quantile(.75)),
        'minimum': float(values.min()),
        'maximum': float(values.max()),
        'stddev': volatility,
        'volatility_category': category,
        'latest': float(values.iloc[-1]),
        'trend_change_pp': float(values.iloc[-1] - values.iloc[-3]) if len(values) >= 3 else None,
        'snapshot': snapshot,
    }


def evaluate_capital_ratio_assumptions(
    data: pd.DataFrame,
    origin_year: int,
    user_assumptions: AssumptionValue,
    *,
    metric: CapitalRatioMetric,
) -> RecommendationResult:
    """NWC·CapEx의 매출 대비 비율을 기준일 당시 분포와 변동성으로 평가한다."""
    if metric not in CAPITAL_RATIO_CONFIG:
        raise RecommendationError(f'지원하지 않는 자본효율 지표입니다: {metric}')
    config = CAPITAL_RATIO_CONFIG[metric]
    normalized, forecast_years, values = _normalize_assumptions(
        int(origin_year), user_assumptions, metric_label=str(config['label']),
    )
    if any(value < 0 for value in values):
        raise RecommendationError(f"{config['label']}은 0% 이상이어야 합니다.")
    multi_year = isinstance(normalized, dict)
    prepared = _prepare_capital_ratio_data(data)
    meta = capital_ratio_metadata(prepared, int(origin_year))
    stats = capital_ratio_statistics(prepared, int(origin_year), metric)
    lower, base, upper = stats['lower'], stats['median'], stats['upper']
    within_range = [lower <= value <= upper for value in values]

    supporting = [
        f"정보 기준일 {meta['cutoff_date'].date().isoformat()}까지 공개된 연간 연결 자료만 사용했습니다.",
        f"{config['definition']}으로 계산했습니다.",
        f"과거 {stats['count']}개년 평균은 {stats['mean']:.2f}%, 중앙값은 {base:.2f}%입니다.",
        f"중앙 50% 범위는 {lower:.2f}%~{upper:.2f}%이고 변동성은 "
        f"{stats['stddev']:.2f}%p({stats['volatility_category']})입니다.",
    ]
    conflicting: list[str] = []
    warnings = [
        f"{config['label']} 평가는 과거 분포·변동성 검토이며 미래 현금흐름의 정답이나 예측 백테스트가 아닙니다.",
        '높은 비율은 운전자본 또는 투자 현금유출 부담이 커지는 방향이므로 보수·낙관 시나리오의 순서가 매출·마진과 반대입니다.',
    ]
    if metric == 'nwc_ratio':
        warnings.append('이 입력은 기말 NWC 잔액/매출 가정입니다. FCFF에서는 NWC 잔액 전체가 아니라 전년 대비 ΔNWC를 차감해야 합니다.')
    if all(within_range):
        supporting.append(f"사용자 {config['label']} 가정이 모든 예측 연도에서 기업 과거 중앙 범위 안에 있습니다.")
    else:
        outside = [str(year) for year, ok in zip(forecast_years, within_range) if not ok]
        conflicting.append(f"{', '.join(outside)}년 {config['label']} 가정이 기업 과거 중앙 범위를 벗어납니다.")
    if stats['volatility_category'] == '높음':
        conflicting.append(f"과거 {config['label']} 변동성이 높아 단일 비율 가정의 지속 가능성에 주의가 필요합니다.")
    if metric == 'capex_ratio' and stats['trend_change_pp'] is not None:
        direction = '상승' if stats['trend_change_pp'] > 0 else '하락'
        supporting.append(f"최근 비율은 2년 전보다 {abs(stats['trend_change_pp']):.2f}%p {direction}했습니다.")

    verified = bool(stats['snapshot']['point_in_time_verified'].astype(bool).all())
    provider_status = {
        'company': 'active' if verified else 'partial',
        'latest_disclosure': 'partial',
        'peer': 'unconnected',
    }
    if verified:
        supporting.append('구성 계정과 매출의 당시 연간 공시 원문 확인 표시가 활성화되어 있습니다.')
    else:
        warnings.append('일부 구성 계정의 당시 공시 원문이 검증되지 않았습니다.')
    notes = stats['snapshot'].get('comparability_note')
    if notes is not None and notes.astype(str).str.strip().ne('').any():
        warnings.append('사업결합·회계기준·업황 변화가 과거 비율 비교에 영향을 줄 수 있으므로 연도별 주석을 함께 확인하세요.')
    if multi_year:
        warnings.append(f"2~5년차 {config['label']}은 동일한 과거 분포를 연장한 시나리오이며 지속성이 검증되지 않았습니다.")
    warnings.append('동종기업·산업의 NWC·CapEx 기준은 아직 연결되지 않았습니다.')

    if stats['count'] < 5:
        verdict: Verdict = 'insufficient'
        confidence: Confidence = 'low'
        conflicting.append('유효한 연간 자료가 5개 미만이어서 판정을 확정하지 않습니다.')
    elif not all(within_range):
        verdict = 'adjust'
        confidence = 'low' if stats['volatility_category'] == '높음' else 'medium'
    elif stats['volatility_category'] == '높음':
        verdict = 'caution'
        confidence = 'low'
    else:
        verdict = 'retain'
        confidence = 'medium'

    # 단기 FCFF 관점에서 비율 상승은 부담이므로 bear=상단, bull=하단으로 배치한다.
    return RecommendationResult(
        verdict=verdict,
        confidence=confidence,
        user_assumption=normalized,
        suggested_range=(lower, upper),
        base_case=_case_value(base, forecast_years, multi_year),
        bear_case=_case_value(upper, forecast_years, multi_year),
        bull_case=_case_value(lower, forecast_years, multi_year),
        supporting_evidence=supporting,
        conflicting_evidence=conflicting,
        data_warnings=warnings,
        provider_status=provider_status,
    )


def evaluate_nwc_assumptions(
    data: pd.DataFrame,
    origin_year: int,
    user_assumptions: AssumptionValue,
) -> RecommendationResult:
    return evaluate_capital_ratio_assumptions(
        data, origin_year, user_assumptions, metric='nwc_ratio',
    )


def evaluate_capex_assumptions(
    data: pd.DataFrame,
    origin_year: int,
    user_assumptions: AssumptionValue,
) -> RecommendationResult:
    return evaluate_capital_ratio_assumptions(
        data, origin_year, user_assumptions, metric='capex_ratio',
    )


def build_capital_ratio_scenario_table(
    recommendation: RecommendationResult,
    *,
    origin_year: int,
    metric: CapitalRatioMetric,
) -> pd.DataFrame:
    if metric not in CAPITAL_RATIO_CONFIG:
        raise RecommendationError(f'지원하지 않는 자본효율 지표입니다: {metric}')
    value_column = CAPITAL_RATIO_CONFIG[metric]['value_column']
    cases = {
        '사용자 입력': recommendation.user_assumption,
        '보수': recommendation.bear_case,
        '기본': recommendation.base_case,
        '낙관': recommendation.bull_case,
    }
    rows = []
    for name, assumptions in cases.items():
        values = assumptions if isinstance(assumptions, dict) else {origin_year + 1: float(assumptions)}
        for year in sorted(values):
            rows.append({'시나리오': name, '예측 연도': int(year), value_column: float(values[year])})
    return pd.DataFrame(rows)


def build_scenario_table(
    recommendation: RecommendationResult,
    *,
    current_revenue_krw: float,
    origin_year: int,
) -> pd.DataFrame:
    """사용자·보수·기본·낙관 성장률을 연도별 매출로 복리 전개한다."""
    cases = {
        '사용자 입력': recommendation.user_assumption,
        '보수': recommendation.bear_case,
        '기본': recommendation.base_case,
        '낙관': recommendation.bull_case,
    }
    rows = []
    for name, assumptions in cases.items():
        values = assumptions if isinstance(assumptions, dict) else {origin_year + 1: float(assumptions)}
        revenue = float(current_revenue_krw)
        for year in sorted(values):
            growth = float(values[year])
            revenue *= 1 + growth / 100
            rows.append({'시나리오': name, '예측 연도': int(year), '성장률 (%)': growth, '예측 매출 (원)': revenue})
    return pd.DataFrame(rows)


def review_revenue_assumption(
    data: pd.DataFrame,
    results: pd.DataFrame,
    origin_year: int,
    user_growth_pct: float,
    *,
    peer_benchmark_available: bool = False,
) -> tuple[RecommendationResult, pd.DataFrame, pd.DataFrame]:
    """이전 단일연도 호출부를 위한 호환 래퍼."""
    if peer_benchmark_available:
        raise RecommendationError('불리언 Peer 표시는 지원하지 않습니다. PeerBenchmarkProvider를 전달하세요.')
    recommendation = evaluate_user_assumptions(data, results, origin_year, float(user_growth_pct))
    meta = evaluation_metadata(data, origin_year)
    return (
        recommendation,
        build_method_candidates(data, origin_year),
        build_scenario_table(recommendation, current_revenue_krw=meta['current_revenue_krw'], origin_year=origin_year),
    )
