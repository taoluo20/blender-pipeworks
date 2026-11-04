"""Native viewport-event regression checks in a disposable Blender profile."""
import json
import importlib
import math
import os
from pathlib import Path
import sys
import traceback
import tomllib
import bpy
from mathutils import Quaternion, Vector
from bpy_extras import view3d_utils

ROOT = Path(__file__).resolve().parents[1]
BASELINE = '--baseline' in sys.argv
OUT = ROOT / 'verification' / ('interaction-baseline' if BASELINE else
                              'navigation-ui' if '--navigation-only' in sys.argv else 'interaction-ui')
OUT.mkdir(parents=True, exist_ok=True)
for key in ('BLENDER_USER_CONFIG', 'BLENDER_USER_SCRIPTS', 'BLENDER_USER_EXTENSIONS'):
    assert Path(os.environ[key]).is_relative_to(OUT) and Path(os.environ[key]).is_dir()
assert Path(bpy.utils.user_resource('CONFIG')).is_relative_to(OUT)
sys.path.insert(0, os.environ.get('PIPEWORKS_SOURCE', str(ROOT)))
if '--installed' in sys.argv:
    version = tomllib.loads((ROOT / 'line_pipe/blender_manifest.toml').read_text())['version']
    bpy.ops.extensions.package_install_files(filepath=str(ROOT / 'dist' / ('pipeworks-' + version + '.zip')),
                                             repo='user_default', enable_on_install=True)
    line_pipe = importlib.import_module('bl_ext.user_default.line_pipe')
else:
    import line_pipe
operators = line_pipe.operators

trace = []
cleanup_receipts = []
original_modal = operators.LP_OT_draw.modal
original_cleanup = operators.LP_OT_draw.cleanup


def traced_modal(self, context, event):
    if event.type == 'MOUSEMOVE':
        pointer[:] = [event.mouse_x, event.mouse_y]
    if event.type != 'TIMER':
        trace.append((event.type, event.value))
    result = original_modal(self, context, event)
    if (event.type == self._turn_key and event.value == 'PRESS' and self.route
            and self.route.turning and self._warp_pending is not None):
        target = self._warp_pending
        anchor = self.project(self.route.tip)
        left, right = self.viewport_bounds()
        expected = Vector((round(max(left + 100, min(right - 100, anchor.x))),
                           round(max(100, min(self.region.height - 100, anchor.y)))))
        check('turn press targets current tip guide center', (target - expected).length < .01)
        check('turn press does not choose a bend', self.route.candidate is None)
        measurements['turn_length'] = self.route.length
        # Native simulation suppresses the OS mouse move from cursor_warp.
        window.event_simulate(type='MOUSEMOVE', value='NOTHING',
                              x=int(region.x + target.x), y=int(region.y + target.y))
    elif event.type == 'MOUSEMOVE' and self.route and self.route.turning and self.route.candidate is None:
        if 'turn_length' in measurements:
            check('turn cursor move preserves pipe length', abs(self.route.length - measurements['turn_length']) < 1e-6)
    return result


def traced_cleanup(self, context, cancel):
    original_cleanup(self, context, cancel)
    cleanup_receipts.append(dict(cleaned=self._cleaned, handlers=len(self._handles),
                                 timer=hasattr(self, '_timer'), warp=self._warp_pending is not None,
                                 navigation_timer=self._navigation_timer is not None,
                                 navigation_feedback=self._navigation_feedback is not None))


operators.LP_OT_draw.modal = traced_modal
operators.LP_OT_draw.cleanup = traced_cleanup
line_pipe.register()
bpy.context.preferences.view.show_splash = False
bpy.context.preferences.filepaths.temporary_directory = str(OUT)
window = bpy.context.window
area = next(a for a in window.screen.areas if a.type == 'VIEW_3D')
region = next(r for r in area.regions if r.type == 'WINDOW')
space = area.spaces.active
space.show_region_ui = True
space.region_3d.view_rotation = Quaternion((1, 0, 0), math.radians(65))
space.region_3d.view_distance = 12
space.region_3d.view_location = (0, 0, 0)
space.region_3d.view_perspective = 'PERSP'
for obj in tuple(bpy.context.scene.objects):
    bpy.data.objects.remove(obj, do_unlink=True)
