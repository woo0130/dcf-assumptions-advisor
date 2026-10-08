"""로컬 비밀 설정을 사용하여 API 응답과 정규화 전 CSV를 저장한다."""
import argparse
from datetime import date
import json
import os
from pathlib import Path
import sys

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from revenue_agent.collect import DartClient, DartError


def main():
    parser = argparse.ArgumentParser(description='삼성전자 연간 연결 매출 수집')
    parser.add_argument('--start-year', type=int, default=max(2015, date.today().year - 10))
    parser.add_argument('--end-year', type=int, default=date.today().year - 1)
    parser.add_argument('--output-dir', type=Path, default=Path('.local/dart'))
    args = parser.parse_args()
    load_dotenv(ROOT / '.env', override=False)
    try:
        data, audit, warnings = DartClient(os.environ.get('DART_API_KEY', '')).collect(args.start_year, args.end_year)
    except DartError as exc:
        parser.exit(1, str(exc) + '\n')
    args.output_dir.mkdir(parents=True, exist_ok=True)
    data.to_csv(args.output_dir / 'revenue.csv', index=False, encoding='utf-8-sig')
    (args.output_dir / 'raw_response.json').write_text(json.dumps(audit, ensure_ascii=False, indent=2), encoding='utf-8')
    for warning in warnings:
        print(warning)
    print(f'확보된 회계연도 수: {len(data)} / 요청 {args.start_year}~{args.end_year}')
    print('현재 API 응답: 당시 원문과 최초 보고서 값은 미검증입니다.')
    if data.empty:
        parser.exit(1, '매출을 확보하지 못했습니다. 원본 응답과 경고를 확인하세요.\n')


if __name__ == '__main__':
    main()
