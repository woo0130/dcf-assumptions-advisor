# DCF Assumptions Advisor (Reviewer UX)

한국 상장기업의 DCF 가정을 과거 실적과 공시 근거로 검토하고, 실무에 적용할 시나리오를 제안하는 Streamlit 서비스입니다. 현재 삼성전자 연결재무제표를 기준으로 네 가지 핵심 가정을 지원합니다.

## 주요 기능

- **4대 가정 검토:** 매출 성장률, 영업이익률, NWC/매출액, CapEx/매출액
- **4단계 Reviewer UX:** 자료 확인 → 질문 입력 → 즉시 판정·시나리오 → 상세 근거
- **시점 통제:** 공시일 기준으로 미래 정보를 차단해 Look-ahead bias를 방지
- **검증 방법 구분:** 매출은 시간순 백테스트, 나머지 항목은 과거 분포·변동성으로 검토
- **실무 내보내기:** 세션에서 검토한 가정을 Markdown, JSON, Excel/DCF 연동용 CSV로 통합 다운로드
- **3~5개년 시나리오:** 보수·기본·낙관 가정을 연도별로 확인

## 1분 실행 가이드

Python 3.12가 필요합니다. ZIP 파일을 먼저 완전히 압축 해제한 뒤 프로젝트 폴더에서 실행하세요. 첫 실행은 가상환경 생성과 패키지 설치 때문에 몇 분 걸릴 수 있으며, 이후 실행은 더 빠릅니다.

### Windows

파일 탐색기에서 `run_app.bat`을 더블 클릭하거나 PowerShell에서 다음 명령을 실행합니다.

```powershell
cd C:\Users\woosj\Downloads\KIC-revenue-review\KIC-revenue
.\run_app.bat
```

스크립트가 `.venv`를 자동 생성하고 의존성을 설치한 뒤 Streamlit을 시작합니다. 브라우저가 자동으로 열리지 않으면 터미널에 표시된 `Local URL`을 브라우저에 입력하세요.

### macOS

터미널에서 프로젝트 폴더로 이동한 뒤 최초 한 번 실행 권한을 부여하고 실행합니다.

```bash
cd /path/to/KIC
chmod +x run_app.sh
./run_app.sh
```

### Linux

```bash
cd /path/to/KIC
chmod +x run_app.sh
./run_app.sh
```

종료하려면 앱을 실행한 터미널에서 `Ctrl+C`를 누릅니다. 기본 제공 공식 대조 CSV 기능은 OpenDART 키 없이 실행됩니다.

## 프로젝트 개요

삼성전자(005930 / DART 00126380)의 **연간 연결 매출**을 이용해 다음 회계연도 매출 가정 네 가지를 비교하는 Python/Streamlit 앱입니다. 장기간 공식 연결재무제표를 제공하는 비금융 제조업이라는 이유로 선정했습니다. 반도체 사이클·사업 구성 변화의 영향은 따로 검토해야 합니다.

현재 화면은 **DCF Assumptions Advisor의 Reviewer UX**를 제공합니다. `매출 성장률 / 영업이익률 / 순운전자본(NWC) / 설비투자(CapEx)`를 전환한 뒤 질문에 답하고 `가정 검토하기`를 누르면 입력 가정, `retain/adjust/caution/insufficient` 판정, 권고 범위, 기본 시나리오, 신뢰도와 한 줄 해석을 먼저 표시합니다. 이어서 DCF 적용용 보수·기본·낙관 시나리오와 판단 근거를 보여주며, 세션에서 검토한 항목을 공통 CSV·Markdown·JSON에 누적해 내보냅니다. 매출의 기존 네 방식 그래프와 MAPE·공시 근거는 맨 아래 `왜 이런 결론이 나왔나요? (상세 분석)`에 접어 두었습니다. 영업이익률·NWC·CapEx는 과거 평균·중앙값·25~75% 범위·표준편차로 검토하며 예측 백테스트로 표현하지 않습니다. 3~5개년 입력도 별도 접기 메뉴에서 지원합니다. 제품 구조와 판정 규칙은 [DCF Assumptions Advisor 구조](docs/ASSUMPTION_ADVISOR.md)에 정리했습니다.

