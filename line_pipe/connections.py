# SPDX-License-Identifier: GPL-3.0-or-later
"""Atomic rigid docking, fixed-end bridging and group curvature operations."""
from contextlib import contextmanager
import json
import math
import uuid
import bmesh
import bpy
from mathutils import Matrix, Vector, Quaternion
from . import ports, port_rings, connection_geometry as cg, geometry, data
from .model import fillet_radii, bend_floor

PATH = '_pipeworks_path_v1'


def frame(normal, radial):
    n = normal.normalized()
    u = (radial - n * radial.dot(n)).normalized()
    return Matrix((u, n.cross(u), n)).transposed()


def curve_matches(obj, generated):
    if len(obj.data.splines) != 1 or len(generated.data.splines) != 1:
        return False
    left, right = obj.data.splines[0], generated.data.splines[0]
    if (left.type != 'BEZIER' or left.use_cyclic_u or left.resolution_u != right.resolution_u
            or len(left.bezier_points) != len(right.bezier_points)):
        return False
    return all(abs(a.tilt - b.tilt) < 1e-6 and abs(a.radius - b.radius) < 1e-6
               and all((getattr(a, name) - getattr(b, name)).length < 1e-6
                       for name in ('co', 'handle_left', 'handle_right'))
               for a, b in zip(left.bezier_points, right.bezier_points))


@contextmanager
def prepared_ports(context, source, source_key, target, target_key):
    """Stage a potential moving-side retessellation without editing the endpoints."""
    scene = context.scene
    a, b = ports.read(scene, source, source_key), ports.read(scene, target, target_key)
    ports.compatible(a, b)
    if a.sides == b.sides:
        yield a, b, None
        return
    details = dict(moving=a.sides, anchor=b.sides)
    if ports.LIBRARY_ASSET in source or ports.LIBRARY_ASSET in target:
        raise ports.ConnectionError('library_side_mismatch', **details)
    if a.sides not in ports.STANDARD_SIDES or b.sides not in ports.STANDARD_SIDES:
        raise ports.ConnectionError('side_mismatch', **details)
    if (not source.get('line_pipe_route_v1') or source.get(ports.CUSTOM)
            or not geometry.generated_mesh_intact(source, require_signature=True)):
        raise ports.ConnectionError('fixed_side_mismatch', **details)
    ports.editable([source])
    geometry.require_free_profile(source, scene)
    recipe = dict(recipe_for(source), sides=b.sides)
    spec = next(p for p in ports.local_ports(source) if p['key'] == source_key)
    temp, block = None, None
    try:
        if source.type == 'CURVE':
            temp = geometry.create(context)
            geometry.update(temp, recipe['points'], recipe['diameter'], recipe['radius'],
                            recipe['sides'], recipe['steps'])
            if not curve_matches(source, temp):
                raise ports.ConnectionError('fixed_side_mismatch', **details)
            context.view_layer.update()
            resolved = ports.measured(temp, spec)
        else:
            block = stage_recipe(source, recipe)
            resolved = ports.measured(source, spec, block)
        if resolved['sides'] != b.sides:
            raise ports.ConnectionError('invalid_ring')
        yield ports.world_port(source, resolved), b, (source, recipe, block)
    finally:
        if temp is not None:
            geometry.remove(temp)
        if block is not None and block.users == 0:
            discard(block)


def apply_side_change(change):
    if change is None:
        return
    obj, recipe, block = change
    if block is None:
        geometry.set_sweep_profile(obj, recipe['diameter'], recipe['sides'])
    else:
        discard(swap_data(obj, block))
        geometry.remember_mesh(obj)
    data._updating = True
    try:
        obj.line_pipe.radial_segments = recipe['sides']
    finally:
        data._updating = False
    obj['_line_pipe_dimensions'] = [getattr(obj.line_pipe, key) for key in data.DIMENSIONS]
    geometry.store_route(obj, [Vector(p) for p in recipe['points']], recipe['diameter'],
                         recipe['sides'], recipe['bore'])
    obj.update_tag()


