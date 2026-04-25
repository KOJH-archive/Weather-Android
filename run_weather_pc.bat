@echo off
cd /d "%~dp0"
echo Starting Weather App...
if exist .venv\Scripts\activate (
    echo Activating virtual environment...
    call .venv\Scripts\activate
)
python pc_main.py
if %ERRORLEVEL% neq 0 (
    echo Error occurred.
    pause
)
