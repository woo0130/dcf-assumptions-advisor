"""UI 없이 CSV 백테스트 결과를 재현한다. 예: python scripts/backtest_csv.py data/mock_revenue.csv"""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from revenue_agent.schema import DataError, normalize, read_csv
from revenue_agent.backtest import run_backtest, summarize


def main():
    parser = argparse.ArgumentParser(description='연간 연결 매출 CSV 백테스트')
    parser.add_argument('input', type=Path)
    parser.add_argument('--output-dir', type=Path, default=Path('.local/results'))
    args = parser.parse_args()
    try:
        normalized = normalize(read_csv(args.input))
    except (DataError, OSError) as exc:
        parser.exit(1, f'입력 오류: {exc}\n')
    for warning in normalized.warnings:
        print(warning)
    if normalized.data.empty:
        parser.exit(1, '사용 가능한 연간 연결 자료가 없습니다.\n')
    results = run_backtest(normalized.data)
    summary, common, split = summarize(results)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    for name, frame in [('normalized', normalized.data), ('rejected', normalized.rejected),
                        ('backtest', results), ('summary', summary)]:
        frame.to_csv(args.output_dir / f'{name}.csv', index=False, encoding='utf-8-sig')
    (args.output_dir / 'selection.json').write_text(json.dumps(split, ensure_ascii=False, indent=2), encoding='utf-8')
    print('모의 데이터' if normalized.data['is_mock'].all() else '실제 입력 자료 (원문 검증 여부는 결과 기준 참조)')
    print(f'공통 평가 연도: {common}')
    print(summary.to_string(index=False))
    print(split['reason'])
    print(f'결과 저장: {args.output_dir.resolve()}')


if __name__ == '__main__':
    main()