NWC는 `매출채권 + 재고자산 − 매입채무`, CapEx는 연결 현금흐름표의 `유형자산 취득 + 무형자산 취득` 현금유출로 정의합니다. NWC 입력은 기말 잔액/매출 가정이며 실제 FCFF에는 이 잔액의 전년 대비 증감(ΔNWC)을 사용해야 합니다. 두 비율은 단기 FCFF 관점에서 높을수록 현금 유출 부담이 커지므로 보수 시나리오가 과거 상단, 낙관 시나리오가 과거 하단입니다. 원본 구성 계정과 공식 PDF 근거는 `data/samsung_nwc_capex.csv`에 보존합니다.

SK하이닉스·TSMC 동종기업 비교는 매출·영업이익률에만 **비검증 Mock 샘플 공급자**가 연결되어 있습니다. NWC·CapEx Peer는 미연결입니다. 화면 상태는 공급자 연결이 실제 동작한다는 의미에서 `활성화됨`으로 표시하지만, 공식·실시간 Peer 데이터라는 뜻은 아니며 판정의 보조 지표로만 사용합니다. Markdown 검토 보고서와 Excel/Power Query용 공통 long-form DCF 시나리오 CSV를 다운로드할 수 있습니다.

**현재 검증 상태:** 삼성전자 **2015~2025년 11개 연도**의 실제 매출을 확보했습니다. 최근 10년(2016~2025)에 초기 예측 입력용 2015년을 추가했습니다. 각 연도의 최초 DART 사업보고서 접수번호·공시일과 고정 원문을 확인하고, 당기·전기 매출을 삼성전자 공식 감사 연결재무제표 PDF 11개와 대조했습니다. 전부 일치했습니다. `data/samsung_official_revenue.csv`에는 당기·비교표시를 구분한 **30개 공시 버전 행**이 있으며, 키 없이 기본 화면에서 분석됩니다. `data/official_evidence.json`에 원문 URL·SHA-256·페이지·공시일·매출 행 대조 근거를 보존했습니다.

OpenDART API 자체의 실제 호출은 키가 없어 미검증입니다. 실제 자료 검증은 **공식 DART 웹 원문 + 공식 IR PDF → CSV** 경로로 완료했습니다. `data/mock_revenue.csv`는 별도로 구분한 2015~2024년 모의 수치·모의 공시일이며 실제 실적이 아닙니다.

NWC·CapEx 비율 검토까지 제공하지만 매출 전망과 결합한 실제 FCFF 계산, 감가상각, 세금, WACC, 영구성장률, DCF 가치평가, LLM 및 유료 AI API 기능은 이번 범위에 포함하지 않았습니다.

### 수동 설치 및 실행

원클릭 스크립트를 사용하지 않는 경우 저장소 루트에서 아래 순서로 실행합니다.

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m streamlit run app.py
```

기본 화면은 `CSV` → `공식 원문 대조 자료 (2015~2025)`이며 키 없이 실제 매출 결과가 표시됩니다. `직접 업로드`로 자신의 CSV를 입력하거나 `모의 데이터 (2015~2024)`로 예외·화면을 확인할 수 있습니다. 금액 그래프·예측표는 **억원(KRW)**, 원본 및 결과 CSV는 **원(KRW)** 또는 원래 단위를 명시합니다.

macOS/Linux:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m streamlit run app.py
```

저장소를 새 worktree로 분리할 필요가 없습니다. 클라우드 작업은 이미 격리되어 있으므로 기존 checkout에서 진행하세요.

### OpenDART 키와 네트워크

키는 채팅·로그·Git에 넣지 않습니다. 다음 중 하나만 설정하세요.

