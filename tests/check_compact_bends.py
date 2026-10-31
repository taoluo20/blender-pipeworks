"""Numerical and evaluated-solid regressions at compact circular-bend boundaries."""
import json
import math
import os
from pathlib import Path
import sys
import bmesh
import bpy
from mathutils import Quaternion, Vector
from mathutils.bvhtree import BVHTree

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'verification' / 'line-pipe'
for key in ('BLENDER_USER_CONFIG', 'BLENDER_USER_SCRIPTS', 'BLENDER_USER_EXTENSIONS'):
    assert Path(os.environ[key]).is_relative_to(OUT) and Path(os.environ[key]).is_dir()
assert Path(bpy.utils.user_resource('CONFIG')).is_relative_to(OUT)
sys.path.insert(0, str(ROOT))
import line_pipe
from line_pipe import data, geometry
from line_pipe.model import Route, bend_floor, fillet_radii, rounded_samples

line_pipe.register()
checks = []


def check(name, condition):
    assert condition, name
    checks.append(name)
    print('PASS COMPACT:', name, flush=True)


def rejected(name, points, diameter=.2, radius=.4):
    try:
        rounded_samples(points, radius, 16, diameter / 2)
    except ValueError:
        check(name, True)
    else:
        raise AssertionError(name)


def solid(name, points, diameter=.2, radius=.4, steps=16):
    points = [Vector(p) for p in points]
    radii = fillet_radii(points, radius, diameter / 2)
    samples = rounded_samples(points, radius, steps, diameter / 2)
    check(name + ' circular fillets retain positive inner radius', all(r > diameter / 2 for r in radii))
    check(name + ' sample positions and tangents are finite', all(
        math.isfinite(v) for position, tangent in samples for v in (*position, *tangent)))
    check(name + ' no duplicate adjacent samples', all(
        (a[0] - b[0]).length > diameter * 1e-7 for a, b in zip(samples, samples[1:])))
    obj = geometry.create(bpy.context)
    for key, value in zip(data.DIMENSIONS, (diameter, radius, 32, steps)):
        setattr(obj.line_pipe, key, value)
    geometry.update(obj, points, diameter, radius, 32, steps, store=True)
    obj['_line_pipe_dimensions'] = [diameter, radius, 32, steps]
    bpy.context.view_layer.update()
    evaluated = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
    mesh = evaluated.to_mesh()
    bm = bmesh.new()
    bm.from_mesh(mesh)
    check(name + ' closed oriented manifold', bool(bm.faces) and all(
        e.is_manifold and e.is_contiguous for e in bm.edges))
    check(name + ' no zero-area faces', all(f.calc_area() > diameter ** 2 * 1e-12 for f in bm.faces))
    mesh.calc_loop_triangles()
    triangles = [tuple(t.vertices) for t in mesh.loop_triangles]
    tree = BVHTree.FromPolygons([v.co for v in mesh.vertices], triangles, all_triangles=True)
    overlaps = [(a, b) for a, b in tree.overlap(tree) if a < b
                and not set(triangles[a]).intersection(triangles[b])]
    if overlaps:
        (OUT / 'compact-overlaps.json').write_text(json.dumps(dict(name=name, pairs=[
            [[list(mesh.vertices[i].co) for i in triangles[t]] for t in pair]
            for pair in overlaps[:10]]), indent=2))
    check(name + ' no nonadjacent surface intersections', not overlaps)
    caps = [p for p in mesh.polygons if len(p.vertices) > 4]
    check(name + ' exactly two flat caps', len(caps) == 2 and all(not p.use_smooth for p in caps))
    for label, endpoint, normal in (
            ('start', points[0], (points[0] - points[1]).normalized()),
            ('end', points[-1], (points[-1] - points[-2]).normalized())):
        cap = min(caps, key=lambda p: (p.center + obj.location - endpoint).length)
        center = cap.center + obj.location
        check(name + ' ' + label + ' cap at route endpoint', (center - endpoint).length < diameter * 1e-4)
        check(name + ' ' + label + ' cap perpendicular to heading', cap.normal.dot(normal) > .99999)
        check(name + ' ' + label + ' circular diameter retained', all(
            abs((mesh.vertices[i].co + obj.location - endpoint).length - diameter / 2) < diameter * 1e-4
            for i in cap.vertices))
    expected_length = sum((b - a).length for a, b in zip(points, points[1:])) + (math.pi / 2 - 2) * sum(radii)
    volume = bm.calc_volume(signed=True)
    check(name + ' positive volume matches solid circular sweep', volume > 0 and
          abs(volume / (math.pi * (diameter / 2) ** 2 * expected_length) - 1) < .04)
    bm.free()
    evaluated.to_mesh_clear()
    return obj, radii


for length in (.10001, .12, .4, .401):
    obj, radii = solid('single ' + str(length), [(0, 0, 0), (length, 0, 0), (length, 0, length)])
    check('single fitted radius ' + str(length), abs(radii[0] - min(length, .4)) < 1e-6)
    geometry.remove(obj)
