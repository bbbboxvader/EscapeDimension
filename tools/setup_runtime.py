"""Prepare the local source-run environment; prefer downloaded wheels offline."""
from pathlib import Path
import subprocess
import sys

root = Path(__file__).resolve().parents[1]
env_root = root / '.venv'
python = env_root / 'Scripts' / 'python.exe'
if sys.version_info < (3, 10):
    raise SystemExit('Python 3.10 or newer is required.')
if not python.exists():
    subprocess.run([sys.executable, '-m', 'venv', str(env_root)], check=True)
subprocess.run([str(python), '-m', 'ensurepip', '--upgrade'], check=True)
wheels = root / '.runtime' / 'wheels'
command = [str(python), '-m', 'pip', 'install']
if wheels.exists() and list(wheels.glob('*.whl')):
    command += ['--no-index', '--find-links', str(wheels)]
command += ['-r', str(root / 'requirements.txt')]
subprocess.run(command, cwd=root, check=True)
subprocess.run([str(python), '-m', 'pip', 'check'], check=True)
print(f'Ready: {python} {root / "main.py"}')