def docking_matrices(scene, a, b, roll):
    moving = ports.members(scene, a.obj)
    if b.obj in moving:
        raise ports.ConnectionError('same_group_snap')
    ports.editable(moving)
    ancestor = b.obj.parent
    while ancestor:
        if ancestor in moving:
            raise ports.ConnectionError('nonuniform_parent')
        ancestor = ancestor.parent
    step = math.tau / a.sides
    aligned_roll = round(roll / step) * step
    rotation = (frame(-b.direction, b.radial) @ Quaternion(Vector((0, 0, 1)), aligned_roll).to_matrix()
                @ frame(a.direction, a.radial).transposed())
    if a.bore and b.bore:
        mismatch = port_rings.phase_offset(b.inner_radial, rotation @ a.inner_radial, -b.direction, a.sides)
        if abs(mismatch) > 1e-4:
            raise ports.ConnectionError('inner_phase')
    delta = Matrix.Translation(b.position) @ rotation.to_4x4() @ Matrix.Translation(-a.position)
    return {obj: delta @ obj.matrix_world for obj in moving}, aligned_roll


def direct_plan(scene, source, source_key, target, target_key, roll=0):
    with prepared_ports(bpy.context, source, source_key, target, target_key) as (a, b, _):
        return docking_matrices(scene, a, b, roll)[0]


def set_matrices(matrices):
    def depth(obj):
        level, parent = 0, obj.parent
        while parent:
            level += 1; parent = parent.parent
        return level
    for obj in sorted(matrices, key=depth):
        obj.matrix_world = matrices[obj]
    bpy.context.view_layer.update()


def merge_groups(scene, source, target, extra=None):
    left, right = ports.members(scene, source), ports.members(scene, target)
    for obj in (*left, *right):
        ports.ensure_identity(obj)
    group = ports.group_id(target)
    for obj in {*left, *right, *([extra] if extra else [])}:
        ports.ensure_identity(obj)
        obj[ports.GROUP] = group


def new_link(scene, source, source_key, target, target_key, mode, connector=None, radius=.4, smooth=True):
    record = scene.line_pipe_connections.links.add()
    record.uid = uuid.uuid4().hex
    record.source, record.source_port = source, source_key
    record.target, record.target_port = target, target_key
    record.mode, record.connector, record.radius, record.smooth = mode, connector, radius, smooth
    return record


def direct(context, source, source_key, target, target_key, roll=0):
    with prepared_ports(context, source, source_key, target, target_key) as (a, b, change):
        matrices, aligned_roll = docking_matrices(context.scene, a, b, roll)
        original = {o: o.matrix_world.copy() for o in matrices}
        groups = {o: o.get(ports.GROUP) for o in (*matrices, *ports.members(context.scene, target))}
        link_count = len(context.scene.line_pipe_connections.links)
        try:
            set_matrices(matrices)
            for obj, wanted in matrices.items():
                if max(abs(obj.matrix_world[r][c] - wanted[r][c]) for r in range(4) for c in range(4)) > 2e-5:
                    raise ports.ConnectionError('nonuniform_parent')
            merge_groups(context.scene, source, target)
            record = new_link(context.scene, source, source_key, target, target_key, 'DIRECT')
            record.roll, record.sides = aligned_roll, a.sides
            apply_side_change(change)
            context.view_layer.update()
            return record
        except Exception:
            links = context.scene.line_pipe_connections.links
            if len(links) > link_count:
                links.remove(link_count)
            set_matrices(original)
            for obj, group in groups.items():
                if group is None:
                    if ports.GROUP in obj:
                        del obj[ports.GROUP]
                else:
                    obj[ports.GROUP] = group
            raise


def apply_materials(mesh, original):
    for material in original.materials:
        mesh.materials.append(material)


