# SPDX-License-Identifier: GPL-3.0-or-later
"""Read actual circular edge loops and preserve authored ports with mesh edge tags."""
import math
from collections import defaultdict
from mathutils import Vector

TAG = 'pipeworks_port_ring'


def loops(edges):
    adjacency = defaultdict(list)
    for edge in edges:
        for vertex in edge.verts:
            adjacency[vertex].append(edge)
    if any(len(items) != 2 for items in adjacency.values()):
        raise ValueError('invalid_ring')
    remaining = set(edges)
    result = []
    while remaining:
        edge = next(iter(remaining))
        start, vertex = edge.verts
        vertices, ring = [start], [edge]
        remaining.remove(edge)
        while vertex != start:
            vertices.append(vertex)
            edge = next(e for e in adjacency[vertex] if e != edge)
            if edge not in remaining:
                raise ValueError('invalid_ring')
            remaining.remove(edge)
            ring.append(edge)
            vertex = edge.other_vert(vertex)
        result.append((vertices, ring))
    return result


def circle(points, normal=None):
    count = len(points)
    if count < 3:
        raise ValueError('invalid_ring')
    center = sum(points, Vector((0, 0, 0))) / count
    offsets = [p - center for p in points]
    radius = sum(v.length for v in offsets) / count
    if radius <= 1e-8:
        raise ValueError('invalid_ring')
    if normal is None:
        normal = sum((a.cross(b) for a, b in zip(offsets, offsets[1:] + offsets[:1])),
                     Vector((0, 0, 0))).normalized()
    tolerance = radius * 4e-4
    if normal.length < .9 or any(abs(v.length - radius) > tolerance or abs(v.dot(normal)) > tolerance for v in offsets):
        raise ValueError('invalid_ring')
    step = math.tau / count
    radial = offsets[0].normalized()
    second = normal.cross(radial)
    angles = sorted(math.atan2(v.dot(second), v.dot(radial)) for v in offsets)
    gaps = [b - a for a, b in zip(angles, angles[1:])] + [angles[0] + math.tau - angles[-1]]
    if any(abs(gap - step) > max(step * .008, 1e-4) for gap in gaps):
        raise ValueError('invalid_ring')
    # The starting vertex is deterministic even when the mesh edge order changes.
    from .ports import perpendicular
    axis = perpendicular(normal)
    radial = max((v.normalized() for v in offsets), key=lambda v: (round(v.dot(axis), 7), v.dot(normal.cross(axis))))
    return dict(position=center, direction=normal, radial=radial, diameter=2 * radius, sides=count)


def phase_offset(outer, inner, normal, sides):
    return math.remainder(math.atan2(normal.dot(outer.cross(inner)), outer.dot(inner)), math.tau / sides)


def profile(edges, hint=None):
    rings = loops(edges)
    if not 1 <= len(rings) <= 2:
        raise ValueError('invalid_ring')
    specs = [circle([v.co for v in vertices], hint) for vertices, _ in rings]
    for spec, (_, ring) in zip(specs, rings):
        chord = spec['diameter'] * math.sin(math.pi / spec['sides'])
        if any(abs(edge.calc_length() - chord) > chord * .01 for edge in ring):
            raise ValueError('invalid_ring')
    outer = max(specs, key=lambda p: p['diameter'])
    normal = outer['direction']
    center = outer['position']
    tolerance = outer['diameter'] * 2e-4
    surrounding = {face for edge in edges for face in edge.link_faces}
    distances = [(face.calc_center_median() - center).dot(normal) for face in surrounding]
    positive = any(d > tolerance for d in distances)
    negative = any(d < -tolerance for d in distances)
    if positive == negative:
        raise ValueError('invalid_ring')
    if positive:
        outer['direction'] = -normal
    outer['bore'] = 0
    if len(specs) == 2:
        inner = next(p for p in specs if p is not outer)
        if ((inner['position'] - center).length > tolerance or inner['sides'] != outer['sides']
                or abs(inner['direction'].dot(normal)) < .9999
                or outer['diameter'] - inner['diameter'] <= outer['diameter'] * 2e-6):
            raise ValueError('invalid_ring')
        outer['bore'] = inner['diameter']
        outer['inner_radial'] = inner['radial']
    return outer