bpy.ops.mesh.primitive_cube_add(size=2, location=(-3, 0, 0))
bpy.context.object.name = 'Disposable Start Surface'
events, checks, measurements = [], [], {}
pointer = [500, 400]
guide_receipt = []
guide_draws = []
parent_draws = []
native_parent = bpy.types.VIEW3D_MT_object_parent


def parent_draw(self, context):
    parent_draws.append(True)


native_parent.append(parent_draw)
parent_keymap = bpy.context.window_manager.keyconfigs.default.keymaps['Object Mode']
parent_bindings = [(item.id, item.idname, item.type, item.value, item.ctrl, item.shift,
                    item.alt, item.active) for item in parent_keymap.keymap_items]
original_lines = operators.lines


def traced_lines(vertices, color, width=2):
    guide_receipt.append(tuple(color))
    guide_draws.append((tuple(tuple(v) for v in vertices), tuple(color)))
    original_lines(vertices, color, width)


operators.lines = traced_lines


def has_color(color, dimensions=None):
    return any(all(abs(a - b) < 1e-6 for a, b in zip(actual, color))
               and (dimensions is None or len(vertices[0]) == dimensions)
               for vertices, actual in guide_draws)


def clear_guides():
    guide_receipt.clear()
    guide_draws.clear()


def check_anchor(name, initial=False, displaced=False):
    s = operators.session
    anchor = s.project(s.route.points[0] if initial else s.route.tip)
    left, right = s.viewport_bounds()
    expected = Vector((max(left + 100, min(right - 100, anchor.x)),
                       max(100, min(s.region.height - 100, anchor.y))))
    arrows = [vertices for vertices, _ in guide_draws if len(vertices) == 6 and len(vertices[0]) == 2]
    centers = [Vector(v[0]) - (Vector(v[1]) - Vector(v[0])).normalized() * 22 for v in arrows]
    check(name, bool(centers) and all((center - expected).length < .01 for center in centers))
    if (expected - anchor).length > 1:
        check(name + ' keeps an edge-clamp connector', any(len(v) == 2 and len(v[0]) == 2
              and (Vector(v[0]) - anchor).length < .01 and (Vector(v[1]) - expected).length < .01
              for v, _ in guide_draws))
    if displaced:
        check(name + ' remains independent of pointer', (expected - Vector((pointer[0] - region.x, pointer[1] - region.y))).length > 90)


def custom_colors():
    preferences = line_pipe.data.guide_preferences()
    preferences.guide_idle = (.19, .61, .59, .35)
    preferences.guide_active = (.85, .2, .55, .65)


def check_custom_colors(name, world=False):
    idle, active = line_pipe.data.guide_colors()
    check(name + ' uses independent RGBA on screen', has_color(idle, 2) and has_color(active, 2))
    check(name + ' has no per-axis color exceptions', all(any(all(abs(a - b) < 1e-6
          for a, b in zip(actual, color)) for color in (idle, active))
          for vertices, actual in guide_draws if len(vertices) == 6 and len(vertices[0]) == 2))
    if world:
        check(name + ' shares RGBA with world guides', has_color(idle, 3) and has_color(active, 3))


def override():
    return dict(window=window, area=area, region=region)


def check(name, value):
    assert value, name
    checks.append(name)
    print('PASS UI:', name, flush=True)


def event(kind, value='NOTHING', x=None, y=None, **kwargs):
    if x is not None:
        pointer[:] = [int(x), int(y)]
    window.event_simulate(type=kind, value=value, x=pointer[0], y=pointer[1], **kwargs)


def move(dx, dy):
    event('MOUSEMOVE', x=pointer[0] + dx, y=pointer[1] + dy)


def extend(pixels=80):
    s = operators.session
    projected = (s.rv3d.view_rotation.inverted() @ s.route.heading).xy
    projected = projected.normalized() if projected.length > .15 else Vector((0, 1))
    move(projected.x * pixels, projected.y * pixels)


def begin(direction='X'):
    settings = bpy.context.scene.line_pipe_settings
    settings.start_mode, settings.direction = 'COORDINATES', direction
    settings.diameter, settings.bend_radius = .2, .4
    if not BASELINE:
        settings.follow_tip = False
    bpy.ops.line_pipe.draw('INVOKE_DEFAULT')


def capture(name):
    bpy.ops.screen.screenshot(filepath=str(OUT / (name + '.png')))


def finish():
    measurements['events'] = trace
    measurements['installed_module'] = line_pipe.__name__
    native_parent.remove(parent_draw)
    (OUT / 'results.json').write_text(json.dumps(dict(checks=checks, measurements=measurements), indent=2))
    bpy.ops.wm.quit_blender()


