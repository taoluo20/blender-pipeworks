# SPDX-License-Identifier: GPL-3.0-or-later
"""One endpoint contract for drawn curves, converted meshes and Pipe Assembly files."""
import json
import math
import uuid
from dataclasses import dataclass
from mathutils import Vector
from . import port_rings

UID = '_pipeworks_uid_v1'
GROUP = '_pipeworks_group_v1'
PORTS = '_pipeworks_ports_v1'
CUSTOM = '_pipeworks_custom_ports_v1'
LIBRARY_ASSET = '_pipeworks_library_asset_v1'
DISABLED = '_pipeworks_disabled_ports_v1'
STANDARD_SIDES = (6, 12, 24, 36, 48, 60, 72, 144, 288, 576)
DEFAULT_SIDES = 60
MAX_SIDES = 100000


class ConnectionError(ValueError):
    def __init__(self, key, **details):
        super().__init__(key)
        self.details = details


def value(data, key, default=None):
    if data is None:
        return default
    try:
        return getattr(data, key)
    except AttributeError:
        return data.get(key, default)


def legacy(obj):
    data = getattr(obj, 'pipe_component', None) or obj.get('pipe_component')
    return data if value(data, 'enabled', False) else None


def perpendicular(normal):
    n = Vector(normal).normalized()
    axis = min((Vector((1, 0, 0)), Vector((0, 1, 0)), Vector((0, 0, 1))), key=lambda a: abs(a.dot(n)))
    return (axis - n * axis.dot(n)).normalized()


def local_ports(obj):
    if not obj or obj.type not in {'MESH', 'CURVE'}:
        return []
    encoded = obj.get(CUSTOM) or obj.get('line_pipe_ports_v1') or obj.get(PORTS)
    if encoded:
        try:
            specs = json.loads(encoded)
        except (ValueError, TypeError):
            raise ConnectionError('invalid_ports')
    else:
        old = legacy(obj)
        specs = []
        for p in value(old, 'ports', ()):
            diameter = value(p, 'diameter', value(old, 'diameter', .2))
            wall = value(old, 'wall', 0)
            bore = value(p, 'inner_diameter', 0) or (max(0, diameter - 2 * wall) if wall > 0 else 0)
            specs.append(dict(key=value(p, 'key', ''), position=list(value(p, 'position', (0, 0, 0))),
                direction=list(value(p, 'direction', (0, 0, 1))), radial=list(value(p, 'radial', (1, 0, 0))),
                diameter=diameter, bore=bore, interface=value(p, 'interface', 'PLAIN'),
                occupied=value(p, 'occupied', False), sides=value(old, 'segments', 32)))
    disabled = set(json.loads(obj.get(DISABLED, '[]')))
    keys, result = set(), []
    for p in specs:
        try:
            p = dict(p)
            key, diameter = str(p['key']), float(p['diameter'])
            position, normal = Vector(p['position']), Vector(p['direction'])
            bore = float(p.get('bore', 0))
            if (not key or key in keys or not math.isfinite(diameter) or not 0 <= bore < diameter
                    or diameter <= 0 or normal.length < 1e-7
                    or not all(math.isfinite(v) for v in (*position, *normal))):
                raise ValueError()
            normal.normalize()
            radial = Vector(p.get('radial', perpendicular(normal)))
            radial = (radial - normal * radial.dot(normal)).normalized()
            if radial.length < .9:
                radial = perpendicular(normal)
            p.update(key=key, diameter=diameter, bore=bore, position=position, direction=normal, radial=radial)
            if 'inner_radial' in p:
                p['inner_radial'] = Vector(p['inner_radial']).normalized()
            p['sides'] = int(p.get('sides', obj.get('_line_pipe_dimensions', [0, 0, 32])[2]))
            if p['sides'] < 3:
                raise ValueError()
            p['enabled'] = p.get('enabled', True) and key not in disabled
            result.append(p)
            keys.add(key)
        except (KeyError, TypeError, ValueError):
            raise ConnectionError('invalid_ports')
    return result


def is_pipe(obj):
    try:
        return bool(local_ports(obj))
    except ConnectionError:
        return False


def group_id(obj):
    if obj.get(UID):
        import bpy
        owner = next((o for o in bpy.data.objects if o.get(UID) == obj[UID]), obj)
        if owner != obj:
            return 'copy:' + obj.name_full
    return obj.get(GROUP) or ('legacy:' + value(legacy(obj), 'group_id', '')
                              if value(legacy(obj), 'group_id', '') else obj.get(UID) or 'object:' + obj.name_full)


def members(scene, obj):
    if not obj or not is_pipe(obj):
        return []
    key = group_id(obj)
    return [o for o in scene.objects if is_pipe(o) and group_id(o) == key]


def ensure_identity(obj):
    import bpy
    current = obj.get(UID)
    duplicate = current and next((o for o in bpy.data.objects if o.get(UID) == current), obj) != obj
    if not current or duplicate:
        prior = group_id(obj)
        obj[UID] = uuid.uuid4().hex
        if not obj.get(GROUP):
            obj[GROUP] = prior if prior.startswith('legacy:') else obj[UID]
        elif duplicate:
            obj[GROUP] = obj[UID]
    return obj[UID]


