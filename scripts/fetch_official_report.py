"""삼성전자 공식 감사 연결재무제표를 TLS 검증을 유지하여 확보한다.
다운로드만으로 공시일, 최초 DART 사업보고서 또는 과거 시점 수치가 검증되지는 않는다.
"""
import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
import urllib.error
import urllib.request


def main():
    parser = argparse.ArgumentParser(description='삼성전자 공식 연간 감사 연결재무제표 PDF 확보')
    parser.add_argument('--year', type=int, required=True)
    parser.add_argument('--output-dir', type=Path, default=Path('.local/official'))
    args = parser.parse_args()
    if not 2015 <= args.year < datetime.now().year:
        parser.error('2015년 이후 완료된 회계연도를 지정하세요.')
    url = f'https://images.samsung.com/is/content/samsung/assets/global/ir/docs/{args.year}_con_quarter04_all.pdf'
    try:
        with urllib.request.urlopen(url, timeout=45) as response:
            payload = response.read(50 * 1024 * 1024 + 1)
    except (urllib.error.URLError, TimeoutError):
        parser.exit(1, '공식 PDF를 받지 못했습니다. 도메인 허용과 공식 IR의 문서 경로를 확인하세요.\n')
    if not payload.startswith(b'%PDF') or len(payload) > 50 * 1024 * 1024:
        parser.exit(1, '정상 PDF가 아니거나 50MB 제한을 넘었습니다.\n')
    args.output_dir.mkdir(parents=True, exist_ok=True)
    path = args.output_dir / f'{args.year}_consolidated.pdf'
    if path.exists() and path.read_bytes() != payload:
        parser.exit(1, '기존 PDF와 새 내용이 다릅니다. 기존 증거를 보존하도록 다른 출력 폴더를 지정하세요.\n')
    path.write_bytes(payload)
    metadata = {'source_url': url, 'retrieved_at': datetime.now(timezone.utc).isoformat(),
                'sha256': hashlib.sha256(payload).hexdigest(), 'file': path.name,
                'status': '공식 PDF 확보; 매출·공시일·정정 여부는 수동 대조 필요'}
    (args.output_dir / f'{args.year}_source.json').write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'공식 PDF 저장: {path}')
    print('연결 손익계산서 Revenue와 단위·대상 기간을 대조하세요. 최초 사업보고서 여부는 DART에서 별도로 확인하세요.')


if __name__ == '__main__':
    main()