def parent_fixture():
    bpy.ops.object.select_all(action='DESELECT')
    bpy.ops.mesh.primitive_cube_add(location=(3, 0, 0))
    child = bpy.context.object
    bpy.ops.mesh.primitive_cube_add(location=(5, 0, 0))
    parent = bpy.context.object
    child.select_set(True)
    measurements['parent_child'] = child.name
    measurements['parent_target'] = parent.name
    measurements['native_ctrl_p'] = [(item.idname, str(item.properties)) for item in parent_keymap.keymap_items
                                     if item.type == 'P' and item.ctrl and not item.shift]


def compact_view(distance):
    space.region_3d.view_rotation = (Quaternion((0, 0, 1), .35) @
                                    Quaternion((1, 0, 0), math.radians(75)) if distance < 2 else
                                    Quaternion((1, 0, 0), math.radians(65)))
    space.region_3d.view_distance = distance
    space.region_3d.view_location = (.18, 0, .12) if distance < 2 else (0, 0, 0)


def set_length(length):
    s = operators.session
    target = s._mouse_base + s._extension_scale * ((length - s._length_base) / s._extension_scale.length_squared)
    event('MOUSEMOVE', x=region.x + target.x, y=region.y + target.y)


def choose_bend(heading):
    s = operators.session
    sector = max(s._directions, key=lambda key: s._directions[key].dot(Vector(heading)))
    dx, dy = {'UP': (0, 65), 'DOWN': (0, -65), 'LEFT': (-65, 0), 'RIGHT': (65, 0)}[sector]
    event('MOUSEMOVE', x=region.x + s._turn_mouse.x + dx, y=region.y + s._turn_mouse.y + dy)


def tap_turn():
    # Queue release ahead of the OS warp destination, as a fast hardware tap can do.
    event('B', 'PRESS')
    event('B', 'RELEASE')


def quick():
    event('P', 'PRESS', ctrl=True)


def center_mouse():
    event('MOUSEMOVE', x=region.x + region.width * .45, y=region.y + region.height * .5)


def aim_initial(key):
    s = operators.session
    target = s._mouse_base - s._initial_base + s._initial_directions[key] * 130
    event('MOUSEMOVE', x=region.x + target.x, y=region.y + target.y)


def click_world(point):
    p = view3d_utils.location_3d_to_region_2d(region, space.region_3d, Vector(point))
    event('MOUSEMOVE', x=region.x + p.x, y=region.y + p.y)
    event('LEFTMOUSE', 'PRESS')
    event('LEFTMOUSE', 'RELEASE')


def remember():
    s = operators.session
    measurements['length'] = s.route.length
    measurements['view'] = s.view_state()


def resumed(label):
    check(label + ' resumes extension', operators.session.route.length > measurements['length'] + .05)


def settle_wrap():
    target = operators.session._warp_pending
    if target is not None:
        # Event simulation suppresses OS input, including cursor_warp's move.
        # Feed its returned destination through the same native event queue.
        check('edge requests a cursor warp', target.x < region.width * .5)
        event('MOUSEMOVE', x=region.x + target.x, y=region.y + target.y)


def remember_navigation():
    s = operators.session
    check('native drag attaches feedback observer', s._navigation_feedback is not None)
    measurements['nav_length'] = s.route.length
    measurements['nav_heading'] = list(s.route.heading)
    measurements['nav_scale'] = list(s._extension_scale)


def check_navigation(label, dx, dy):
    s = operators.session
    normal_delta = Vector((dx, dy)).dot(Vector(measurements['nav_scale']))
    expected = max(s.route.minimum, measurements['nav_length'] + normal_delta * .5)
    check(label + ' gives exactly half-speed length feedback', abs(s.route.length - expected) < 1e-6)
    check(label + ' preserves chosen heading', list(s.route.heading) == measurements['nav_heading'])
    check(label + ' releases feedback observer', s._navigation_feedback is None and s._navigation_timer is None)
    measurements.setdefault('navigation_feedback', []).append(dict(label=label, before=measurements['nav_length'],
        after=s.route.length, full_speed_delta=normal_delta, follow=s._follow))


def remember_resume():
    measurements['resume_mouse'] = pointer.copy()
    measurements['resume_length'] = operators.session.route.length
    measurements['resume_scale'] = list(operators.session._extension_scale)


