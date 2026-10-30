# SPDX-License-Identifier: GPL-3.0-or-later
"""Capture the actual PipeWorks panel and modal guides in a disposable wide viewport."""
import json
import os
from pathlib import Path
import runpy
import sys
import traceback
import bpy
from bpy_extras import view3d_utils
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'verification' / 'release-0.1.1'
OUT.mkdir(parents=True, exist_ok=True)
assert Path(bpy.utils.user_resource('CONFIG')).is_relative_to(OUT)
assert not bpy.data.filepath, 'Capture only in a disposable factory-startup scene'
runpy.run_path(str(ROOT / 'tools' / 'build_example.py'), run_name='__main__')
import line_pipe
from line_pipe import operators

window = bpy.context.window_manager.windows[0]
actions = []
mouse = (450, 450)
captures = []
hidden_examples = []


def area_context():
    area = next(a for a in window.screen.areas if a.type == 'VIEW_3D')
    region = next(r for r in area.regions if r.type == 'WINDOW')
    return {'window': window, 'area': area, 'region': region}


def event(kind, value='NOTHING', point=None):
    global mouse
    if point is not None:
        mouse = tuple(int(v) for v in point)
    window.event_simulate(type=kind, value=value, x=mouse[0], y=mouse[1])


def capture(name):
    context = area_context()
    space = context['area'].spaces.active
    assert space.region_3d.view_perspective == 'PERSP'
    assert context['area'].width / context['area'].height >= 16 / 9
    with bpy.context.temp_override(**context):
        bpy.ops.screen.screenshot_area(filepath=str(OUT / name))
    captures.append(name)


def maximize():
    with bpy.context.temp_override(**area_context()):
        bpy.ops.screen.screen_full_area(use_hide_panels=False)


def prepare_panel():
    context = area_context()
    area = context['area']
    space = area.spaces.active
    space.show_region_ui = True
    space.show_region_toolbar = False
    space.region_3d.view_location = (.3, 1, 1.9)
    space.region_3d.view_distance = 9
    space.region_3d.view_perspective = 'PERSP'
    space.overlay.show_floor = False
    space.overlay.show_axis_x = False
    space.overlay.show_axis_y = False
    ui = next(r for r in area.regions if r.type == 'UI')
    try:
        ui.active_panel_category = 'PipeWorks'
    except AttributeError:
        pass
    bpy.context.scene.line_pipe_settings.direction = 'AUTO'


def aim():
    operation = operators.session
    assert operation and operation.route.choosing_initial
    target = operation._mouse_base + operation._initial_directions['+Z'] * 175
    event('MOUSEMOVE', point=target + Vector((operation.region.x, operation.region.y)))


def prepare_modal():
    context = area_context()
    for obj in bpy.context.scene.objects:
        if not obj.hide_get():
            hidden_examples.append(obj)
            obj.hide_set(True)
    view = context['area'].spaces.active.region_3d
    view.view_location = (0, 0, .8)
    view.view_distance = 6


def begin():
    context = area_context()
    view = context['area'].spaces.active.region_3d
    projected = view3d_utils.location_3d_to_region_2d(context['region'], view, Vector((0, 0, 0)))
    event('MOUSEMOVE', point=(projected.x + context['region'].x, projected.y + context['region'].y))


def restore_examples():
    for obj in hidden_examples:
        obj.hide_set(False)
    prepare_panel()


def bend_move():
    event('MOUSEMOVE', point=(mouse[0] + 85, mouse[1]))


def finish():
    (OUT / 'capture-result.json').write_text(json.dumps({
        'product': 'PipeWorks', 'screenshots': captures, 'perspective': True,
        'minimum_aspect_ratio': '16:9', 'self_authored_geometry': True,
        'source_module': line_pipe.__file__, 'blender': bpy.app.version_string,
        'no_active_drawing': operators.session is None,
    }, indent=2), encoding='utf8')
    bpy.ops.wm.quit_blender()


def tick():
    try:
        with bpy.context.temp_override(**area_context()):
            actions.pop(0)()
        return .6 if actions else None
    except Exception:
        (OUT / 'failure.txt').write_text(traceback.format_exc(), encoding='utf8')
        traceback.print_exc()
        bpy.ops.wm.quit_blender()
        return None


actions.extend([
    maximize, prepare_panel, lambda: capture('pipeworks-overview-en.png'),
    lambda: bpy.ops.line_pipe.language(), lambda: capture('pipeworks-overview-zh.png'),
    lambda: bpy.ops.line_pipe.language(), prepare_modal, begin,
    lambda: event('P', 'PRESS'), lambda: event('P', 'RELEASE'), aim,
    lambda: capture('pipeworks-six-axis.png'),
    lambda: event('B', 'PRESS'), bend_move,
    lambda: capture('pipeworks-bend-preview.png'),
    lambda: event('B', 'RELEASE'), lambda: event('ESC', 'PRESS'),
    restore_examples,
    lambda: bpy.ops.wm.save_as_mainfile(filepath=str(ROOT / 'examples' / 'pipeworks-example.blend')),
    finish,
])
bpy.app.timers.register(tick, first_interval=2)
