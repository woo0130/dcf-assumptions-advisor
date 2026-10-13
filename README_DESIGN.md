# KIC RESEARCH 스타일 UI 업데이트

기존 프로젝트 루트에 app.py를 교체하고 revenue_agent 폴더의 세 파일을 함께 교체/추가하세요.
workspace_theme.py는 신규 필수 파일입니다. .streamlit/config.toml은 프로젝트 루트의 .streamlit 폴더에 배치하세요.
기존 backtest.py, forecast.py, recommendation.py, schema.py, collect.py, review.py와 data 폴더는 유지합니다.
실행: python -m streamlit run app.py

6단계 이동은 사이드바와 하단 이전/다음 버튼으로 가능합니다.
01 자료 선택 → 02 가정 입력 → 03 백테스트 → 04 공시 근거 → 05 참고 시나리오 → 06 후속 확인 목록.
04 자동 뉴스 수집과 05 공시 조사 기반 가설 생성, 06 자동 미래 가이던스는 구현하지 않았습니다.
세 추가 가정은 준비 중 안내를 표시합니다. 순부채는 사용자 입력 방식입니다.
브랜드 표기는 공모전 프로토타입으로 표시합니다. 공식 KIC 서비스로 주장하지 않습니다.
CSS는 외부 폰트/서비스를 호출하지 않습니다. 통신 보안 전체를 검증한 것은 아닙니다.

검증: 4개 Python 파일 구문 검사, Streamlit AppTest로 6개 데이터 미연결 화면,
실제 삼성전자 CSV를 사용한 6개 화면 및 매출 가정 제출, 이전/다음/초기화 검증 통과.
실제 CSV 검증은 미제공 schema.py 대신 테스트 전용 정규화 코드를 사용했습니다.
테스트 코드는 배포 파일에 포함하지 않습니다. 원본 schema.py/API/Windows 전체 실행은 미검증입니다.
