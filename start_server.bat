@echo off
chcp 65001 >nul
echo ==========================================
echo   서대리 듀얼 모델 서버
echo ==========================================
echo.

:: -- 메인 모델 선택 --
echo 메인 모델 선택:
echo   [1] Qwen3.5 9B              (기본, 한국어)
echo   [2] GLM-4 9B Chat           (Zhipu AI)
echo   [3] Ministral 3 8B          (추론 특화)
echo   [4] OpenReasoning-Nemotron  (추론 괴물)
echo.
set /p MODEL_CHOICE=번호 입력 (기본=1):
if "%MODEL_CHOICE%"=="" set MODEL_CHOICE=1

if "%MODEL_CHOICE%"=="1" (
    set EXECUTOR_MODEL_FILE=Qwen3.5-9B-Q8_0.gguf
    set EXECUTOR_MODEL_NAME=qwen3.5-9b
    set MODEL_LABEL=Qwen3.5 9B
)
if "%MODEL_CHOICE%"=="2" (
    set EXECUTOR_MODEL_FILE=glm-4-9b-chat-Q8_0.gguf
    set EXECUTOR_MODEL_NAME=glm-4-9b
    set MODEL_LABEL=GLM-4 9B Chat
)
if "%MODEL_CHOICE%"=="3" (
    set EXECUTOR_MODEL_FILE=Ministral-3-8B-Reasoning-2512-Q8_0.gguf
    set EXECUTOR_MODEL_NAME=ministral-3-8b
    set MODEL_LABEL=Ministral 3 8B
)
if "%MODEL_CHOICE%"=="4" (
    set EXECUTOR_MODEL_FILE=OpenReasoning-Nemotron-7B-q8_0.gguf
    set EXECUTOR_MODEL_NAME=openreasoning-nemotron-7b
    set MODEL_LABEL=OpenReasoning-Nemotron 7B
)

if not defined EXECUTOR_MODEL_FILE (
    echo [오류] 잘못된 번호입니다. 1~4 중 선택하세요.
    pause
    exit /b 1
)

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
set EXECUTOR_FILE=%MODELS_DIR%\%EXECUTOR_MODEL_FILE%

echo [모델 확인]
if exist "%ROUTER_FILE%" ( echo   [O] Router : %ROUTER_FILE% ) else ( echo   [X] Router : %ROUTER_FILE% )
if exist "%EXECUTOR_FILE%" ( echo   [O] Main   : %EXECUTOR_FILE% ) else ( echo   [X] Main   : %EXECUTOR_FILE% )

:: -- 서버 시작 --
echo.
echo 선택 모델: %MODEL_LABEL%
echo 서버 시작 중... (종료: Ctrl+C)
echo.
call server\.venv\Scripts\activate.bat
python -m server.main
