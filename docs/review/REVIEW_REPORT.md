# 매출 단계 검토 보고서

2026-10-07(한국 시간). 기존 CAGR 선택과 불리한 최종 평가 결과를 유지했습니다. 예측·평가 모듈과 실제 CSV의 SHA-256을 `original_lock.json`에 고정했고 재검증했습니다. Publish 및 영업이익률 확장은 진행하지 않았습니다.

## 실행과 화면 확인

현재 클라우드의 Streamlit 서버를 실행하고 실제 Chromium 브라우저에서 화면을 확인했습니다. 이 환경에는 외부 포트 공개/미리보기 도구가 제공되지 않아 클라우드 외부 접속 URL을 만들지 않았습니다. 내부 IP나 localhost를 외부 접속 주소로 안내하지 않습니다.

- 실제 화면 캡처: `preview_overview.png`, `preview_case_2023.png`, `preview_segments.png` (이미지이며 대화형 웹 링크가 아닙니다).
- 현재 검토용 코드 ZIP: `KIC-revenue-review.zip`.
- Windows에서 직접 실행·접속: [초보자용 순서 안내](../WINDOWS_QUICKSTART.md).

## 2023년 예측 추적

예측 기준일은 **2023-03-07**, 2022년 최초 사업보고서 `20230307000542` 공개일입니다. 그날 공시를 열람한 뒤 예측하는 일 단위 가정입니다. 공시 시각 이전 실행을 가정하지 않습니다. 대상은 **2023년 1~12월 전체 매출**이며 연초 이전 또는 기준일부터 향후 12개월 예측은 아닙니다. 기준일부터 연말까지 299일, 실제 정기보고서 발표까지 371일입니다.

사용한 수치와 공시 버전(금액 **조원**, KRW):

| 매출 연도 | 매출 (조원) | 사용한 값의 공시일 | 최초 당기 공시일 | 사용한 보고서 접수번호 | 표시 |
|---|---:|---|---|---|---|
| 2019 | 230.400881 | 2022-03-08 | 2020-03-30 | 20220308000798 | 비교표시 |
| 2020 | 236.806988 | 2023-03-07 | 2021-03-09 | 20230307000542 | 비교표시 |
| 2021 | 279.604799 | 2023-03-07 | 2022-03-08 | 20230307000542 | 비교표시 |
| 2022 | 302.231360 | 2023-03-07 | 2023-03-07 | 20230307000542 | 당기 |

2019년 값은 2021년 보고서의 전전기 비교표시(2022-03-08), 2020·2021년 값은 2022년 보고서의 비교표시(2023-03-07)를 사용했습니다. 최초 발표일로 잘못 소급하지 않았습니다. 해당 비교표시 금액은 최초 금액과 같음을 별도로 확인했습니다.

- 직전 성장률: 2021·2022년 사용. `302.231360 × (302.231360 / 279.604799)`; 성장률 **8.092336%**.
- 3년 CAGR: 2019·2022년으로 계산하고 2020·2021년 연속성도 확인. `302.231360 × (302.231360 / 230.400881)^(1/3)`; CAGR **9.467482%**.
- 3개 성장률 평균: 2019~2022년 사용. `g2020=2.780418%`, `g2021=18.072867%`, `g2022=8.092336%`; 평균 **9.648540%**. `302.231360 × (1 + (g2020+g2021+g2022)/3)`.
- 매출 유지: 2022년만 사용. `예측=302.231360`.

실제 2023년 매출은 **258.935494조원**, 최초 2023년 사업보고서 `20240312000736`의 **2024-03-12** 공시 값입니다. 오차는 예측−실제이며 네 방식 모두 과대 예측입니다. 표시는 소수점 여섯 자리까지 반올림했지만 계산에는 원래 수치를 사용했습니다.