def swap_data(obj, block):
    slots = [(slot.link, slot.material) for slot in obj.material_slots]
    old = obj.data
    obj.data = block
    for slot, (link, material) in zip(obj.material_slots, slots):
        slot.link, slot.material = link, material
    return old


def store_path(obj, recipe):
    previous = ports.local_ports(obj)
    keys = [p['key'] for p in previous] if len(previous) == 2 else ['START', 'END']
    obj[PATH] = json.dumps(recipe)
    centers, tangents, _ = cg.samples(recipe)
    obj[ports.PORTS] = json.dumps([
        dict(key=keys[0], position=list(centers[0]), direction=list(-tangents[0]),
             diameter=recipe['diameter'], bore=recipe.get('bore', 0), sides=recipe['sides']),
        dict(key=keys[1], position=list(centers[-1]), direction=list(tangents[-1]),
             diameter=recipe['diameter'], bore=recipe.get('bore', 0), sides=recipe['sides'])])


def bridge_recipe(scene, a, b, radius, smooth, max_distance):
    if (a.position - b.position).length > max_distance:
        raise ports.ConnectionError('connection_range')
    if radius < bend_floor(a.diameter):
        raise ports.ConnectionError('bad_radius')
    a.bore = min(a.bore, b.bore)
    recipe = cg.route(a, b, radius, smooth, a.sides, preferred_basis(scene, a, b))
    recipe.update(start_radial=list(a.radial), end_radial=list(b.radial))
    if a.bore:
        recipe.update(start_inner=list(a.inner_radial), end_inner=list(b.inner_radial))
    return recipe


def bridge(context, source, source_key, target, target_key, radius=.4, smooth=True, max_distance=5, sides=None):
    with prepared_ports(context, source, source_key, target, target_key) as (a, b, change):
        recipe = bridge_recipe(context.scene, a, b, radius, smooth, max_distance)
        origin = a.position.copy()
        recipe['points'] = [list(Vector(p) - origin) for p in recipe['points']]
        mesh = cg.mesh_from_recipe(recipe)
        obj = None
        link_count = len(context.scene.line_pipe_connections.links)
        groups = {o: o.get(ports.GROUP) for end in (source, target) for o in ports.members(context.scene, end)}
        try:
            apply_materials(mesh, source.data)
            obj = bpy.data.objects.new('PipeWorks Bridge', mesh)
            context.collection.objects.link(obj)
            obj.location = origin
            store_path(obj, recipe)
            merge_groups(context.scene, source, target, obj)
            record = new_link(context.scene, source, source_key, target, target_key, 'BRIDGE', obj, radius, smooth)
            record.max_distance, record.sides = max_distance, a.sides
            obj['_pipeworks_link_v1'] = record.uid
            apply_side_change(change)
            context.view_layer.update()
            return obj
        except Exception:
            links = context.scene.line_pipe_connections.links
            if len(links) > link_count:
                links.remove(link_count)
            if obj:
                bpy.data.objects.remove(obj, do_unlink=True)
            discard(mesh)
            for pipe, group in groups.items():
                if group is None:
                    if ports.GROUP in pipe:
                        del pipe[ports.GROUP]
                else:
                    pipe[ports.GROUP] = group
            raise


