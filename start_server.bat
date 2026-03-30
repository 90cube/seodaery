@echo off
chcp 65001 >nul
echo ╔══════════════════════════════════════╗
echo ║  듀얼 모델 LLM 서버 — 시작          ║
echo ╚══════════════════════════════════════╝
echo.

:: ── 가상환경 확인 ──
if not exist "server\.venv\Scripts\activate.bat" (
    echo [오류] 가상환경이 없습니다. setup.bat 를 먼저 실행하세요.
    pause
    exit /b 1
)

:: ── 모델 파일 확인 ──
set MODELS_DIR=server\models
set ROUTER_FILE=%MODELS_DIR%\Qwen3.5-0.8B-UD-Q8_K_XL.gguf
set EXECUTOR_FILE=%MODELS_DIR%\Qwen3.5-9B-Q8_0.gguf

if not exist "%ROUTER_FILE%" (
    echo [경고] 라우터 모델 없음: %ROUTER_FILE%
    echo        ROUTER_MODEL_FILE 환경변수로 다른 파일명 지정 가능
)
if not exist "%EXECUTOR_FILE%" (
    echo [경고] 실행기 모델 없음: %EXECUTOR_FILE%
    echo        EXECUTOR_MODEL_FILE 환경변수로 다른 파일명 지정 가능
)

:: ── 서버 시작 ──
echo.
echo 서버 시작 중... (종료: Ctrl+C)
echo.
call server\.venv\Scripts\activate.bat
python -m server.main
