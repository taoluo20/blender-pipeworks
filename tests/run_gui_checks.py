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
parser.add_argument('--only', nargs='+', choices=['interaction', 'routing', 'navigation', 'alt-navigation', 'connections', 'groups', 'endpoint-selection', 'selection-edit'])
args = parser.parse_args()
build()
jobs = [
    ('interaction', 'tests/gui_interaction.py', 'verification/interaction-ui', ['--', '--installed']),
    ('routing', 'tests/gui_line_pipe.py', 'verification/line-pipe/six-axis-ui', ['--', '--six-axis', '--quit']),
    ('navigation', 'tests/gui_interaction.py', 'verification/navigation-ui', ['--', '--navigation-only', '--installed']),
    ('alt-navigation', 'tests/gui_interaction.py', 'verification/alt-navigation-ui', ['--', '--alt-navigation-only', '--installed']),
    ('connections', 'tests/gui_connections.py', 'verification/connections-ui', []),
    ('groups', 'tests/gui_groups.py', 'verification/groups-ui', []),
    ('endpoint-selection', 'tests/gui_endpoint_selection.py', 'verification/endpoint-selection-ui', []),
    ('selection-edit', 'tests/gui_selection_edit.py', 'verification/selection-edit-ui', []),
]
for name, script, directory, extra in jobs:
    if args.only and name not in args.only:
        continue
    out = ROOT / directory
    out.mkdir(parents=True, exist_ok=True)
    for filename in ('failure.txt', 'results.json', 'ui-checks.json', 'command.json'):
        (out / filename).unlink(missing_ok=True)
    result = subprocess.run([args.blender, '--factory-startup', '--python-exit-code', '1', '--enable-event-simulate',
                             '--window-geometry', '80', '80', '1600', '950', '--python', script, *extra],
                            cwd=ROOT, env=isolated_environment(out), timeout=180,
                            text=True, encoding='utf8', errors='replace',
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    (out / 'native.log').write_text(result.stdout, encoding='utf8')
    receipt = out / ('ui-checks.json' if name == 'routing' else 'results.json')
    if (result.returncode or (out / 'failure.txt').exists() or not receipt.exists()
            or 'Traceback (most recent call last):' in result.stdout):
        print(result.stdout)
        raise SystemExit(name + ' failed; see ' + str(out))
    summary = json.loads(receipt.read_text())
    print(name, 'PASS', len(summary['checks']), 'native assertions', flush=True)