def recipe_for(obj):
    if obj.get(ports.CUSTOM) or not geometry.generated_mesh_intact(obj):
        specs = ports.local_ports(obj)
        if len(specs) != 2:
            raise ports.ConnectionError('unsupported_curvature')
        return cg.infer_recipe(obj.data, [ports.measured(obj, spec) for spec in specs])
    if obj.get(PATH):
        return json.loads(obj[PATH])
    if obj.get('line_pipe_route_v1'):
        settings = obj.line_pipe
        return dict(kind='ORTHOGONAL', points=json.loads(obj['line_pipe_route_v1']), smooth=True,
                    radius=settings.bend_radius, diameter=settings.diameter, bore=data.bore(settings),
                    sides=settings.radial_segments, steps=settings.bend_steps,
                    **json.loads(obj.get(geometry.SWEEP_FRAMES, '{}')))
    old = ports.legacy(obj)
    if old is None:
        if obj.type=='MESH':return cg.infer_recipe(obj.data,ports.local_ports(obj))
        raise ports.ConnectionError('unsupported_curvature')
    kind = ports.value(old, 'kind', 0)
    if isinstance(kind, int):
        kind = ('STRAIGHT', 'ELBOW_90', 'IMPORTED', 'REDUCER', 'CUSTOM', 'PATH',
                'TEE', 'WYE', 'VALVE', 'FLANGE', 'CAP', 'COUPLING', 'ELBOW')[min(max(kind, 0), 12)]
    local = ports.local_ports(obj)
    if len(local) != 2 or kind not in {'STRAIGHT', 'IMPORTED', 'ELBOW_90', 'ELBOW', 'VALVE', 'FLANGE', 'COUPLING'}:
        raise ports.ConnectionError('unsupported_curvature')
    a, b = local
    p, q, u, t = a['position'], b['position'], -a['direction'], b['direction']
    if kind in {'STRAIGHT', 'IMPORTED', 'VALVE', 'FLANGE', 'COUPLING'}:
        points = [p, q]
    elif abs(u.dot(t)) < 2e-4:
        corner = p + u * (q-p).dot(u)
        if (corner - (q-t*(q-p).dot(t))).length > 1e-5:
            raise ports.ConnectionError('unsupported_curvature')
        points = [p, corner, q]
    else:
        raise ports.ConnectionError('nonorthogonal_group')
    return dict(kind='ORTHOGONAL', points=[list(x) for x in points], diameter=a['diameter'], bore=a['bore'],
                radius=ports.value(old, 'bend_radius', .4), smooth=True,
                sides=a['sides'], steps=16)


def uniform_scale(obj):
    matrix = obj.matrix_world.to_3x3()
    sizes = [c.length for c in matrix.col]
    if min(sizes) < 1e-7 or max(sizes) - min(sizes) > max(sizes) * 1e-4 or any(
            abs(matrix.col[a].dot(matrix.col[b])) > max(sizes)**2 * 1e-4 for a, b in ((0,1), (0,2), (1,2))):
        raise ports.ConnectionError('curvature_scale')
    return sum(sizes) / 3


def preferred_basis(scene, a, b):
    try:
        rows = group_recipes(scene, a.obj)
        directions = [obj.matrix_world.to_3x3() @ (Vector(q)-Vector(p)) for obj,recipe,_ in rows
                      for p,q in zip(recipe['points'], recipe['points'][1:])]
        if len(directions) <= 1:
            return None
        basis = cg.axis_frame(directions)
        return basis if any(abs(b.direction.dot(axis)) > 1-2e-4 for axis in basis.col) else None
    except ValueError:
        return None


def group_recipes(scene, representative):
    rows, directions = [], []
    for obj in ports.members(scene, representative):
        if ports.value(ports.legacy(obj), 'kind', None) in {6, 'TEE'}:
            recipe = dict(kind='FIXED', points=[], radius=ports.value(ports.legacy(obj), 'bend_radius', .4), smooth=False)
            directions.extend(obj.matrix_world.to_3x3() @ p['direction'] for p in ports.local_ports(obj))
        else:
            recipe = recipe_for(obj)
        if recipe.get('kind') == 'BEZIER':
            raise ports.ConnectionError('nonorthogonal_group')
        points = [Vector(v) for v in recipe['points']]
        for a, b in zip(points, points[1:]):
            directions.append(obj.matrix_world.to_3x3() @ (b-a))
        scale = uniform_scale(obj)
        rows.append((obj, recipe, scale))
    cg.axis_frame(directions)
    return rows


