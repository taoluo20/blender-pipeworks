"""Focused integration checks using Blender's evaluated solid geometry."""
import json
import math
import pathlib
import sys
import bmesh
import bpy
from mathutils import Quaternion, Vector

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import line_pipe as addon
from line_pipe import data, geometry, i18n, operators
from line_pipe.model import (Route, WORLD_AXES, choose_initial_direction, initial_directions,
                             rounded_path, frame, turn_directions, choose_sector)

OUT = ROOT / 'verification' / 'line-pipe'
OUT.mkdir(parents=True, exist_ok=True)
checks = []


def check(name, value):
    if not value:
        raise AssertionError(name)
    checks.append(name)
    print('PASS:', name, flush=True)


def solid(obj, expected_volume=None):
    bpy.context.view_layer.update()
    evaluated = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
    mesh = evaluated.to_mesh()
    bm = bmesh.new()
    bm.from_mesh(mesh)
    check(obj.name + ' closed manifold', bool(bm.faces) and all(e.is_manifold for e in bm.edges))
    check(obj.name + ' positive solid volume', bm.calc_volume(signed=True) > 0)
    check(obj.name + ' exactly two flat solid caps', sum(len(p.vertices) > 4 and not p.use_smooth for p in mesh.polygons) == 2)
    if expected_volume is not None:
        check(obj.name + ' cross section is solid, not a hollow shell', abs(bm.calc_volume() / expected_volume - 1) < .04)
    result = (len(mesh.vertices), len(mesh.polygons), bm.calc_volume())
    bm.free()
    evaluated.to_mesh_clear()
    return result


def make(points, diameter=.2, radius=.4):
    obj = geometry.create(bpy.context)
    state = obj.line_pipe
    state.diameter, state.bend_radius = diameter, radius
    geometry.update(obj, points, diameter, radius, state.radial_segments, state.bend_steps, store=True)
    obj['_line_pipe_dimensions'] = [getattr(state, key) for key in data.DIMENSIONS]
    return obj


addon.register()
addon.register()
check('registration idempotent', bpy.app.handlers.load_pre.count(addon.before_scene_change) == 1)
check('public brand is PipeWorks', addon.bl_info['name'] == 'PipeWorks')
check('sidebar category is PipeWorks', addon.ui.LP_PT_main.bl_category == 'PipeWorks')
check('internal saved-data identifiers remain compatible', hasattr(bpy.types.Scene, 'line_pipe_settings') and hasattr(bpy.types.Object, 'line_pipe'))
settings = bpy.context.scene.line_pipe_settings
check('English default', i18n.language() == 'EN')
check('B is default hold key', settings.turn_key == 'B')
check('new panels default to six-axis mouse direction', settings.direction == 'AUTO')
check('helpers default on and following is opt-in', settings.show_guides and not settings.follow_tip)
def close_color(actual, expected):
    return all(abs(a - b) < 1e-6 for a, b in zip(actual, expected))


colors = data.guide_preferences()
check('source import falls back without an enabled preferences entry', isinstance(colors, data.LP_GuideColors))
check('factory arrow colors are white and warm yellow', all(close_color(a, b) for a, b in
      zip(data.guide_colors(), (data.GUIDE_IDLE, data.GUIDE_ACTIVE))))
check('native color controls use display-space RGBA', all(colors.bl_rna.properties[key].subtype == 'COLOR_GAMMA'
      and colors.bl_rna.properties[key].array_length == 4 for key in ('guide_idle', 'guide_active')))
colors.guide_idle = (.2, .3, .4, .25)
check('normal arrow color and alpha edit independently', close_color(data.guide_colors()[0], (.2, .3, .4, .25))
      and close_color(data.guide_colors()[1], data.GUIDE_ACTIVE))
colors.guide_active_zh = (.7, .6, .5, .4)
check('Chinese arrow color alias shares RGBA storage', close_color(colors.guide_active, (.7, .6, .5, .4)))
check('color tooltips are localized', 'opacity' in colors.bl_rna.properties['guide_idle'].description
      and '透明度' in colors.bl_rna.properties['guide_active_zh'].description)
bpy.ops.line_pipe.reset_guide_colors()
check('one action restores both factory colors and alpha', all(close_color(a, b) for a, b in
      zip(data.guide_colors(), (data.GUIDE_IDLE, data.GUIDE_ACTIVE))))
