"""Native list/viewport box selection and live absolute batch parameter dragging."""
import importlib
import json
import os
import sys
from pathlib import Path
import traceback
import tomllib
import bpy
from bpy_extras import view3d_utils
from mathutils import Euler, Vector

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'verification/selection-edit-ui'
for key in ('BLENDER_USER_CONFIG', 'BLENDER_USER_SCRIPTS', 'BLENDER_USER_EXTENSIONS'):
    assert Path(os.environ[key]).is_relative_to(OUT) and Path(os.environ[key]).is_dir()
assert Path(bpy.utils.user_resource('CONFIG')).is_relative_to(OUT)
version = tomllib.loads((ROOT / 'line_pipe/blender_manifest.toml').read_text())['version']
bpy.ops.extensions.package_install_files(filepath=str(ROOT / 'dist' / ('pipeworks-' + version + '.zip')),
                                         repo='user_default', enable_on_install=True)
addon = importlib.import_module('bl_ext.user_default.line_pipe')
g, e, ports, c = addon.groups, addon.editing, addon.ports, addon.connections
window = bpy.context.window
area = next(a for a in window.screen.areas if a.type == 'VIEW_3D')
region = next(r for r in area.regions if r.type == 'WINDOW')
space = area.spaces.active
space.show_region_ui = True
space.region_3d.view_rotation = Euler((1.25, 0, .35)).to_quaternion()
space.region_3d.view_location = (-1, 0, 0)
space.region_3d.view_distance = 16
space.region_3d.view_perspective = 'PERSP'
bpy.context.preferences.view.show_splash = False
bpy.context.preferences.filepaths.temporary_directory = str(OUT)
for obj in tuple(bpy.context.scene.objects):
    bpy.data.objects.remove(obj, do_unlink=True)
checks, events, measurements = [], [], {}
pointer = [500, 400]


def pipe(name, points, radius=.4):
    obj = addon.geometry.create(bpy.context)
    obj.name = name
    addon.data.store_parameters(obj, .2, radius, 32, 16, [False, 'FREE', .02, '10'])
    addon.geometry.update(obj, points, .2, radius, 32, 16, store=True)
    return obj


a = pipe('A Supply', [(-4, 0, 0), (-3, 0, 0)], .4)
b = pipe('B Return', [(1, 2, 0), (2, 2, 0)], .6)
bpy.context.view_layer.update()
bridge = c.bridge(bpy.context, a, 'END', b, 'START', .3, True, 20)
outside = pipe('Outside', [(4, 4, 0), (5, 4, 0)])
names = dict(a=a.name, b=b.name, bridge=bridge.name, outside=outside.name)
g.refresh(bpy.context.scene, reset=True)
group_uid = next(row.uid for row in g.state_for(bpy.context.scene).items if row.kind == 'GROUP')
uids = {key: next(row.uid for row in g.state_for(bpy.context.scene).items if row.source == obj)
        for key, obj in (('a', a), ('b', b), ('bridge', bridge), ('outside', outside))}
bpy.context.scene.line_pipe_settings.tool_mode = 'GROUPS'
g.select_objects(bpy.context, set())


def obj(key):
    return bpy.context.scene.objects[names[key]]


def state():
    return g.state_for(bpy.context.scene)


def event(kind, value='NOTHING', x=None, y=None, **kwargs):
    if x is not None:
        pointer[:] = [int(x), int(y)]
    window.event_simulate(type=kind, value=value, x=pointer[0], y=pointer[1], **kwargs)


def capture(name):
    bpy.ops.screen.screenshot(filepath=str(OUT / (name + '.png')))


def check(name, condition):
    assert condition, name
    checks.append(name)
    print('PASS SELECTION UI:', name, flush=True)


def selected():
    return {o.name for o in e.targets(bpy.context)}


def begin_box(uid):
    ui = next(r for r in area.regions if r.type == 'UI')
    index = [row.uid for row in g.visible_rows(state())].index(uid)
    event('MOUSEMOVE', x=ui.x+180, y=window.height-330-index*20*bpy.context.preferences.system.ui_scale)


def press_box():
    event('LEFTMOUSE', 'PRESS')


def release_box():
    event('LEFTMOUSE', 'RELEASE')


def hover_selection_mode():
    ui = next(r for r in area.regions if r.type == 'UI')
    event('MOUSEMOVE', x=ui.x+280, y=window.height-288)


def box_to(uid):
    index = [row.uid for row in g.visible_rows(state())].index(uid)
    event('MOUSEMOVE', x=pointer[0]+70, y=window.height-330-index*20*bpy.context.preferences.system.ui_scale)


