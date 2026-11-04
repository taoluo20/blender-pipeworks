# SPDX-License-Identifier: GPL-3.0-or-later
"""Read a source-authored connection scene with a freshly installed ZIP."""
import importlib
import json
import os
from pathlib import Path
import tomllib
import bpy
from mathutils import Matrix

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'verification' / 'line-pipe' / 'connection-restart-user'
for key in ('BLENDER_USER_CONFIG', 'BLENDER_USER_SCRIPTS', 'BLENDER_USER_EXTENSIONS'):
    assert Path(os.environ[key]).is_relative_to(OUT)
assert Path(bpy.utils.user_resource('CONFIG')).is_relative_to(OUT)
version = tomllib.loads((ROOT / 'line_pipe/blender_manifest.toml').read_text())['version']
bpy.ops.extensions.package_install_files(filepath=str(ROOT / 'dist' / ('pipeworks-' + version + '.zip')),
                                         repo='user_default', enable_on_install=True)
addon = importlib.import_module('bl_ext.user_default.line_pipe')
c, ports = addon.connections, addon.ports
bpy.ops.wm.open_mainfile(filepath=str(ROOT / 'verification/connections/connections-roundtrip.blend'),
                         load_ui=False, use_scripts=False)
scene = bpy.context.scene
assert len(scene.line_pipe_connections.links) == 1
record = scene.line_pipe_connections.links[0]
assert record.mode == 'BRIDGE' and record.source and record.target and record.connector
assert record.source.type == 'MESH' and record.target.type == 'CURVE'
assert record.source.line_pipe.diameter > 0
assert record.source.get('line_pipe_route_v1') and record.source.get('line_pipe_ports_v1')
for obj, key in ((record.source, record.source_port), (record.target, record.target_port)):
    assert ports.occupied(scene, obj, key)
original = record.source.matrix_world.copy()
record.target.matrix_world = Matrix.Translation((0, 0, .5)) @ record.target.matrix_world
bpy.context.view_layer.objects.active = record.source
bpy.context.view_layer.update()
assert c.update_bridges(bpy.context) == 1
assert record.source.matrix_world == original
for obj, key, end in ((record.source, record.source_port, 0), (record.target, record.target_port, 1)):
    endpoint = ports.world_ports(record.connector)[end]
    anchor = ports.read(scene, obj, key, False)
    assert (endpoint.position - anchor.position).length < 1e-5
assert len(scene.line_pipe_connections.links) == 1
(OUT / 'restart.json').write_text(json.dumps(dict(fresh_zip_restored_links=True,
    source_mesh_and_target_curve=True, occupied_ports_restored=True,
    saved_bridge_updated=True, native_mesh_parameters_restored=True), indent=2))
print('CONNECTION_RESTART_OK', flush=True)
