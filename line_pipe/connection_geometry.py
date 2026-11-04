# SPDX-License-Identifier: GPL-3.0-or-later
"""Fixed endpoint routes and validated solid/hollow sweeps, without scene mutation."""
import itertools
import math
import bmesh
import bpy
from mathutils import Matrix, Vector, Quaternion
from mathutils.bvhtree import BVHTree
from .model import rounded_samples
from .ports import ConnectionError, perpendicular


def clean_points(points):
    result = []
    for p in map(Vector, points):
        if result and (p - result[-1]).length < 1e-7:
            continue
        if len(result) > 1:
            a, b = (result[-1] - result[-2]).normalized(), (p - result[-1]).normalized()
            if a.dot(b) > 1 - 1e-6:
                result[-1] = p
                continue
            if a.dot(b) < -1 + 1e-6:
                raise ConnectionError('route_reverses')
        result.append(p)
    return result


def axis_frame(directions):
    axes = []
    for direction in directions:
        n = Vector(direction).normalized()
        if n.length < .9:
            raise ConnectionError('nonorthogonal_group')
        if any(abs(n.dot(a)) > 1 - 2e-4 for a in axes):
            continue
        if any(abs(n.dot(a)) > 2e-4 for a in axes) or len(axes) == 3:
            raise ConnectionError('nonorthogonal_group')
        axes.append(n)
    if not axes:
        raise ConnectionError('choose_pipe')
    if len(axes) == 1:
        axes.append(perpendicular(axes[0]))
    return Matrix((axes[0], axes[1], axes[0].cross(axes[1]).normalized())).transposed()


def angular_samples(points, diameter):
    directions = [(b - a).normalized() for a, b in zip(points, points[1:])]
    tangents = [directions[0]]
    miters = [None]
    cuts = [0.0]
    for i, (a, b) in enumerate(zip(directions, directions[1:]), 1):
        cosine = a.dot(b)
        if cosine < -.9999:
            raise ConnectionError('route_reverses')
        angle = a.angle(b)
        extent = diameter / 2 * math.tan(angle / 2)
        cuts.append(extent)
        if min((points[i] - points[i-1]).length, (points[i+1] - points[i]).length) <= extent * 1.001:
            raise ConnectionError('route_clearance')
        tangent = (a + b).normalized()
        axis = a.cross(b)
        miters.append((axis.normalized().cross(tangent), 1 / math.cos(angle / 2)) if axis.length > 1e-6 else None)
        tangents.append(tangent)
    tangents.append(directions[-1]); miters.append(None)
    cuts.append(0.0)
    if any((b-a).length <= cuts[i] + cuts[i+1] + diameter * 1e-6
           for i, (a, b) in enumerate(zip(points, points[1:]))):
        raise ConnectionError('route_clearance')
    return points, tangents, miters


def bezier_samples(points, diameter, steps=96):
    p, c, e, q = points
    centers, tangents, arcs = [], [], [0.0]
    for i in range(steps + 1):
        x, y = i / steps, 1 - i / steps
        position = y**3*p + 3*y*y*x*c + 3*y*x*x*e + x**3*q
        first = 3*y*y*(c-p) + 6*y*x*(e-c) + 3*x*x*(q-e)
        second = 6*y*(e-2*c+p) + 6*x*(q-2*e+c)
        cross = first.cross(second).length
        if first.length < 1e-7 or cross > 1e-10 and first.length**3 / cross <= diameter * .501:
            raise ConnectionError('route_clearance')
        if centers:
            arcs.append(arcs[-1] + (position - centers[-1]).length)
        centers.append(position); tangents.append(first.normalized())
    for i, a in enumerate(centers):
        for j in range(i + 1, len(centers)):
            if arcs[j] - arcs[i] > diameter * 2.5 and (a - centers[j]).length < diameter * 1.01:
                raise ConnectionError('route_self_intersection')
    return centers, tangents, [None] * len(centers)


def samples(recipe):
    points = [Vector(p) for p in recipe['points']]
    diameter = recipe['diameter']
    if recipe.get('kind') == 'BEZIER':
        return bezier_samples(points, diameter)
    if recipe.get('smooth', True):
        values = rounded_samples(points, recipe['radius'], recipe.get('steps', 16), diameter / 2)
        return [x[0] for x in values], [x[1] for x in values], [None] * len(values)
    return angular_samples(points, diameter)


