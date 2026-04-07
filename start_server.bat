@echo off
chcp 65001 >nul
echo ==========================================
echo   서대리 LLM 서버
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
set EXECUTOR_FILE=%MODELS_DIR%\%EXECUTOR_MODEL_FILE%

echo [모델 확인]
if exist "%EXECUTOR_FILE%" ( echo   [O] %MODEL_LABEL% : %EXECUTOR_FILE% ) else ( echo   [X] %MODEL_LABEL% : %EXECUTOR_FILE% )

:: -- 서버를 별도 창에서 시작 --
echo.
echo 선택 모델: %MODEL_LABEL%
echo 서버 시작 중...
echo.
start "서대리 서버" cmd /k "call server\.venv\Scripts\activate.bat && python -m server.main"

:: -- 모델 로딩 대기 (헬스체크) --
echo [대기] 모델 로딩 중... (최대 3분)
set /a WAITED=0
set /a MAX_WAIT=180

:health_loop
if %WAITED% geq %MAX_WAIT% (
    echo.
    echo [오류] 모델 로딩 타임아웃 (%MAX_WAIT%초 초과)
    pause
    exit /b 1
)

:: 0.8B 헬스체크
curl -sf http://localhost:8081/health >nul 2>&1
if errorlevel 1 (
    <nul set /p="."
    timeout /t 2 /nobreak >nul
    set /a WAITED+=2
    goto health_loop
)

:: 9B 헬스체크
curl -sf http://localhost:8082/health >nul 2>&1
if errorlevel 1 (
    <nul set /p="."
    timeout /t 2 /nobreak >nul
    set /a WAITED+=2
    goto health_loop
)

echo.
echo [완료] 모델 로딩 완료 (%WAITED%초 소요)
echo.

:: -- Brain Map 브라우저 열기 --
echo [열기] Brain Map 대시보드
start "" http://127.0.0.1:8000/static/brain_map.html

:: -- 클라이언트 실행 --
echo [실행] 채팅 클라이언트
echo.
call server\.venv\Scripts\activate.bat
python client.py
