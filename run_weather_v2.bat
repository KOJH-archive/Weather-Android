@echo off
cd /d "%~dp0"
echo Starting Weather Insight v2 with UV...

:: uv가 설치되어 있는지 확인
uv --version >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [ERROR] 'uv' is not installed or not in PATH.
    echo Please install uv or use the previous version.
    pause
    exit /b
)

:: 라이브러리 설치 (가장 빠른 방식)
echo Syncing dependencies...
uv pip install flet httpx python-dotenv >nul 2>&1

:: 앱 실행 (가상환경 내의 파이썬 직접 호출)
echo Launching Premium Weather Hub v2...
.venv\Scripts\python.exe pc_main_v2.py

if %ERRORLEVEL% neq 0 (
    echo.
    echo [ERROR] Application crashed.
    pause
)