def sweep(recipe):
    centers, tangents, miters = samples(recipe)
    sides = int(recipe.get('sides', 32))
    bore, diameter = recipe.get('bore', 0), recipe['diameter']
    if sides < 3 or not 0 <= bore < diameter:
        raise ConnectionError('invalid_ports')
    shells = 2 if bore > 0 else 1
    width = sides * shells
    vertices, faces, smooth = [], [], []
    radii = (diameter / 2, bore / 2) if bore else (diameter / 2,)
    frames = []
    for start_key, end_key in (('start_radial', 'end_radial'), ('start_inner', 'end_inner'))[:shells]:
        radial = Vector(recipe.get(start_key, recipe.get('start_radial', perpendicular(tangents[0]))))
        transported = []
        for i, tangent in enumerate(tangents):
            if i:
                radial = tangents[i - 1].rotation_difference(tangent) @ radial
            radial = (radial - tangent * radial.dot(tangent)).normalized()
            transported.append(radial)
        end = recipe.get(end_key, recipe.get('end_radial'))
        if end is not None:
            end = Vector(end)
            last = transported[-1]
            axis = tangents[-1]
            twist = math.remainder(math.atan2(axis.dot(last.cross(end)), last.dot(end)), math.tau / sides)
            distance = [0.]
            for a, b in zip(centers, centers[1:]):
                distance.append(distance[-1] + (b - a).length)
            transported = [Quaternion(axis, twist * along / distance[-1]) @ direction
                           for axis, along, direction in zip(tangents, distance, transported)]
        frames.append(transported)
    for i, (center, tangent) in enumerate(zip(centers, tangents)):
        for radius, directions in zip(radii, frames):
            radial = directions[i]
            second = tangent.cross(radial).normalized()
            for j in range(sides):
                angle = math.tau * j / sides
                offset = radius * (radial * math.cos(angle) + second * math.sin(angle))
                if miters[i]:
                    axis, stretch = miters[i]
                    offset += axis * offset.dot(axis) * (stretch - 1)
                vertices.append(tuple(center + offset))
    for i in range(len(centers) - 1):
        for j in range(sides):
            k = (j + 1) % sides
            a, b = i * width, (i + 1) * width
            faces.append((a+j, a+k, b+k, b+j)); smooth.append(bool(recipe.get('smooth', True)))
            if bore:
                faces.append((a+sides+k, a+sides+j, b+sides+j, b+sides+k)); smooth.append(True)
    end = (len(centers) - 1) * width
    if bore:
        for j in range(sides):
            k = (j + 1) % sides
            faces.extend([(k, j, sides+j, sides+k), (end+j, end+k, end+sides+k, end+sides+j)])
            smooth.extend([False, False])
    else:
        faces.extend([tuple(reversed(range(sides))), tuple(end + j for j in range(sides))])
        smooth.extend([False, False])
    return vertices, faces, smooth


def mesh_from_recipe(recipe, name='PipeWorks Connector'):
    vertices, faces, smooth = sweep(recipe)
    mesh = bpy.data.meshes.new(name)
    try:
        mesh.from_pydata(vertices, [], faces); mesh.update()
        for polygon, flag in zip(mesh.polygons, smooth):
            polygon.use_smooth = flag
        bm = bmesh.new()
        try:
            bm.from_mesh(mesh)
            bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
            if (not bm.faces or any(not e.is_manifold for e in bm.edges)
                    or any(f.calc_area() <= recipe['diameter']**2 * 1e-11 for f in bm.faces)
                    or bm.calc_volume(signed=True) <= 0):
                raise ConnectionError('invalid_mesh')
            bm.to_mesh(mesh)
        finally:
            bm.free()
        mesh.update()
        if tiny_triangles(mesh, recipe['diameter']):
            raise ConnectionError('invalid_mesh')
        if self_intersections(mesh):
            raise ConnectionError('route_self_intersection')
        return mesh
    except Exception:
        bpy.data.meshes.remove(mesh)
        raise


