"""Build a standalone Windows game using the current Python environment."""
from pathlib import Path
import subprocess
import sys

root = Path(__file__).resolve().parents[1]
build = root / 'build'
build.mkdir(exist_ok=True)
command = [sys.executable, '-m', 'PyInstaller', '--noconfirm', '--onefile',
           '--windowed', '--name', 'EscapeDimension', '--collect-all', 'pico2d',
           '--collect-all', 'sdl2dll', '--hidden-import', 'sdl2.sdlimage',
           '--hidden-import', 'sdl2.sdlttf', '--hidden-import', 'sdl2.sdlmixer',
           '--add-data', f'{root / "assets"};assets',
           '--add-data', f'{root / "levels.json"};.',
           '--distpath', str(root), '--workpath', str(build / 'cache'),
           '--specpath', str(build), str(root / 'main.py')]
subprocess.run(command, cwd=root, check=True)
print(f'Built: {root / "EscapeDimension.exe"}')
