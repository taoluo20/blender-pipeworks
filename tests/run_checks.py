# SPDX-License-Identifier: GPL-3.0-or-later
"""Run the integration and real installed-extension checks in separate profiles."""
import argparse
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from build import build, isolated_environment

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--blender', required=True)
args = parser.parse_args()
build()
out = ROOT / 'verification' / 'line-pipe'
out.mkdir(parents=True, exist_ok=True)
jobs = [
    ('integration', ['--factory-startup', '--python', 'tests/check_line_pipe.py'], out / 'backend-user'),
    ('compact', ['--factory-startup', '--python', 'tests/check_compact_bends.py'], out / 'compact-user'),
    ('connections', ['--factory-startup', '--python', 'tests/check_connections.py'], out / 'connections-user'),
    ('profiles', ['--factory-startup', '--python', 'tests/check_profiles.py'], out / 'profiles-user'),
    ('connection-restart', ['--factory-startup', '--python', 'tests/check_connection_restart.py'], out / 'connection-restart-user'),
    ('installed', ['--factory-startup', '--python', 'tests/check_installed_line_pipe.py'], out / 'install-user'),
    ('restart', ['--python', 'tests/check_installed_line_pipe.py', '--', '--reload-preferences'], out / 'install-user'),
]
for name, arguments, profile in jobs:
    completed = subprocess.run([args.blender, '--background', '--python-exit-code', '1', *arguments],
                               cwd=ROOT, env=isolated_environment(profile), text=True, encoding='utf8',
                               errors='replace', stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    (out / (name + '.log')).write_text(completed.stdout, encoding='utf8')
    print(name, 'PASS' if completed.returncode == 0 else 'FAIL', flush=True)
    if completed.returncode:
        print(completed.stdout)
        raise SystemExit(completed.returncode)
result = json.loads((out / 'checks.json').read_text())
print('Integration checks:', result['count'], '| Actual ZIP install and preference restart passed')