settings.follow_tip_zh = True
settings.show_guides_zh = False
check('Chinese interaction toggles share English storage', settings.follow_tip and not settings.show_guides)
settings.follow_tip, settings.show_guides = False, True
check('localized interaction tooltips', 'Ctrl+F' in settings.bl_rna.properties['follow_tip_zh'].description
      and '角度' in settings.bl_rna.properties['show_guides_zh'].description)
for key, axis in WORLD_AXES.items():
    check('signed bend label ' + key, operators.axis_label(axis) == key)
bpy.ops.line_pipe.language()
check('one action switches to Chinese', i18n.language() == 'ZH' and i18n.tr('draw') == '绘制管道')
check('Chinese color controls and restore tooltip', i18n.tr('guide_colors') == '箭头颜色'
      and '暖黄色' in operators.LP_OT_reset_guide_colors.description(bpy.context, None))
settings.diameter_zh = .3
check('Chinese dimension alias shares English storage', abs(settings.diameter - .3) < 1e-6)
settings.start_mode_zh = 'COORDINATES'
check('Chinese enum alias shares English storage', settings.start_mode == 'COORDINATES')
check('Chinese hover descriptions are localized', '外径' in settings.bl_rna.properties['diameter_zh'].description)
check('English hover descriptions remain English', 'Outside' in settings.bl_rna.properties['diameter'].description)
bpy.ops.line_pipe.language()
check('one action switches back to English', i18n.tr('draw') == 'Draw Pipe')

for name, view in [('front', Quaternion((1, 0, 0), 0)),
                   ('top', Quaternion((1, 0, 0), math.pi / 2)),
                   ('angled', Quaternion(Vector((1, 2, 3)).normalized(), .73)),
                   ('edge', Quaternion((1, 0, 0), math.radians(18)))]:
    inverse = view.inverted()
    directions = initial_directions(lambda axis: (inverse @ axis).xy)
    check(name + ' exposes six distinct initial guide rays', len({tuple(round(v, 4) for v in ray) for ray in directions.values()}) == 6)
    for key, ray in directions.items():
        check(name + key + ' mouse ray selects exact signed world axis', choose_initial_direction(ray * 100, directions) == key)
check('initial mouse deadzone does not force +X', choose_initial_direction((1, 1), directions) is None)

auto = Route((0, 0, 0), (1, 0, 0), .2, .4, axis_initial=True)
for key, axis in WORLD_AXES.items():
    auto.aim_initial(key, 2)
    check(key + ' can replace the first segment before turning', len(auto.points) == 1 and (auto.tip - axis * 2).length < 1e-6)
auto.begin_turn()
check('holding bend key freezes six-axis initial choice', not auto.choosing_initial)
incoming = auto.heading.copy()
auto.aim_initial('+X', 3)
check('six-axis aiming cannot rotate a bend preview', auto.heading == incoming)
auto.choose(auto.u)
auto.release_turn()
auto.aim_initial('+X', 3)
check('committed bend keeps later straight direction locked', not auto.choosing_initial and abs(auto.heading.dot(incoming)) < 1e-6)
auto.undo()
check('retracting first bend restores six-axis initial selection', auto.choosing_initial and auto.heading == incoming)
auto.aim_initial('-X', 2)
check('restored first segment can reverse direction', auto.heading == WORLD_AXES['-X'])

rotation = Quaternion(Vector((1, 2, 3)).normalized(), .73)
for name, heading in [('axis', Vector((1, 0, 0))), ('rotated', rotation @ Vector((1, 0, 0)))]:
    u, v = frame(heading)
    for key, candidate in [('u', u), ('-u', -u), ('v', v), ('-v', -v)]:
        route = Route((0, 0, 0), heading, .2, .4)
        route.extend(.1)
        check(name + key + ' short straight cannot turn', not route.begin_turn())
        route.extend(2)
        check(name + key + ' hold begins turn', route.begin_turn())
        route.choose(candidate)
        before = route.route_points()
        check(name + key + ' hold previews without committing', len(route.points) == 1 and len(before) == 3)
        route.release_turn()
        check(name + key + ' release commits exactly one bend', len(route.points) == 2 and route.heading.dot(candidate) > .9999)
        route.extend(2)
        obj = make(route.route_points(False))
        obj.name = name + key
        solid(obj, math.pi * .1 ** 2 * (4 - .8 + math.pi * .4 / 2))
        route.undo()
        check(name + key + ' undo restores straight length and frame', len(route.points) == 1 and abs(route.length - 2) < 1e-6 and route.heading.dot(heading) > .9999)
        geometry.remove(obj)

