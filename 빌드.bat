@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo 필요한 빌드 도구: py -3 -m pip install pyinstaller
py -3 -m PyInstaller --noconfirm --onefile --windowed --name EscapeDimension --collect-all pico2d --collect-all sdl2dll --hidden-import sdl2.sdlimage --hidden-import sdl2.sdlttf --hidden-import sdl2.sdlmixer --add-data "assets;assets" --add-data "levels.json;." --distpath "빌드결과" --workpath "빌드임시" main.py
if errorlevel 1 ( echo 빌드 실패 ) else ( echo 빌드결과 폴더의 실행 파일을 사용하세요. )
pause