def mesh_plane_profile(mesh, spec):
    """Measure the real ring phase and count of a procedural or older endpoint."""
    center, normal = spec['position'], spec['direction']
    diameter, bore = spec['diameter'], spec['bore']
    tolerance = diameter * 1e-4
    plane = {v.index for v in mesh.vertices if abs((v.co - center).dot(normal)) <= tolerance}
    caps = {index for face in mesh.polygons if abs(face.normal.dot(normal)) > .9999
            and all(i in plane for i in face.vertices) for index in face.vertices}
    outer, inner = {}, {}
    for index in caps or plane:
        vertex = mesh.vertices[index]
        delta = vertex.co - center
        height = delta.dot(normal)
        distance = (delta - normal * height).length
        to_outer = abs(distance - diameter / 2)
        to_inner = abs(distance - bore / 2) if bore else math.inf
        if min(to_outer, to_inner) <= tolerance:
            ring = outer if to_outer <= to_inner else inner
            ring[index] = vertex.co

    def checked_ring(vertices):
        ring = circle(list(vertices.values()), normal)
        chord = ring['diameter'] * math.sin(math.pi / ring['sides'])
        degree = dict.fromkeys(vertices, 0)
        for edge in mesh.edges:
            a, b = edge.vertices
            if a in vertices and b in vertices and abs((vertices[a] - vertices[b]).length - chord) < chord * .01:
                degree[a] += 1
                degree[b] += 1
        if any(count != 2 for count in degree.values()):
            raise ValueError('invalid_ring')
        return ring

    result = checked_ring(outer)
    result['bore'] = bore
    if bore:
        inner_spec = checked_ring(inner)
        if inner_spec['sides'] != result['sides']:
            raise ValueError('invalid_ring')
        result['inner_radial'] = inner_spec['radial']
    return result


def scan(bm):
    """Find terminal loops on planar caps, annular faces, and open boundaries."""
    bm.normal_update()
    unseen = set(bm.faces)
    result = []
    while unseen:
        seed = unseen.pop()
        normal = seed.normal.copy()
        if normal.length < .9:
            continue
        origin = seed.verts[0].co
        tolerance = max(1e-7, max(e.calc_length() for e in seed.edges) * 1e-5)
        cluster, pending = {seed}, [seed]
        while pending:
            for edge in pending.pop().edges:
                for face in edge.link_faces:
                    if (face in unseen and face.normal.dot(normal) > 1 - 1e-5
                            and all(abs((v.co - origin).dot(normal)) < tolerance for v in face.verts)):
                        unseen.remove(face)
                        cluster.add(face)
                        pending.append(face)
        edges = {e for f in cluster for e in f.edges if sum(x in cluster for x in e.link_faces) == 1}
        # Uncovered planar strips should not masquerade as pipe mouths.
        if len(edges) < 5:
            continue
        try:
            result.append((profile(edges, normal), edges))
        except ValueError:
            pass
    boundaries = {edge for edge in bm.edges if edge.is_boundary}
    open_ports = []
    while boundaries:
        seed = boundaries.pop()
        connected, pending = {seed}, [seed]
        while pending:
            for vertex in pending.pop().verts:
                for edge in vertex.link_edges:
                    if edge in boundaries:
                        boundaries.remove(edge)
                        connected.add(edge)
                        pending.append(edge)
        try:
            open_ports.append((profile(connected), connected))
        except ValueError:
            pass
    while open_ports:
        outer, edges = open_ports.pop()
        partner = next((i for i, (other, _) in enumerate(open_ports)
                        if (outer['position'] - other['position']).length < outer['diameter'] * 2e-4
                        and outer['direction'].dot(other['direction']) > .9999
                        and outer['sides'] == other['sides']), None)
        if partner is not None:
            _, second_ring = open_ports.pop(partner)
            edges = edges | second_ring
            outer = profile(edges, outer['direction'])
        result.append((outer, edges))
    result.sort(key=lambda entry: tuple(round(v, 6) for v in entry[0]['position']))
    return result