def route(a, b, radius, smooth=True, sides=32, basis=None):
    """Search orthogonal lead-out routes before a tangent-preserving spatial fallback."""
    p, q, u, t = a.position, b.position, a.direction, -b.direction
    gap = (q - p).length
    if gap < a.diameter * .01:
        raise ConnectionError('gap_too_small')
    heading = (q - p) / gap
    if heading.dot(u) > 1 - 1e-6 and heading.dot(t) > 1 - 1e-6:
        return dict(kind='ORTHOGONAL', points=[list(p), list(q)], diameter=a.diameter,
                    bore=a.bore, radius=radius, smooth=smooth, sides=sides, steps=16)
    candidates = []
    if basis is None:
        try:
            basis = (Matrix((u, a.radial, u.cross(a.radial))).transposed()
                     if abs(u.dot(t)) > 1-2e-4 else axis_frame((u, t)))
        except ConnectionError:
            basis = None
    if basis is not None:
        inverse = basis.transposed()
        for multiplier in (1, 2, 4):
            lead = max(radius * 2, a.diameter * 2) * multiplier
            start, end = p + u * lead, q - t * lead
            for order in itertools.permutations(range(3)):
                cursor, middle = inverse @ start, [start]
                destination = inverse @ end
                for axis in order:
                    cursor = cursor.copy(); cursor[axis] = destination[axis]
                    middle.append(basis @ cursor)
                variants = [[p, *middle, q]]
                for axis in range(3):
                    for sign in (-1, 1):
                        offset = basis.col[axis] * lead * sign
                        variants.append([p, start, *[v + offset for v in middle], end, q])
                for points in variants:
                    try:
                        points = clean_points(points)
                        recipe = dict(kind='ORTHOGONAL', points=[list(v) for v in points], diameter=a.diameter,
                                      bore=a.bore, radius=radius, smooth=smooth, sides=sides, steps=16)
                        centers, _, _ = samples(recipe)
                        # Nonlocal samples may not return through an earlier part of the tube.
                        arc = [0.0]
                        for c, d in zip(centers, centers[1:]): arc.append(arc[-1] + (d-c).length)
                        if any(arc[j]-arc[i] > a.diameter*2.5 and (centers[j]-c).length < a.diameter*1.01
                               for i, c in enumerate(centers) for j in range(i+1, len(centers))):
                            continue
                        score = sum((d-c).length for c, d in zip(points, points[1:])) + len(points)*a.diameter*.1
                        candidates.append((score, recipe))
                    except (ValueError, ZeroDivisionError):
                        continue
        if candidates:
            return min(candidates, key=lambda x: x[0])[1]
    for fraction in (.25, .5, 1, 2, 4):
        lead = max(a.diameter * 2, gap * fraction)
        controls = [p, p+u*lead, q-t*lead, q]
        recipe = dict(kind='BEZIER' if smooth else 'POLYLINE', points=[list(v) for v in controls],
                      diameter=a.diameter, bore=a.bore, radius=radius, smooth=smooth, sides=sides, steps=16)
        try:
            samples(recipe)
            return recipe
        except ValueError:
            continue
    raise ConnectionError('route_clearance')


def evaluated_mesh(obj, depsgraph):
    return bpy.data.meshes.new_from_object(obj.evaluated_get(depsgraph), preserve_all_data_layers=True, depsgraph=depsgraph)


def topology(mesh):
    bm = bmesh.new()
    try:
        bm.from_mesh(mesh)
        return dict(nonmanifold=sum(not e.is_manifold for e in bm.edges),
                    degenerate=sum(f.calc_area() < 1e-12 for f in bm.faces), volume=bm.calc_volume(signed=True))
    finally:
        bm.free()


def self_intersections(mesh):
    mesh.calc_loop_triangles()
    triangles = [tuple(t.vertices) for t in mesh.loop_triangles]
    tree = BVHTree.FromPolygons([v.co for v in mesh.vertices], triangles, all_triangles=True)
    return any(a < b and not set(triangles[a]).intersection(triangles[b]) for a, b in tree.overlap(tree))


def tiny_triangles(mesh, diameter):
    mesh.calc_loop_triangles()
    vertices = mesh.vertices
    return sum((vertices[t.vertices[1]].co-vertices[t.vertices[0]].co).cross(
        vertices[t.vertices[2]].co-vertices[t.vertices[0]].co).length <= diameter**2 * 2e-11
        for t in mesh.loop_triangles)


def detect_ports(mesh):
    """Recover exposed circular cap/annulus planes from an unregistered mesh."""
    bm = bmesh.new()
    try:
        bm.from_mesh(mesh); bm.normal_update()
        if not bm.verts: raise ConnectionError('no_mesh_ports')
        size = max((v.co.length for v in bm.verts), default=1)
        tolerance = max(size * 1e-6, 1e-7)
        unseen, candidates = set(bm.faces), []
        while unseen:
            seed = unseen.pop()
            if seed.calc_area() <= tolerance**2: continue
            normal, origin = seed.normal.copy(), seed.verts[0].co.copy()
            cluster, queue = {seed}, [seed]
            while queue:
                face = queue.pop()
                for edge in face.edges:
                    for neighbor in edge.link_faces:
                        if (neighbor in unseen and neighbor.normal.dot(normal) > 1-1e-5 and
                                all(abs((v.co-origin).dot(normal)) < tolerance for v in neighbor.verts)):
                            unseen.remove(neighbor);cluster.add(neighbor);queue.append(neighbor)
            boundary = {e for f in cluster for e in f.edges if sum(x in cluster for x in e.link_faces) == 1}
            vertices = {v for e in boundary for v in e.verts}
            if len(vertices) < 8: continue
            center = sum((v.co for v in vertices), Vector((0,0,0))) / len(vertices)
            if any((v.co-center).dot(normal) > tolerance*3 for v in bm.verts): continue
            radii = [(v.co-center).length for v in vertices]
            outer = max(radii)
            if outer < tolerance: continue
            outer_vertices = [v for v,r in zip(vertices,radii) if abs(r-outer)<outer*1e-4]
            if len(outer_vertices) < 8: continue
            inner_values = [r for r in radii if r < outer*.99]
            inner = sum(inner_values)/len(inner_values) if inner_values else 0
            if inner_values and (len(inner_values)<8 or max(inner_values)-min(inner_values)>outer*1e-4):continue
            radial = perpendicular(normal); second = normal.cross(radial)
            angles=sorted(math.atan2((v.co-center).dot(second),(v.co-center).dot(radial)) for v in outer_vertices)
            gaps=[b-a for a,b in zip(angles,angles[1:])]+[angles[0]+math.tau-angles[-1]]
            if max(gaps)>math.pi/3:continue
            candidates.append(dict(position=list(center),direction=list(normal),radial=list(radial),diameter=outer*2,bore=inner*2))
        hollow = [p for p in candidates if p['bore'] > 0]
        candidates = hollow or candidates
        if len(candidates)>2:
            # Repeated pipe diameters exclude an isolated valve handwheel face.
            counts=[sum(abs(p['diameter']-q['diameter'])<p['diameter']*1e-4 for q in candidates) for p in candidates]
            if max(counts)>1:candidates=[p for p,count in zip(candidates,counts) if count==max(counts)]
        candidates.sort(key=lambda p:tuple(round(v,5) for v in p['position']))
        if not candidates:raise ConnectionError('no_mesh_ports')
        for i,p in enumerate(candidates):p['key']='P'+str(i+1)
        return candidates
    finally:
        bm.free()


