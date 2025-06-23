@echo off
CHCP 65001 > nul
echo ======================================================
echo GitHub 저장소와 동기화를 시작합니다...
echo 동기화 시작 시간: %date% %time%
echo ======================================================

set "PROJECT_PATH=D:\onedrive\01.프로젝트\00.ACE\00.Cursor Ai\000_upload_everyday\ou_stock_parady"

echo.
echo 프로젝트 폴더로 이동합니다:
echo %PROJECT_PATH%
echo.

D:
cd "%PROJECT_PATH%"

IF %ERRORLEVEL% NEQ 0 (
    echo [ERROR] 프로젝트 폴더로 이동하지 못했습니다. 스크립트의 경로를 확인해주세요.
    pause
    exit /b
)

echo.
echo Git LFS를 포함하여 원격 저장소의 변경사항을 가져옵니다 (git pull)...
echo.
git pull

echo.
echo ======================================================
echo 동기화가 완료되었습니다.
echo ======================================================
echo.
echo 이 창은 5초 후에 자동으로 닫힙니다.
timeout /t 5 > nul 