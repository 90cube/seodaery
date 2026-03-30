@echo off
chcp 65001 >nul
echo ╔══════════════════════════════════════╗
echo ║  듀얼 모델 LLM 서버 — 초기 설치     ║
echo ╚══════════════════════════════════════╝
echo.

:: ── 1. 폴더 구조 생성 ──
echo [1/4] 폴더 구조 생성...
if not exist "server\models" mkdir "server\models"
echo       server\models\  (GGUF 파일 배치 경로)

:: ── 2. Python 3.13 확인 ──
echo.
echo [2/4] Python 3.13 확인...
py -3.13 --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [오류] Python 3.13을 찾을 수 없습니다.
    echo        py -3.13 --version 으로 직접 확인하세요.
    pause
    exit /b 1
)
for /f "tokens=*" %%v in ('py -3.13 --version') do echo       %%v 확인됨

:: ── 3. 가상환경 생성 ──
echo.
echo [3/4] 가상환경 생성 (server\.venv) ...
if exist "server\.venv" (
    echo       기존 .venv 발견 — 건너뜀
) else (
    py -3.13 -m venv server\.venv
    if %errorlevel% neq 0 (
        echo [오류] 가상환경 생성 실패
        pause
        exit /b 1
    )
    echo       생성 완료
)

:: ── 4. 의존성 설치 ──
echo.
echo [4/4] 패키지 설치...
call server\.venv\Scripts\activate.bat
pip install -r server\requirements.txt --quiet
if %errorlevel% neq 0 (
    echo [오류] pip install 실패
    pause
    exit /b 1
)
echo       설치 완료

:: ── 완료 ──
echo.
echo ════════════════════════════════════════
echo  설치 완료! 다음 단계:
echo.
echo  1. 모델 파일 배치:
echo     server\models\Qwen3.5-0.8B-UD-Q8_K_XL.gguf
echo     server\models\Qwen3.5-9B-Q8_0.gguf
echo.
echo  2. llama-server.exe 경로 확인 (PATH 또는 LLAMA_BIN 환경변수)
echo.
echo  3. start_server.bat 실행
echo ════════════════════════════════════════
pause
