"""Record rule checks and optional standalone EXE input checks."""
from pathlib import Path
import argparse
import hashlib
import json
import subprocess
import sys
import unittest

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root))
parser = argparse.ArgumentParser()
parser.add_argument('--exe', action='store_true', help='Also verify the built Windows executable')
args = parser.parse_args()
target = root / 'verification'
target.mkdir(exist_ok=True)
suite = unittest.defaultTestLoader.discover(str(root / 'tests'))
result = unittest.TextTestRunner(verbosity=1).run(suite)
report = {'rules': {'status': 'pass' if result.wasSuccessful() else 'fail',
                    'count': result.testsRun, 'failures': len(result.failures),
                    'errors': len(result.errors)},
          'engine': 'Python + pico2d',
          'limitations': 'Automated rule and input checks; human balance testing remains.'}
if not result.wasSuccessful():
    (target / 'summary.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    raise SystemExit(1)
if args.exe:
    exe = root / 'EscapeDimension.exe'
    input_report = target / 'exe-input-tests.json'
    # Remove a previous report so a failed launch cannot appear successful.
    input_report.unlink(missing_ok=True)
    subprocess.run([str(exe), '--self-test', '--test-report', str(input_report)],
                   cwd=root, check=True, timeout=60)
    checks = json.loads(input_report.read_text(encoding='utf-8'))
    if checks.get('status') != 'pass':
        raise RuntimeError('Executable input checks did not pass')
    report['executable_input'] = {'status': checks['status'], 'count': checks['count']}
    report['executable_sha256'] = hashlib.sha256(exe.read_bytes()).hexdigest()
    report['executable_bytes'] = exe.stat().st_size
(target / 'summary.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print(json.dumps(report, indent=2))
