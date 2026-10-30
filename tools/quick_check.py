# SPDX-License-Identifier: GPL-3.0-or-later
"""Portable syntax, metadata, scope, and reproducible-package checks."""
import ast
import hashlib
from pathlib import Path
import tomllib
import zipfile
from build import build, ROOT, SOURCE

EXPECTED = {'__init__.py', 'blender_manifest.toml', 'LICENSE', 'data.py', 'geometry.py',
            'i18n.py', 'model.py', 'operators.py', 'ui.py'}
manifest = tomllib.loads((SOURCE / 'blender_manifest.toml').read_text(encoding='utf8'))
assert manifest['name'] == 'PipeWorks' and manifest['id'] == 'line_pipe'
assert manifest['license'] == ['SPDX:GPL-3.0-or-later']
assert {p.name for p in SOURCE.iterdir() if p.is_file() and p.suffix != '.pyc'} == EXPECTED
assert (ROOT / 'LICENSE').read_bytes() == (SOURCE / 'LICENSE').read_bytes()
tree = ast.parse((SOURCE / '__init__.py').read_text(encoding='utf8'))
info = ast.literal_eval(next(node.value for node in tree.body if isinstance(node, ast.Assign)
                             and any(isinstance(t, ast.Name) and t.id == 'bl_info' for t in node.targets)))
assert '.'.join(map(str, info['version'])) == manifest['version']
assert info['name'] == manifest['name']
checked = 0
for path in ROOT.rglob('*.py'):
    if any(part in {'verification', '__pycache__', '.git', 'dist'} for part in path.relative_to(ROOT).parts):
        continue
    source = path.read_text(encoding='utf8')
    compile(source, str(path), 'exec')
    parsed = ast.parse(source)
    for node in ast.walk(parsed):
        names = [a.name for a in node.names] if isinstance(node, ast.Import) else (
            [node.module or ''] if isinstance(node, ast.ImportFrom) else [])
        assert all(not name.startswith('pipe_assembly') for name in names), path
    checked += 1
archive = build()
first = archive.read_bytes()
build()
assert archive.read_bytes() == first, 'non-reproducible archive'
with zipfile.ZipFile(archive) as package:
    assert set(package.namelist()) == EXPECTED
    assert package.testzip() is None
    for name in package.namelist():
        assert package.read(name) == (SOURCE / name).read_bytes()
assert hashlib.sha256(first).hexdigest() in (archive.parent / 'SHA256SUMS.txt').read_text()
print('PASS:', checked, 'Python files; product metadata; standalone scope; exact ZIP contents; reproducible bytes')
