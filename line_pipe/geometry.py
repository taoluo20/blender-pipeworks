# SPDX-License-Identifier: GPL-3.0-or-later
"""Editable centerline plus Blender's native solid Curve to Mesh sweep."""
import json
import bpy
from mathutils import Vector
from .model import rounded_samples

GROUP_KEY = 'line_pipe_solid_sweep_v1'
TANGENT_KEY = 'line_pipe_exact_tangents_v1'


def sweep_group():
    for group in bpy.data.node_groups:
        if group.get(GROUP_KEY) and group.get(TANGENT_KEY):
            return group
    group = bpy.data.node_groups.new('PipeWorks - Solid Sweep', 'GeometryNodeTree')
    group[GROUP_KEY] = True
    group[TANGENT_KEY] = True
    group.interface.new_socket(name='Geometry', in_out='INPUT', socket_type='NodeSocketGeometry')
    group.interface.new_socket(name='Geometry', in_out='OUTPUT', socket_type='NodeSocketGeometry')
    radius = group.interface.new_socket(name='Radius', in_out='INPUT', socket_type='NodeSocketFloat')
    radius.default_value, radius.min_value = .1, .000001
    sides = group.interface.new_socket(name='Sides', in_out='INPUT', socket_type='NodeSocketInt')
    sides.default_value, sides.min_value, sides.max_value = 32, 8, 128
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


def create(context):
    curve = bpy.data.curves.new('PipeWorks Centerline', 'CURVE')
    curve.dimensions = '3D'
    curve.twist_mode = 'MINIMUM'
    obj = bpy.data.objects.new('PipeWorks', curve)
    context.collection.objects.link(obj)
    modifier = obj.modifiers.new('Solid Pipe', 'NODES')
    modifier.node_group = sweep_group()
    obj.line_pipe.enabled = True
    return obj


def update(obj, points, diameter, radius, sides, steps, store=False):
    points = [Vector(p) for p in points]
    # Keep coordinates local to the initial point for precision in large scenes.
    if store:
        obj.location = points[0]
    origin = obj.location.copy()
    sampled = rounded_samples([p - origin for p in points], radius, steps, diameter / 2)
    curve = obj.data
    curve.splines.clear()
    if len(sampled) >= 2 and sum((b[0] - a[0]).length for a, b in zip(sampled, sampled[1:])) > 1e-7:
        # Explicit Bezier derivatives keep end caps perpendicular even when a
        # circular fillet consumes the entire straight. Evaluate at sample knots.
        spline = curve.splines.new('BEZIER')
        spline.resolution_u = 1
        spline.bezier_points.add(len(sampled) - 1)
        spline.use_smooth = True
        for index, (point, (position, tangent)) in enumerate(zip(spline.bezier_points, sampled)):
            left = (position - sampled[max(0, index - 1)][0]).length / 3
            right = (sampled[min(len(sampled) - 1, index + 1)][0] - position).length / 3
            point.handle_left_type = point.handle_right_type = 'FREE'
            point.co = position
            point.handle_left = point.co - tangent * (left or right)
            point.handle_right = point.co + tangent * (right or left)
    modifier = next(m for m in obj.modifiers if m.type == 'NODES' and m.node_group and m.node_group.get(GROUP_KEY))
    if not modifier.node_group.get(TANGENT_KEY):
        modifier.node_group = sweep_group()
    for socket in modifier.node_group.interface.items_tree:
        if socket.item_type == 'SOCKET' and socket.in_out == 'INPUT':
            if socket.name == 'Radius':
                getattr(modifier.properties.inputs, socket.identifier).value = diameter / 2
            elif socket.name == 'Sides':
                getattr(modifier.properties.inputs, socket.identifier).value = sides
    if store:
        obj['line_pipe_route_v1'] = json.dumps([list(p - origin) for p in points])
        obj['line_pipe_ports_v1'] = json.dumps([
            {'key': 'START', 'position': list(points[0] - origin),
             'direction': list((points[0] - points[1]).normalized()), 'diameter': diameter, 'solid': True},
            {'key': 'END', 'position': list(points[-1] - origin),
             'direction': list((points[-1] - points[-2]).normalized()), 'diameter': diameter, 'solid': True}])
    obj.update_tag()


def rebuild(obj):
    if not obj or obj.type != 'CURVE' or not obj.get('line_pipe_route_v1'):
        return
    state = obj.line_pipe
    points = [Vector(p) + obj.location for p in json.loads(obj['line_pipe_route_v1'])]
    update(obj, points, state.diameter, state.bend_radius, state.radial_segments, state.bend_steps, store=True)


def remove(obj):
    if obj and obj.name in bpy.data.objects:
        data = obj.data
        bpy.data.objects.remove(obj, do_unlink=True)
        if data.users == 0:
            bpy.data.curves.remove(data)
    for group in tuple(bpy.data.node_groups):
        if group.get(GROUP_KEY) and group.users == 0:
            bpy.data.node_groups.remove(group)