def check_resume(label):
    delta = Vector(pointer) - Vector(measurements['resume_mouse'])
    expected = measurements['resume_length'] + delta.dot(Vector(measurements['resume_scale']))
    check(label + ' restores normal drawing speed', abs(operators.session.route.length - expected) < 1e-6)


def navigation(kind, count=1, reverse=False):
    for index in range(count):
        label = kind + ' ' + str(index + 1)
        events.append(remember)
        if kind == 'zoom':
            events.append(lambda: event('WHEELUPMOUSE', 'PRESS', x=region.x + region.width * .4,
                                        y=region.y + region.height * .4))
        else:
            shift = kind == 'pan'
            alt = kind == 'axis'
            ctrl = kind == 'drag_zoom'
            dx, dy = (70, 0) if alt else (-45, -30) if reverse else (45, 30)
            if alt:
                events.append(lambda: event('LEFT_ALT', 'PRESS', alt=True))
            events.append(
                lambda shift=shift, alt=alt, ctrl=ctrl: event('MIDDLEMOUSE', 'PRESS', x=region.x + region.width * .4,
                                                 y=region.y + region.height * .4, shift=shift, alt=alt, ctrl=ctrl))
            if not alt:
                events.append(remember_navigation)
            events.extend([
                lambda shift=shift, alt=alt, ctrl=ctrl, dx=dx, dy=dy: event('MOUSEMOVE', x=pointer[0] + dx,
                                                 y=pointer[1] + dy,
                                                 shift=shift, alt=alt, ctrl=ctrl),
                lambda shift=shift, alt=alt, ctrl=ctrl: event('MIDDLEMOUSE', 'RELEASE', shift=shift, alt=alt, ctrl=ctrl),
            ])
            if alt:
                events.append(lambda: event('LEFT_ALT', 'RELEASE'))
        events.extend([
            lambda label=label: check(label + ' changes native view', operators.session.view_state() != measurements['view']),
        ])
        if kind in {'orbit', 'pan', 'drag_zoom'}:
            events.append(lambda label=label, dx=dx, dy=dy: check_navigation(label, dx, dy))
        events.extend([
            lambda: measurements.update(length=operators.session.route.length),
            lambda: extend(12),
            lambda label=label: check(label + ' rebases without changing length',
                                     abs(operators.session.route.length - measurements['length']) < 1e-6),
            remember_resume, lambda: extend(55),
            lambda label=label: resumed(label),
            lambda label=label: check_resume(label),
        ])