route = Route((0, 0, 0), (1, 0, 0), .2, .4)
route.extend(2)
route.begin_turn()
route.release_turn()
check('release without mouse intent adds no bend', len(route.points) == 1)
route.begin_turn()
route.choose((0, 1, 0))
route.undo()
check('undo during hold discards preview only', not route.turning and len(route.points) == 1)
for heading in [(0, 1, 0), (0, 0, 1), (-1, 0, 0), (0, -1, 0)]:
    route.extend(2)
    route.begin_turn()
    route.choose(heading)
    route.release_turn()
route.extend(2)
spatial = make(route.route_points(False))
spatial.name = 'Spatial multi-bend'
solid(spatial)
check('centerline is retained as editable curve', spatial.type == 'CURVE' and len(spatial.modifiers) == 1)
ports = json.loads(spatial['line_pipe_ports_v1'])
check('two endpoint metadata entries ready for later assembly', len(ports) == 2 and all(p['solid'] for p in ports))
old = solid(spatial)
spatial.line_pipe.diameter_zh = .3
new = solid(spatial)
check('diameter edit changes evaluated solid volume', abs(new[2] / old[2] - 2.25) < .03)
previous_radius = spatial.line_pipe.bend_radius
spatial.line_pipe.bend_radius = 10
check('maximum radius fits local bends without moving route corners', spatial.line_pipe.bend_radius == 10
      and spatial.line_pipe.error == '' and spatial.get('line_pipe_route_v1') is not None)
spatial.line_pipe.bend_radius = previous_radius
spatial.line_pipe.diameter = 2
check('impossible diameter rolls back', abs(spatial.line_pipe.diameter - .3) < 1e-6 and spatial.line_pipe.error == 'bad_radius')
spatial.line_pipe.bend_radius = .5
check('valid edit clears error', spatial.line_pipe.error == '')
solid(spatial)

for projected in [lambda v: v.xy, lambda v: Vector((0, 0)), lambda v: Vector((v.x + v.z, v.y))]:
    directions = turn_directions(Vector((1, 0, 0)), Vector((0, 0, 1)), projected)
    check('four directions accessible even edge-on', len({tuple(v) for v in directions.values()}) == 4)
check('mouse sectors cover all four directions', [choose_sector(v) for v in [(40, 0), (-40, 0), (0, 40), (0, -40)]] == ['RIGHT', 'LEFT', 'UP', 'DOWN'])
check('mouse deadzone suppresses accidental turns', choose_sector((3, 2)) is None)

bpy.context.view_layer.objects.active = bpy.data.objects['Cube']
bpy.context.object.scale = (2, 1, .5)
settings.face_index = 0
origin, normal = operators.selected_face(bpy.context, settings)
check('selected face supports transformed mesh normals', abs(normal.length - 1) < 1e-6)
settings.face_index = 999
try:
    operators.selected_face(bpy.context, settings)
    raise AssertionError('invalid face accepted')
except ValueError:
    check('invalid numeric face index rejected', True)

for obj in bpy.context.selected_objects:
    obj.select_set(False)
spatial.select_set(True)
bpy.context.view_layer.objects.active = spatial
before_mesh = solid(spatial)
bpy.ops.line_pipe.mesh()
check('native mesh conversion produces standalone solid', spatial.type == 'MESH' and not spatial.line_pipe.enabled)
after_mesh = solid(spatial)
check('mesh conversion preserves evaluated geometry', before_mesh == after_mesh)

addon.unregister()
check('unregister removes properties and lifecycle hooks', not hasattr(bpy.types.Scene, 'line_pipe_settings') and addon.before_scene_change not in bpy.app.handlers.save_pre)
addon.register()
check('re-register succeeds', hasattr(bpy.types.Scene, 'line_pipe_settings'))
(OUT / 'checks.json').write_text(json.dumps({'checks': checks, 'count': len(checks), 'blender': bpy.app.version_string}, indent=2), encoding='utf8')
print('TOTAL', len(checks), flush=True)
