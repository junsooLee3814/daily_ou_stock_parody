@echo off
echo ========================================
echo   아나콘다 환경에서 파이썬 실행
echo ========================================
echo.

REM 아나콘다 파이썬 경로 설정
set ANACONDA_PATH=C:\Users\juncp\anaconda3
set PYTHON_PATH=%ANACONDA_PATH%\python.exe
set PIP_PATH=%ANACONDA_PATH%\Scripts\pip.exe

echo 아나콘다 파이썬 버전 확인:
"%PYTHON_PATH%" --version
echo.

echo 사용 가능한 스크립트:
echo 1. step1_ou_stock_parody_collection.py - 뉴스 수집 및 패러디 생성
echo 2. step2_ou_stock_parody_card.py - 패러디 카드 생성
echo 3. step3_ou_stock_parody_video.py - 패러디 비디오 생성
echo 4. step4_ou_stock_parody_final.py - 최종 통합 실행
echo.

set /p choice="실행할 스크립트 번호를 선택하세요 (1-4): "

if "%choice%"=="1" (
    echo.
    echo step1_ou_stock_parody_collection.py 실행 중...
    "%PYTHON_PATH%" step1_ou_stock_parody_collection.py
) else if "%choice%"=="2" (
    echo.
    echo step2_ou_stock_parody_card.py 실행 중...
    "%PYTHON_PATH%" step2_ou_stock_parody_card.py
) else if "%choice%"=="3" (
    echo.
    echo step3_ou_stock_parody_video.py 실행 중...
    "%PYTHON_PATH%" step3_ou_stock_parody_video.py
) else if "%choice%"=="4" (
    echo.
    echo step4_ou_stock_parody_final.py 실행 중...
    "%PYTHON_PATH%" step4_ou_stock_parody_final.py
) else (
    echo 잘못된 선택입니다. 1-4 중에서 선택해주세요.
)

echo.
echo 실행 완료. 아무 키나 누르면 종료됩니다.
pause > nul