def interaction_suite():
    events.extend([
        lambda: check('Object Mode Ctrl+P overrides parent only through addon keymap',
                      len(line_pipe._keymaps) == 1 and line_pipe._keymaps[0][0].name == 'Object Mode'
                      and line_pipe._keymaps[0][1].ctrl and not line_pipe._keymaps[0][1].shift),
        center_mouse,
        lambda: event('P', 'PRESS'),
        lambda: event('P', 'RELEASE'),
        lambda: check('plain P does not invoke PipeWorks', operators.session is None),
        lambda: event('P', 'PRESS', shift=True),
        lambda: event('P', 'RELEASE'),
        lambda: check('Shift+P no longer invokes PipeWorks', operators.session is None),
        lambda: bpy.ops.object.select_all(action='SELECT'),
        quick,
        lambda: check('Ctrl+P on selected mesh opens selector and no Parent popup', operators.session is not None
                      and operators.session.route is None and not parent_draws),
        clear_guides,
        lambda: capture('startup-selector'),
        lambda: check('start-selector arrows use white normal preference', has_color(operators.GUIDE_IDLE)
                      and not has_color(operators.GUIDE_ACTIVE)),
        lambda: event('P', 'RELEASE'),
        lambda: move(0, 10),
        lambda: check('key release and vertical jitter do not choose a start', operators.session.route is None),
        lambda: move(-50, 0),
        lambda: check('left gesture confirms zero-length world origin', operators.session.route is not None
                      and operators.session.route.points[0].length == 0 and operators.session.route.length == 0),
        lambda: extend(35),
        lambda: check('origin confirmation rebases before drawing', operators.session.route.length > .05),
    ])
    for key in ('+X', '-X', '+Y', '-Y', '+Z', '-Z'):
        events.extend([
            lambda key=key: aim_initial(key),
            lambda key=key: check('selector start retains ' + key,
                                  operators.axis_label(operators.session.route.heading) == key),
        ])
    events.extend([
        clear_guides,
        lambda: capture('six-axes'),
        lambda: check('six-axis guides draw white idle and warm yellow active arrows', has_color(operators.GUIDE_IDLE)
                      and has_color(operators.GUIDE_ACTIVE)),
        lambda: check_anchor('manual six-axis guides remain at the start', initial=True, displaced=True),
        custom_colors, clear_guides,
        lambda: capture('six-axes-custom-alpha'),
        lambda: check_custom_colors('live six-axis customization'),
        lambda: bpy.ops.line_pipe.reset_guide_colors(),
        lambda: event('WHEELUPMOUSE', 'PRESS'),
        clear_guides,
        lambda: capture('six-axes-after-navigation'),
        lambda: check_anchor('manual six-axis guides remain at start after navigation', initial=True),
        lambda: event('ESC', 'PRESS'),
        center_mouse, quick,
        lambda: event('P', 'RELEASE'),
        lambda: move(50, 0),
        lambda: check('right gesture waits for surface pick', operators.session.route is None
                      and operators.session._start_mode == 'SURFACE'),
        lambda: click_world((4, 0, 0)),
        lambda: check('surface miss stays in pick mode', operators.session.route is None),
        lambda: click_world((-3, 0, 1)),
        lambda: check('surface hit starts without selector displacement', operators.session.route is not None
                      and operators.session.route.length == 0 and operators.session.route.points[0].length > 1),
        lambda: event('ESC', 'PRESS'),
        lambda: compact_view(1.2), begin, center_mouse,
        lambda: set_length(.099),
        lambda: event('B', 'PRESS'),
        lambda: check('native short singular segment refuses a bend and retains preview', operators.session is not None
                      and not operators.session.route.turning),
        lambda: event('B', 'RELEASE'),
        lambda: set_length(.12),
        lambda: event('B', 'PRESS'),
        lambda: choose_bend((0, 0, 1)),
        lambda: check('native compact single bend fits below configured maximum', operators.session.route.turning
                      and .11 < operators.session.route.preview_length < .13 and not operators.session._notice),
        lambda: capture('compact-bend-english'),
        lambda: bpy.ops.line_pipe.language(),
        lambda: capture('compact-bend-chinese'),
        lambda: bpy.ops.line_pipe.language(),
        lambda: event('B', 'RELEASE'),
        lambda: check('native compact single bend commits', len(operators.session.route.points) == 2),
        lambda: set_length(.205),
        lambda: event('B', 'PRESS'),
        lambda: choose_bend((0, 1, 0)),
        lambda: check('native compact adjacent bend previews below twice maximum', operators.session.route.turning
                      and operators.session.route.candidate is not None and operators.session.route.length < .21),
        lambda: capture('compact-adjacent-bends'),
        lambda: event('B', 'RELEASE'),
        lambda: check('native compact adjacent bend commits', len(operators.session.route.points) == 3),
        lambda: event('BACK_SPACE', 'PRESS'),
        lambda: check('native compact bend undo restores prior heading', len(operators.session.route.points) == 2
                      and operators.session.route.heading.z > .999),
        lambda: event('RET', 'PRESS'),
        lambda: check('native compact route finishes with saved recipe', operators.session is None
                      and bpy.context.object.get('line_pipe_route_v1') is not None),
        lambda: line_pipe.geometry.remove(bpy.context.object),
        lambda: compact_view(12),
        begin, center_mouse, lambda: extend(130),
    ])
    navigation('orbit', 2)
    navigation('orbit', reverse=True)
    navigation('pan', 2)
    navigation('zoom', 2)
    navigation('axis', 2)
    events.extend([
        lambda: event('B', 'PRESS'),
        lambda: move(0, 70),
        lambda: check('bend previews a direction after navigation', operators.session.route.candidate is not None),
        clear_guides,
        lambda: capture('bend-guides-english'),
        lambda: check('bend guides draw white idle and warm yellow active arrows', has_color(operators.GUIDE_IDLE)
                      and has_color(operators.GUIDE_ACTIVE)),
        lambda: check_anchor('manual bend guides remain at tip after navigation'),
        custom_colors, clear_guides,
        lambda: capture('bend-guides-custom-alpha'),
        lambda: check_custom_colors('live bend customization', world=True),
        lambda: bpy.ops.line_pipe.reset_guide_colors(),
        clear_guides,
        lambda: capture('bend-guides-reset'),
        lambda: check('reset immediately restores white and yellow in both overlays', all(
                      has_color(color, dimensions) for color in (operators.GUIDE_IDLE, operators.GUIDE_ACTIVE)
                      for dimensions in (2, 3))),
        lambda: bpy.ops.line_pipe.language(),
        lambda: capture('bend-guides-chinese'),
        lambda: setattr(bpy.context.scene.line_pipe_settings, 'show_guides', False),
        lambda: capture('guides-hidden'),
        lambda: check('hiding guides preserves bend candidate', operators.session.route.candidate is not None),
        lambda: setattr(bpy.context.scene.line_pipe_settings, 'show_guides', True),
        lambda: bpy.ops.line_pipe.language(),
        lambda: event('B', 'RELEASE'),
        lambda: check('bend release commits after navigation', len(operators.session.route.points) == 2),
        lambda: extend(80),
    ])
    navigation('orbit')
    events.extend([
        lambda: event('BACK_SPACE', 'PRESS'),
        lambda: check('Backspace retracts bend after orbit', len(operators.session.route.points) == 1),
        lambda: event('ESC', 'PRESS'),
        lambda: check('navigation session cancels cleanly', operators.session is None
                      and not any(o.type == 'CURVE' for o in bpy.context.scene.objects)),
        begin, center_mouse, lambda: extend(100),
        lambda: event('F', 'PRESS', ctrl=True),
        lambda: event('F', 'RELEASE', ctrl=True),
        lambda: check('Ctrl+F enables follow while drawing', operators.session._follow),
        lambda: extend(10), remember,
        lambda: extend(40),
        lambda: measurements.update(first_delta=operators.session.route.length - measurements['length']),
        remember,
        lambda: extend(40),
        lambda: check('following keeps stable pixel-to-world scale', abs(operators.session.route.length
                      - measurements['length'] - measurements['first_delta']) < .02),
        lambda: check('follow tracks tip without changing rotation or zoom',
                      (space.region_3d.view_location - operators.session.route.tip).length < 1e-5
                      and operators.session.view_state()[0] == measurements['view'][0]
                      and operators.session.view_state()[2:] == measurements['view'][2:]),
    ])
    navigation('pan')
    navigation('zoom')
    navigation('axis')
    for index in range(3):
        events.extend([
            remember,
            lambda index=index: event('MOUSEMOVE', x=next(r.x for r in area.regions if r.type == 'UI')
                                      + (30 if index == 2 else -10), y=region.y + region.height * .5),
            settle_wrap,
            lambda index=index: check('edge wrap ' + str(index + 1) + ' moves pointer inward',
                                     pointer[0] < region.x + region.width * .5),
            lambda: measurements.update(wrapped_length=operators.session.route.length),
            lambda: event('MOUSEMOVE', x=pointer[0], y=pointer[1]),
            lambda: check('warp event adds no spurious length',
                          abs(operators.session.route.length - measurements['wrapped_length']) < 1e-5),
            remember,
            lambda: extend(50),
            lambda: resumed('post-wrap'),
        ])
    events.extend([
        lambda: capture('follow-long-pipe'),
        lambda: event('F', 'PRESS', ctrl=True),
        lambda: event('F', 'RELEASE', ctrl=True),
        lambda: check('Ctrl+F disables follow immediately', not operators.session._follow),
        lambda: extend(10), remember,
        lambda: extend(35),
        lambda: check('disabled follow leaves view stationary', operators.session.view_state() == measurements['view']),
        lambda: event('RET', 'PRESS'),
        lambda: check('follow session finishes as a saved procedural pipe', operators.session is None
                      and bpy.context.object.get('line_pipe_route_v1') is not None),
        begin, center_mouse, lambda: extend(100),
        lambda: event('B', 'PRESS'),
        lambda: move(0, 60),
        lambda: event('MIDDLEMOUSE', 'PRESS'),
        lambda: move(40, 20),
        lambda: event('MIDDLEMOUSE', 'RELEASE'),
        lambda: event('B', 'RELEASE'),
        lambda: check('view change clears stale bend choice', len(operators.session.route.points) == 1),
        lambda: event('WINDOW_DEACTIVATE'),
        lambda: check('focus loss removes active preview and session', operators.session is None),
        lambda: setattr(bpy.context.scene.line_pipe_settings, 'follow_tip', False),
        lambda: setattr(bpy.context.scene.line_pipe_settings, 'show_guides', False),
        begin, center_mouse, lambda: extend(100), remember,
        lambda: event('MOUSEMOVE', x=region.x + region.width + 100, y=region.y + region.height * .5),
        lambda: check('outside pointer does not extend manual route',
                      abs(operators.session.route.length - measurements['length']) < 1e-6),
        lambda: event('B', 'PRESS'),
        lambda: check('B recovers outside pointer even with guides hidden', operators.session.route.turning
                      and operators.session.inside(type('Pointer', (), dict(mouse_x=pointer[0], mouse_y=pointer[1]))())),
        lambda: event('B', 'RELEASE'),
        lambda: check('B tap returns pointer without adding a bend or changing length',
                      len(operators.session.route.points) == 1 and
                      abs(operators.session.route.length - measurements['length']) < 1e-6),
        lambda: event('MOUSEMOVE', x=region.x + region.width + 100, y=region.y + region.height * .5),
        tap_turn,
        lambda: check('fast B tap tolerates release before the warp move', not operators.session.route.turning
                      and len(operators.session.route.points) == 1
                      and abs(operators.session.route.length - measurements['length']) < 1e-6),
        lambda: extend(55), lambda: resumed('returned pointer'),
        lambda: event('B', 'PRESS'),
        lambda: choose_bend((0, 0, 1)),
        lambda: measurements.update(turn_anchor=list(operators.session._turn_mouse),
                                    turn_candidate=list(operators.session.route.candidate)),
        lambda: event('B', 'PRESS'),
        lambda: check('held key does not repeatedly recenter or clear chosen bend',
                      list(operators.session._turn_mouse) == measurements['turn_anchor'] and
                      list(operators.session.route.candidate) == measurements['turn_candidate']),
        lambda: event('B', 'RELEASE'),
        lambda: extend(75), remember,
        lambda: event('B', 'PRESS'),
        lambda: check('next bend uses the new pipe tip',
                      (operators.session._turn_mouse - Vector(measurements['turn_anchor'])).length > 5),
        lambda: event('B', 'RELEASE'),
        lambda: check('repeated returns preserve committed bend and pipe length',
                      len(operators.session.route.points) == 2 and
                      abs(operators.session.route.length - measurements['length']) < 1e-6),
        lambda: event('ESC', 'PRESS'),
        lambda: setattr(bpy.context.scene.line_pipe_settings, 'show_guides', True),
    ])
    if '--cleanup-only' in sys.argv:
        events.clear()
    events.extend([
        begin, center_mouse, lambda: extend(90),
        lambda: event('F', 'PRESS', ctrl=True),
        lambda: event('F', 'RELEASE', ctrl=True),
        lambda: check('disable test has a live following route', operators.session is not None and operators.session._follow),
        line_pipe.unregister,
        lambda: check('disable removes modal session and preview', operators.session is None
                      and sum(o.type == 'CURVE' for o in bpy.context.scene.objects) == (0 if '--cleanup-only' in sys.argv else 1)),
        lambda: check('disable removes draw handlers and timer', cleanup_receipts[-1] ==
                      dict(cleaned=True, handlers=0, timer=False, warp=False,
                           navigation_timer=False, navigation_feedback=False)),
        lambda: check('disable removes settings and keymap', not hasattr(bpy.types.Scene, 'line_pipe_settings')
                      and not line_pipe._keymaps),
    ])
    if '--keymap-only' in sys.argv:
        events.clear()
        events.append(line_pipe.unregister)
    for cycle in range(3):
        events.extend([
            line_pipe.register,
            line_pipe.register,
            lambda cycle=cycle: check('enable cycle ' + str(cycle + 1) + ' registers exactly one shortcut',
                len(line_pipe._keymaps) == 1 and sum(item.idname == 'line_pipe.draw'
                for km in bpy.context.window_manager.keyconfigs.addon.keymaps for item in km.keymap_items) == 1),
            center_mouse, quick,
            lambda: check('re-enabled Ctrl+P invokes selector', operators.session is not None
                          and operators.session.route is None and not parent_draws),
            lambda: event('ESC', 'PRESS'),
            line_pipe.unregister,
        ])
    events.extend([
        lambda: check('disable restores default Object Mode keymap unchanged', parent_bindings == [
            (item.id, item.idname, item.type, item.value, item.ctrl, item.shift, item.alt, item.active)
            for item in parent_keymap.keymap_items]),
        parent_fixture, center_mouse,
        lambda: event('P', 'PRESS', ctrl=True),
        lambda: event('P', 'RELEASE'),
        lambda: capture('native-parent-restored'),
        lambda: event('RET', 'PRESS'),
        lambda: event('RET', 'RELEASE'),
        lambda: check('disabled Ctrl+P restores native parenting', operators.session is None and
                      bpy.data.objects[measurements['parent_child']].parent == bpy.data.objects[measurements['parent_target']]),
        lambda: event('ESC', 'PRESS'),
        finish,
    ])


