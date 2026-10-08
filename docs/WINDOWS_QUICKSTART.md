# Windows에서 매출 검토 화면 실행하기

이 안내는 초보자용입니다. 실제 매출 CSV가 포함되어 있어 **OpenDART 키 없이** 먼저 화면을 확인할 수 있습니다. 클라우드 Publish가 필요하지 않습니다. 아래 주소는 Windows PC에서 실행한 뒤 그 PC에서 접속하는 주소이며, 클라우드 서버의 외부 주소가 아닙니다.

## 1. 검토용 ZIP 내려받기

이 대화의 `KIC-revenue-review.zip`을 Windows의 **다운로드** 폴더에 저장하세요. 파일 이름을 그대로 유지하세요. 이번 코드가 GitHub main에 반영됐다고 가정하지 마세요. 제공 ZIP에는 현재 검토 코드가 들어 있습니다. 실제 키·가상환경·Git 이력은 포함하지 않았습니다.

Windows 시작 메뉴에서 **PowerShell**을 검색해 실행하세요. 한 블록씩 복사하고 Enter를 누르세요.

```powershell
Test-Path "$env:USERPROFILE\Downloads\KIC-revenue-review.zip"
```

`True`가 나와야 합니다. `False`면 실제로 저장한 위치와 파일 이름을 확인하세요. 아래 명령은 새 폴더에 압축을 풉니다. 이미 같은 폴더를 사용 중이면 날짜 뒤에 `-2` 같은 문자를 붙여 새 폴더를 사용하세요. 기존 작업을 덮어쓰지 마세요.

```powershell
Expand-Archive -LiteralPath "$env:USERPROFILE\Downloads\KIC-revenue-review.zip" -DestinationPath "$env:USERPROFILE\Documents\KIC-review-20261007"
Set-Location "$env:USERPROFILE\Documents\KIC-review-20261007\KIC-revenue"
Get-ChildItem
```

목록에 `app.py`, `requirements.txt`, `data`, `revenue_agent`가 보여야 합니다. ZIP 파일을 탐색기에서 직접 풀었다면 주소 표시줄에서 해당 폴더 경로를 복사한 뒤 `Set-Location "복사한 경로"`로 이동해도 됩니다.

## 2. Python 3.12 확인·설치

```powershell
py -3.12 --version
```

`Python 3.12.x`가 보이면 다음 단계로 진행하세요. 없으면 Microsoft의 winget이 있는 PC에서는 다음 명령을 실행할 수 있습니다.

```powershell
winget install --exact --id Python.Python.3.12
```

설치 중 Windows가 묻는 허용·약관을 확인한 뒤, **PowerShell을 닫고 새로 여세요.** 1단계 `Set-Location` 명령으로 프로젝트 폴더에 다시 들어가서 `py -3.12 --version`을 확인하세요.

winget도 없다면 python.org의 Downloads → Windows에서 **Python 3.12, Windows installer (64-bit)**를 설치하세요. Python Launcher(`py`) 설치 옵션을 선택하세요. 설치 후 PowerShell을 다시 열어 버전을 확인하세요.

## 3. 가상환경과 패키지 설치

프로젝트 폴더에서 순서대로 실행하세요.

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

처음에는 인터넷으로 패키지를 내려받으므로 시간이 걸립니다. 빨간 오류가 나오면 마지막 오류를 확인하고 다음 단계로 넘어가지 마세요. `activate` 명령이나 PowerShell 실행 정책 변경은 필요하지 않습니다.

## 4. 화면 실행

```powershell
.\.venv\Scripts\python.exe -m streamlit run app.py --server.address 127.0.0.1 --server.port 8501 --browser.gatherUsageStats false
```

PowerShell 창을 열린 상태로 두고 Edge 또는 Chrome 주소창에 다음을 입력하세요.

```text
http://localhost:8501
```

