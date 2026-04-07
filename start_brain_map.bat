@echo off
chcp 65001 >nul
if not exist "server\.venv\Scripts\activate.bat" (
    echo [오류] 가상환경이 없습니다. setup.bat 를 먼저 실행하세요.
    pause
    exit /b 1
)
call server\.venv\Scripts\activate.bat
python brain_map_app.py %*
