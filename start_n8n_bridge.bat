@echo off
chcp 65001 >nul
echo ==========================================
echo   서대리 n8n Bridge Server
echo ==========================================
echo.
echo   n8n 연동 테스트 전용 서버
echo   모델 로딩 없이 API만 실행
echo.

if not exist "server\.venv\Scripts\activate.bat" (
    echo [오류] 가상환경이 없습니다. setup.bat 를 먼저 실행하세요.
    pause
    exit /b 1
)

call server\.venv\Scripts\activate.bat
python n8n_bridge.py
