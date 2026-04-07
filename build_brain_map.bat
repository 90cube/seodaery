@echo off
chcp 65001 >nul
echo ==========================================
echo   서대리 Brain Map → EXE 빌드
echo ==========================================
echo.

if not exist "server\.venv\Scripts\activate.bat" (
    echo [오류] 가상환경이 없습니다. setup.bat 를 먼저 실행하세요.
    pause
    exit /b 1
)

call server\.venv\Scripts\activate.bat

:: PyInstaller 설치
pip install pyinstaller pywebview --quiet

echo.
echo [빌드] brain_map_app.exe 생성 중...
pyinstaller --onefile --noconsole --name "서대리" brain_map_app.py

echo.
if exist "dist\서대리.exe" (
    echo [완료] dist\서대리.exe 생성됨
    echo        다른 PC에 배포할 때: 서대리.exe만 복사하면 됩니다.
    echo        실행 전 서버가 켜져 있어야 합니다.
    echo.
    echo        다른 PC에서 실행 시:
    echo          서대리.exe http://서대리IP:8000
) else (
    echo [오류] 빌드 실패
)

pause
