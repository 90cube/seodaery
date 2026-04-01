@echo off
chcp 65001 >nul
echo ==========================================
echo   서대리 트리오 모델 서버
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
set REASONER_FILE=%MODELS_DIR%\Qwen3.5-0.8B.Q8_0.gguf

echo [모델 확인]
if exist "%ROUTER_FILE%" ( echo   [O] 라우터  : %ROUTER_FILE% ) else ( echo   [X] 라우터  : %ROUTER_FILE% )
if exist "%EXECUTOR_FILE%" ( echo   [O] 실행기  : %EXECUTOR_FILE% ) else ( echo   [X] 실행기  : %EXECUTOR_FILE% )
if exist "%REASONER_FILE%" ( echo   [O] 추론기  : %REASONER_FILE% ) else ( echo   [-] 추론기  : %REASONER_FILE% [선택] )

:: -- 서버 시작 --
echo.
echo 서버 시작 중... (종료: Ctrl+C)
echo.
call server\.venv\Scripts\activate.bat
python -m server.main
