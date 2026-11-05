"""Installed extension group-list UI, drag, Undo and bilingual layout checks."""
import importlib
import json
import math
import os
from pathlib import Path
import sys
import traceback
import tomllib
import bpy
from mathutils import Euler

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'verification/groups-ui'
for key in ('BLENDER_USER_CONFIG', 'BLENDER_USER_SCRIPTS', 'BLENDER_USER_EXTENSIONS'):
    assert Path(os.environ[key]).is_relative_to(OUT) and Path(os.environ[key]).is_dir()
assert Path(bpy.utils.user_resource('CONFIG')).is_relative_to(OUT)
version = tomllib.loads((ROOT / 'line_pipe/blender_manifest.toml').read_text())['version']
bpy.ops.extensions.package_install_files(filepath=str(ROOT / 'dist' / ('pipeworks-' + version + '.zip')),
                                         repo='user_default', enable_on_install=True)
addon = importlib.import_module('bl_ext.user_default.line_pipe')
g = addon.groups
checks, events, measurements = [], [], {}
window = bpy.context.window
area = next(a for a in window.screen.areas if a.type == 'VIEW_3D')
region = next(r for r in area.regions if r.type == 'WINDOW')
space = area.spaces.active
space.show_region_ui = True
space.region_3d.view_perspective = 'PERSP'
space.region_3d.view_rotation = Euler((1.3, 0, .25)).to_quaternion()
space.region_3d.view_distance = 12
space.region_3d.view_location = (0, 0, 1)
space.shading.color_type = 'OBJECT'
bpy.context.preferences.view.show_splash = False
bpy.context.preferences.filepaths.temporary_directory = str(OUT)
for obj in tuple(bpy.context.scene.objects):
    bpy.data.objects.remove(obj, do_unlink=True)


def check(name, condition):
    assert condition, name
    checks.append(name)
    print('PASS GROUP UI:', name, flush=True)


def state():
    return g.state_for(bpy.context.scene)


def pipe(name, points, location, color):
    obj = addon.geometry.create(bpy.context)
    obj.name = name
    addon.geometry.update(obj, points, .2, .4, 32, 16, store=True)
    obj.location, obj.color = location, color
    return obj


first = pipe('Cooling Supply', [(0,0,0), (2,0,0), (2,0,2)], (-2,-1,0), (.12,.6,.8,1))
second = pipe('Cooling Return', [(0,0,0), (2,0,0), (2,0,1)], (-2,0,0), (.8,.45,.12,1))
third = pipe('Service Line', [(0,0,0), (1,0,0), (1,0,1)], (1,1,0), (.6,.65,.68,1))
names = [obj.name for obj in (first, second, third)]
bpy.context.view_layer.update()
g.refresh(bpy.context.scene, reset=True)
group = g.group_rows(bpy.context, [row for row in state().items if row.source in {first, second}])
group.name = 'Cooling Assembly'
group_uid = group.uid
third_uid = next(row.uid for row in state().items if row.source == third)
first_uid = next(row.uid for row in state().items if row.source == first)
settings = bpy.context.scene.line_pipe_settings
settings.tool_mode = 'GROUPS'
state().show_templates = True
state().template_scope = 'PIPES'
state().template = '{group}_{index:03d}'
pointer = [region.x + region.width * .45, region.y + region.height * .5]


def event(kind, value='NOTHING', x=None, y=None, **kwargs):
    if x is not None:
        pointer[:] = [int(x), int(y)]
    window.event_simulate(type=kind, value=value, x=int(pointer[0]), y=int(pointer[1]), **kwargs)


def capture(name):
    bpy.ops.screen.screenshot(filepath=str(OUT / (name + '.png')))


def begin_drag(uid):
    ui = next(r for r in area.regions if r.type == 'UI')
    visible = [row.uid for row in g.visible_rows(state())]
    index = visible.index(uid)
    # Grip centers observed in the 1600x950 factory-profile screenshot.
    event('MOUSEMOVE', x=ui.x + 80, y=window.height - 330 - index * 20 * bpy.context.preferences.system.ui_scale)
    event('LEFTMOUSE', 'PRESS')
    print('GRIP CLICK', dict(ui=(ui.x,ui.y,ui.width,ui.height), window=(window.width,window.height),
                            scale=bpy.context.preferences.system.ui_scale, index=index, pointer=pointer), flush=True)
    measurements['drag_start'] = tuple(pointer)


def drag_to(source_uid, target_uid):
    visible = [row.uid for row in g.visible_rows(state())]
    difference = visible.index(target_uid) - visible.index(source_uid)
    event('MOUSEMOVE', x=pointer[0], y=pointer[1] - difference * 20 * bpy.context.preferences.system.ui_scale)


