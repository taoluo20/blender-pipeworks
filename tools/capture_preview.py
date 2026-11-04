# SPDX-License-Identifier: GPL-3.0-or-later
"""Capture the actual PipeWorks panel and modal guides in a disposable wide viewport."""
import json
from mathutils import Euler
import os
from pathlib import Path
import runpy
import sys
import tomllib
import traceback
import bpy
from bpy_extras import view3d_utils
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1]
VERSION = tomllib.loads((ROOT / 'line_pipe' / 'blender_manifest.toml').read_text(encoding='utf8'))['version']
OUT = ROOT / 'verification' / ('release-' + VERSION)
OUT.mkdir(parents=True, exist_ok=True)
assert Path(bpy.utils.user_resource('CONFIG')).is_relative_to(OUT)
assert not bpy.data.filepath, 'Capture only in a disposable factory-startup scene'
bpy.context.preferences.filepaths.temporary_directory = str(OUT)
bpy.context.preferences.view.show_splash = False
sys.path.insert(0, str(ROOT))
bpy.ops.preferences.addon_enable(module='line_pipe')
import line_pipe
from line_pipe import operators
assert bpy.context.preferences.addons['line_pipe'].preferences.guide_idle[:] == (1, 1, 1, 1)
runpy.run_path(str(ROOT / 'tools' / 'build_example.py'), run_name='__main__')

window = bpy.context.window_manager.windows[0]
actions = []
mouse = (450, 450)
captures = []
hidden_examples = []


def area_context():
    area = next(a for a in window.screen.areas if a.type == 'VIEW_3D')
    region = next(r for r in area.regions if r.type == 'WINDOW')
    return {'window': window, 'area': area, 'region': region}


def event(kind, value='NOTHING', point=None, **modifiers):
    global mouse
    if point is not None:
        mouse = tuple(int(v) for v in point)
    window.event_simulate(type=kind, value=value, x=mouse[0], y=mouse[1], **modifiers)


def capture(name):
    operation = operators.session
    if name == 'pipeworks-start-selector.png':
        assert operation and operation.route is None and operation._start_mode == 'QUICK'
    elif name == 'pipeworks-six-axis.png':
        assert operation and operation.route.choosing_initial and operation._initial_choice == '+Z'
    elif name == 'pipeworks-bend-preview.png':
        assert operation and operation.route.turning and operation.route.candidate is not None
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


def choose_origin():
    operation = operators.session
    assert operation and operation.route is None
    target = operation._start_mouse + Vector((-48, 0))
    event('MOUSEMOVE', point=target + Vector((operation.region.x, operation.region.y)))


def prepare_modal():
    context = area_context()
    for obj in bpy.context.scene.objects:
        if not obj.hide_get():
            hidden_examples.append(obj)
            obj.hide_set(True)
    view = context['area'].spaces.active.region_3d
    view.view_location = (0, 0, .35)
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
    operation = operators.session
    target = operation._turn_mouse + Vector((85, 0))
    event('MOUSEMOVE', point=target + Vector((operation.region.x, operation.region.y)))


def prepare_connections():
    runpy.run_path(str(ROOT / 'tools' / 'build_connection_example.py'), run_name='__main__')


def prepare_library():
    # Only the disposable self-authored scene created by this script is replaced.
    for obj in tuple(bpy.context.scene.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    settings = bpy.context.scene.line_pipe_settings
    settings.tool_mode = 'LIBRARY'
    settings.diameter = .4
    settings.hollow = True
    settings.wall = .035
    settings.free_sides = False
    settings.template_length = 1.2
    family = ''
    for sides, x in ((24, -1.1), (60, 1.1)):
        settings.radial_segments = sides
        obj = line_pipe.fittings.create_fitting(bpy.context, 'ELBOW')
        obj.name = 'Hollow Elbow ' + str(sides)
        obj.location.x = x
        obj.rotation_euler.x = -.65
        bpy.context.view_layer.update()
        identifier = line_pipe.fittings.add_to_library(bpy.context, obj, family)
        family = family or identifier
    settings.continuation_fitting = family
    view = area_context()['area'].spaces.active.region_3d
    view.view_rotation = Euler((1.35, 0, .3)).to_quaternion()
    view.view_location = (.5, .3, .6)
    view.view_distance = 6
    view.view_perspective = 'PERSP'


def finish():
    (OUT / 'capture-result.json').write_text(json.dumps({
        'product': 'PipeWorks', 'screenshots': captures, 'perspective': True,
        'minimum_aspect_ratio': '16:9', 'self_authored_geometry': True,
        'source_module': line_pipe.__file__, 'blender': bpy.app.version_string,
        'version': VERSION, 'default_arrow_rgba': list(line_pipe.data.GUIDE_IDLE),
        'selected_arrow_rgba': list(line_pipe.data.GUIDE_ACTIVE),
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
    lambda: event('P', 'PRESS', ctrl=True), lambda: event('P', 'RELEASE'),
    lambda: capture('pipeworks-start-selector.png'), choose_origin, aim,
    lambda: capture('pipeworks-six-axis.png'),
    lambda: event('B', 'PRESS'), bend_move,
    lambda: capture('pipeworks-bend-preview.png'),
    lambda: event('B', 'RELEASE'), lambda: event('ESC', 'PRESS'),
    restore_examples,
    lambda: bpy.ops.wm.save_as_mainfile(filepath=str(ROOT / 'examples' / 'pipeworks-example.blend')),
    prepare_connections, lambda: capture('pipeworks-connections.png'),
    prepare_library, lambda: capture('pipeworks-library-en.png'),
    lambda: bpy.ops.line_pipe.language(), lambda: capture('pipeworks-library-zh.png'),
    lambda: bpy.ops.line_pipe.language(),
    finish,
])
bpy.app.timers.register(tick, first_interval=2)
