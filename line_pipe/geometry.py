# SPDX-License-Identifier: GPL-3.0-or-later
"""Editable centerline plus Blender's native solid Curve to Mesh sweep."""
import json
import bpy
from mathutils import Vector
from .model import rounded_path

GROUP_KEY = 'line_pipe_solid_sweep_v1'


def sweep_group():
    for group in bpy.data.node_groups:
        if group.get(GROUP_KEY):
            return group
    group = bpy.data.node_groups.new('PipeWorks - Solid Sweep', 'GeometryNodeTree')
    group[GROUP_KEY] = True
    group.interface.new_socket(name='Geometry', in_out='INPUT', socket_type='NodeSocketGeometry')
    group.interface.new_socket(name='Geometry', in_out='OUTPUT', socket_type='NodeSocketGeometry')
    radius = group.interface.new_socket(name='Radius', in_out='INPUT', socket_type='NodeSocketFloat')
    radius.default_value, radius.min_value = .1, .000001
    sides = group.interface.new_socket(name='Sides', in_out='INPUT', socket_type='NodeSocketInt')
    sides.default_value, sides.min_value, sides.max_value = 32, 8, 128
    source = group.nodes.new('NodeGroupInput')
    source.location = (-360, 100)
    profile = group.nodes.new('GeometryNodeCurvePrimitiveCircle')
    profile.location = (-160, -120)
    sweep = group.nodes.new('GeometryNodeCurveToMesh')
    sweep.location = (60, 100)
    sweep.inputs['Fill Caps'].default_value = True
    output = group.nodes.new('NodeGroupOutput')
    output.location = (300, 100)
    group.links.new(source.outputs['Geometry'], sweep.inputs['Curve'])
    group.links.new(source.outputs['Radius'], profile.inputs['Radius'])
    group.links.new(source.outputs['Sides'], profile.inputs['Resolution'])
    group.links.new(profile.outputs['Curve'], sweep.inputs['Profile Curve'])
    group.links.new(sweep.outputs['Mesh'], output.inputs['Geometry'])
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
    sampled = rounded_path(points, radius, steps)
    curve = obj.data
    curve.splines.clear()
    if len(sampled) >= 2 and (sampled[-1] - sampled[0]).length + sum(
            (b - a).length for a, b in zip(sampled, sampled[1:])) > 1e-7:
        spline = curve.splines.new('POLY')
        spline.points.add(len(sampled) - 1)
        spline.use_smooth = True
        for point, position in zip(spline.points, sampled):
            point.co = (*(position - origin), 1)
    modifier = next(m for m in obj.modifiers if m.type == 'NODES' and m.node_group and m.node_group.get(GROUP_KEY))
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