def stage_recipe(obj, recipe):
    if obj.type == 'CURVE' and obj.get('line_pipe_route_v1'):
        temp = geometry.create(bpy.context)
        try:
            geometry.update(temp, recipe['points'], recipe['diameter'], recipe['radius'], recipe['sides'], recipe['steps'])
            result = temp.data
            apply_materials(result, obj.data)
        except Exception:
            geometry.remove(temp)
            raise
        bpy.data.objects.remove(temp, do_unlink=True)
        return result
    specs = ports.local_ports(obj)
    if len(specs) == 2 and 'start_radial' not in recipe:
        for end, spec in zip(('start', 'end'), specs):
            physical = ports.measured(obj, spec)
            recipe[end + '_radial'] = list(physical['radial'])
            if 'inner_radial' in physical:
                recipe[end + '_inner'] = list(physical['inner_radial'])
    mesh = cg.mesh_from_recipe(recipe, obj.data.name + ' Updated')
    apply_materials(mesh, obj.data)
    return mesh


def discard(block):
    if block.users == 0:
        (bpy.data.meshes if isinstance(block, bpy.types.Mesh) else bpy.data.curves).remove(block)


def sync_curvature(context, active=None, selected=None):
    active = active or context.active_object
    selected = selected if selected is not None else [o for o in context.selected_objects if ports.is_pipe(o)]
    groups = {ports.group_id(o): o for o in selected}
    if not active or not ports.is_pipe(active) or len(groups) != 2 or ports.group_id(active) not in groups:
        raise ports.ConnectionError('select_two_groups')
    first = next(obj for key, obj in groups.items() if key != ports.group_id(active))
    reference = group_recipes(context.scene, first)
    reference_radii = []
    for obj, recipe, scale in reference:
        if recipe.get('smooth', True):
            reference_radii.extend(r * scale for r in fillet_radii(recipe['points'], recipe['radius'], recipe['diameter']/2))
    # A compact reference may contain smaller fitted bends: use its smallest
    # existing radius so unifying never silently enlarges a short reference bend.
    radius = min(reference_radii) if reference_radii else next(r['radius']*scale for obj,r,scale in reference if obj == first)
    plans, staged = [], []
    for obj, recipe, scale in group_recipes(context.scene, active):
        ports.editable([obj])
        if len(recipe['points']) < 3:
            continue
        if obj.get(ports.CUSTOM) or not geometry.generated_mesh_intact(obj):
            raise ports.ConnectionError('edited_recipe')
        recipe = dict(recipe, radius=radius / scale, smooth=True)
        actual = fillet_radii(recipe['points'], recipe['radius'], recipe['diameter']/2)
        if any(abs(r - recipe['radius']) > max(r, recipe['radius']) * 1e-4 for r in actual):
            raise ports.ConnectionError('curvature_clearance')
        plans.append((obj, recipe))
    try:
        for obj, recipe in plans:
            staged.append((obj, recipe, stage_recipe(obj, recipe)))
    except Exception:
        for _, _, block in staged: discard(block)
        raise
    old_blocks = []
    data._updating = True
    try:
        for obj, recipe, block in staged:
            old_blocks.append(swap_data(obj, block))
            if obj.get('line_pipe_route_v1'):
                obj.line_pipe.bend_radius = recipe['radius']
                if obj.type == 'MESH':
                    geometry.remember_mesh(obj)
                obj['_line_pipe_dimensions'] = [getattr(obj.line_pipe, key) for key in data.DIMENSIONS]
            else:
                store_path(obj, recipe)
                old = ports.legacy(obj)
                if old is not None: old['bend_radius'] = recipe['radius']
            for link in context.scene.line_pipe_connections.links:
                if link.connector == obj:
                    link.radius, link.smooth = radius, True
    finally:
        data._updating = False
    for block in old_blocks: discard(block)
    return radius, len(plans)