def finish():
    g.unregister_callbacks()
    (OUT / 'results.json').write_text(json.dumps(dict(checks=checks, measurements=measurements), indent=2))
    if '--manual' not in sys.argv:
        bpy.ops.wm.quit_blender()


events.extend([
    lambda: check('Groups panel leaves scene objects unmerged', len(bpy.context.scene.objects) == 3),
    lambda: capture('groups-english'),
    lambda: check('group list defaults to Mesh apply', state().apply_mode == 'MERGE'),
    lambda: bpy.ops.ed.undo_push(message='Group list before drag'),
    lambda: begin_drag(third_uid),
    lambda: drag_to(third_uid, group_uid),
    lambda: check('drag targets group with into placement', g._drag is not None and g._drag.target == group_uid and g._drag.placement == 'INTO'),
    lambda: capture('groups-drag-preview'),
    lambda: event('LEFTMOUSE', 'RELEASE'),
    lambda: check('native drag moves only the staged row', g.find(state(), third_uid).parent_uid == group_uid and len(bpy.context.scene.objects) == 3),
    lambda: bpy.ops.ed.undo(),
    lambda: check('native Undo restores staged regrouping', not g.find(state(), third_uid).parent_uid and len(bpy.context.scene.objects) == 3),
    lambda: bpy.ops.ed.redo(),
    lambda: check('native Redo restores staged regrouping', g.find(state(), third_uid).parent_uid == group_uid),
    lambda: begin_drag(first_uid),
    lambda: event('ESC', 'PRESS'),
    lambda: check('drag cancel removes overlay without moving a row', g._drag is None and g.find(state(), first_uid).parent_uid == group_uid),
    lambda: bpy.ops.line_pipe.group_list(action='TEMPLATE'),
    lambda: check('template rename stays in list', set(obj.name for obj in bpy.context.scene.objects) == set(names) and state().items[1].name != state().items[1].source.name),
    lambda: addon.i18n.language(),
    lambda: bpy.ops.line_pipe.language(),
    lambda: capture('groups-chinese'),
    lambda: check('Chinese mode covers controls and templates', addon.i18n.language() == 'ZH' and state().template_zh == state().template),
    lambda: bpy.ops.line_pipe.language(),
    lambda: bpy.ops.ed.undo_push(message='Before staged Mesh apply'),
    lambda: bpy.ops.line_pipe.group_apply('EXEC_DEFAULT', True, mode='MERGE'),
    lambda: check('apply makes one actual Mesh in Outliner', len(bpy.context.scene.objects) == 1 and next(iter(bpy.context.scene.objects)).type == 'MESH'),
    lambda: capture('groups-applied-mesh'),
    lambda: bpy.ops.ed.undo(),
    lambda: check('Undo apply restores all original objects and pending group', len(bpy.context.scene.objects) == 3 and any(row.kind == 'GROUP' for row in state().items)),
    lambda: bpy.ops.ed.redo(),
    lambda: check('Redo apply restores merged Mesh and list', len(bpy.context.scene.objects) == 1 and len(state().items) == 1),
    lambda: bpy.ops.ed.undo(),
    lambda: bpy.ops.line_pipe.group_apply('EXEC_DEFAULT', True, mode='COLLECTION'),
    lambda: check('Collection alternative retains three independent objects', len(bpy.context.scene.objects) == 3 and len({next(iter(obj.users_collection)) for obj in bpy.context.scene.objects}) == 1),
    lambda: capture('groups-applied-collection'),
    lambda: bpy.ops.ed.undo(),
    lambda: check('Undo Collection apply restores pending names', len(bpy.context.scene.objects) == 3 and state().dirty),
    lambda: bpy.ops.wm.save_as_mainfile(filepath=str(OUT / 'groups-review.blend'), check_existing=False),
    lambda: begin_drag(first_uid), g.unregister_callbacks,
    lambda: check('disabling drag callbacks removes active handler', g._drag is None),
    finish,
])


def tick():
    try:
        next(r for r in area.regions if r.type == 'UI').active_panel_category = 'PipeWorks'
        if events:
            with bpy.context.temp_override(window=window, area=area, region=region):
                events.pop(0)()
    except Exception:
        (OUT / 'failure-state.json').write_text(json.dumps(dict(
            objects=[obj.name for obj in bpy.context.scene.objects],
            rows=[dict(uid=row.uid, name=row.name, parent=row.parent_uid, kind=row.kind,
                       source=row.source.name if row.source else None) for row in state().items],
            dirty=state().dirty,
            drag=dict(uid=g._drag.uid, target=g._drag.target, index=g._drag.index) if g._drag else None,
        ), indent=2))
        capture('groups-failure')
        (OUT / 'failure.txt').write_text(traceback.format_exc(), encoding='utf8')
        traceback.print_exc()
        bpy.ops.wm.quit_blender()
        return None
    return .25 if events else None


bpy.app.timers.register(tick, first_interval=3)