def baseline_suite():
    events.extend([
        begin,
        lambda: event('MOUSEMOVE', x=region.x + region.width * .45, y=region.y + region.height * .5),
        lambda: extend(110),
        lambda: measurements.update(rotation=list(space.region_3d.view_rotation)),
        lambda: event('MIDDLEMOUSE', 'PRESS'),
        lambda: move(60, 40),
        lambda: event('MIDDLEMOUSE', 'RELEASE'),
        lambda: measurements.update(rotated=list(space.region_3d.view_rotation),
                                    navigation_latched=operators.session._navigation,
                                    before=operators.session.route.length),
        lambda: extend(70),
        lambda: measurements.update(after=operators.session.route.length),
        lambda: capture('after-native-orbit'),
        lambda: check('native MMB changes the view', measurements['rotation'] != measurements['rotated']),
        lambda: check('baseline reproduces navigation latch', measurements['navigation_latched'] and
                      measurements['before'] == measurements['after']),
        lambda: event('ESC', 'PRESS'),
        finish,
    ])


def tick():
    try:
        if line_pipe._registered:
            next(r for r in area.regions if r.type == 'UI').active_panel_category = 'PipeWorks'
        if events:
            with bpy.context.temp_override(**override()):
                events.pop(0)()
    except Exception:
        (OUT / 'failure.txt').write_text(traceback.format_exc())
        if operators.session and operators.session.route:
            s = operators.session
            measurements['failure_state'] = dict(pending=list(s._warp_pending) if s._warp_pending is not None else None,
                                                base=list(s._mouse_base), length=s.route.length,
                                                bounds=s.viewport_bounds(), needs_rebase=s._needs_rebase)
        (OUT / 'failure-events.json').write_text(json.dumps(dict(pointer=pointer, trace=trace, measurements=measurements)))
        traceback.print_exc()
        bpy.ops.wm.quit_blender()
        return None
    return .25