def rebuild_mesh(obj):
    recipe = recipe_for(obj)
    if obj.get('line_pipe_route_v1'):
        recipe.update(radius=obj.line_pipe.bend_radius, diameter=obj.line_pipe.diameter,
                      sides=obj.line_pipe.radial_segments, steps=obj.line_pipe.bend_steps, bore=data.bore(obj.line_pipe))
    block = stage_recipe(obj, recipe)
    old = swap_data(obj, block)
    discard(old)
    if obj.get(PATH) or obj.get(ports.PORTS): store_path(obj, recipe)
    if obj.get('line_pipe_route_v1'):
        geometry.store_route(obj, [Vector(p) for p in recipe['points']], recipe['diameter'],
                             recipe['sides'], recipe['bore'])
        geometry.remember_mesh(obj)


def disconnect(context, obj):
    links = context.scene.line_pipe_connections.links
    for i in reversed(range(len(links))):
        record = links[i]
        if obj not in (record.source, record.target, record.connector):
            continue
        connector = record.connector
        links.remove(i)
        if connector:
            block = connector.data; bpy.data.objects.remove(connector, do_unlink=True); discard(block)


def repair_mesh(obj):
    if not obj or obj.type != 'MESH':
        raise ports.ConnectionError('choose_mesh')
    mesh = obj.data.copy()
    bm = bmesh.new()
    try:
        bm.from_mesh(mesh)
        diameter = max((p['diameter'] for p in ports.local_ports(obj)), default=1)
        bmesh.ops.remove_doubles(bm, verts=list(bm.verts), dist=diameter * 1e-6)
        bmesh.ops.dissolve_degenerate(bm, edges=list(bm.edges), dist=diameter * 1e-7)
        bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
        if (any(not e.is_manifold for e in bm.edges) or not bm.faces or bm.calc_volume(signed=True) <= 0
                or any(f.calc_area() <= diameter**2 * 1e-11 for f in bm.faces)):
            raise ports.ConnectionError('mesh_needs_remodel')
        bm.to_mesh(mesh); mesh.update()
        if cg.tiny_triangles(mesh, diameter) or cg.self_intersections(mesh):
            raise ports.ConnectionError('mesh_needs_remodel')
    except Exception:
        bpy.data.meshes.remove(mesh)
        raise
    finally:
        bm.free()
    old = swap_data(obj, mesh); discard(old)


def can_roll(scene, obj):
    if len(ports.members(scene, obj)) > 1:
        return True
    try:
        return len(recipe_for(obj)['points']) > 2
    except ValueError:
        return True


def register_cylinder(obj, axis='Z'):
    if not obj or obj.type != 'MESH': raise ports.ConnectionError('choose_mesh')
    ports.editable([obj])
    if any(m.show_viewport for m in obj.modifiers): raise ports.ConnectionError('modified_ports')
    index = 'XYZ'.index(axis)
    other = [i for i in range(3) if i != index]
    points = [v.co for v in obj.data.vertices]
    if len(points) < 6: raise ports.ConnectionError('not_cylinder')
    low, high = min(v[index] for v in points), max(v[index] for v in points)
    tolerance = max((high-low)*1e-5, 1e-7)
    if high-low < 1e-7 or any(min(abs(v[index]-low),abs(v[index]-high)) > tolerance for v in points):
        raise ports.ConnectionError('not_cylinder')
    center = sum(points, Vector((0,0,0))) / len(points)
    radii = [math.sqrt(sum((p[i]-center[i])**2 for i in other)) for p in points]
    radius = max(radii)
    if radius < 1e-7: raise ports.ConnectionError('not_cylinder')
    nonzero = [r for r in radii if radius*.01 < r < radius*.95]
    inner = sum(nonzero)/len(nonzero) if nonzero else 0
    if nonzero and max(nonzero)-min(nonzero) > radius*.005: raise ports.ConnectionError('not_cylinder')
    ring_counts = []
    for endpoint in (low, high):
        angles = sorted(math.atan2(p[other[1]]-center[other[1]],p[other[0]]-center[other[0]])
                        for p,r in zip(points,radii) if abs(p[index]-endpoint)<tolerance and abs(r-radius)<radius*.005)
        gaps = [b-a for a,b in zip(angles,angles[1:])] + ([angles[0]+math.tau-angles[-1]] if angles else [])
        if len(angles) < 3 or any(abs(gap - math.tau / len(angles)) > .002 for gap in gaps):
            raise ports.ConnectionError('not_cylinder')
        ring_counts.append(len(angles))
    report = cg.topology(obj.data)
    if report['nonmanifold'] or report['volume']<=0: raise ports.ConnectionError('bad_existing_mesh')
    p, q = center.copy(), center.copy(); p[index], q[index] = low, high
    recipe = dict(kind='ORTHOGONAL', points=[list(p),list(q)], diameter=radius*2,bore=inner*2,
                  radius=max(radius*2,.4),smooth=True,sides=ring_counts[0],steps=16)
    store_path(obj,recipe)
    ports.ensure_identity(obj)