@dataclass
class Port:
    obj: object
    key: str
    position: Vector
    direction: Vector
    radial: Vector
    diameter: float
    bore: float
    interface: str = 'PLAIN'
    legacy_occupied: bool = False
    sides: int = DEFAULT_SIDES
    enabled: bool = True
    inner_radial: Vector | None = None


def world_ports(obj, matrix=None):
    return [world_port(obj, spec, matrix) for spec in local_ports(obj)]


def world_port(obj, p, matrix=None):
    matrix = obj.matrix_world if matrix is None else matrix
    linear = matrix.to_3x3()
    if abs(linear.determinant()) < 1e-12:
        raise ConnectionError('singular_pipe')
    normals = linear.inverted().transposed()
    n, u = p['direction'], p['radial']
    u, v = linear @ u, linear @ n.cross(u)
    a, b, c = u.dot(u), u.dot(v), v.dot(v)
    spread = math.sqrt(max(0, (a - c) ** 2 + 4 * b * b))
    major, minor = math.sqrt(max(0, (a + c + spread) / 2)), math.sqrt(max(0, (a + c - spread) / 2))
    if major < 1e-8 or major - minor > major * 1e-4:
        raise ConnectionError('elliptical_pipe')
    inner = p.get('inner_radial', p['radial'])
    return Port(obj, p['key'], matrix @ p['position'], (normals @ n).normalized(), u.normalized(),
                p['diameter'] * major, p['bore'] * major, p.get('interface', 'PLAIN'),
                bool(p.get('occupied', False)), p['sides'], p['enabled'], (linear @ inner).normalized())


def measured(obj, spec, mesh=None):
    import bpy
    import bmesh
    evaluated = None
    if mesh is None:
        if obj.type == 'CURVE':
            evaluated = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
            mesh = evaluated.to_mesh()
        else:
            mesh = obj.data
    try:
        if 'tag' not in spec:
            profile = port_rings.mesh_plane_profile(mesh, spec)
        else:
            bm = bmesh.new()
            try:
                bm.from_mesh(mesh)
                layer = bm.edges.layers.int.get(port_rings.TAG)
                if layer is None:
                    raise ValueError('invalid_ring')
                profile = port_rings.profile([edge for edge in bm.edges if edge[layer] == spec['tag']])
            finally:
                bm.free()
        return dict(spec, **profile)
    except ValueError as error:
        raise ConnectionError('invalid_ring') from error
    finally:
        if evaluated is not None:
            evaluated.to_mesh_clear()


def occupied(scene, obj, key):
    settings = getattr(scene, 'line_pipe_connections', None)
    return bool(settings and any((r.source == obj and r.source_port == key or
                                 r.target == obj and r.target_port == key or
                                 r.connector == obj and key in {'START', 'END'})
                                and r.source and r.target for r in settings.links))


def read(scene, obj, key, free=True):
    if not is_pipe(obj):
        raise ConnectionError('choose_pipe')
    for modifier in obj.modifiers:
        if modifier.show_viewport and not (modifier.type == 'NODES' and modifier.node_group
                                           and modifier.node_group.get('line_pipe_solid_sweep_v1')):
            raise ConnectionError('modified_ports')
    if obj.type == 'MESH' and obj.data.shape_keys and any(abs(k.value) > 1e-7 for k in obj.data.shape_keys.key_blocks[1:]):
        raise ConnectionError('modified_ports')
    specs = local_ports(obj)
    spec = next((p for p in specs if p['key'] == key), None)
    if spec is None:
        raise ConnectionError('missing_port')
    if not spec['enabled']:
        raise ConnectionError('disabled_port')
    if obj.type == 'MESH':
        from . import connection_geometry as cg
        diameter = min(p['diameter'] for p in specs)
        if obj.get(CUSTOM):
            import bmesh
            bm = bmesh.new()
            try:
                bm.from_mesh(obj.data)
                bad = any(len(edge.link_faces) not in {1, 2} for edge in bm.edges)
            finally:
                bm.free()
        else:
            report = cg.topology(obj.data)
            bad = report['nonmanifold'] or report['volume'] <= 0
        if bad or cg.tiny_triangles(obj.data, diameter):
            raise ConnectionError('bad_existing_mesh')
    found = world_port(obj, measured(obj, spec))
    if free and (found.legacy_occupied or occupied(scene, obj, key)):
        raise ConnectionError('occupied_port')
    return found


def compatible(a, b):
    if a.obj == b.obj:
        raise ConnectionError('same_pipe')
    if abs(a.diameter - b.diameter) > max(a.diameter, b.diameter) * 1e-4:
        raise ConnectionError('different_diameter')
    if (a.bore > 0 and b.bore > 0 and abs(a.bore - b.bore) > max(a.diameter,b.diameter)*1e-4) or a.interface != b.interface:
        raise ConnectionError('different_profile')


def editable(objects):
    for obj in objects:
        if (obj.library or obj.data.library or obj.mode != 'OBJECT' or obj.hide_select
                or any(not c.mute and c.influence > 0 for c in obj.constraints)):
            raise ConnectionError('pipe_not_editable')
        if obj.parent:
            m = obj.parent.matrix_world.to_3x3()
            sizes = [c.length for c in m.col]
            if max(sizes) - min(sizes) > max(sizes) * 1e-5:
                raise ConnectionError('nonuniform_parent')