- `.env.example`을 로컬 `.env`로 복사한 뒤 `DART_API_KEY=`에 발급받은 키 입력
- 운영체제 환경변수 `DART_API_KEY`
- Streamlit 실행 시 로컬 `.streamlit/secrets.toml`에 `DART_API_KEY = "발급받은 값"`

`.env`, `.streamlit/secrets.toml`은 Git 제외 설정에 포함되어 있습니다. 키는 화면에 표시하거나 API 원본 다운로드에 포함하지 않습니다. CLI 수집은 환경변수와 `.env`를 지원하며, Streamlit secrets는 웹 앱에서만 읽습니다. API 예외는 요청 URL을 출력하지 않습니다.

필요한 HTTPS 도메인: `opendart.fss.or.kr`, `dart.fss.or.kr`, `www.samsung.com`, `images.samsung.com`. 패키지 설치에는 PyPI 접속이 필요합니다. 개발 클라우드에는 위 공식 도메인 추가를 설정 초안으로 저장했고, 이후 DART 웹 원문 및 삼성전자 공식 PDF 조회 성공을 실제 확인했습니다. 설정 초안 저장과 환경 게시(Publish)는 별도 절차입니다.

OpenDART 화면에서 시작·종료 연도를 선택하고 수집 버튼을 누르세요. 기본은 최근 완료된 10개 회계연도입니다. 2015년 이후만 요청하며, 실제 확보 연도 수와 누락을 표시합니다. 연결 손익계산서 `IS/CIS`, 매출 표준 계정, `reprt_code=11011`, `fs_div=CFS`, `thstrm_amount`(당기)만 사용합니다. 표준 계정이 없을 때 정해진 매출 계정명으로만 대체하고 서로 다른 후보가 있으면 제외합니다. 재무 API 접수번호를 사업보고서 목록과 대조해 공시일·정정 여부를 가져옵니다. API가 기간을 제공하지 않으면 사업보고서 제목의 12월 결산과 연간 보고서 코드로 기간을 매핑하고 **기간 원문 미검토**를 표시합니다.

API의 재무 수치를 과거 원본으로 간주하지 않습니다. 목록의 최초 보고서를 발견해도 API 금액이 그 당시 금액임을 보장할 수 없어 `point_in_time_verified=false`, `first_annual_report=false`로 저장합니다. 키 누락·인증 실패·호출 한도·네트워크 오류·매출 누락을 별도 처리합니다. HTTP 429/일시적 서버 오류만 최대 3회 시도합니다.

```powershell
.\.venv\Scripts\python.exe scripts/collect_dart.py --start-year 2016 --end-year 2025
.\.venv\Scripts\python.exe scripts/backtest_csv.py .local/dart/revenue.csv --output-dir .local/dart-results
```

원본 JSON·CSV·분석 출력은 기본적으로 Git 제외 폴더 `.local/`에 저장합니다. CLI 결과를 보존하려면 실행마다 다른 `--output-dir`을 사용하세요.

### CSV 입력 형식과 원문 확인

`data/manual_template.csv`는 헤더만 있는 수동 입력 서식입니다. `data/mock_revenue.csv`는 형식을 보여주는 **모의** 예제입니다. UTF-8(가능하면 BOM)으로 저장하세요. 종목코드·기업코드·접수번호를 Excel에서 숫자로 변환하지 마세요. CSV의 각 행은 **연도 하나의 매출에 대한 특정 공시 버전**입니다. 같은 연도라도 원문·정정·후속 보고서 비교표시는 별도 행으로 보존합니다.

