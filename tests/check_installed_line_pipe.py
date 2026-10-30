"""Install the actual extension archive and verify preference/file persistence."""
import importlib
import json
import os
import pathlib
import sys
import tomllib
import zipfile
import bpy

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / 'verification' / 'line-pipe' / 'install-user'
OUT.mkdir(parents=True, exist_ok=True)
for key in ('BLENDER_USER_CONFIG', 'BLENDER_USER_SCRIPTS', 'BLENDER_USER_EXTENSIONS'):
    assert pathlib.Path(os.environ[key]).is_relative_to(OUT)
    assert pathlib.Path(os.environ[key]).is_dir()
assert pathlib.Path(bpy.utils.user_resource('CONFIG')).is_relative_to(OUT)
module = 'bl_ext.user_default.line_pipe'
if '--reload-preferences' in sys.argv:
    addon = importlib.import_module(module)
    assert addon.i18n.language() == 'ZH', 'language not restored in a new Blender process'
    assert addon._registered
    bpy.ops.line_pipe.language()
    assert addon.i18n.language() == 'EN'
    bpy.ops.wm.save_userpref()
    (OUT / 'restart.json').write_text(json.dumps({'restored_chinese': True, 'reset_english': True}), encoding='utf8')
    print('PREFERENCE_RESTART_OK', flush=True)
else:
    version = tomllib.loads((ROOT / 'line_pipe' / 'blender_manifest.toml').read_text(encoding='utf8'))['version']
    archive = ROOT / 'dist' / ('pipeworks-' + version + '.zip')
    bpy.ops.extensions.package_install_files(filepath=str(archive), repo='user_default', enable_on_install=True)
    addon = importlib.import_module(module)
    assert addon._registered and addon.i18n.language() == 'EN'
    installed_manifest = tomllib.loads((pathlib.Path(addon.__file__).parent / 'blender_manifest.toml').read_text(encoding='utf8'))
    assert installed_manifest['name'] == 'PipeWorks' and installed_manifest['version'] == version
    assert addon.ui.LP_PT_main.bl_category == 'PipeWorks'
    assert bpy.context.scene.line_pipe_settings.direction == 'AUTO'
    bpy.ops.line_pipe.language()
    assert addon.i18n.language() == 'ZH'
    bpy.ops.wm.save_userpref()
    new_scene = bpy.data.scenes.new('Language persistence')
    bpy.context.window.scene = new_scene
    assert addon.i18n.language() == 'ZH' and new_scene.line_pipe_settings.language == 'EN'
    obj = addon.geometry.create(bpy.context)
    addon.geometry.update(obj, [(0, 0, 0), (2, 0, 0), (2, 0, 2)], .2, .4, 32, 16, store=True)
    obj['_line_pipe_dimensions'] = [.2, .4, 32, 16]
    recipe = obj['line_pipe_route_v1']
    bpy.ops.wm.save_as_mainfile(filepath=str(OUT / 'saved.blend'))
    bpy.ops.wm.open_mainfile(filepath=str(OUT / 'saved.blend'))
    saved = next(o for o in bpy.context.scene.objects if o.get('line_pipe_route_v1'))
    assert saved['line_pipe_route_v1'] == recipe
    saved.line_pipe.diameter_zh = .25
    assert abs(saved.line_pipe.diameter - .25) < 1e-6
    assert all(abs(p['diameter'] - .25) < 1e-6 for p in json.loads(saved['line_pipe_ports_v1']))
    with zipfile.ZipFile(archive) as package:
        assert all((pathlib.Path(addon.__file__).parent / name).read_bytes() == package.read(name) for name in package.namelist())
    (OUT / 'installed.json').write_text(json.dumps({'version': version, 'actual_zip_installed': True, 'independent_of_assembly': True,
        'preference_applies_to_new_scenes': True, 'save_reopen_preserves_route_and_parameters': True,
        'saved_pipe_edits_in_chinese': True, 'installed_files_match_zip': True}, indent=2), encoding='utf8')
    print('INSTALLED_LINE_PIPE_OK', flush=True)
