# SPDX-License-Identifier: GPL-3.0-or-later
"""Connection profile, authored edge and library round-trip regressions."""
import json
from pathlib import Path
import sys

import bmesh
import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import line_pipe as addon
from line_pipe import connections, connection_geometry, data, fittings, geometry, port_rings, ports

addon.register()
context = bpy.context
scene = context.scene
settings = scene.line_pipe_settings


def reset():
    scene.line_pipe_connections.links.clear()
    for obj in list(scene.objects):
        bpy.data.objects.remove(obj, do_unlink=True)


def curve(name, sides, offset=0):
    obj = geometry.create(context)
    obj.name = name
    obj.line_pipe.radial_segments = sides
    geometry.update(obj, [(offset, 0, 0), (offset + 1, 0, 0)], .2, .4, sides, 16, store=True)
    obj['_line_pipe_dimensions'] = [.2, .4, sides, 16]
    context.view_layer.update()
    return obj


def endpoint(obj, key='END'):
    context.view_layer.update()
    return ports.read(scene, obj, key, free=False)


def expect_error(key, operation):
    try:
        operation()
    except ports.ConnectionError as error:
        assert str(error) == key, (str(error), key)
        return error
    raise AssertionError(f'{key} was expected')


reset()
assert settings.radial_segments == 60 and not settings.free_sides and not settings.hollow
for count in (*ports.STANDARD_SIDES, 601):
    obj = curve(str(count), count)
    assert endpoint(obj).sides == count, count
    geometry.remove(obj)
settings.radial_segments = 37
assert data.generation_sides(settings) == 60
settings.free_sides = True
assert data.generation_sides(settings) == 37
print('All standard rings and free resolution measured from actual curve geometry', flush=True)

reset()
reference = curve('First reference', 60, 3)
moving = curve('Second moving', 24)
reference_data = reference.data
reference_matrix = reference.matrix_world.copy()
connections.direct_plan(scene, moving, 'END', reference, 'START', .33)
assert endpoint(moving).sides == 24
link = connections.direct(context, moving, 'END', reference, 'START', .33)
a, b = endpoint(moving), endpoint(reference, 'START')
assert a.sides == b.sides == link.sides == 60
assert (a.position - b.position).length < 1e-5 and a.direction.dot(b.direction) < -.9999
assert abs(port_rings.phase_offset(b.radial, a.radial, b.direction, 60)) < 1e-4
assert reference.data == reference_data and reference.matrix_world == reference_matrix
other = curve('Other reference', 24, 6)
expect_error('profile_in_use', lambda: connections.direct(context, moving, 'START', other, 'END'))
assert endpoint(moving).sides == 60 and len(scene.line_pipe_connections.links) == 1

reset()
reference = curve('Reference', 60, 3)
moving = curve('Moving', 24)
reference.rotation_euler.x = .31
context.view_layer.update()
expect_error('connection_range', lambda: connections.bridge(context, moving, 'END', reference, 'START', max_distance=.01))
assert endpoint(moving).sides == 24 and not len(scene.line_pipe_connections.links)
before = moving.matrix_world.copy(), reference.matrix_world.copy()
bridge = connections.bridge(context, moving, 'END', reference, 'START')
assert (moving.matrix_world, reference.matrix_world) == before
for obj, key, connector_key in ((moving, 'END', 'START'), (reference, 'START', 'END')):
    a, b = endpoint(obj, key), endpoint(bridge, connector_key)
    assert a.sides == b.sides == 60 and (a.position - b.position).length < 1e-5
    assert abs(port_rings.phase_offset(a.radial, b.radial, a.direction, 60)) < 1e-4
print('Direct and distance match the first port, including real vertex phase and failure rollback', flush=True)

reset()
a, b = curve('37', 37), curve('24', 24, 2)
error = expect_error('side_mismatch', lambda: connections.direct(context, a, 'END', b, 'START'))
assert error.details == {'moving': 37, 'anchor': 24}
b.line_pipe.radial_segments = 37
connections.direct(context, a, 'END', b, 'START')
assert endpoint(a).sides == endpoint(b, 'START').sides == 37