| 열 | 의미 및 허용값 |
|---|---|
| company_name, stock_code, corp_code | 기업명, `005930`, `00126380` |
| fiscal_year | 매출의 대상 회계연도 |
| period_start, period_end | 대상 기간 `YYYY-01-01`, `YYYY-12-31`; 분기·비정상 결산기간은 제외 |
| revenue, unit, currency | 원문 수치, `원/천원/백만원/억원`, `KRW`; 원으로 환산 |
| fs_div, report_type | `CFS`, `annual` 고정 |
| publication_date | **이 행의 수치를 공개한 보고서** 공시일 `YYYY-MM-DD` |
| receipt_no | DART 14자리 접수번호; DART 외 공식 IR이면 빈 값 가능 |
| source_url | 원문 HTTPS 링크; DART viewer 또는 공식 보고서 PDF |
| is_correction | 정정공시 여부 `true/false` |
| retrieved_at | 조회 시각: 예 `2026-10-06T09:00:00+09:00` (시간대 필수) |
| value_basis | `current` 당기 / `comparative` 후속 보고서 비교표시 |
| source_fiscal_year | 수치를 가져온 보고서의 대상 연도; comparative는 fiscal_year보다 커야 함 |
| point_in_time_verified | **그 공시 당시 원문 금액**을 직접 확인했으면 true; 현재 API 조회만으로 true 금지 |
| first_annual_report | 해당 연도 최초 연간 정기보고서의 당기 값임을 확인했으면 true; 정정·비교표시는 false |
| comparability_notes | 합병·분할·중단영업·재작성·기간 차이·정정 내역; 미검토라면 미검토를 명시 |
| comparability_reviewed | 해당 비교 가능성 항목을 원문에서 검토했는지 `true/false` |
| is_mock | 모의이면 true; 실제와 모의 혼합 불가 |
| evidence_note | 원문 제목·쪽·표·행 및 확인 방법. 당시 검증 true일 때 필수 |

불리언은 `true/false`만 허용합니다. 예: 2024년 보고서에 표시된 2023년 매출은 `fiscal_year=2023`, `source_fiscal_year=2024`, `value_basis=comparative`, 공시일은 **2024년 보고서 공시일**로 기록합니다. 과거 연도에 소급해 공시일을 붙이면 안 됩니다. 정정 전 원문을 보관하고 정정 수치로 덮어쓰지 마세요.

공식 자료 대조 절차:

