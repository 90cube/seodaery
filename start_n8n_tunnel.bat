@echo off
chcp 65001 >nul
echo ==========================================
echo   서대리 n8n 터널
echo ==========================================
echo.

:: ngrok 설치 확인
where ngrok >nul 2>&1
if errorlevel 1 (
    echo [오류] ngrok이 설치되어 있지 않습니다.
    echo.
    echo   설치 방법:
    echo     winget install ngrok
    echo.
    echo   또는 https://ngrok.com/download 에서 다운로드
    echo.
    echo   설치 후 무료 계정 가입하고 토큰 등록:
    echo     ngrok config add-authtoken 토큰값
    echo.
    pause
    exit /b 1
)

echo 서대리 서버(localhost:8000)를 외부에 노출합니다.
echo 서버가 먼저 실행 중이어야 합니다. (start_server.bat)
echo.
echo n8n에서 아래 주소를 사용하세요:
echo   Forwarding 주소 → /api/n8n/ping
echo   Forwarding 주소 → /api/n8n/tool
echo   Forwarding 주소 → /api/n8n/chat
echo.
echo 종료: Ctrl+C
echo ──────────────────────────────────────────
echo.

ngrok http 8000