def infer_recipe(mesh, ports):
    """Recover only a verified straight or single 90-degree circular pipe sweep."""
    if len(ports)!=2:raise ConnectionError('unsupported_curvature')
    a,b=ports;p,q=a['position'],b['position'];u,t=-a['direction'],b['direction']
    diameter,bore=a['diameter'],a.get('bore',0)
    if abs(diameter-b['diameter'])>diameter*1e-4:raise ConnectionError('unsupported_curvature')
    outer,inner=diameter/2,bore/2
    tolerance=max(diameter*3e-4,(q-p).length*2e-6)
    if u.dot(t)>.9999 and (q-p).normalized().dot(u)>.9999:
        length=(q-p).length
        for v in mesh.vertices:
            axial=(v.co-p).dot(u)
            radial=(v.co-p-u*axial).length
            if min(abs(axial),abs(axial-length))<tolerance and radial<=outer+tolerance:continue
            if min(abs(radial-outer),abs(radial-inner) if inner else outer)>tolerance:
                raise ConnectionError('unsupported_curvature')
        points=[list(p),list(q)];radius=max(diameter,.4)
    elif abs(u.dot(t))<2e-4:
        incoming,outgoing=(q-p).dot(u),(q-p).dot(t)
        corner=p+u*incoming
        if (corner-(q-t*outgoing)).length>tolerance or min(incoming,outgoing)<=outer*(1+2**-14):
            raise ConnectionError('unsupported_curvature')
        axis=u.cross(t)
        projected=[((v.co-corner).dot(u),(v.co-corner).dot(t),(v.co-corner).dot(axis)) for v in mesh.vertices]
        def deviation(point,radius):
            x,y,z=point
            angle=max(0,min(math.pi/2,math.atan2(x+radius,radius-y)))
            dx,dy=x+radius-radius*math.sin(angle),y-radius+radius*math.cos(angle)
            arc=dx*dx+dy*dy
            straight_in=(x-max(-incoming,min(-radius,x)))**2+y*y
            straight_out=x*x+(y-max(radius,min(outgoing,y)))**2
            distance=math.sqrt(min(arc,straight_in,straight_out)+z*z)
            return min(abs(distance-outer),abs(distance-inner) if inner else outer)
        subset=projected[::max(1,len(projected)//384)]
        def error(radius):return sum(deviation(v,radius)**2 for v in subset)
        low,high=outer*(1+2**-14),min(incoming,outgoing)
        grid=[low+(high-low)*i/48 for i in range(49)]
        best=min(range(49),key=lambda i:error(grid[i]))
        left,right=grid[max(0,best-1)],grid[min(48,best+1)]
        for _ in range(28):
            first,second=(2*left+right)/3,(left+2*right)/3
            if error(first)<error(second):right=second
            else:left=first
        radius=min((left+right)/2,grid[best],key=error)
        if max(deviation(v,radius) for v in projected)>tolerance:raise ConnectionError('unsupported_curvature')
        points=[list(p),list(corner),list(q)]
    else:raise ConnectionError('unsupported_curvature')
    return dict(kind='ORTHOGONAL',points=points,diameter=diameter,bore=bore,radius=radius,smooth=True,sides=a.get('sides', 32),steps=16)
