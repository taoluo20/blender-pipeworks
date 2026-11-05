"""Native connection buttons must use newly picked endpoints, including after redo."""
import importlib
import json
import os
from pathlib import Path
import traceback
import tomllib
import bpy
from mathutils import Euler
from bpy_extras import view3d_utils

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'verification/endpoint-selection-ui'
for key in ('BLENDER_USER_CONFIG', 'BLENDER_USER_SCRIPTS', 'BLENDER_USER_EXTENSIONS'):
    assert Path(os.environ[key]).is_relative_to(OUT) and Path(os.environ[key]).is_dir()
assert Path(bpy.utils.user_resource('CONFIG')).is_relative_to(OUT)
version = tomllib.loads((ROOT / 'line_pipe/blender_manifest.toml').read_text())['version']
bpy.ops.extensions.package_install_files(filepath=str(ROOT / 'dist' / ('pipeworks-' + version + '.zip')),
                                         repo='user_default', enable_on_install=True)
addon = importlib.import_module('bl_ext.user_default.line_pipe')
ports, connections, ops = addon.ports, addon.connections, addon.connection_ops
window = bpy.context.window
area = next(a for a in window.screen.areas if a.type == 'VIEW_3D')
region = next(r for r in area.regions if r.type == 'WINDOW')
space = area.spaces.active
space.show_region_ui = True
space.region_3d.view_rotation = Euler((1.25, 0, .35)).to_quaternion()
space.region_3d.view_location = (0, 0, 1)
space.region_3d.view_distance = 16
space.region_3d.view_perspective = 'PERSP'
bpy.context.preferences.view.show_splash = False
bpy.context.preferences.filepaths.temporary_directory = str(OUT)
for obj in tuple(bpy.context.scene.objects):
    bpy.data.objects.remove(obj, do_unlink=True)
checks, events, expected = [], [], {}
pointer = [500, 400]


def pipe(name, points, location):
    obj = addon.geometry.create(bpy.context)
    obj.name = name
    addon.geometry.update(obj, points, .2, .3, 32, 16, store=True)
    obj.location = location
    return obj


for suffix in ('A', 'B'):
    pipe('Moving ' + suffix, [(0, 0, 0), (1.5, 0, 0), (1.5, 0, 1.5)], (.5, 0, 0))
    pipe('Anchor ' + suffix, [(0, 0, 0), (0, 0, 2), (1.5, 0, 2)], (-2, 0, 0))
bpy.context.view_layer.update()
original = {obj.name: obj.matrix_world.copy() for obj in bpy.context.scene.objects}
bpy.context.scene.line_pipe_settings.tool_mode = 'CONNECT'
# Native keymap invocation uses Blender's saved operator defaults, as a UI button does.
keymap = bpy.context.window_manager.keyconfigs.addon.keymaps.new(name='Object Mode', space_type='EMPTY')
bridge_key = keymap.keymap_items.new('line_pipe.connect_distance', type='F8', value='PRESS')


def state():
    return bpy.context.scene.line_pipe_connections


def check(name, condition):
    assert condition, name
    checks.append(name)
    print('PASS ENDPOINT UI:', name, flush=True)


def near_matrix(a, b):
    return max(abs(a[r][c] - b[r][c]) for r in range(4) for c in range(4)) < 3e-5


def event(kind, value='NOTHING', x=None, y=None):
    if x is not None:
        pointer[:] = [int(x), int(y)]
    window.event_simulate(type=kind, value=value, x=pointer[0], y=pointer[1])


def click(x, y):
    event('MOUSEMOVE', x=x, y=y)
    event('LEFTMOUSE', 'PRESS')
    event('LEFTMOUSE', 'RELEASE')


def click_direct():
    ui = next(r for r in area.regions if r.type == 'UI')
    # Native sidebar button in the fixed factory-profile 1600x950 layout.
    click(ui.x + 180, window.height - 744)


def click_port(role):
    obj, key = expected[role], expected[role + '_key']
    port = next(p for p in ports.world_ports(bpy.context.scene.objects[obj]) if p.key == key)
    point = view3d_utils.location_3d_to_region_2d(region, space.region_3d, port.position)
    assert point is not None
    click(region.x + point.x, region.y + point.y)


def setup(language, source_key, target_key, suffix):
    for connector in {link.connector for link in state().links if link.connector}:
        addon.geometry.remove(connector)
    state().links.clear()
    for obj in bpy.context.scene.objects:
        obj.matrix_world = original[obj.name]
        obj[ports.GROUP] = obj[ports.UID]
        obj.hide_set(not obj.name.endswith(suffix))
    preferences = bpy.context.preferences.addons[addon.__name__].preferences
    preferences.language = language
    expected.update(source='Moving ' + suffix, source_key=source_key,
                    target='Anchor ' + suffix, target_key=target_key,
                    label=language + ' ' + suffix + ' ' + source_key + '-' + target_key)
    active = bpy.context.scene.objects[expected['source']]
    bpy.context.view_layer.objects.active = active
    active.select_set(True)
    bpy.context.view_layer.update()


def selected():
    return (state().source.name, state().source_port, state().target.name, state().target_port)


def wanted():
    return tuple(expected[key] for key in ('source', 'source_key', 'target', 'target_key'))


def check_picked():
    check(expected['label'] + ' picker retains Anchor and both port keys',
          ops.picker is None and selected() == wanted()
          and state().source_zh == state().source and state().target_zh == state().target
          and state().source_port_zh == state().source_port and state().target_port_zh == state().target_port)