1. [삼성전자 감사 재무제표](https://www.samsung.com/global/ir/reports-disclosures/audited-financial-statements/)에서 연결 보고서를 확보합니다. `python scripts/fetch_official_report.py --year 2024`로 알려진 공식 PDF 경로를 시도할 수도 있습니다. 문서 URL이 바뀌면 공식 IR에서 확인하세요. 이 스크립트는 원문과 URL·조회 시각·SHA-256을 저장하며 TLS 검증을 유지합니다.
2. 연결 손익계산서 `Revenue` 행에서 회계기간·KRW 단위·당기/전기 열을 확인합니다. 전기 수치가 다음 보고서에서 달라지면 두 버전과 원문 쪽수를 모두 기록합니다. PDF 파일명으로 공시일을 추정하지 마세요.
3. [DART](https://dart.fss.or.kr/)에서 최초 연간 사업보고서와 정정 내역, 공개 날짜·접수번호를 확인합니다. IR 감사보고서 공개일과 DART 최초 정기보고서 공시일을 같은 것으로 간주하지 마세요.
4. CSV 금액을 원으로 환산한 값과 공식 표 금액의 환산값이 같은지 대조하고, 차이가 있으면 연결/별도·당기/전기·재작성·단위를 먼저 확인합니다. 확인한 원문 쪽과 표 행을 `evidence_note`에 기록합니다.
5. 합병·분할·중단영업·회계정책 변경 주석을 검토합니다. `comparability_notes`가 있는 연도는 자동 제외하지 않으며 화면에 경고합니다. 필요하면 해당 관측을 제외한 별도 CSV로 민감도를 확인하고 제외 사유를 기록하세요.

기본 제공 실제 CSV는 위 절차로 **11개 연도 당기·전기 매출 대조를 완료**했습니다. 최초 사업보고서는 DART 비정정 연간 목록에서 확인했고, 각 접수번호의 문서번호(dcmNo)를 지정한 원문에서 매출을 가져왔습니다. 후속 보고서의 전기·전전기 수치는 실제 후속 공시일로 저장합니다. 전전기 수치는 DART 원문에서 확인했으며 해당 PDF와의 교차 대조 대상은 당기·전기입니다.

재현 명령(문서 파서 의존성을 포함한 `requirements-dev.txt` 설치 필요):

```powershell
.\.venv\Scripts\python.exe scripts/build_official_csv.py --start-year 2015 --end-year 2025 --output-dir .local/official-build
.\.venv\Scripts\python.exe scripts/backtest_csv.py .local/official-build/samsung_official_revenue.csv --output-dir .local/official-results
```

이 스크립트는 공개 DART 연간 공시 목록 → 해당 접수번호 원문 → 연결 손익계산서 → 공식 감사 PDF를 순서대로 대조합니다. 같은 출력 폴더로 재실행하면 기존 원문을 재사용하며, 최신 재조회에는 새 폴더를 지정합니다. HTML 구조·기간·단위·금액 대조가 실패하면 CSV를 완성하지 않고 오류를 보고합니다. 원문과 해시를 보존하되 큰 PDF는 Git에 포함하지 않습니다. CSV 업로드의 검증 플래그는 작성자의 증거 확인을 전제로 하며 앱이 임의 업로드 파일의 진위를 인증하지 않습니다.

확인한 비교 가능성 문제는 2017년 Harman 인수(감사 PDF p.101, 주석 35), 2018년 IFRS 15 최초 적용 및 비교기간 미재작성(감사 PDF p.31~32)입니다. 이 경고를 CSV에 넣었으며, 모든 주석을 전수 검토한 것은 아니므로 `comparability_reviewed=false`를 유지했습니다.

### 예측·평가 규칙

- 직전 성장률: `R_t × (R_t / R_(t−1))`
- 3년 CAGR: `R_t × (R_t / R_(t−3))^(1/3)`; 중간 연도까지 4개 연속 매출 필수
- 3개 성장률 평균: `R_t × [1 + mean(g_(t−2), g_(t−1), g_t)]`
- 매출 유지 기준: `R_t`

수작업 예시: 매출이 100 → 110 → 121 → 133.1이면 세 성장 방식의 다음 예측은 146.41, 유지 기준은 133.1입니다. 100 → 120 → 90 → 108이면 산술평균 성장률은 `(20%−25%+20%)/3=5%`, 예측은 113.4로 CAGR과 다릅니다. 테스트에서 이 값을 검증합니다.

예측 기준일은 t년 당기 연간 실적 공개일입니다. 검증된 최초 정기보고서를 우선하고, 없으면 확보한 당기 행 중 가장 이른 공시일을 쓰며 **회고적 비교**로 표시합니다. 입력은 그 날까지 공시된 각 연도의 가장 최근 버전만 사용합니다. 이후 정정·비교표시 값은 이전 예측에 들어가지 않습니다. 입력 공시 버전은 결과 CSV의 `input_vintages` JSON에 기록합니다. 예측은 t+1년 **전체 회계연도** 대상이며, 기준일에서 연말·실제 공시일까지 남은 일수를 함께 저장합니다. t+1 실적이 이미 발표되었거나 t+1 연말 이후라면 해당 예측을 평가에서 제외합니다.

평가 실제는 검증된 최초 연간 정기보고서 당기 값을 우선합니다. 없으면 확보된 가장 이른 당기 값을 사용하고 미검증임을 명시합니다. 정정 여부·실제 사용 기준·출처를 결과에 보존합니다. 예측 입력 및 최초 실제 원문이 확인되지 않으면 **‘최신 재무자료 기반의 회고적 비교’**로 표시합니다. 날짜 필터는 검증되지 않은 API 수치의 재작성 가능성을 제거하지 못합니다.

입력이 0·음수·비유한 값이거나 필요한 연도가 없으면 예측을 만들지 않습니다. 실제가 0·음수이면 금액 오차는 보이되 백분율 성능 표본에서 제외합니다. 마지막 연도의 예측은 계산 가능하면 보여주지만 실제 미확보로 점수에 포함하지 않습니다.

오차 = 예측−실제, 절대오차 = |오차|, APE = |오차|/실제×100, MAPE = 평균 APE, 평균 부호 백분율오차 = 평균(오차/실제×100)입니다. 양수 편향은 과대, 음수는 과소 예측을 의미합니다. **네 방식이 모두 유효한 동일 연도**로 성능을 계산하고 방식별 전체 유효 연도·표본 수를 따로 표시합니다. 기준 개선도는 `유지 MAPE − 해당 MAPE`(%p)입니다. 공통 표본이 없으면 성능을 억지로 생성하지 않습니다.

공통 평가 연도가 7개 이상일 때만 앞선 약 60%(최소 4개 연도)에서 성장 방식 후보를 고르고 마지막 최소 3개 연도로 최종 평가합니다. 선택 기간 실제 값이 첫 최종 평가 기준일까지 공개되었는지도 확인합니다. 공통 표본 7개 미만이면 추천하지 않습니다. 이 기준은 소표본 신뢰를 보장하는 통계 기준이 아닙니다. 10개 연도 자료에서 3년 방식의 공통 평가는 보통 6개 연도뿐이므로 추천이 나오지 않는 것이 정상입니다. 최종 평가 결과는 매출 유지와 별도로 비교하며, 전체 기간 성능표는 기술 통계입니다.

### 재현·테스트

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe scripts/backtest_csv.py data/mock_revenue.csv --output-dir .local/mock-results
```

모듈: `collect.py`(수집), `schema.py`(정규화·출처), `forecast.py`(가정 계산), `backtest.py`(시점별 예측·평가), `app.py`(한국어 UI). 네트워크 없는 단위 테스트는 모의 API 응답임을 구분합니다. 계산식, 단위, 분기/별도 제외, 미래 정정·비교표시 배제, 최초 실제 유지, 0/음수, 누락, 공통 표본, 시간순 선택, 키를 숨긴 오류, Streamlit 화면을 확인합니다. 실제 DART 웹 원문/IR 수집·대조, 실제 CSV 분석, Streamlit 기본 실제 화면 검증도 포함합니다. OpenDART API 통합 검증 및 Windows 실기기 실행은 이번 환경에서 수행하지 못했습니다.

실제 공통 평가 기간 **2019~2025년, 7개 표본**의 MAPE는 직전 성장률 13.59%, 3년 CAGR 11.44%, 3개 성장률 평균 11.29%, 매출 유지 10.25%입니다. 전체 기간 결과만으로 방식을 추천하지 않습니다. **2019~2022년 선택 기간**에서는 CAGR이 선택됐지만, **2023~2025년 최종 평가**에서는 MAPE 15.56%로 유지 기준 13.49%보다 2.07%p 나빴습니다. 세 성장 후보가 기준을 이긴다는 근거가 없습니다.

실제 FCFF 계산으로 확장하기 전에는 NWC 정의에 기타 영업채권·채무를 포함할지 확정하고, CapEx와 감가상각·리스·사업결합 취득액을 구분하며, 비교 가능성 주석의 전수 검토와 실제 Peer 공급자 연결을 완료해야 합니다.

### 매출 단계 검토 자료 (2026-10-07)

[2023년 예측 추적·2015~2025년 공식 주석·구간 진단 보고서](docs/review/REVIEW_REPORT.md)와 [초보자용 Windows 설치·실행 순서](docs/WINDOWS_QUICKSTART.md)를 추가했습니다. 기본 실제 CSV 화면 아래에도 같은 검토 내용을 표시합니다. 원래 매출·예측 방식·선택/최종 평가 기간과 CAGR의 불리한 결과는 유지했습니다. 별도 구간은 사후 진단이며 방식 재선택에 쓰지 않습니다.

`python scripts/review_revenue.py`는 원래 파일 해시 및 선택 결과를 확인한 뒤 추적·구간 CSV를 재생성합니다. 코드 ZIP과 실제 화면 캡처는 `docs/review`에 있습니다. 클라우드 Publish는 진행하지 않았습니다.
