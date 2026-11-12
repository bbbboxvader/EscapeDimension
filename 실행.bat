@echo off
chcp 65001 >nul
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  python tools\setup_runtime.py
  if errorlevel 1 (
    echo Python 환경 준비에 실패했습니다.
    pause
    exit /b 1
  )
)
".venv\Scripts\python.exe" main.py
if errorlevel 1 (
  echo.
  echo 실행 오류를 확인하세요. 환경 복구: python tools\setup_runtime.py
  pause
)
