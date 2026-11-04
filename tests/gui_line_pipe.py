"""Native event-queue integration exercise in an isolated interactive Blender."""
import json
import math
import os
import pathlib
import sys
import time
import traceback
import bpy
from mathutils import Quaternion, Vector
from bpy_extras import view3d_utils

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / 'verification' / 'line-pipe' / ('six-axis-ui' if '--six-axis' in sys.argv else 'ui')
OUT.mkdir(parents=True, exist_ok=True)
assert pathlib.Path(os.environ['BLENDER_USER_CONFIG']).is_relative_to(OUT)
assert pathlib.Path(bpy.utils.user_resource('CONFIG')).is_relative_to(OUT)
sys.path.insert(0, str(ROOT))
import line_pipe
from line_pipe import geometry, operators
from line_pipe.model import WORLD_AXES
line_pipe.register()
bpy.context.preferences.filepaths.temporary_directory = str(OUT)
bpy.context.preferences.view.show_splash = False

window = bpy.context.window_manager.windows[0]
area = next(a for a in window.screen.areas if a.type == 'VIEW_3D')
region = next(r for r in area.regions if r.type == 'WINDOW')
space = area.spaces.active
space.show_region_ui = True
space.region_3d.view_rotation = Quaternion((1, 0, 0), math.radians(18))
space.region_3d.view_distance = 12
space.region_3d.view_location = (0, 0, 0)
space.region_3d.view_perspective = 'ORTHO'
space.shading.type = 'SOLID'
space.shading.color_type = 'OBJECT'
space.overlay.show_floor = False
space.overlay.show_axis_x = False
space.overlay.show_axis_y = False
for obj in tuple(bpy.context.scene.objects):
    bpy.data.objects.remove(obj, do_unlink=True)
bpy.ops.mesh.primitive_cube_add(size=1, location=(-4, 0, -1))
wall = bpy.context.object
wall.name = 'Start Surface'
wall.scale = (3, 3, .3)
wall.color = (.15, .18, .21, 1)
bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
wall.select_set(False)
checks = []
events = []
last_command = None
current_mouse = (400, 400)
original_modal = operators.LP_OT_draw.modal


def simulated_modal(self, context, event):
    global current_mouse
    result = original_modal(self, context, event)
    if (event.type == self._turn_key and event.value == 'PRESS' and self.route
            and self.route.turning and self._warp_pending is not None):
        target = self._warp_pending
        current_mouse = (int(region.x + target.x), int(region.y + target.y))
        # Native simulation suppresses OS cursor-warp events; feed the destination back.
        window.event_simulate(type='MOUSEMOVE', value='NOTHING', x=current_mouse[0], y=current_mouse[1])
    return result


operators.LP_OT_draw.modal = simulated_modal


def override():
    return dict(window=window, area=area, region=region)


def check(name, value):
    assert value, name
    checks.append(name)
    print('PASS UI:', name, flush=True)


def snapshot():
    s = operators.session
    return {'checks': checks, 'session': bool(s), 'turning': s.route.turning if s and s.route else False,
            'points': [list(p) for p in s.route.points] if s and s.route else [],
            'length': s.route.length if s and s.route else None,
            'candidate': list(s.route.candidate) if s and s.route and s.route.candidate is not None else None,
            'heading': list(s.route.heading) if s and s.route else None,
            'six_axis_initial': s.route.choosing_initial if s and s.route else False,
            'objects': len(bpy.data.objects), 'curves': len(bpy.data.curves),
            'pipes': [o.name for o in bpy.context.scene.objects if o.get('line_pipe_route_v1')],
            'regions': [(r.type, r.x, r.y, r.width, r.height) for r in area.regions],
            'command_id': last_command}


def event(kind, value='NOTHING', x=None, y=None, **kw):
    global current_mouse
    if x is not None:
        current_mouse = (int(x), int(y))
    window.event_simulate(type=kind, value=value, x=current_mouse[0], y=current_mouse[1], **kw)


def begin(mode='COORDINATES', key='B'):
    s = bpy.context.scene.line_pipe_settings
    s.start_mode, s.direction, s.turn_key = mode, 'X', key
    s.origin = (0, 0, 0)
    s.diameter, s.bend_radius = .2, .4
    with bpy.context.temp_override(**override()):
        bpy.ops.line_pipe.draw('INVOKE_DEFAULT')


def mouse_base():
    event('MOUSEMOVE', x=region.x + region.width * .35, y=region.y + region.height * .4)


def move(dx=0, dy=0):
    event('MOUSEMOVE', x=current_mouse[0] + dx, y=current_mouse[1] + dy)


