# SPDX-License-Identifier: GPL-3.0-or-later
"""Editable centerline plus Blender's native solid Curve to Mesh sweep."""
from array import array
import hashlib
import json
import bpy
from mathutils import Vector
from .model import rounded_samples

GROUP_KEY = 'line_pipe_solid_sweep_v1'
TANGENT_KEY = 'line_pipe_exact_tangents_v1'
PROFILE_KEY = '_pipeworks_profile_resolution_v1'
MESH_SIGNATURE = '_pipeworks_generated_mesh_v1'
SWEEP_FRAMES = '_pipeworks_sweep_frames_v1'


def sweep_group():
    for group in bpy.data.node_groups:
        if group.get(GROUP_KEY) and group.get(TANGENT_KEY) and group.get(PROFILE_KEY):
            return group
    group = bpy.data.node_groups.new('PipeWorks - Solid Sweep', 'GeometryNodeTree')
    group[GROUP_KEY] = True
    group[TANGENT_KEY] = True
    group[PROFILE_KEY] = True
    group.interface.new_socket(name='Geometry', in_out='INPUT', socket_type='NodeSocketGeometry')
    group.interface.new_socket(name='Geometry', in_out='OUTPUT', socket_type='NodeSocketGeometry')
    radius = group.interface.new_socket(name='Radius', in_out='INPUT', socket_type='NodeSocketFloat')
    radius.default_value, radius.min_value = .1, .000001
    sides = group.interface.new_socket(name='Sides', in_out='INPUT', socket_type='NodeSocketInt')
    from .ports import DEFAULT_SIDES, MAX_SIDES
    sides.default_value, sides.min_value, sides.max_value = DEFAULT_SIDES, 3, MAX_SIDES
    source = group.nodes.new('NodeGroupInput')
    source.location = (-900, 300)
    position = group.nodes.new('GeometryNodeInputPosition')
    position.location = (-1100, 0)
    tangent = group.nodes.new('GeometryNodeInputTangent')
    tangent.location = (-1100, -180)
    handles = group.nodes.new('GeometryNodeInputCurveHandlePositions')
    handles.location = (-1100, -360)

    def vector(operation, a, b=None, location=(0, 0)):
        node = group.nodes.new('ShaderNodeVectorMath')
        node.operation, node.location = operation, location
        group.links.new(a, node.inputs[0])
        if b is not None:
            group.links.new(b, node.inputs[1])
        return node.outputs['Value' if operation in {'LENGTH', 'DOT_PRODUCT'} else 'Vector']

    exact = vector('NORMALIZE', vector('SUBTRACT', handles.outputs['Right'], handles.outputs['Left'],
                                     (-850, -360)), location=(-650, -360))
    capture = group.nodes.new('GeometryNodeCaptureAttribute')
    capture.location = (-400, 300)
    capture.domain = 'POINT'
    for name, field in [('Center', position.outputs['Position']), ('Tangent', tangent.outputs['Tangent']),
                        ('Exact', exact)]:
        capture.capture_items.new('VECTOR', name)
        group.links.new(field, capture.inputs[name])
    group.links.new(source.outputs['Geometry'], capture.inputs['Geometry'])
    profile = group.nodes.new('GeometryNodeCurvePrimitiveCircle')
    profile.location = (-400, 600)
    sweep = group.nodes.new('GeometryNodeCurveToMesh')
    sweep.location = (-150, 300)
    sweep.inputs['Fill Caps'].default_value = True
    output = group.nodes.new('NodeGroupOutput')
    output.location = (1400, 300)
    group.links.new(capture.outputs['Geometry'], sweep.inputs['Curve'])
    group.links.new(source.outputs['Radius'], profile.inputs['Radius'])
    group.links.new(source.outputs['Sides'], profile.inputs['Resolution'])
    group.links.new(profile.outputs['Curve'], sweep.inputs['Profile Curve'])
    # Curve to Mesh estimates knot tangents from neighboring samples. Rotate
    # each swept ring onto its analytic tangent to avoid overlaps at short tails.
    axis = vector('CROSS_PRODUCT', capture.outputs['Tangent'], capture.outputs['Exact'], (50, -100))
    sine = vector('LENGTH', axis, location=(250, -100))
    cosine = vector('DOT_PRODUCT', capture.outputs['Tangent'], capture.outputs['Exact'], (250, -280))
    angle = group.nodes.new('ShaderNodeMath')
    angle.operation, angle.location = 'ARCTAN2', (450, -100)
    group.links.new(sine, angle.inputs[0])
    group.links.new(cosine, angle.inputs[1])
    offset = vector('SUBTRACT', position.outputs['Position'], capture.outputs['Center'], (450, 100))
    rotate = group.nodes.new('ShaderNodeVectorRotate')
    rotate.rotation_type, rotate.location = 'AXIS_ANGLE', (650, 100)
    group.links.new(offset, rotate.inputs['Vector'])
    group.links.new(axis, rotate.inputs['Axis'])
    group.links.new(angle.outputs[0], rotate.inputs['Angle'])
    corrected = vector('ADD', capture.outputs['Center'], rotate.outputs['Vector'], (900, 100))
    set_position = group.nodes.new('GeometryNodeSetPosition')
    set_position.location = (1150, 300)
    group.links.new(sweep.outputs['Mesh'], set_position.inputs['Geometry'])
    group.links.new(corrected, set_position.inputs['Position'])
    group.links.new(set_position.outputs['Geometry'], output.inputs['Geometry'])
    return group