reset()
settings.free_sides = False
settings.radial_segments = 24
hollow = fittings.create_fitting(context, 'CYLINDER')
assert endpoint(hollow).sides == 24 and not endpoint(hollow).bore
hollow.line_pipe.hollow = True
assert abs(endpoint(hollow).bore - .16) < 1e-6
hollow.line_pipe.wall_mode = 'PRESET'
hollow.line_pipe.wall_preset = '5'
assert abs(endpoint(hollow).bore - .18) < 1e-6
report = connection_geometry.topology(hollow.data)
assert report['volume'] > 0 and not report['nonmanifold']
# The inner wall and the annular rims leave the axis clear.
assert not hollow.ray_cast(Vector((0, 0, -1)), Vector((0, 0, 1)))[0]
assert fittings.mark_ports(context) == 2
assert abs(endpoint(hollow).bore - .18) < 1e-6
reference = curve('60 anchor', 60, 4)
expect_error('fixed_side_mismatch', lambda: connections.direct(context, hollow, 'END', reference, 'START'))
assert endpoint(hollow).sides == 24
print('Hollow rims, presets, and read-only custom meshes validated', flush=True)

reset()
vertices, faces = [], []
for index, count in enumerate((24, 60, 37, 6, 48)):
    recipe = dict(kind='ORTHOGONAL', points=[(0, index, 0), (0, index, 1)], radius=.4,
                  diameter=.2, bore=0, sides=count, steps=16, smooth=True)
    verts, polys, _ = connection_geometry.sweep(recipe)
    base = len(vertices)
    vertices.extend(verts)
    faces.extend(tuple(i + base for i in face) for face in polys)
mesh = bpy.data.meshes.new('Ten mouth geometry')
mesh.from_pydata(vertices, [], faces)
obj = bpy.data.objects.new('Ten mouth fitting', mesh)
context.collection.objects.link(obj)
fittings.select_object(context, obj)
context.view_layer.update()
bpy.ops.object.mode_set(mode='EDIT')
bpy.ops.mesh.select_mode(type='EDGE')
bpy.ops.mesh.select_all(action='DESELECT')
bm = bmesh.from_edit_mesh(mesh)
for edge in bm.edges:
    if all(abs(v.co.y) < .15 and abs(v.co.z) < 1e-6 for v in edge.verts):
        edge.select_set(True)
assert bpy.ops.line_pipe.mark_ports(selected=True) == {'FINISHED'}
bpy.ops.object.mode_set(mode='OBJECT')
assert len(ports.local_ports(obj)) == 1
key = ports.local_ports(obj)[0]['key']
assert endpoint(obj, key).sides == 24
assert bpy.ops.line_pipe.toggle_port(key=key) == {'FINISHED'}
assert fittings.mark_ports(context) == 10
assert len(ports.local_ports(obj)) == 10
assert not next(p for p in ports.local_ports(obj) if p['key'] == key)['enabled']
expect_error('disabled_port', lambda: endpoint(obj, key))
for port in ports.local_ports(obj):
    if port['enabled']:
        assert endpoint(obj, port['key']).sides == port['sides']
identifier = fittings.add_to_library(context, obj)
metadata_path = fittings.library_dir() / (identifier + '.json')
metadata = json.loads(metadata_path.read_text(encoding='utf8'))
assert {p['sides'] for p in metadata['ports']} == {6, 24, 37, 48, 60}
assert len(metadata['ports']) == 9
asset_path = metadata_path.with_suffix('.blend')
with fittings.loaded_asset(asset_path) as copy:
    assert len(ports.local_ports(copy)) == 10 and not copy.get(ports.GROUP)
    assert copy.data.attributes.get(port_rings.TAG)
library_count = len(list(fittings.library_dir().glob('*.json')))
object_count = len(scene.objects)
assert bpy.ops.line_pipe.import_fitting(filepath=str(asset_path)) == {'FINISHED'}
assert len(list(fittings.library_dir().glob('*.json'))) == library_count + 1
assert len(scene.objects) == object_count
assert bpy.ops.line_pipe.insert_fitting(identifier=identifier) == {'FINISHED'}
inserted = context.active_object
assert inserted != obj and len(fittings.asset_info(context, inserted)['ports']) == 9
print('Ten manual and automatic ports, toggle persistence, asset export and library insert passed', flush=True)