첫 화면의 데이터 입력은 **CSV**, 자료 선택은 **공식 원문 대조 자료 (2015~2025)**입니다. 다음을 확인하세요.

1. 실제 매출 추이와 네 방식의 예측 결과
2. 원래 선택/최종 평가 결과: CAGR 15.56%, 유지 13.49%
3. 아래쪽 `검토: 2023년 예측 한 건 추적`
4. `검토: 공식 주석의 비교 가능성`과 `검토: 원래 결과와 별도 구간 진단`
5. 결과 CSV 다운로드

창을 닫으면 서버가 종료될 수 있습니다. 종료할 때는 PowerShell에서 `Ctrl+C`를 누르세요. 다음에 실행할 때는 프로젝트 폴더로 이동한 뒤 4단계 실행 명령만 다시 입력하면 됩니다.

포트 사용 중 오류가 나오면 `--server.port 8502`로 실행하고 브라우저에서도 `http://localhost:8502`로 접속하세요. 화면이 안 뜨면 먼저 PowerShell 창의 오류를 확인하세요. 사내 PC의 설치·네트워크 정책은 임의로 끄지 마세요.

## 5. 키 없이 작동하는 기능과 키가 필요한 기능

| 기능 | OpenDART 키 | 최초 설치 후 인터넷 |
|---|---|---|
| 포함된 실제 CSV로 네 방식 백테스트·2023년 사례·주석 검토 보기 | 불필요 | 불필요 |
| 모의 CSV 실행·직접 CSV 업로드·결과 다운로드 | 불필요 | 불필요 |
| 공식 주석 PDF 링크 열기 | 불필요 | 필요 |
| 공개 DART 원문+공식 IR PDF를 다시 내려받아 CSV 생성 | 불필요 | 필요; 별도 개발 의존성 설치 필요 |
| 화면 `OpenDART`에서 API로 최신 매출 조회 | **필요** | 필요 |
| `scripts/collect_dart.py` API 수집 | **필요** | 필요 |

주석 검토와 구간 진단은 기본 제공 공식 CSV에 맞춰 작성했습니다. 다른 업로드 CSV에 동일한 주석을 자동 적용하지 않습니다. 현재 환경에서 **실제 공식 자료 수집은 완료했지만 OpenDART 실 API 호출은 키가 없어 미검증**입니다.

API 기능을 사용할 때만 로컬 키를 설정하세요. 키를 채팅에 붙여 넣거나 화면·Git에 올리지 마세요.

```powershell
Test-Path .env
```

`False`일 때만 예시를 복사하세요. `True`면 기존 `.env`를 그대로 보존하고 메모장으로 여세요.

```powershell
Copy-Item .env.example .env
notepad .env
```

메모장에서 `DART_API_KEY=` 뒤에 본인의 발급 키를 입력하고 저장하세요. 실제 값을 PowerShell 명령줄에 쓰거나 공유하지 마세요. 실행 중이었다면 `Ctrl+C`로 종료한 뒤 4단계 명령으로 다시 시작하고 화면에서 `OpenDART`를 선택하세요.

## 6. 선택 사항: 테스트와 공식 자료 재수집

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe scripts/review_revenue.py
```

공식 자료를 새로 조회하려면 새 출력 폴더를 지정하세요. 다음 경로는 API 키가 필요하지 않습니다.

```powershell
.\.venv\Scripts\python.exe scripts/build_official_csv.py --start-year 2015 --end-year 2025 --output-dir .local/official-new-review
```

이 명령은 기본 제공 실제 CSV를 덮어쓰지 않습니다. 공개 사이트의 구조·금액이 달라졌다면 오류를 확인하고 차이를 검토해야 합니다. 기존 결과가 나빴다는 이유로 데이터를 바꾸거나 방식을 다시 선택하지 마세요.

검증 환경은 Linux/Python 3.12입니다. 위 명령은 Windows용으로 작성했지만 Windows 실기기에서 직접 실행한 결과는 아닙니다.