def mesh_signature(mesh):
    digest = hashlib.sha256()
    for collection, field, kind, length in (
            (mesh.vertices, 'co', 'f', len(mesh.vertices) * 3),
            (mesh.edges, 'vertices', 'i', len(mesh.edges) * 2),
            (mesh.loops, 'vertex_index', 'i', len(mesh.loops)),
            (mesh.polygons, 'loop_total', 'i', len(mesh.polygons))):
        values = array(kind, [0]) * length
        collection.foreach_get(field, values)
        digest.update(length.to_bytes(8, 'little'))
        digest.update(values.tobytes())
    return digest.hexdigest()


def remember_mesh(obj):
    obj[MESH_SIGNATURE] = mesh_signature(obj.data)


def generated_mesh_intact(obj, require_signature=False):
    if obj.type != 'MESH':
        return True
    signature = obj.get(MESH_SIGNATURE)
    return (not require_signature if signature is None else signature == mesh_signature(obj.data))


def curve_knots(sampled):
    for index, (position, tangent) in enumerate(sampled):
        left = (position - sampled[max(0, index - 1)][0]).length / 3
        right = (sampled[min(len(sampled) - 1, index + 1)][0] - position).length / 3
        yield position, position - tangent * (left or right), position + tangent * (right or left)


def editable_route(obj):
    from . import ports
    if not obj or not obj.get('line_pipe_route_v1') or obj.get(ports.CUSTOM):
        return False
    active_modifiers = [mod for mod in obj.modifiers if mod.show_viewport]
    if obj.type == 'MESH':
        return (not active_modifiers and not obj.data.shape_keys
                and generated_mesh_intact(obj, require_signature=True))
    if (obj.type != 'CURVE' or len(active_modifiers) != 1 or active_modifiers[0].type != 'NODES'
            or not active_modifiers[0].node_group or not active_modifiers[0].node_group.get(GROUP_KEY)
            or len(obj.data.splines) != 1):
        return False
    spline = obj.data.splines[0]
    if spline.type != 'BEZIER' or spline.use_cyclic_u or spline.resolution_u != 1:
        return False
    settings = obj.line_pipe
    points = [Vector(p) for p in json.loads(obj['line_pipe_route_v1'])]
    sampled = rounded_samples(points, settings.bend_radius, settings.bend_steps, settings.diameter / 2)
    return (len(spline.bezier_points) == len(sampled)
            and all(abs(knot.tilt) < 1e-6 and abs(knot.radius - 1) < 1e-6
                    and all((getattr(knot, name) - value).length < 1e-6
                            for name, value in zip(('co', 'handle_left', 'handle_right'), values))
                    for knot, values in zip(spline.bezier_points, curve_knots(sampled))))


def centerline_length(points):
    return sum((b - a).length for a, b in zip(points, points[1:]))


def route_length(obj):
    return centerline_length([Vector(p) for p in json.loads(obj.get('line_pipe_route_v1', '[]'))])


def resize_route(obj, scene, length):
    from . import connections, ports
    if not editable_route(obj):
        raise ports.ConnectionError('edited_recipe')
    ports.editable([obj])
    start_used = ports.occupied(scene, obj, 'START')
    end_used = ports.occupied(scene, obj, 'END')
    if start_used and end_used:
        raise ports.ConnectionError('length_both_ports')
    recipe = connections.recipe_for(obj)
    points = [Vector(p) for p in recipe['points']]
    scale = length / centerline_length(points)
    pivot = points[-1] if end_used else points[0]
    points = [pivot + (p - pivot) * scale for p in points]
    recipe['points'] = [list(p) for p in points]
    block = connections.stage_recipe(obj, recipe)
    connections.discard(connections.swap_data(obj, block))
    store_route(obj, points, recipe['diameter'], recipe['sides'], recipe['bore'])
    if obj.type == 'MESH':
        remember_mesh(obj)
    obj.update_tag()


def require_free_profile(obj, scene):
    from . import ports
    if any(p.get('occupied') or ports.occupied(scene, obj, p['key']) for p in ports.local_ports(obj)):
        raise ports.ConnectionError('profile_in_use')


