# SPDX-License-Identifier: GPL-3.0-or-later
"""Build the extension with deterministic ZIP metadata and optional validation."""
import argparse
import hashlib
import os
from pathlib import Path
import subprocess
import tempfile
import tomllib
import zipfile

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'line_pipe'


def isolated_environment(directory):
    env = os.environ.copy()
    for key, folder in [('BLENDER_USER_CONFIG', 'config'), ('BLENDER_USER_SCRIPTS', 'scripts'),
                        ('BLENDER_USER_EXTENSIONS', 'extensions')]:
        path = Path(directory) / folder
        path.mkdir(parents=True, exist_ok=True)
        env[key] = str(path)
    return env


def build():
    manifest = tomllib.loads((SOURCE / 'blender_manifest.toml').read_text(encoding='utf8'))
    target = ROOT / 'dist' / ('pipeworks-' + manifest['version'] + '.zip')
    target.parent.mkdir(exist_ok=True)
    with zipfile.ZipFile(target, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in sorted(SOURCE.iterdir()):
            if not path.is_file() or path.suffix == '.pyc':
                continue
            entry = zipfile.ZipInfo(path.name, date_time=(1980, 1, 1, 0, 0, 0))
            entry.compress_type = zipfile.ZIP_DEFLATED
            entry.external_attr = 0o100644 << 16
            archive.writestr(entry, path.read_bytes(), compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
    digest = hashlib.sha256(target.read_bytes()).hexdigest()
    (target.parent / 'SHA256SUMS.txt').write_text(digest + '  ' + target.name + '\n', encoding='utf8')
    print('Built', target.name, 'SHA256', digest, flush=True)
    return target


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--blender', help='Blender executable for extension validation')
    args = parser.parse_args()
    archive = build()
    if args.blender:
        with tempfile.TemporaryDirectory(prefix='pipeworks-build-') as temporary:
            subprocess.run([args.blender, '--background', '--factory-startup', '--command', 'extension',
                            'validate', str(archive)], env=isolated_environment(temporary), check=True)
