@echo off
chcp 65001 >nul
echo ==========================================
echo   서대리 듀얼 모델 서버
echo ==========================================
echo.

:: -- 가상환경 확인 --
if not exist "server\.venv\Scripts\activate.bat" (
    echo [오류] 가상환경이 없습니다. setup.bat 를 먼저 실행하세요.
    pause
    exit /b 1
)

:: -- 모델 파일 확인 --
set MODELS_DIR=server\models
set ROUTER_FILE=%MODELS_DIR%\Qwen3.5-0.8B-UD-Q8_K_XL.gguf
set EXECUTOR_FILE=%MODELS_DIR%\Qwen3.5-9B-Q8_0.gguf

echo [모델 확인]
if exist "%ROUTER_FILE%" ( echo   [O] Qwen3.5 0.8B    : %ROUTER_FILE% ) else ( echo   [X] Qwen3.5 0.8B    : %ROUTER_FILE% )
if exist "%EXECUTOR_FILE%" ( echo   [O] Qwen3.5 9B      : %EXECUTOR_FILE% ) else ( echo   [X] Qwen3.5 9B      : %EXECUTOR_FILE% )

:: -- 서버 시작 --
echo.
echo 서버 시작 중... (종료: Ctrl+C)
echo.
call server\.venv\Scripts\activate.bat
python -m server.main