def extend(pixels=120):
    heading = operators.session.rv3d.view_rotation.inverted() @ operators.session.route.heading
    projected = Vector((heading.x, heading.y))
    projected = projected.normalized() if projected.length > .15 else Vector((0, 1))
    move(projected.x * pixels, projected.y * pixels)


def aim_initial(key, pixels=150):
    operation = operators.session
    target = operation._mouse_base - operation._initial_base + operation._initial_directions[key] * pixels
    event('MOUSEMOVE', x=region.x + target.x, y=region.y + target.y)


def save_image(name):
    with bpy.context.temp_override(**override()):
        bpy.ops.screen.screenshot(filepath=str(OUT / name), hide_props_region=False)


def enqueue(function):
    events.append(function)


def native_suite():
    enqueue(mouse_base)
    enqueue(lambda: event('P', 'PRESS', ctrl=True))
    enqueue(lambda: check('Ctrl+P starts selector waiting', operators.session is not None and operators.session.route is None))
    enqueue(lambda: event('P', 'RELEASE'))
    enqueue(lambda: move(-50, 0))
    enqueue(lambda: check('left gesture starts exactly at world origin', operators.session.route.points[0].length < 1e-7))
    for key in WORLD_AXES:
        enqueue(lambda key=key: aim_initial(key))
        enqueue(lambda key=key: check('P drag selects ' + key + ' before first bend',
                                     operators.session.route.heading.dot(WORLD_AXES[key]) > .999
                                     and operators.session.route.length > .4
                                     and len(operators.session.route.points) == 1))
    enqueue(lambda: save_image('six-axis-initial.png'))
    enqueue(lambda: event('B', 'PRESS'))
    enqueue(lambda: move(0, 70))
    enqueue(lambda: event('B', 'RELEASE'))
    enqueue(lambda: check('six-axis initial segment supports a perpendicular bend', len(operators.session.route.points) == 2))
    enqueue(lambda: event('BACK_SPACE', 'PRESS'))
    enqueue(lambda: aim_initial('-X'))
    enqueue(lambda: check('Backspace restores signed initial direction selection', operators.session.route.heading.x < -.999))
    enqueue(mouse_base)
    enqueue(lambda: extend(120))
    enqueue(lambda: event('ESC', 'PRESS'))
    enqueue(mouse_base)
    enqueue(lambda: event('P', 'PRESS', ctrl=True))
    enqueue(lambda: event('P', 'RELEASE'))
    enqueue(lambda: move(50, 0))
    enqueue(lambda: click_world((-4, 0, -.85)))
    enqueue(lambda: check('right gesture plus native click starts on surface', operators.session.route is not None and abs(operators.session.route.points[0].z + .85) < .001))
    enqueue(lambda: aim_initial('+Z'))
    enqueue(lambda: check('surface-picked P start can choose +Z', operators.session.route.heading.z > .999))
    enqueue(lambda: event('P', 'RELEASE'))
    enqueue(lambda: check('P release after surface click preserves picked start', operators.session.route.points[0].length > 1))
    enqueue(lambda: event('ESC', 'PRESS'))
    for sector, delta in [('UP', (0, 80)), ('DOWN', (0, -80)), ('RIGHT', (80, 0)), ('LEFT', (-80, 0))]:
        enqueue(begin)
        enqueue(mouse_base)
        enqueue(lambda: extend(160))
        enqueue(lambda: event('B', 'PRESS'))
        enqueue(lambda sector=sector: check(sector + ' native key press starts hold', operators.session.route.turning))
        enqueue(lambda delta=delta: move(*delta))
        enqueue(lambda sector=sector: check(sector + ' native move previews uncommitted bend', len(operators.session.route.points) == 1 and operators.session.route.candidate is not None))
        enqueue(lambda sector=sector: save_image('turn-' + sector.lower() + '.png'))
        enqueue(lambda: event('B', 'RELEASE'))
        enqueue(lambda sector=sector: check(sector + ' native release commits bend', len(operators.session.route.points) == 2 and not operators.session.route.turning))
        enqueue(lambda: extend(110))
        enqueue(lambda sector=sector: check(sector + ' mouse continues extending after release', operators.session.route.length > operators.session.route.minimum + .05))
        enqueue(lambda: event('RET', 'PRESS'))
        enqueue(lambda sector=sector: check(sector + ' native Enter completes solid curve', operators.session is None and bpy.context.object.get('line_pipe_route_v1') is not None))
    enqueue(lambda: bpy.ops.ed.undo())
    enqueue(lambda: check('native undo removes one entire pipe', len(snapshot()['pipes']) == 3))
    enqueue(lambda: bpy.ops.ed.redo())
    enqueue(lambda: check('native redo restores whole procedural pipe', len(snapshot()['pipes']) == 4))
    enqueue(begin)
    enqueue(mouse_base)
    enqueue(lambda: extend(160))
    enqueue(lambda: event('B', 'PRESS'))
    enqueue(lambda: move(0, 80))
    enqueue(lambda: event('B', 'RELEASE'))
    enqueue(lambda: event('BACK_SPACE', 'PRESS'))
    enqueue(lambda: check('native Backspace removes one bend', len(operators.session.route.points) == 1))
    enqueue(lambda: event('ESC', 'PRESS'))
    enqueue(lambda: check('native Escape removes preview curve and restores prior pipes', operators.session is None and len(snapshot()['pipes']) == 4 and len(bpy.data.curves) == 4))
    enqueue(lambda: begin(key='T'))
    enqueue(mouse_base)
    enqueue(lambda: extend(160))
    enqueue(lambda: event('T', 'PRESS'))
    enqueue(lambda: move(0, 80))
    enqueue(lambda: event('T', 'RELEASE'))
    enqueue(lambda: check('configurable hold key receives separate press and release', len(operators.session.route.points) == 2))
    enqueue(lambda: event('ESC', 'PRESS'))
    enqueue(lambda: begin(mode='POINT'))
    enqueue(mouse_base)
    enqueue(lambda: event('LEFTMOUSE', 'PRESS'))
    enqueue(lambda: event('LEFTMOUSE', 'RELEASE'))
    enqueue(lambda: check('native point placement starts route', operators.session.route is not None))
    enqueue(lambda: extend(140))
    enqueue(lambda: event('ESC', 'PRESS'))
    enqueue(lambda: begin(mode='SURFACE'))
    enqueue(lambda: click_world((-4, 0, -.85)))
    enqueue(lambda: check('native surface ray starts at wall', operators.session.route is not None and abs(operators.session.route.points[0].z + .85) < .001))
    enqueue(lambda: event('ESC', 'PRESS'))
    enqueue(lambda: bpy.ops.line_pipe.language())
    enqueue(lambda: check('native Chinese UI state', bpy.context.scene.line_pipe_settings.language == 'ZH'))
    enqueue(lambda: save_image('chinese.png'))
    enqueue(lambda: bpy.ops.line_pipe.language())
    enqueue(finish_suite)


