"""고정된 원래 결과와 2023년 사례·주석 구간 진단을 재현한다. 원래 데이터/방식 파일은 수정하지 않는다."""
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from revenue_agent.schema import normalize, read_csv
from revenue_agent.backtest import run_backtest, summarize
from revenue_agent.review import trace_case, segment_diagnostics, comparative_checks


def main():
    out = ROOT / 'docs/review'
    lock = json.loads((out / 'original_lock.json').read_text(encoding='utf-8'))
    for path, expected in lock['method_files_sha256'].items():
        if hashlib.sha256((ROOT / path).read_bytes()).hexdigest() != expected:
            raise RuntimeError('원래 예측/평가 구현이 달라졌습니다: ' + path)
    if hashlib.sha256((ROOT / 'data/samsung_official_revenue.csv').read_bytes()).hexdigest() != lock['source_sha256']:
        raise RuntimeError('원래 실제 데이터가 달라졌습니다.')
    data = normalize(read_csv(ROOT / 'data/samsung_official_revenue.csv')).data
    results = run_backtest(data)
    summary, common, split = summarize(results)
    if split != lock['selection'] or common != lock['common_years']:
        raise RuntimeError('원래 선택/최종평가 결과가 달라졌습니다.')
    protocol = json.loads((out / 'review_protocol.json').read_text(encoding='utf-8'))
    inputs, case, in_time = trace_case(data, results)
    if not in_time:
        raise RuntimeError('2023년 사례의 예측 입력에 기준일 이후 공시가 포함되어 있습니다.')
    diagnostics = segment_diagnostics(results, protocol)
    checks = comparative_checks(data)
    for name, frame in [('case_2023_inputs', inputs), ('case_2023_results', case),
                        ('segment_diagnostics', diagnostics), ('comparative_checks', checks)]:
        frame.to_csv(out / f'{name}.csv', index=False, encoding='utf-8-sig')
    print('원래 자료·방식 해시 및 선택/평가 결과 보존: PASS')
    print('2023년 예측 입력 공시일 <= 기준일: PASS')
    print(f'비교표시 {len(checks)}행 중 최초 매출과 다른 행: {(checks["차이 (원)"] != 0).sum()}')
    print(diagnostics.pivot(index='구간', columns='방식', values='MAPE (%)').to_string())


if __name__ == '__main__':
    main()