def begin_radius_drag():
    ui = next(r for r in area.regions if r.type == 'UI')
    event('MOUSEMOVE', x=ui.x+250, y=window.height-692)
    measurements['drag_start'] = tuple(pointer)


def check_live(label):
    values = [e.values(o)['bend_radius'] for o in e.targets(bpy.context)]
    measurements[label] = values
    check(label + ' synchronizes every selected pipe before mouse release',
          len(values) == 3 and max(values)-min(values) < 1e-6 and abs(values[0]-.3) > .01)
    check(label + ' leaves unselected pipe untouched', abs(e.values(obj('outside'))['bend_radius']-.4) < 1e-6)


def hover_preset():
    ui = next(r for r in area.regions if r.type == 'UI')
    event('MOUSEMOVE', x=ui.x+250, y=window.height-788)


def check_sides(label, expected):
    check(label, addon.data._preset_drag is not None and all(
        e.values(obj(key))['radial_segments'] == expected for key in ('a', 'b', 'bridge')))


def viewport_box_bounds():
    points = [view3d_utils.location_3d_to_region_2d(region, space.region_3d, obj(key).matrix_world.translation)
              for key in ('a', 'bridge')]
    assert all(point is not None for point in points)
    low = Vector((min(point.x for point in points)-12, min(point.y for point in points)-12))
    high = Vector((max(point.x for point in points)+12, max(point.y for point in points)+12))
    return (region.x+low.x, region.y+low.y), (region.x+high.x, region.y+high.y)


def begin_viewport_box():
    low, high = viewport_box_bounds()
    event('MOUSEMOVE', x=low[0], y=low[1])


def finish():
    (OUT / 'results.json').write_text(json.dumps(dict(checks=checks, measurements=measurements), indent=2))
    bpy.ops.wm.quit_blender()


