import math

METHODS = {
    'last_growth': ('직전연도 성장률 유지', 'gₜ = Rₜ/Rₜ₋₁ − 1; 예측 = Rₜ × (1+gₜ)', 1),
    'cagr3': ('최근 3년 CAGR 유지', 'g = (Rₜ/Rₜ₋₃)^(1/3) − 1; 예측 = Rₜ × (1+g)', 3),
    'mean3': ('최근 3개 성장률 평균', 'g = (gₜ₋₂ + gₜ₋₁ + gₜ)/3; 예측 = Rₜ × (1+g)', 3),
    'flat': ('매출 유지 (기준)', '예측 = Rₜ', 0),
}


def predict(revenues: dict[int, float], origin_year: int, method: str):
    if method not in METHODS:
        raise ValueError('알 수 없는 예측 방식')
    needed = range(origin_year - METHODS[method][2], origin_year + 1)
    missing = [y for y in needed if y not in revenues]
    if missing:
        return None, f'필요한 연속 연도 부족: {missing}'
    if any(not math.isfinite(float(revenues[y])) or revenues[y] <= 0 for y in needed):
        return None, '입력 매출에 0·음수·비유한 값이 있습니다.'
    r = float(revenues[origin_year])
    if method == 'flat':
        value = r
    elif method == 'last_growth':
        value = r * (r / revenues[origin_year - 1])
    elif method == 'cagr3':
        value = r * (r / revenues[origin_year - 3]) ** (1 / 3)
    else:
        growth = [revenues[y] / revenues[y - 1] - 1 for y in range(origin_year - 2, origin_year + 1)]
        value = r * (1 + sum(growth) / 3)
    if not math.isfinite(value) or value <= 0:
        return None, '계산 결과가 유한한 양수가 아닙니다.'
    return value, ''