| 방식 | 예측 (조원) | 실제 (조원) | 오차 (조원) | 절대오차 (조원) | APE |
|---|---:|---:|---:|---:|---:|
| 직전연도 성장률 유지 | 326.688938 | 258.935494 | +67.753444 | 67.753444 | 26.1661% |
| 최근 3년 CAGR 유지 | 330.845061 | 258.935494 | +71.909567 | 71.909567 | 27.7712% |
| 최근 3개 성장률 평균 | 331.392274 | 258.935494 | +72.456780 | 72.456780 | 27.9826% |
| 매출 유지 (기준) | 302.231360 | 258.935494 | +43.295866 | 43.295866 | 16.7207% |

**시점 확인:** `input_vintages`의 모든 공시일은 기준일 이하이며, 최대값은 2023-03-07입니다. 2023년 실적 및 그 이후 정정·비교표시는 입력에서 제외됐습니다. 2024-03-12 공시된 실제 값은 예측 이후 평가에만 사용했습니다. 이번 2015~2025년 주석 검토는 사후 설명용으로, 2023년 예측 입력·방식 선택에 추가하지 않았습니다.

원문: [2022년 사업보고서](https://dart.fss.or.kr/dsaf001/main.do?rcpNo=20230307000542), [2019년 값을 가져온 2021년 사업보고서](https://dart.fss.or.kr/dsaf001/main.do?rcpNo=20220308000798), [실제 2023년 사업보고서](https://dart.fss.or.kr/dsaf001/main.do?rcpNo=20240312000736). 상세 원문 문서번호와 값은 `case_2023_inputs.csv`, `case_2023_results.csv`에 보존했습니다.

## 공식 주석 검토: 확인과 미확인

검토 대상은 11개 연도의 공식 감사 연결재무제표 PDF에서 연결 범위, 사업결합, 매각예정, 회계정책 변경, 관계기업 및 연결 매출 비교표시입니다. 아래 페이지는 **PDF 뷰어 페이지**이며 본문 인쇄 페이지와 다를 수 있습니다. 모든 국문 사업보고서 주석과 개별 사업 양수도 계약을 전수 감사한 결과는 아닙니다. 기존 CSV를 다시 쓰거나 `comparability_reviewed`를 일괄 true로 바꾸지 않았습니다.

### 2015년

- **사업결합·연결 범위:** LoopPay(Samsung Pay), Simpress, YESCO 등 연결 편입. LoopPay 2015-02-23 인수 후 매출 4,871백만원.
- **매각·중단영업:** 광소재 사업 2015-03 매각. 주석에서 별도의 주요 사업이 아니므로 중단영업으로 표시하지 않았다고 명시. Techwin/General Chemicals 등의 지분 매각도 확인되나 지분 처분과 연결 매출 제거는 구분해야 함.
- **회계정책:** K-IFRS 1019 개정: 연결재무제표에 중요한 영향이 없다고 공시.
- **재작성 점검:** 확보된 당기·후속 비교표시 매출에서 차이 없음. 주석 전체의 재작성 부재를 보증하지 않음.
- **미확인:** LoopPay 외 편입 및 광소재 매각의 연결 매출 기여·감소액 전체는 확보하지 못함.

공식 근거: [주석 1 연결 범위 p.21](https://images.samsung.com/is/content/samsung/assets/global/ir/docs/2015_con_quarter04_all.pdf#page=21) · [주석 2.2 p.22](https://images.samsung.com/is/content/samsung/assets/global/ir/docs/2015_con_quarter04_all.pdf#page=22) · [주석 36 사업결합 p.90](https://images.samsung.com/is/content/samsung/assets/global/ir/docs/2015_con_quarter04_all.pdf#page=90) · [주석 37 매각예정 p.91](https://images.samsung.com/is/content/samsung/assets/global/ir/docs/2015_con_quarter04_all.pdf#page=91)

### 2016년

- **사업결합·연결 범위:** Joyent(2016-06-24), Dacor(2016-09-07), Viv Labs(2016-10-07) 인수. 인수 후 Joyent 매출 14,142백만원, Dacor 16,239백만원. AdGear 등 다른 연결 편입도 있음.
- **매각·중단영업:** 프린팅 사업 HP 매각 계약(2016-09-12) 및 매각예정 자산·부채 분류. 이 분류만으로 중단영업이라고 단정하지 않음.
- **회계정책:** K-IFRS 1001 공시 개정은 중요한 영향이 없다고 공시.
- **재작성 점검:** 확보된 당기·후속 비교표시 매출에서 차이 없음. 주석 전체의 재작성 부재를 보증하지 않음.
- **미확인:** Viv Labs 및 다른 편입의 매출 기여, 프린팅 사업의 연도별 외부 매출·제거액 미확인.

공식 근거: [주석 1 연결 범위 p.22](https://images.samsung.com/is/content/samsung/assets/global/ir/docs/2016_con_quarter04_all.pdf#page=22) · [주석 2.2 p.23](https://images.samsung.com/is/content/samsung/assets/global/ir/docs/2016_con_quarter04_all.pdf#page=23) · [주석 35 Joyent p.91](https://images.samsung.com/is/content/samsung/assets/global/ir/docs/2016_con_quarter04_all.pdf#page=91) · [주석 35 Dacor/Viv Labs p.92](https://images.samsung.com/is/content/samsung/assets/global/ir/docs/2016_con_quarter04_all.pdf#page=92) · [주석 35~36 p.93](https://images.samsung.com/is/content/samsung/assets/global/ir/docs/2016_con_quarter04_all.pdf#page=93) · [주석 36 매각예정 p.94](https://images.samsung.com/is/content/samsung/assets/global/ir/docs/2016_con_quarter04_all.pdf#page=94)

### 2017년

- **사업결합·연결 범위:** Harman 2017-03-10 인수. 인수 후 기여 매출 7,103,437백만원, 연초부터 연결 가정 매출 8,581,461백만원. 일부 기간 연결되어 2018년과도 연결 기간 차이가 존재.
- **매각·중단영업:** 프린팅 사업 HP 매각 2017-11-01 완료. 전기 CE 부문을 Others로 재분류하여 부문 비교표시를 재작성했으나 연결 총매출은 동일.
- **회계정책:** K-IFRS 1007 개정은 재무활동 부채 변동 공시 관련. 2018년 시행 예정 기준과 당기 적용을 구분.
- **재작성 점검:** 확보된 당기·후속 비교표시 매출에서 차이 없음. 주석 전체의 재작성 부재를 보증하지 않음.
- **미확인:** Harman·프린팅을 모두 동일 범위·동일 기간으로 맞춘 유기적 연결 매출 계열은 미확보. 인수 기여액을 단순 차감해 성장률을 재구성하지 않음.

공식 근거: [주석 1 연결 범위 p.25](https://images.samsung.com/is/content/samsung/assets/global/ir/docs/2017_con_quarter04_all.pdf#page=25) · [주석 2.2 p.28](https://images.samsung.com/is/content/samsung/assets/global/ir/docs/2017_con_quarter04_all.pdf#page=28) · [주석 32 부문 재분류 p.95](https://images.samsung.com/is/content/samsung/assets/global/ir/docs/2017_con_quarter04_all.pdf#page=95) · [주석 35 Harman p.101](https://images.samsung.com/is/content/samsung/assets/global/ir/docs/2017_con_quarter04_all.pdf#page=101) · [주석 36 프린팅 매각 p.102](https://images.samsung.com/is/content/samsung/assets/global/ir/docs/2017_con_quarter04_all.pdf#page=102)

### 2018년

- **사업결합·연결 범위:** Zhilabs 편입, NexusDX 매각 및 그룹 내 합병 확인. 주석 35의 Harman 설명은 2017년 거래 재기재이며 2018년 신규 인수로 중복 집계하지 않음.
- **매각·중단영업:** 연결 범위 변동은 있으나 이 검토에서 연결 총매출의 중단영업 재작성은 발견하지 못함.
- **회계정책:** K-IFRS 1115(수익)·1109(금융상품) 최초 적용, 비교기간 미재작성. 1115로 2018년 매출이 243,760,820 → 243,771,415백만원(＋10,595) 변경. 이는 2018년 인식 기준 차이이며 2017년 매출 재작성액이 아님.
- **재작성 점검:** 확보된 당기·후속 비교표시 매출에서 차이 없음. 주석 전체의 재작성 부재를 보증하지 않음.
- **미확인:** 2017년을 1115로 환산한 매출 및 모든 연결 범위 변화의 순효과 미확보.

공식 근거: [주석 1 연결 범위 p.27](https://images.samsung.com/is/content/samsung/assets/global/ir/docs/2018_con_quarter04_all.pdf#page=27) · [주석 1~2.2/1109 p.28](https://images.samsung.com/is/content/samsung/assets/global/ir/docs/2018_con_quarter04_all.pdf#page=28) · [주석 2.2/1115 p.31](https://images.samsung.com/is/content/samsung/assets/global/ir/docs/2018_con_quarter04_all.pdf#page=31) · [주석 2.2/매출 영향 p.32](https://images.samsung.com/is/content/samsung/assets/global/ir/docs/2018_con_quarter04_all.pdf#page=32) · [주석 35: 2017년 인수 재기재 p.102](https://images.samsung.com/is/content/samsung/assets/global/ir/docs/2018_con_quarter04_all.pdf#page=102)

### 2019년

- **사업결합·연결 범위:** Corephotonics 인수 후 기여 매출 1,102백만원, 연초 연결 가정 1,421백만원. PLP 사업 2019-06-01 인수 후 매출 없음이라고 공시. Foodient·Dowooinsys 등도 신규 편입.
- **매각·중단영업:** 연결 내부 합병·청산은 확인되나 신규 외부 매출로 자동 간주하지 않음.
- **회계정책:** K-IFRS 1116 리스 최초 적용, 비교기간 미재작성. 주된 공시 영향은 사용권자산·리스부채이며 매출 직접 영향액은 미확인.
- **재작성 점검:** 확보된 당기·후속 비교표시 매출에서 차이 없음. 주석 전체의 재작성 부재를 보증하지 않음.
- **미확인:** Dowooinsys 등 전체 편입의 외부 매출 기여, 리스 기준 전환의 매출 영향액 미확보.

공식 근거: [주석 1 연결 범위 p.28](https://images.samsung.com/is/content/samsung/assets/global/ir/docs/2019_con_quarter04_all.pdf#page=28) · [주석 1~2.2 p.29](https://images.samsung.com/is/content/samsung/assets/global/ir/docs/2019_con_quarter04_all.pdf#page=29) · [주석 2.2/리스 p.30](https://images.samsung.com/is/content/samsung/assets/global/ir/docs/2019_con_quarter04_all.pdf#page=30) · [주석 34 Corephotonics p.93](https://images.samsung.com/is/content/samsung/assets/global/ir/docs/2019_con_quarter04_all.pdf#page=93) · [주석 34 PLP p.94](https://images.samsung.com/is/content/samsung/assets/global/ir/docs/2019_con_quarter04_all.pdf#page=94)

### 2020년

- **사업결합·연결 범위:** TeleWorld Solutions 및 관련 법인 연결 편입 확인.
- **매각·중단영업:** SSM(쑤저우 모듈) 100%, SSL(쑤저우 LCD) 60% 지분 매각 계약(2020-08-28), 연말 매각예정 분류.
- **회계정책:** K-IFRS 1103 사업 정의 개정: 중요한 연결재무제표 영향이 없다고 공시.
- **재작성 점검:** 확보된 당기·후속 비교표시 매출에서 차이 없음. 주석 전체의 재작성 부재를 보증하지 않음.
- **미확인:** TeleWorld 매출 기여와 SSM/SSL 외부 매출 분리액 미확인. 매각예정과 중단영업을 동일시하지 않음.

공식 근거: [주석 1.4 p.27](https://images.samsung.com/is/content/samsung/assets/global/ir/docs/2020_con_quarter04_all.pdf#page=27) · [주석 2.2 p.28](https://images.samsung.com/is/content/samsung/assets/global/ir/docs/2020_con_quarter04_all.pdf#page=28) · [주석 32 매각예정 p.93](https://images.samsung.com/is/content/samsung/assets/global/ir/docs/2020_con_quarter04_all.pdf#page=93)

### 2021년

- **사업결합·연결 범위:** 법인 신설 및 그룹 내 합병·청산이 확인됨. 연결 편입 변동 자체를 독립 외부 사업 인수와 동일시하지 않음.
- **매각·중단영업:** SSM/SSL 매각 2021-04-01 완료 및 연결 제외. 매출 연결 기간이 전기와 달라짐.
- **회계정책:** K-IFRS 1116 코로나 임차료 감면 실무적 간편법은 중요한 영향이 없다고 공시.
- **재작성 점검:** 확보된 당기·후속 비교표시 매출에서 차이 없음. 주석 전체의 재작성 부재를 보증하지 않음.
- **미확인:** 매각 사업의 기중 기여 매출·매각 후 감소액과 계속영업 기준 동일범위 매출을 확보하지 못함.

공식 근거: [주석 1.4 p.26](https://images.samsung.com/is/content/samsung/assets/global/ir/docs/2021_con_quarter04_all.pdf#page=26) · [주석 2.2 p.28](https://images.samsung.com/is/content/samsung/assets/global/ir/docs/2021_con_quarter04_all.pdf#page=28) · [주석 32 매각 완료 p.94](https://images.samsung.com/is/content/samsung/assets/global/ir/docs/2021_con_quarter04_all.pdf#page=94)

### 2022년

- **사업결합·연결 범위:** Apostera, Red Brick Lane Marketing Solutions 인수·연결 편입 확인.
- **매각·중단영업:** 주석의 관계기업 중단영업을 삼성전자 자체 연결 매출의 중단영업으로 해석하지 않음.
- **회계정책:** K-IFRS 1116·1103·1016·1037 개정은 중요한 영향이 없다고 공시. 1016의 시운전 생산물 판매대금 처리 변경도 검토 범위에 포함.
- **재작성 점검:** 확보된 당기·후속 비교표시 매출에서 차이 없음. 주석 전체의 재작성 부재를 보증하지 않음.
- **미확인:** 신규 편입 회사의 매출 기여·유기적 성장 조정액 미확보.

공식 근거: [주석 1.4 p.26](https://images.samsung.com/is/content/samsung/assets/global/ir/docs/2022_con_quarter04_all.pdf#page=26) · [주석 2.2 p.27](https://images.samsung.com/is/content/samsung/assets/global/ir/docs/2022_con_quarter04_all.pdf#page=27) · [주석 9 관계기업 p.54](https://images.samsung.com/is/content/samsung/assets/global/ir/docs/2022_con_quarter04_all.pdf#page=54)

### 2023년

- **사업결합·연결 범위:** eMagin 2023-10-18 인수. 연결 편입 후 매출 4,684백만원, 연초 연결 가정 27,781백만원. Roon Labs도 편입.
- **매각·중단영업:** Dowooinsys 지분 56.8% 매각 계약(2023-12-07), 매각예정 분류. 관계기업 주석의 중단영업은 별도 구분.
- **회계정책:** 1001 회계정책 공시 변경, 1008 추정 정의, 1012 이연법인세/Pillar Two 개정 확인. 매출을 재작성하는 정책 변경으로 확인된 것은 아님.
- **재작성 점검:** 확보된 당기·후속 비교표시 매출에서 차이 없음. 주석 전체의 재작성 부재를 보증하지 않음.
- **미확인:** Roon 및 Dowooinsys의 연결 매출 기여 미확인. eMagin의 소규모 기여만으로 2023년 예측 오차 원인을 설명할 수 없음.

공식 근거: [주석 1.4 p.26](https://images.samsung.com/is/content/samsung/assets/global/ir/docs/2023_con_quarter04_all.pdf#page=26) · [주석 2.2 p.27](https://images.samsung.com/is/content/samsung/assets/global/ir/docs/2023_con_quarter04_all.pdf#page=27) · [주석 9 관계기업 p.47](https://images.samsung.com/is/content/samsung/assets/global/ir/docs/2023_con_quarter04_all.pdf#page=47) · [주석 9 비교표시 p.48](https://images.samsung.com/is/content/samsung/assets/global/ir/docs/2023_con_quarter04_all.pdf#page=48) · [주석 32 eMagin p.86](https://images.samsung.com/is/content/samsung/assets/global/ir/docs/2023_con_quarter04_all.pdf#page=86) · [주석 33 매각예정 p.87](https://images.samsung.com/is/content/samsung/assets/global/ir/docs/2023_con_quarter04_all.pdf#page=87)

### 2024년

- **사업결합·연결 범위:** Sonio·Oxford Semantic Technologies 등 연결 편입.
- **매각·중단영업:** Dowooinsys 2024-01-31 매각 완료. 관련 VINA, Gf-System 등 연결 제외 확인.
- **회계정책:** 1001 부채 분류·1116 판매후리스·1007/1107 공급자금융 개정 확인. 매출 직접 영향액은 확인되지 않음.
- **재작성 점검:** 확보된 당기·후속 비교표시 매출에서 차이 없음. 주석 전체의 재작성 부재를 보증하지 않음.
- **미확인:** 인수·매각 전체의 순매출 영향 미확보. 관계기업의 중단영업/분류 변경은 삼성전자 총매출 재작성과 구분.

공식 근거: [주석 1.4 p.26](https://images.samsung.com/is/content/samsung/assets/global/ir/docs/2024_con_quarter04_all.pdf#page=26) · [주석 2.2 p.27](https://images.samsung.com/is/content/samsung/assets/global/ir/docs/2024_con_quarter04_all.pdf#page=27) · [주석 9 관계기업 p.47](https://images.samsung.com/is/content/samsung/assets/global/ir/docs/2024_con_quarter04_all.pdf#page=47) · [주석 9 비교표시 p.48](https://images.samsung.com/is/content/samsung/assets/global/ir/docs/2024_con_quarter04_all.pdf#page=48) · [주석 9 바이오로직스 불확실성 p.50](https://images.samsung.com/is/content/samsung/assets/global/ir/docs/2024_con_quarter04_all.pdf#page=50) · [주석 32 매각 완료 p.87](https://images.samsung.com/is/content/samsung/assets/global/ir/docs/2024_con_quarter04_all.pdf#page=87)

### 2025년

- **사업결합·연결 범위:** Rainbow Robotics(2025-03-12 지분 취득 완료 후 지배력 확보), Sound United, FläktGroup 등 주요 사업결합. Xealth 등 추가 편입도 확인.
- **매각·중단영업:** Harman Connected Services 계열의 여러 법인 매각·연결 제외가 확인됨.
- **회계정책:** K-IFRS 1021 환율 교환가능성 개정은 중요한 영향이 없다고 공시. 미래 IFRS 18 시행 예정은 당기 매출 재작성으로 취급하지 않음.
- **재작성 점검:** 후속 연간 비교표시 없음. 현재 원문 매출만 확인.
- **미확인:** 주석 33의 인수대금·영업권은 매출이 아님. 인수·매각 각각의 연결 매출 기여·감소액 및 동일범위 연간 매출은 미확보. 2025년은 후속 연간 비교표시가 없어 미래 재작성 여부를 판단할 수 없음.

공식 근거: [주석 1.4 편입 p.27](https://images.samsung.com/is/content/samsung/assets/global/ir/docs/2025_con_quarter04_all.pdf#page=27) · [주석 1.4 편입 p.28](https://images.samsung.com/is/content/samsung/assets/global/ir/docs/2025_con_quarter04_all.pdf#page=28) · [주석 1.4 매각 p.29](https://images.samsung.com/is/content/samsung/assets/global/ir/docs/2025_con_quarter04_all.pdf#page=29) · [주석 2.2 p.30](https://images.samsung.com/is/content/samsung/assets/global/ir/docs/2025_con_quarter04_all.pdf#page=30) · [주석 9 관계기업 p.51](https://images.samsung.com/is/content/samsung/assets/global/ir/docs/2025_con_quarter04_all.pdf#page=51) · [주석 9 바이오로직스 불확실성 p.54](https://images.samsung.com/is/content/samsung/assets/global/ir/docs/2025_con_quarter04_all.pdf#page=54) · [주석 33 Rainbow Robotics p.92](https://images.samsung.com/is/content/samsung/assets/global/ir/docs/2025_con_quarter04_all.pdf#page=92) · [주석 33 취득배분 p.93](https://images.samsung.com/is/content/samsung/assets/global/ir/docs/2025_con_quarter04_all.pdf#page=93) · [주석 33 Sound United p.94](https://images.samsung.com/is/content/samsung/assets/global/ir/docs/2025_con_quarter04_all.pdf#page=94) · [주석 33 FläktGroup p.95](https://images.samsung.com/is/content/samsung/assets/global/ir/docs/2025_con_quarter04_all.pdf#page=95)

### 재작성·중단영업에 대한 종합 판단

- 2015~2024년 **19개 후속 비교표시 매출 행**을 최초 당기 값과 대조했고, 차이는 **0행**입니다. 2025년은 후속 연간 비교표시가 없습니다. 이는 확보한 매출 계열의 점검이며 모든 계정·주석의 수정이 없다는 보증이 아닙니다.
- 2026-10-07 DART 비최종 전용 필터 없이 연간 목록을 재조회해 대상 보고서 11건을 확인했고 정정 표시 건수는 0건이었습니다(`filing_review.json`). 조회 범위 밖 문서나 향후 정정 가능성까지 배제하지 않습니다.
- 2017년 CE 부문 재분류는 부문 정보의 재작성입니다. 이를 연결 총매출 재작성과 혼동하지 않았습니다.
- 2018년 IFRS 15 도입의 2018년 매출 증가분은 **10,595백만원(105.95억원)**, 해당 연도 매출의 약 **0.00435%**입니다. 비교기간을 재작성하지 않았으므로 기준 전환을 걸치는 성장률은 동일 기준이 아닙니다. 2019년 리스 전환도 비교기간 미재작성이나 매출의 직접 영향액은 확인하지 못했습니다.
- Harman의 2017년 인수 후 기여 매출 **7,103,437백만원(약 7.1034조원)**은 그해 총매출의 약 **2.965%**입니다. 이 비율은 주석상 기여액의 크기 비교이며, 인수가 없었을 때의 연결 매출이나 예측 오차 기여율을 뜻하지 않습니다.
- eMagin의 2023년 편입 후 매출 **4,684백만원(46.84억원)**은 해당 연도 총매출의 약 **0.00181%**입니다. 이를 2023년 큰 예측 오차의 원인으로 단정하지 않습니다.
- 매각예정/사업매각이 곧 중단영업 표시는 아닙니다. 2015년 광소재는 중단영업 미표시를 명시했습니다. 다른 매각 건에 대해서는 검토한 연결손익계산서/주석과 확보된 매출에서 연결 총매출의 중단영업 재작성은 확인하지 못했지만, 건별 회계적 판단을 모두 독립 검증한 것은 아닙니다.
- 2023~2025년 주석 9의 관계기업 중단영업과 삼성바이오로직스 재작성 관련 불확실성은 관계기업 지분법/투자 장부금액 등과 관련됩니다. 이를 삼성전자 자체 연결 매출 조정으로 옮기지 않았습니다.
- **미확인:** 인수·매각 전체의 기여/제거 매출, 동일 범위 유기적 매출, 2025년 주요 인수·매각의 순매출 영향, 향후 정정·재작성. 인수대금·영업권을 매출에서 차감하지 않았습니다.

## 원래 결과와 별도 구간 진단

원래 데이터·방식·선택 기간·최종 평가 기간을 고정했습니다. 아래 경계는 주석 사건과 최장 3년 입력창의 포함 연도로 정했고, 오차가 작은 구간을 찾는 최적화는 하지 않았습니다. **이 구간 분석 자체는 사후 탐색적 진단이며 독립적으로 사전 등록된 실험이 아닙니다.** 모든 구간과 네 방식을 표시합니다. 구간은 중복되므로 표본 수를 합산하지 마세요.

지표는 MAPE, 단위 %. 각 행은 네 방식이 같은 평가 연도를 사용합니다.

| 구간 | 평가 연도 | 표본/방식 | 직전 성장률 | 3년 CAGR | 3개 성장률 평균 | 매출 유지 |
|---|---|---:|---:|---:|---:|---:|
| 원래 공통 평가 전체 | 2019, 2020, 2021, 2022, 2023, 2024, 2025 | 7 | 13.59 | 11.44 | 11.29 | 10.25 |
| IFRS 15 전후 입력이 섞인 구간 | 2019, 2020, 2021 | 3 | 9.55 | 10.07 | 10.31 | 7.94 |
| 입력이 모두 IFRS 15 적용 이후인 구간 | 2022, 2023, 2024, 2025 | 4 | 16.61 | 12.46 | 12.02 | 11.99 |
| 원래 최종 평가 구간 | 2023, 2024, 2025 | 3 | 19.08 | 15.56 | 15.11 | 13.49 |
| eMagin 인수 연도 | 2023 | 1 | 26.17 | 27.77 | 27.98 | 16.72 |
| 도우인시스 매각 완료 연도 | 2024 | 1 | 26.27 | 11.34 | 10.54 | 13.94 |
| 2025년 주요 인수·매각 연도 | 2025 | 1 | 4.79 | 7.58 | 6.82 | 9.81 |

- IFRS 15 전후가 섞이는 표본은 목표 연도 2019~2021년입니다. 목표 2022년부터는 4개 입력 연도가 모두 2018년 이후입니다. 이 구간도 사업결합·매각에서 자유롭다는 의미는 아닙니다.
- 2017년 Harman 인수와 2018년 전환을 목표 연도로 직접 네 방식 비교하려면 더 이른 매출이 필요하므로 원래 자료로는 공통 표본을 만들 수 없습니다. 일부 방식만 성능을 비교하거나 앞선 연도를 채우지 않았습니다.
- 2025년 CAGR은 그 한 해에서 기준보다 낫지만, 원래 최종 평가인 **2023~2025년 CAGR 15.56% vs 유지 13.49%**는 그대로입니다. 2025년만 선택해 우수한 방식이라고 보고하지 않습니다.
- 전체 검토 연도에 연결 범위 변화가 있습니다. 사건이 없는 ‘깨끗한 표본’을 얻었다는 주장은 할 수 없습니다. 동일 범위 매출을 재구성할 증거가 부족해 인수·매각액으로 수치를 조정하지 않았습니다.
- 사후 설명·구간 기술 통계는 인과 효과 추정이나 새로운 모델 추천이 아닙니다. 다음 단계 확장은 사용자 검토 후 결정합니다.

## 재현 파일

`python scripts/review_revenue.py`로 2023년 추적·비교표시·구간 표를 재생성합니다. `original_lock.json`은 원래 소스·알고리즘 해시와 선택 결과를 잠그며, 달라지면 재현 스크립트와 테스트가 실패합니다. 공식 주석 요약은 `data/comparability_review.json`, 원문 파일 해시는 `note_source_manifest.json`에 있습니다.

## 실행 검증

2026-10-07 Linux/Python 3.12에서 전체 테스트 50개가 통과했습니다. 마지막 화면 표시 수정 후 관련 테스트 8개도 통과했습니다. 실제 Chromium 브라우저에서 Streamlit 화면을 열어 JavaScript 오류 없이 3개 화면을 캡처했습니다. 원래 CSV·예측·평가 코드의 해시와 기존 최종 평가 결과가 유지되는지 자동 확인했습니다.

현재 클라우드 내부 Streamlit은 8501번 포트에서 실행했습니다. 이 세션에는 외부 미리보기 주소를 발급하는 기능이 없어 화면 캡처와 Windows 실행용 ZIP을 제공합니다. Publish는 진행하지 않았습니다. Windows 실기기 실행과 OpenDART 실 API 호출은 미검증입니다.
