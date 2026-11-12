@echo off
chcp 65001 >nul
cd /d "%~dp0"
if exist "EscapeDimension.exe" (
  start "" "%~dp0EscapeDimension.exe"
  exit /b
)
py -3 main.py
if errorlevel 1 (
  echo.
  echo 소스 실행에는 Python과 pico2d가 필요합니다.
  echo 설치: py -3 -m pip install -r requirements.txt
  pause
)
