"""Run native viewport checks with isolated profiles and bounded lifetimes."""
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
jobs = [
    ('interaction', 'tests/gui_interaction.py', 'verification/interaction-ui', ['--', '--installed']),
    ('routing', 'tests/gui_line_pipe.py', 'verification/line-pipe/six-axis-ui', ['--', '--six-axis', '--quit']),
]
for name, script, directory, extra in jobs:
    out = ROOT / directory
    out.mkdir(parents=True, exist_ok=True)
    for filename in ('failure.txt', 'results.json', 'ui-checks.json'):
        (out / filename).unlink(missing_ok=True)
    result = subprocess.run([args.blender, '--factory-startup', '--enable-event-simulate',
                             '--window-geometry', '80', '80', '1600', '950', '--python', script, *extra],
                            cwd=ROOT, env=isolated_environment(out), timeout=180,
                            text=True, encoding='utf8', errors='replace',
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    (out / 'native.log').write_text(result.stdout, encoding='utf8')
    receipt = out / ('results.json' if name == 'interaction' else 'ui-checks.json')
    if result.returncode or (out / 'failure.txt').exists() or not receipt.exists():
        print(result.stdout)
        raise SystemExit(name + ' failed; see ' + str(out))
    summary = json.loads(receipt.read_text())
    print(name, 'PASS', len(summary['checks']), 'native assertions', flush=True)