expect_error('continuation_fixed', lambda: fittings.fitted_continuation(context, identifier, .3, 0, 60))
reset()
settings.hollow = False
settings.diameter = .2
settings.radial_segments = 24
settings.template_length = 1.25
template = fittings.create_fitting(context, 'CYLINDER')
assert geometry.editable_route(template)
identifier = fittings.add_to_library(context, template)
assert bpy.ops.line_pipe.insert_fitting(identifier=identifier) == {'FINISHED'}
instance = context.active_object
instance.line_pipe.route_length = 3
instance.line_pipe.diameter = .3
assert abs(instance.line_pipe.route_length - 3) < 1e-6
assert abs(endpoint(instance).diameter - .3) < 1e-6
assert abs(template.line_pipe.route_length - 1.25) < 1e-6

before = set(scene.objects)
error = expect_error('continuation_variant_missing',
                     lambda: fittings.fitted_continuation(context, identifier, .42, .31, 37))
assert error.details == {'count': 37, 'counts': '24'} and set(scene.objects) == before
settings.free_sides = True
settings.radial_segments = 37
variant = fittings.create_fitting(context, 'CYLINDER')
variant_id = fittings.add_to_library(context, variant, identifier)
expect_error('variant_duplicate', lambda: fittings.add_to_library(context, variant, identifier))
assert set(fittings.library_families()[identifier][1]) == {identifier, variant_id}
adapted = fittings.fitted_continuation(context, identifier, .42, .31, 37)
end = endpoint(adapted)
assert end.sides == 37 and abs(end.diameter - .42) < 1e-6 and abs(end.bore - .31) < 1e-6
assert abs(adapted.line_pipe.route_length - 2.625) < 1e-6
anchor = fittings.fitted_continuation(context, 'CYLINDER', .42, .31, 37)
anchor.location.x = 3
context.view_layer.update()
connections.direct(context, adapted, 'END', anchor, 'START')
fixed = endpoint(adapted).position.copy()
adapted.line_pipe.route_length = 4
assert abs(adapted.line_pipe.route_length - 4) < 1e-6
assert (endpoint(adapted).position - fixed).length < 1e-6
mate = fittings.fitted_continuation(context, 'CYLINDER', .42, .31, 37)
connections.direct(context, mate, 'END', adapted, 'START')
adapted.line_pipe.route_length = 5
assert adapted.line_pipe.error == 'length_both_ports'
assert abs(adapted.line_pipe.route_length - 4) < 1e-6

editable_curve = curve('Procedural Curve', 60)
assert geometry.editable_route(editable_curve)
editable_curve.line_pipe.route_length = 2
assert abs(editable_curve.line_pipe.route_length - 2) < 1e-6
print('Editable library instances, inherited hollow profiles and linked-end length changes passed', flush=True)

# Authored meshes keep their real rings and arbitrary port keys during continuation.
reset()
settings.free_sides = False
settings.radial_segments = 24
settings.hollow = True
settings.wall = .02
generated = fittings.create_fitting(context, 'ELBOW')
authored = bpy.data.objects.new('Authored hollow elbow', generated.data.copy())
context.collection.objects.link(authored)
geometry.remove(generated)
fittings.select_object(context, authored)
assert fittings.mark_ports(context) == 2
authored_id = fittings.add_to_library(context, authored)
reference = curve('60 reference', 60, 4)
assert bpy.ops.line_pipe.insert_fitting(identifier=authored_id) == {'FINISHED'}
inserted = context.active_object
inlet, outlet = fittings.continuation_keys(inserted)
before = inserted.matrix_world.copy(), inserted.data, len(scene.line_pipe_connections.links)
expect_error('library_side_mismatch',
             lambda: connections.direct(context, inserted, inlet, reference, 'START'))
assert (inserted.matrix_world, inserted.data, len(scene.line_pipe_connections.links)) == before
adapted = fittings.fitted_continuation(context, authored_id, .4, .32, 24)
assert not geometry.editable_route(adapted)
inlet, outlet = fittings.continuation_keys(adapted)
assert abs(endpoint(adapted, inlet).diameter - .4) < 1e-6
assert abs(endpoint(adapted, outlet).bore - .32) < 1e-6
expect_error('continuation_profile',
             lambda: fittings.fitted_continuation(context, authored_id, .4, 0, 24))
print('Library variants, missing-size rollback and authored-mesh continuation passed', flush=True)

out = ROOT / 'verification' / 'line-pipe' / 'profiles.json'
out.write_text(json.dumps(dict(presets=list(ports.STANDARD_SIDES), free_count=601,
                               authored_ports=10, exposed_library_ports=9, saved_hollow=True)), encoding='utf8')