def create(context, mesh=False):
    if mesh:
        obj = bpy.data.objects.new('PipeWorks', bpy.data.meshes.new('PipeWorks Pipe'))
        context.collection.objects.link(obj)
        obj.line_pipe.enabled = True
        return obj
    curve = bpy.data.curves.new('PipeWorks Centerline', 'CURVE')
    curve.dimensions = '3D'
    curve.twist_mode = 'MINIMUM'
    obj = bpy.data.objects.new('PipeWorks', curve)
    context.collection.objects.link(obj)
    modifier = obj.modifiers.new('Solid Pipe', 'NODES')
    modifier.node_group = sweep_group()
    obj.line_pipe.enabled = True
    return obj


def update(obj, points, diameter, radius, sides, steps, store=False, bore=0):
    points = [Vector(p) for p in points]
    # Keep coordinates local to the initial point for precision in large scenes.
    if store:
        obj.location = points[0]
    origin = obj.location.copy()
    local = [p - origin for p in points]
    if obj.type == 'MESH':
        from . import connection_geometry as cg, connections
        recipe = dict(kind='ORTHOGONAL', points=[list(p) for p in local], diameter=diameter,
                      bore=bore, radius=radius, sides=sides, steps=steps, smooth=True)
        recipe.update(json.loads(obj.get(SWEEP_FRAMES, '{}')))
        if store:
            old = connections.swap_data(obj, cg.mesh_from_recipe(recipe))
            connections.discard(old)
            remember_mesh(obj)
        else:
            obj.data.clear_geometry()
            if (local[-1] - local[0]).length > 1e-7 or len(local) > 2:
                vertices, faces, smooth = cg.sweep(recipe)
                obj.data.from_pydata(vertices, [], faces)
                obj.data.polygons.foreach_set('use_smooth', smooth)
                obj.data.update()
    else:
        update_curve(obj, local, diameter, radius, sides, steps)
    if store:
        store_route(obj, local, diameter, sides, bore)
    obj.update_tag()


def update_curve(obj, local, diameter, radius, sides, steps):
    sampled = rounded_samples(local, radius, steps, diameter / 2)
    curve = obj.data
    curve.splines.clear()
    if len(sampled) >= 2 and sum((b[0] - a[0]).length for a, b in zip(sampled, sampled[1:])) > 1e-7:
        # Explicit Bezier derivatives keep end caps perpendicular even when a
        # circular fillet consumes the entire straight. Evaluate at sample knots.
        spline = curve.splines.new('BEZIER')
        spline.resolution_u = 1
        spline.bezier_points.add(len(sampled) - 1)
        spline.use_smooth = True
        for point, (position, left, right) in zip(spline.bezier_points, curve_knots(sampled)):
            point.handle_left_type = point.handle_right_type = 'FREE'
            point.co = position
            point.handle_left = left
            point.handle_right = right
    set_sweep_profile(obj, diameter, sides)


def set_sweep_profile(obj, diameter, sides):
    modifier = next(m for m in obj.modifiers if m.type == 'NODES' and m.node_group and m.node_group.get(GROUP_KEY))
    if not modifier.node_group.get(TANGENT_KEY) or not modifier.node_group.get(PROFILE_KEY):
        modifier.node_group = sweep_group()
    for socket in modifier.node_group.interface.items_tree:
        if socket.item_type == 'SOCKET' and socket.in_out == 'INPUT':
            if socket.name == 'Radius':
                getattr(modifier.properties.inputs, socket.identifier).value = diameter / 2
            elif socket.name == 'Sides':
                getattr(modifier.properties.inputs, socket.identifier).value = sides


def store_route(obj, points, diameter, sides, bore):
    from . import ports
    obj['line_pipe_route_v1'] = json.dumps([list(p) for p in points])
    obj['line_pipe_ports_v1'] = json.dumps([
        dict(key=key, position=list(position), direction=list(direction.normalized()),
             diameter=diameter, bore=bore, sides=sides, solid=not bore)
        for key, position, direction in (('START', points[0], points[0] - points[1]),
                                          ('END', points[-1], points[-1] - points[-2]))])
    ports.ensure_identity(obj)


def rebuild(obj):
    if not obj or obj.type not in {'CURVE', 'MESH'} or not obj.get('line_pipe_route_v1'):
        return
    if obj.type == 'MESH':
        from . import connections
        connections.rebuild_mesh(obj)
        return
    state = obj.line_pipe
    points = [Vector(p) for p in json.loads(obj['line_pipe_route_v1'])]
    update_curve(obj, points, state.diameter, state.bend_radius, state.radial_segments, state.bend_steps)
    store_route(obj, points, state.diameter, state.radial_segments, 0)
    obj.update_tag()


def remove(obj):
    if obj and obj.name in bpy.data.objects:
        data = obj.data
        bpy.data.objects.remove(obj, do_unlink=True)
        if data.users == 0:
            (bpy.data.meshes if isinstance(data, bpy.types.Mesh) else bpy.data.curves).remove(data)
    for group in tuple(bpy.data.node_groups):
        if group.get(GROUP_KEY) and group.users == 0:
            bpy.data.node_groups.remove(group)
