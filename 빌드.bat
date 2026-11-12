@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo 필요한 빌드 도구: py -3 -m pip install -r requirements-build.txt
py -3 tools\build_game.py
if errorlevel 1 ( echo 빌드 실패 ) else ( echo 같은 폴더의 EscapeDimension.exe가 갱신되었습니다. )
pause
