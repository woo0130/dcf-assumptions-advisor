@echo off
setlocal

cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo [1/3] Python 3.12 virtual environment is being created...
    py -3.12 -m venv .venv
    if errorlevel 1 (
        echo.
        echo [ERROR] Python 3.12 was not found or the virtual environment could not be created.
        echo Install Python 3.12 from https://www.python.org/downloads/ and enable the py launcher.
        exit /b 1
    )
) else (
    echo [1/3] Existing .venv will be used.
)

echo [2/3] Installing required packages...
".venv\Scripts\python.exe" -m pip install --disable-pip-version-check -r requirements.txt
if errorlevel 1 (
    echo.
    echo [ERROR] Package installation failed. Check the messages above and your network connection.
    exit /b 1
)

echo [3/3] Starting DCF Assumptions Advisor...
set "PYTHONPATH=."
".venv\Scripts\python.exe" -m streamlit run app.py

endlocal