events.extend([
    lambda: capture('before-selection'),
    lambda: begin_box(group_uid),
    press_box,
    lambda: check('pressing a list name starts its native selection gesture', g._box is not None),
    lambda: event('LEFTMOUSE', 'RELEASE'),
    lambda: check('clicking a group selects both pipes and its automatic bridge', g._box is None
                  and selected() == {names[key] for key in ('a', 'b', 'bridge')}),
    lambda: capture('group-selected'),
    begin_radius_drag,
    lambda: event('LEFTMOUSE', 'PRESS'),
    lambda: capture('radius-pressed'),
    lambda: event('MOUSEMOVE', x=pointer[0]+5, y=pointer[1]),
    lambda: event('MOUSEMOVE', x=pointer[0]+25, y=pointer[1]),
    lambda: check_live('first drag'),
    lambda: event('MOUSEMOVE', x=pointer[0]+25, y=pointer[1]),
    lambda: check_live('continued drag'),
    lambda: check('continued motion updates the shared displayed number', measurements['continued drag'][0] != measurements['first drag'][0]),
    lambda: event('LEFTMOUSE', 'RELEASE'),
    lambda: bpy.ops.ed.undo(),
    lambda: check('Undo restores all different initial radii as one edit', all(
        abs(e.values(obj(key))['bend_radius']-value) < 1e-6 for key, value in (('a', .4), ('b', .6), ('bridge', .3)))),
    lambda: bpy.ops.ed.redo(),
    lambda: check('Redo restores the common dragged radius', len({round(e.values(obj(key))['bend_radius'], 5) for key in ('a', 'b', 'bridge')}) == 1),
    lambda: bpy.ops.line_pipe.language(),
    begin_radius_drag,
    lambda: event('LEFTMOUSE', 'PRESS'),
    lambda: event('MOUSEMOVE', x=pointer[0]+5, y=pointer[1]),
    lambda: event('MOUSEMOVE', x=pointer[0]+10, y=pointer[1]),
    lambda: check_live('Chinese drag'),
    lambda: event('LEFTMOUSE', 'RELEASE'),
    lambda: bpy.ops.line_pipe.language(),
    lambda: setattr(bpy.context.scene.line_pipe_edit, 'radial_segments', 60),
    lambda: setattr(bpy.context.scene.line_pipe_edit, 'free_sides', False),
    hover_preset,
    lambda: event('LEFTMOUSE', 'PRESS'),
    lambda: event('MOUSEMOVE', x=pointer[0]+45, y=pointer[1]),
    lambda: check_sides('preset drag updates all three profiles before release', 72),
    lambda: event('MOUSEMOVE', x=pointer[0]+45, y=pointer[1]),
    lambda: check_sides('continued preset drag keeps every selected profile live', 144),
    lambda: event('ESC', 'PRESS'),
    lambda: event('LEFTMOUSE', 'RELEASE'),
    lambda: check('canceling a live preset drag restores all initial edge counts', addon.data._preset_drag is None
                  and all(e.values(obj(key))['radial_segments'] == 60 for key in ('a', 'b', 'bridge'))),
    lambda: g.select_objects(bpy.context, set()),
    lambda: begin_box(uids['a']),
    press_box,
    lambda: check('list selection starts after canceling the numeric preset control', g._box is not None),
    lambda: box_to(uids['b']),
    lambda: capture('list-box-preview'),
    lambda: event('LEFTMOUSE', 'RELEASE'),
    lambda: check('list rectangle selects exactly two pipe rows', g._box is None and selected() == {names['a'], names['b']}),
    # Event simulation retains the native row button; physical Windows dragging is checked separately.
    release_box,
    lambda: setattr(bpy.context.scene.line_pipe_edit, 'bend_radius', .65),
    lambda: check('two selected list rows edit exactly two pipes', all(abs(e.values(obj(key))['bend_radius']-.65) < 1e-6 for key in ('a', 'b'))
                  and abs(e.values(obj('bridge'))['bend_radius']-.65) > .01),
    hover_selection_mode,
    lambda: setattr(state(), 'selection_mode', 'ADD'),
    lambda: begin_box(uids['bridge']),
    press_box,
    release_box,
    lambda: check('Add mode includes the bridge without clearing either pipe', selected() == {names[key] for key in ('a', 'b', 'bridge')}),
    hover_selection_mode,
    lambda: setattr(state(), 'selection_mode', 'SUBTRACT'),
    lambda: begin_box(uids['b']),
    press_box,
    release_box,
    lambda: check('Remove mode excludes only the chosen row', selected() == {names['a'], names['bridge']}),
    lambda: setattr(state(), 'selection_mode', 'REPLACE'),
    lambda: begin_box(uids['outside']),
    press_box,
    lambda: box_to(uids['a']),
    lambda: event('ESC', 'PRESS'),
    lambda: event('LEFTMOUSE', 'RELEASE'),
    lambda: check('Escape cancels list box selection without changing it', g._box is None and selected() == {names['a'], names['bridge']}),
    lambda: g.select_objects(bpy.context, set()),
    begin_viewport_box,
    lambda: bpy.ops.view3d.select_box('INVOKE_DEFAULT'),
    lambda: capture('viewport-box-ready'),
    lambda: event('LEFTMOUSE', 'PRESS'),
    lambda: event('MOUSEMOVE', x=viewport_box_bounds()[1][0], y=viewport_box_bounds()[1][1]),
    lambda: capture('viewport-box-preview'),
    lambda: event('LEFTMOUSE', 'RELEASE'),
    lambda: check('native viewport box selection includes the bridge', selected() == {names['a'], names['bridge']}),
    lambda: check('viewport box selection synchronizes list checkboxes', all(
        row.selected == (row.source is not None and row.source.name in selected()) for row in state().items)),
    lambda: setattr(bpy.context.scene.line_pipe_edit, 'bend_steps', 28),
    lambda: check('viewport-box batch edit affects exactly its two objects',
                  all(e.values(obj(key))['bend_steps'] == 28 for key in ('a', 'bridge')) and e.values(obj('b'))['bend_steps'] == 16),
    lambda: bpy.ops.line_pipe.language(),
    lambda: capture('selection-chinese'),
    lambda: check('Chinese shared editor and box tooltip are complete', addon.i18n.language() == 'ZH'
                  and '框选' in g.PW_OT_group_box_select.description(bpy.context, None)),
    lambda: bpy.ops.line_pipe.language(),
    lambda: capture('selection-english'),
    lambda: setattr(bpy.context.scene.line_pipe_settings, 'tool_mode', 'LIBRARY'),
    lambda: capture('library-shared-editor-english'),
    lambda: bpy.ops.line_pipe.language(),
    lambda: capture('library-shared-editor-chinese'),
    lambda: bpy.ops.line_pipe.language(),
    finish,
])


def tick():
    try:
        next(r for r in area.regions if r.type == 'UI').active_panel_category = 'PipeWorks'
        if not events:
            return None
        with bpy.context.temp_override(window=window, area=area, region=region):
            events.pop(0)()
    except Exception:
        (OUT / 'failure.txt').write_text(traceback.format_exc(), encoding='utf8')
        traceback.print_exc()
        capture('failure')
        bpy.ops.wm.quit_blender()
        return None
    return .25


if '--manual' in sys.argv:
    g.select_objects(bpy.context, {obj('a'), obj('b')}, obj('a'))
    state().selection_mode = 'ADD'
    events.clear()
bpy.app.timers.register(tick, first_interval=3)