baseline_suite() if BASELINE else interaction_suite()
if '--navigation-only' in sys.argv:
    events.clear()
    events.extend([begin, center_mouse, lambda: extend(150)])
    navigation('orbit', 2)
    navigation('orbit', reverse=True)
    navigation('pan')
    navigation('pan', reverse=True)
    navigation('drag_zoom')
    navigation('drag_zoom', reverse=True)
    navigation('axis')
    events.extend([lambda: setattr(bpy.context.scene.line_pipe_settings, 'follow_tip', True),
                   lambda: extend(10), lambda: extend(70)])
    navigation('orbit')
    navigation('pan', reverse=True)
    events.extend([
        lambda: event('ESC', 'PRESS'),
        lambda: check('navigation cancellation removes session', operators.session is None),
        lambda: begin('AUTO'), center_mouse, lambda: aim_initial('+X'),
        lambda: event('MIDDLEMOUSE', 'PRESS'), remember_navigation,
        lambda: move(45, 30), lambda: event('MIDDLEMOUSE', 'RELEASE'),
        lambda: check_navigation('automatic first axis', 45, 30),
        lambda: event('ESC', 'PRESS'),
        begin, center_mouse, lambda: extend(120),
        lambda: event('MIDDLEMOUSE', 'PRESS'), remember_navigation,
        lambda: move(25, 15), line_pipe.unregister,
        lambda: event('MIDDLEMOUSE', 'RELEASE'),
        lambda: check('disable during native drag removes feedback timers and operators', operators.session is None
                      and not cleanup_receipts[-1]['navigation_timer']
                      and not cleanup_receipts[-1]['navigation_feedback']
                      and not any(op and op.bl_idname in {'LINE_PIPE_OT_navigation_feedback', 'LINE_PIPE_OT_draw'}
                                  for op in window.modal_operators)),
        finish,
    ])
bpy.app.timers.register(tick, first_interval=3)