def click_world(point):
    projected = view3d_utils.location_3d_to_region_2d(region, space.region_3d, Vector(point))
    event('MOUSEMOVE', x=region.x + projected.x, y=region.y + projected.y)
    event('LEFTMOUSE', 'PRESS')
    event('LEFTMOUSE', 'RELEASE')


def finish_suite():
    (OUT / 'ui-checks.json').write_text(json.dumps({'count': len(checks), 'checks': checks}, indent=2), encoding='utf8')
    bpy.context.scene.line_pipe_settings.start_mode = 'POINT'
    bpy.context.scene.line_pipe_settings.turn_key = 'B'
    save_image('english.png')
    with bpy.context.temp_override(**override()):
        bpy.ops.wm.save_as_mainfile(filepath=str(OUT / 'native-confirmed.blend'))
    print('UI COMPLETE', len(checks), flush=True)
    if '--quit' in sys.argv:
        bpy.app.timers.register(lambda: bpy.ops.wm.quit_blender() and None, first_interval=1)


def tick():
    global last_command
    try:
        ui_region = next(r for r in area.regions if r.type == 'UI')
        if ui_region.active_panel_category != 'PipeWorks':
            try:
                ui_region.active_panel_category = 'PipeWorks'
            except AttributeError:
                pass
        if events:
            with bpy.context.temp_override(**override()):
                events.pop(0)()
        command_file = OUT / 'command.json'
        if command_file.exists():
            command = json.loads(command_file.read_text(encoding='utf-8-sig'))
            if command['id'] != last_command:
                last_command = command['id']
                with bpy.context.temp_override(**override()):
                    if command['command'] == 'suite':
                        native_suite()
                    elif command['command'] == 'language':
                        bpy.ops.line_pipe.language()
                    elif command['command'] == 'capture':
                        save_image(command['name'])
                    elif command['command'] == 'quit':
                        bpy.ops.wm.quit_blender()
                        return None
        (OUT / 'live.json').write_text(json.dumps(snapshot(), indent=2), encoding='utf8')
    except Exception:
        (OUT / 'failure.txt').write_text(traceback.format_exc(), encoding='utf8')
        traceback.print_exc()
        events.clear()
        if '--quit' in sys.argv:
            bpy.ops.wm.quit_blender()
            return None
    return .25


def initialize():
    with bpy.context.temp_override(**override()):
        bpy.ops.ed.undo_push(message='Before PipeWorks UI')
    native_suite()
    return None


bpy.app.timers.register(initialize, first_interval=3)
bpy.app.timers.register(tick, first_interval=3.5, persistent=True)