def check_preview():
    values = ops.preview._objects if ops.preview else ()
    check(expected['label'] + ' native button uses current objects and keys',
          bool(values) and (values[0].name, values[1], values[2].name, values[3]) == wanted())


def check_link():
    link = state().links[-1] if state().links else None
    check(expected['label'] + ' confirm stores selected endpoints',
          len(state().links) == 1 and
          (link.source.name, link.source_port, link.target.name, link.target_port) == wanted())
    anchor = bpy.context.scene.objects[expected['target']]
    check(expected['label'] + ' Anchor stays fixed', near_matrix(anchor.matrix_world, original[anchor.name]))


def check_redo():
    # Reacquire RNA state after Undo/Redo; selection edits must not change this redo's snapshot.
    check_link()


def check_bridge():
    check_link()
    check(expected['label'] + ' native distance command leaves both poses fixed',
          state().links[-1].connector is not None and all(
              near_matrix(bpy.context.scene.objects[expected[role]].matrix_world, original[expected[role]])
              for role in ('source', 'target')))


def setup_merged():
    setup('ZH', 'END', 'END', 'A')
    moving_b = bpy.context.scene.objects['Moving B']
    moving_b.hide_set(False)
    moving_b.location.y += 1
    bpy.context.view_layer.update()
    groups = addon.groups
    groups.refresh(bpy.context.scene, reset=True)
    staged = groups.state_for(bpy.context.scene)
    row = groups.group_rows(bpy.context, [r for r in staged.items if r.source and r.source.name.startswith('Moving')])
    row.name = 'Merged Moving'
    groups.apply(bpy.context, 'MERGE')
    merged = bpy.context.scene.objects['Merged Moving']
    original[merged.name] = merged.matrix_world.copy()
    expected.update(source=merged.name, source_key=ports.local_ports(merged)[-1]['key'],
                    label='ZH merged Mesh named port')


def clear_selection():
    state().source = None
    state().target = None


def finish():
    keymap.keymap_items.remove(bridge_key)
    (OUT / 'results.json').write_text(json.dumps(dict(checks=checks), indent=2))
    bpy.ops.wm.quit_blender()


for language in ('EN', 'ZH'):
    for index, (source_key, target_key) in enumerate((('START', 'START'), ('START', 'END'), ('END', 'START'), ('END', 'END'))):
        events.extend([
            lambda lang=language, a=source_key, b=target_key, s='AB'[index % 2]: setup(lang, a, b, s),
            lambda: bpy.ops.line_pipe.pick_port('INVOKE_DEFAULT', role='pair'),
            lambda: click_port('target'),
            lambda: click_port('source'),
            check_picked,
            lambda: bpy.ops.ed.undo_push(message='Before selected endpoint connection'),
            click_direct, check_preview,
            lambda: event('RET', 'PRESS'), check_link,
            lambda: bpy.ops.ed.undo(),
            lambda: check(expected['label'] + ' Undo restores unconnected objects', len(state().links) == 0),
            clear_selection,
            lambda: bpy.ops.ed.redo(), check_redo,
        ])
events.extend([
    lambda: setup('EN', 'START', 'END', 'A'),
    lambda: bpy.ops.line_pipe.pick_port('INVOKE_DEFAULT', role='target'),
    lambda: click_port('target'),
    lambda: bpy.ops.line_pipe.pick_port('INVOKE_DEFAULT', role='source'),
    lambda: click_port('source'), check_picked,
    click_direct, check_preview,
    lambda: event('ESC', 'PRESS'),
    lambda: check('cancel leaves newly selected Anchor and keys intact', ops.preview is None and selected() == wanted()
                  and all(near_matrix(obj.matrix_world, original[obj.name]) for obj in bpy.context.scene.objects)),
])
for index, (source_key, target_key) in enumerate((('START', 'START'), ('START', 'END'), ('END', 'START'), ('END', 'END'))):
    events.extend([
        lambda a=source_key, b=target_key, s='AB'[index % 2], lang=('EN', 'ZH')[index % 2]: setup(lang, a, b, s),
        lambda: bpy.ops.line_pipe.pick_port('INVOKE_DEFAULT', role='pair'),
        lambda: click_port('target'),
        lambda: click_port('source'), check_picked,
        lambda: setattr(state(), 'distance', 20),
        lambda: setattr(state(), 'radius', .2),
        lambda: event('MOUSEMOVE', x=500, y=400),
        lambda: event('F8', 'PRESS'),
        lambda: event('F8', 'RELEASE'), check_bridge,
    ])
events.extend([
    setup_merged,
    lambda: bpy.ops.line_pipe.pick_port('INVOKE_DEFAULT', role='pair'),
    lambda: click_port('target'),
    lambda: click_port('source'), check_picked,
    click_direct, check_preview,
    lambda: event('RET', 'PRESS'), check_link,
    lambda: bpy.ops.screen.screenshot(filepath=str(OUT / 'endpoint-selection.png')),
    finish,
])


def tick():
    try:
        next(r for r in area.regions if r.type == 'UI').active_panel_category = 'PipeWorks'
        with bpy.context.temp_override(window=window, area=area, region=region):
            events.pop(0)()
    except Exception:
        (OUT / 'failure.txt').write_text(traceback.format_exc(), encoding='utf8')
        traceback.print_exc()
        bpy.ops.screen.screenshot(filepath=str(OUT / 'failure.png'))
        bpy.ops.wm.quit_blender()
        return None
    return .2


bpy.app.timers.register(tick, first_interval=3)