for length in (.09999, .1):
    rejected('single rejects zero or negative inner radius ' + str(length),
             [(0, 0, 0), (length, 0, 0), (length, 0, length)])
for length in (.19999, .2):
    rejected('shared segment cannot hold two positive-inner fillets ' + str(length),
             [(0, 0, 0), (.3, 0, 0), (.3, length, 0), (.6, length, 0)])
obj, _ = solid('large maximum small bend', [(0, 0, 0), (.10001, 0, 0), (.10001, 0, .10001)], radius=1000)
geometry.remove(obj)
obj, _ = solid('translated compact bend', [(10, -20, 8), (10.10001, -20, 8), (10.10001, -20, 8.10001)])
geometry.remove(obj)

rotation = Quaternion(Vector((1, 2, 3)).normalized(), .73)
for label, last in [('S', (.6, .20002, 0)), ('U', (0, .20002, 0)), ('spatial', (.3, .20002, .3))]:
    base = [Vector(p) for p in [(0, 0, 0), (.3, 0, 0), (.3, .20002, 0), last]]
    for direction in (1, -1):
        for rotated in (False, True):
            points = [rotation @ (p * direction) if rotated else p * direction for p in base]
            obj, radii = solid(label + str(direction) + (' rotated' if rotated else ''), points)
            check(label + ' shared radii fit actual segment', sum(radii) <= .200021)
            geometry.remove(obj)

obj, _ = solid('scale .001', [(0, 0, 0), (.00012, 0, 0), (.00012, 0, .00012)], .0002, .0004)
geometry.remove(obj)
obj, _ = solid('low bend resolution', [(0, 0, 0), (.10001, 0, 0), (.10001, 0, .10001)], steps=4)
recipe = obj['line_pipe_route_v1']
before = [tuple(p.co) for p in obj.data.splines[0].bezier_points]
obj.line_pipe.diameter_zh = .21
check('compact diameter edit rolls back before invalidating the solid', abs(obj.line_pipe.diameter - .2) < 1e-6
      and obj.line_pipe.error == 'fit' and obj['line_pipe_route_v1'] == recipe
      and before == [tuple(p.co) for p in obj.data.splines[0].bezier_points])
obj.line_pipe.bend_radius = .3
check('valid maximum-radius edit clears error without moving route', obj.line_pipe.error == ''
      and obj['line_pipe_route_v1'] == recipe)
saved = OUT / 'compact-roundtrip.blend'
bpy.ops.wm.save_as_mainfile(filepath=str(saved))
bpy.ops.wm.open_mainfile(filepath=str(saved))
obj = next(o for o in bpy.context.scene.objects if o.get('line_pipe_route_v1') == recipe)
check('compact saved recipe and maximum survive reload', abs(obj.line_pipe.bend_radius - .3) < 1e-6)
geometry.rebuild(obj)
check('compact rebuild preserves sampled shape', before == [tuple(p.co) for p in obj.data.splines[0].bezier_points])
legacy = obj.modifiers[0].node_group.copy()
del legacy[geometry.TANGENT_KEY]
obj.modifiers[0].node_group = legacy
geometry.rebuild(obj)
check('legacy sweep marker upgrades on recipe rebuild', obj.modifiers[0].node_group.get(geometry.TANGENT_KEY)
      and obj.modifiers[0].node_group != legacy and not legacy.get(geometry.TANGENT_KEY)
      and obj['line_pipe_route_v1'] == recipe)
geometry.remove(obj)

route = Route((0, 0, 0), (1, 0, 0), .2, .4)
route.extend(.1)
check('modal refuses exact single-bend singularity', not route.begin_turn())
route.extend(bend_floor(.2))
check('modal allows single bend at numeric guard above pipe radius', route.begin_turn())
route.choose((0, 0, 1))
preview = route.route_points()
route.release_turn()
check('single release retains exact preview geometry', preview == route.route_points(False))
route.extend(.2)
check('modal refuses exact shared-bend singularity', not route.begin_turn())
route.extend(route.turn_minimum)
check('modal permits compact shared bend far below twice maximum', route.begin_turn() and route.length < .201)
route.choose((0, 1, 0))
preview = route.route_points()
obj, _ = solid('modal shared guard', preview)
geometry.remove(obj)
route.release_turn()
check('shared release retains exact preview geometry', preview == route.route_points(False))
route.undo()
check('compact undo restores incoming segment and direction', len(route.points) == 2
      and route.heading.z > .999 and abs(route.length - route.turn_minimum) < 1e-6)

(OUT / 'compact-checks.json').write_text(json.dumps(dict(checks=checks, count=len(checks),
    blender=bpy.app.version_string), indent=2), encoding='utf8')
print('COMPACT TOTAL', len(checks), flush=True)
