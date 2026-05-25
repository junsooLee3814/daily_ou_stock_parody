@echo off
echo 아나콘다 파이썬 실행기
echo =====================
echo.

REM 아나콘다 파이썬 경로
set PYTHON_PATH=C:\Users\juncp\anaconda3\python.exe

if "%1"=="" (
    echo 사용법: anaconda_python.bat [스크립트명.py]
    echo.
    echo 예시:
    echo   anaconda_python.bat step1_ou_stock_parody_collection.py
    echo   anaconda_python.bat step2_ou_stock_parody_card.py
    echo.
    echo 파이썬 대화형 모드로 실행하려면:
    echo   anaconda_python.bat
    echo.
    pause
    exit /b
)

echo 실행 중: %1
"%PYTHON_PATH%" %*