def detect_mesh_ports(obj):
    if not obj or obj.type != 'MESH': raise ports.ConnectionError('choose_mesh')
    ports.editable([obj])
    if any(m.show_viewport for m in obj.modifiers): raise ports.ConnectionError('modified_ports')
    specs = cg.detect_ports(obj.data)
    obj[ports.PORTS] = json.dumps(specs)
    ports.ensure_identity(obj)
    try:
        obj[PATH]=json.dumps(cg.infer_recipe(obj.data,ports.local_ports(obj)))
    except ValueError:
        pass
    return len(specs)


def update_bridges(context, use_settings=False):
    active = context.active_object
    group = ports.members(context.scene, active)
    settings = context.scene.line_pipe_connections
    records = [r for r in settings.links if r.mode == 'BRIDGE' and
               (r.connector == active if use_settings else r.source in group or r.target in group)]
    staged = []
    try:
        for record in records:
            if not record.source or not record.target or not record.connector:
                raise ports.ConnectionError('missing_port')
            obj = record.connector
            ports.editable([obj])
            a = ports.read(context.scene, record.source, record.source_port, False)
            b = ports.read(context.scene, record.target, record.target_port, False)
            ports.compatible(a, b)
            if a.sides != b.sides:
                raise ports.ConnectionError('side_mismatch', moving=a.sides, anchor=b.sides)
            prior = recipe_for(obj)
            scale = uniform_scale(obj)
            radius = settings.radius if use_settings else prior['radius'] * scale
            smooth = settings.smooth if use_settings else prior['smooth']
            distance = settings.distance if use_settings else record.max_distance
            recipe = bridge_recipe(context.scene, a, b, radius, smooth, distance)
            inverse = obj.matrix_world.inverted()
            recipe['points'] = [list(inverse @ Vector(p)) for p in recipe['points']]
            for key in ('start_radial', 'end_radial', 'start_inner', 'end_inner'):
                if key in recipe:
                    recipe[key] = list((inverse.to_3x3() @ Vector(recipe[key])).normalized())
            recipe.update(diameter=recipe['diameter']/scale, bore=recipe['bore']/scale, radius=radius/scale)
            block = cg.mesh_from_recipe(recipe)
            apply_materials(block, obj.data)
            staged.append((record, recipe, block, radius, distance))
    except Exception:
        for _, _, block, _, _ in staged: discard(block)
        raise
    for record, recipe, block, radius, distance in staged:
        obj = record.connector
        old = swap_data(obj, block)
        store_path(obj, recipe)
        record.radius, record.smooth, record.max_distance, record.sides = radius, recipe['smooth'], distance, recipe['sides']
        discard(old)
    context.view_layer.update()
    return len(staged)
