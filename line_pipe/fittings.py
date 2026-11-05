# SPDX-License-Identifier: GPL-3.0-or-later
"""Mesh port authoring and portable, local fitting assets."""
from contextlib import contextmanager
import json
import math
from pathlib import Path
import uuid

import bmesh
import bpy
import gpu
from bpy.props import BoolProperty, EnumProperty, StringProperty
from bpy_extras import view3d_utils
from bpy_extras.io_utils import ExportHelper, ImportHelper
from mathutils import Vector
from . import connection_ops, connections, data, geometry, i18n, operators, port_rings, ports
from .model import bend_floor

ASSET = ports.LIBRARY_ASSET
TEMPLATES = {
    'CYLINDER': ('PipeWorks Cylinder', 'continuation_cylinder'),
    'ELBOW': ('PipeWorks Elbow', 'continuation_elbow'),
}
_overlay = None


def encoded(spec):
    return {key: list(value) if isinstance(value, Vector) else value for key, value in spec.items()}


def mark_ports(context, selected=False):
    obj = context.active_object
    geometry.require_free_profile(obj, context.scene)
    if obj.library or obj.data.library or any(mod.show_viewport for mod in obj.modifiers):
        raise ports.ConnectionError('modified_ports')
    edit_mode = obj.mode == 'EDIT'
    if edit_mode and obj.data.users > 1:
        raise ports.ConnectionError('shared_port_mesh')
    bm = bmesh.from_edit_mesh(obj.data) if edit_mode else bmesh.new()
    try:
        if not edit_mode:
            bm.from_mesh(obj.data)
        candidates = port_rings.scan(bm)
        if selected:
            selected_loops = [set(ring) for _, ring in port_rings.loops(
                [edge for edge in bm.edges if edge.select and not edge.hide])]
            if not selected_loops:
                raise ports.ConnectionError('select_ring')
            chosen = {}
            for ring in selected_loops:
                profile, edges = next(((spec, edges) for spec, edges in candidates if ring <= edges),
                                      (None, None))
                if profile is None:
                    profile, edges = port_rings.profile(ring), ring
                chosen[frozenset(edges)] = (profile, edges)
            candidates = list(chosen.values())
        if not candidates:
            raise ports.ConnectionError('no_mesh_ports')

        stored = ports.local_ports(obj)
        matched = set()
        layer = bm.edges.layers.int.get(port_rings.TAG)
        next_id = max((p.get('tag', 0) for p in stored), default=0) + 1
        updates = []
        for spec, edges in candidates:
            tags = {edge[layer] for edge in edges if edge[layer]} if layer else set()
            match = next((p for p in stored if p.get('tag') in tags), None)
            if match is None:
                match = next((p for p in stored if
                              (p['position'] - spec['position']).length < spec['diameter'] * 1e-4
                              and p['direction'].dot(spec['direction']) > .999), None)
            if match is not None and match['key'] in matched:
                raise ports.ConnectionError('invalid_ring')
            if match is not None:
                matched.add(match['key'])
            tag = match.get('tag') if match else None
            if tag is None:
                tag = next_id
                next_id += 1
            names = {p['key'] for p in stored} | {p['key'] for p, _ in updates}
            key = match['key'] if match else next(f'P{i}' for i in range(1, len(names) + 2) if f'P{i}' not in names)
            enabled = True
            updates.append((dict(spec, key=key, tag=tag, enabled=enabled), edges))

        bm.edges.index_update()
        indexed = [(spec, [edge.index for edge in edges]) for spec, edges in updates]
        if layer is None:
            layer = bm.edges.layers.int.new(port_rings.TAG)
        bm.edges.ensure_lookup_table()
        changed_tags = {spec['tag'] for spec, _ in indexed}
        for edge in bm.edges:
            if edge[layer] in changed_tags:
                edge[layer] = 0
        for spec, indices in indexed:
            tag = spec['tag']
            for index in indices:
                bm.edges[index][layer] = tag
        if edit_mode:
            bmesh.update_edit_mesh(obj.data, loop_triangles=False, destructive=False)
        else:
            mesh = obj.data.copy() if obj.data.users > 1 else obj.data
            bm.to_mesh(mesh)
            if mesh != obj.data:
                connections.swap_data(obj, mesh)
            mesh.update()
        profiles = {p['key']: p for p in stored}
        profiles.update((p['key'], p) for p, _ in updates)
        obj[ports.CUSTOM] = json.dumps([encoded(dict(p, enabled=True)) for p in profiles.values()])
        ports.ensure_identity(obj)
        obj.update_tag()
        return len(updates)
    finally:
        if not edit_mode:
            bm.free()


def select_object(context, obj):
    for selected in context.selected_objects:
        selected.select_set(False)
    obj.select_set(True)
    context.view_layer.objects.active = obj


def template_recipe(settings, shape):
    length = settings.template_length
    points = [(0, 0, 0), (0, 0, length)]
    if shape == 'ELBOW':
        points.append((length, 0, length))
    return dict(points=points, diameter=settings.diameter, radius=settings.bend_radius,
                sides=data.generation_sides(settings), steps=settings.bend_steps)


def generated_fitting(context, name, recipe, origin, bore, wall_profile, free_sides, material_source=None):
    obj = geometry.create(context, mesh=True)
    obj.name = name
    try:
        points = [Vector(p) + origin for p in recipe['points']]
        dimensions = tuple(recipe[key] for key in ('diameter', 'radius', 'sides', 'steps'))
        data.store_parameters(obj, *dimensions, wall_profile, free_sides)
        geometry.update(obj, points, *dimensions, store=True, bore=bore)
        if material_source is not None:
            connections.apply_materials(obj.data, material_source.data)
            for slot, source_slot in zip(obj.material_slots, material_source.material_slots):
                slot.link, slot.material = source_slot.link, source_slot.material
        return obj
    except Exception:
        geometry.remove(obj)
        raise


def create_fitting(context, shape):
    settings = context.scene.line_pipe_settings
    obj = generated_fitting(context, TEMPLATES[shape][0], template_recipe(settings, shape),
                            context.scene.cursor.location, data.bore(settings),
                            [getattr(settings, key) for key in data.PROFILE], settings.free_sides)
    select_object(context, obj)
    return obj


def continuation_keys(obj):
    keys = tuple(p['key'] for p in ports.local_ports(obj) if p['enabled'])
    if len(keys) != 2:
        raise ports.ConnectionError('continuation_fixed')
    return ('START', 'END') if set(keys) == {'START', 'END'} else keys


def asset_info(context, obj):
    if not ports.is_pipe(obj):
        raise ports.ConnectionError('choose_pipe')
    entries = []
    for spec in ports.local_ports(obj):
        if not spec['enabled']:
            continue
        # Inspect actual counts, including assets with mixed or custom counts.
        port = ports.read(context.scene, obj, spec['key'], free=False)
        entries.append(dict(key=port.key, sides=port.sides, diameter=port.diameter, bore=port.bore))
    if not entries:
        raise ports.ConnectionError('no_enabled_ports')
    return dict(name=obj.name, ports=entries, procedural=geometry.editable_route(obj))


def library_dir():
    return Path(bpy.utils.user_resource('CONFIG')) / 'pipeworks-library'


def library_entries():
    for path in sorted(library_dir().glob('*.json')):
        try:
            item = json.loads(path.read_text(encoding='utf8'))
            if (isinstance(item['name'], str) and item['name'] and item['ports']
                    and path.with_suffix('.blend').is_file()):
                yield path.stem, item
        except (OSError, ValueError, TypeError, KeyError):
            continue


def library_families():
    entries = dict(library_entries())
    families = {}
    for identifier, item in entries.items():
        family = item.get('family')
        if not isinstance(family, str) or family not in entries:
            family = identifier
        families.setdefault(family, {})[identifier] = item
    return {family: (entries[family]['name'], variants) for family, variants in families.items()}


def counts_for(item):
    return sorted({port['sides'] for port in item['ports']})


def continuation_name(identifier, context):
    if identifier in TEMPLATES:
        return i18n.tr(TEMPLATES[identifier][1], context)
    try:
        path = library_dir() / (uuid.UUID(hex=identifier).hex + '.json')
        return json.loads(path.read_text(encoding='utf8'))['name']
    except (OSError, ValueError, TypeError, KeyError):
        return i18n.tr('continuation_unavailable', context)


def write_asset(context, obj, filepath):
    info = asset_info(context, obj)
    filepath = Path(filepath)
    clone = obj.copy()
    try:
        clone.parent = None
        clone.use_fake_user = False
        clone.constraints.clear()
        clone.animation_data_clear()
        clone.matrix_world = obj.matrix_world
        for key in (ports.UID, ports.GROUP, '_pipeworks_link_v1'):
            if key in clone:
                del clone[key]
        clone[ASSET] = json.dumps(info)
        # Atomic file replacement also avoids stale .blend1 files in the library.
        temporary = filepath.with_name(f'.{uuid.uuid4().hex}.blend')
        try:
            bpy.data.libraries.write(str(temporary), {clone}, path_remap='ABSOLUTE', compress=True)
            temporary.replace(filepath)
        finally:
            temporary.unlink(missing_ok=True)
    finally:
        bpy.data.objects.remove(clone)
    return info


def add_to_library(context, obj, family=''):
    if family:
        existing = library_families().get(family)
        if not existing:
            raise ports.ConnectionError('continuation_missing')
        counts = counts_for(asset_info(context, obj))
        variants = existing[1]
        if len(counts) != 1 or any(len(counts_for(item)) != 1 for item in variants.values()):
            raise ports.ConnectionError('variant_uniform')
        if any(counts == counts_for(item) for item in variants.values()):
            raise ports.ConnectionError('variant_duplicate', count=counts[0])
    root = library_dir()
    root.mkdir(parents=True, exist_ok=True)
    identifier = uuid.uuid4().hex
    asset_path = root / (identifier + '.blend')
    metadata = root / (identifier + '.json')
    temp = metadata.with_suffix('.tmp')
    try:
        info = write_asset(context, obj, asset_path)
        if family:
            info['family'] = family
        temp.write_text(json.dumps(info, ensure_ascii=False), encoding='utf8')
        temp.replace(metadata)
    except Exception:
        asset_path.unlink(missing_ok=True)
        raise
    finally:
        temp.unlink(missing_ok=True)
    return identifier


@contextmanager
def loaded_asset(filepath):
    with bpy.data.libraries.load(str(filepath), link=False) as (available, output):
        if len(available.objects) != 1:
            raise ports.ConnectionError('invalid_asset')
        output.objects = list(available.objects)
    obj = output.objects[0]
    if obj is None:
        raise ports.ConnectionError('invalid_asset')
    try:
        if ASSET not in obj or not ports.is_pipe(obj):
            raise ports.ConnectionError('invalid_asset')
        yield obj
    finally:
        if not obj.users_collection:
            geometry.remove(obj)


def fitted_continuation(context, identifier, diameter, bore, sides):
    def fitted(name, recipe, material_source=None):
        points = [Vector(p) for p in recipe['points']]
        scale = diameter / recipe['diameter']
        recipe = dict(recipe, points=[(p - points[0]) * scale for p in points], diameter=diameter,
                      sides=sides, radius=max(bend_floor(diameter), recipe['radius'] * scale))
        profile = (bool(bore), 'FREE', (diameter - bore) / 2 if bore else .02, '10')
        return generated_fitting(context, name, recipe, Vector((0, 0, 0)), bore, profile,
                                 sides not in ports.STANDARD_SIDES, material_source)

    if identifier in TEMPLATES:
        return fitted(TEMPLATES[identifier][0], template_recipe(context.scene.line_pipe_settings, identifier))
    family = next((entry for key, entry in library_families().items() if identifier in entry[1]), None)
    if family is None:
        raise ports.ConnectionError('continuation_missing')
    _, variants = family
    available = {counts_for(item)[0]: key for key, item in variants.items()
                 if len(item['ports']) == 2 and len(counts_for(item)) == 1}
    if not available:
        raise ports.ConnectionError('continuation_fixed')
    if sides not in available:
        raise ports.ConnectionError('continuation_variant_missing', count=sides,
                                    counts=', '.join(map(str, sorted(available))))
    path = library_dir() / (available[sides] + '.blend')
    with loaded_asset(path) as asset:
        keys = continuation_keys(asset)
        context.collection.objects.link(asset)
        keep = False
        try:
            context.view_layer.update()
            inlet, outlet = (ports.read(context.scene, asset, key) for key in keys)
            for port in (inlet, outlet):
                if port.sides != sides:
                    raise ports.ConnectionError('library_side_mismatch', moving=port.sides, anchor=sides)
            if geometry.editable_route(asset):
                obj = fitted(json.loads(asset[ASSET]).get('name', asset.name), connections.recipe_for(asset), asset)
                obj[ASSET] = asset[ASSET]
                return obj
            scale = diameter / inlet.diameter
            tolerance = diameter * 1e-4
            if (abs(outlet.diameter * scale - diameter) > tolerance
                    or any(bool(port.bore) != bool(bore) or abs(port.bore * scale - bore) > tolerance
                           or port.interface != 'PLAIN' for port in (inlet, outlet))):
                raise ports.ConnectionError('continuation_profile')
            asset.scale *= scale
            ports.ensure_identity(asset)
            keep = True
            return asset
        finally:
            if not keep:
                context.collection.objects.unlink(asset)


class PW_OT_choose_continuation(bpy.types.Operator):
    bl_idname = 'line_pipe.choose_continuation'
    bl_label = 'Choose E Fitting'
    bl_options = {'UNDO'}
    identifier: StringProperty(options={'HIDDEN'})

    @classmethod
    def poll(cls, context):
        return connection_ops.ready(context)

    def execute(self, context):
        context.scene.line_pipe_settings.continuation_fitting = self.identifier
        return {'FINISHED'}


class PW_MT_continuation(bpy.types.Menu):
    bl_idname = 'PW_MT_continuation'
    bl_label = 'E Fitting'

    def draw(self, context):
        for key, (_, label) in TEMPLATES.items():
            self.layout.operator('line_pipe.choose_continuation', text=i18n.tr(label, context)).identifier = key
        for key, (name, variants) in library_families().items():
            counts = sorted({counts_for(item)[0] for item in variants.values()
                             if len(item['ports']) == 2 and len(counts_for(item)) == 1})
            if counts:
                label = f"{name} · {', '.join(map(str, counts))}"
                self.layout.operator('line_pipe.choose_continuation', text=label).identifier = key


def draw_continuation(layout, context):
    row = layout.row(align=True)
    row.label(text=i18n.tr('continuation_fitting', context))
    identifier = context.scene.line_pipe_settings.continuation_fitting
    row.menu('PW_MT_continuation', text=continuation_name(identifier, context))


class PW_OT_mark_ports(bpy.types.Operator):
    bl_idname = 'line_pipe.mark_ports'
    bl_label = 'Mark Pipe Ports'
    bl_options = {'UNDO'}
    selected: BoolProperty(options={'HIDDEN'})

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return (obj and obj.type == 'MESH' and context.mode in {'OBJECT', 'EDIT_MESH'}
                and operators.session is None and connection_ops.picker is None and connection_ops.preview is None)

    @classmethod
    def description(cls, context, properties):
        return i18n.tr('mark_selected_tip' if properties.selected else 'scan_ports_tip', context)

    def execute(self, context):
        try:
            if self.selected and context.mode != 'EDIT_MESH':
                raise ports.ConnectionError('select_ring')
            count = mark_ports(context, self.selected)
            self.report({'INFO'}, i18n.tr('conn_detect_done', context, count=count))
            return {'FINISHED'}
        except (ValueError, RuntimeError) as error:
            return connection_ops.failure(self, context, error)


class PW_OT_toggle_port(bpy.types.Operator):
    bl_idname = 'line_pipe.toggle_port'
    bl_label = 'Enable or Disable Pipe Port'
    bl_options = {'UNDO'}
    key: StringProperty(options={'HIDDEN'})

    @classmethod
    def description(cls, context, properties):
        return i18n.tr('toggle_port_tip', context)

    @classmethod
    def poll(cls, context):
        return connection_ops.ready(context) and ports.is_pipe(context.active_object)

    def execute(self, context):
        obj = context.active_object
        spec = next((p for p in ports.local_ports(obj) if p['key'] == self.key), None)
        if not spec:
            return {'CANCELLED'}
        if spec.get('occupied') or ports.occupied(context.scene, obj, self.key):
            return connection_ops.failure(self, context, ports.ConnectionError('occupied_port'))
        disabled = set(json.loads(obj.get(ports.DISABLED, '[]')))
        disabled.symmetric_difference_update({self.key})
        obj[ports.DISABLED] = json.dumps(sorted(disabled))
        return {'FINISHED'}


class PW_OT_make_fitting(bpy.types.Operator):
    bl_idname = 'line_pipe.make_fitting'
    bl_label = 'Generate Pipe Fitting'
    bl_options = {'UNDO'}
    shape: EnumProperty(items=[('CYLINDER', 'Cylinder', ''), ('ELBOW', 'Elbow', '')])

    @classmethod
    def poll(cls, context):
        return connection_ops.ready(context)

    @classmethod
    def description(cls, context, properties):
        return i18n.tr('make_fitting_tip', context)

    def execute(self, context):
        try:
            create_fitting(context, self.shape)
            return {'FINISHED'}
        except (ValueError, RuntimeError) as error:
            return connection_ops.failure(self, context, error)


class PW_OT_save_fitting(bpy.types.Operator):
    bl_idname = 'line_pipe.save_fitting'
    bl_label = 'Add Fitting to My Library'
    family: StringProperty(options={'HIDDEN'})

    @classmethod
    def description(cls, context, properties):
        return i18n.tr('save_variant_tip' if properties.family else 'save_fitting', context)

    @classmethod
    def poll(cls, context):
        return connection_ops.ready(context) and ports.is_pipe(context.active_object)

    def execute(self, context):
        try:
            add_to_library(context, context.active_object, self.family)
            self.report({'INFO'}, i18n.tr('asset_saved', context))
            return {'FINISHED'}
        except (ValueError, RuntimeError, OSError) as error:
            return connection_ops.failure(self, context, error)


class PW_OT_insert_fitting(bpy.types.Operator):
    bl_idname = 'line_pipe.insert_fitting'
    bl_label = 'Insert Library Fitting'
    bl_options = {'UNDO'}
    identifier: StringProperty(options={'HIDDEN'})

    @classmethod
    def poll(cls, context):
        return connection_ops.ready(context)

    def execute(self, context):
        try:
            identifier = uuid.UUID(hex=self.identifier).hex
            with loaded_asset(library_dir() / (identifier + '.blend')) as obj:
                context.collection.objects.link(obj)
                obj.location = context.scene.cursor.location
                ports.ensure_identity(obj)
                select_object(context, obj)
            return {'FINISHED'}
        except (ValueError, RuntimeError, OSError) as error:
            return connection_ops.failure(self, context, error)


class PW_OT_export_fitting(bpy.types.Operator, ExportHelper):
    bl_idname = 'line_pipe.export_fitting'
    bl_label = 'Export Shareable Fitting'
    filename_ext = '.blend'
    filter_glob: StringProperty(default='*.blend', options={'HIDDEN'})

    @classmethod
    def poll(cls, context):
        return PW_OT_save_fitting.poll(context)

    def execute(self, context):
        try:
            write_asset(context, context.active_object, self.filepath)
            return {'FINISHED'}
        except (ValueError, RuntimeError, OSError) as error:
            return connection_ops.failure(self, context, error)


class PW_OT_import_fitting(bpy.types.Operator, ImportHelper):
    bl_idname = 'line_pipe.import_fitting'
    bl_label = 'Import Fitting to My Library'
    filename_ext = '.blend'
    filter_glob: StringProperty(default='*.blend', options={'HIDDEN'})

    @classmethod
    def poll(cls, context):
        return connection_ops.ready(context)

    def execute(self, context):
        try:
            with loaded_asset(self.filepath) as obj:
                # Curves need an evaluated mesh to verify the real endpoint counts.
                context.collection.objects.link(obj)
                try:
                    context.view_layer.update()
                    add_to_library(context, obj)
                finally:
                    context.collection.objects.unlink(obj)
            self.report({'INFO'}, i18n.tr('asset_saved', context))
            return {'FINISHED'}
        except (ValueError, RuntimeError, OSError) as error:
            return connection_ops.failure(self, context, error)


class PW_OT_copy_fitting_prompt(bpy.types.Operator):
    bl_idname = 'line_pipe.copy_fitting_prompt'
    bl_label = 'Copy AI Fitting Prompt'

    def execute(self, context):
        context.window_manager.clipboard = i18n.tr('fitting_prompt', context, counts=', '.join(map(str, ports.STANDARD_SIDES)),
                                                   default=ports.DEFAULT_SIDES)
        self.report({'INFO'}, i18n.tr('fitting_prompt_copied', context))
        return {'FINISHED'}


def draw_ports(layout, context):
    layout.operator('line_pipe.make_fitting', text=i18n.tr('make_cylinder', context), icon='MESH_CYLINDER').shape = 'CYLINDER'
    obj = context.active_object
    if obj and obj.type == 'MESH':
        if context.mode == 'EDIT_MESH':
            layout.operator('line_pipe.mark_ports', text=i18n.tr('mark_selected', context)).selected = True
        else:
            layout.operator('line_pipe.mark_ports', text=i18n.tr('scan_ports', context), icon='VIEWZOOM')
            layout.label(text=i18n.tr('mark_in_edit', context))
    if ports.is_pipe(obj):
        for spec in ports.local_ports(obj):
            row = layout.row(align=True)
            row.label(text=f"{spec['key']} · {i18n.tr('edge_count', context, count=spec['sides'])}")
            op = row.operator('line_pipe.toggle_port', text='',
                              icon='CHECKBOX_HLT' if spec['enabled'] else 'CHECKBOX_DEHLT')
            op.key = spec['key']


def draw_library(layout, context):
    from .ui import dimensions
    settings = context.scene.line_pipe_settings
    box = layout.box()
    box.label(text=i18n.tr('builtin_fittings', context))
    row = box.row(align=True)
    row.operator('line_pipe.make_fitting', text=i18n.tr('make_cylinder', context)).shape = 'CYLINDER'
    row.operator('line_pipe.make_fitting', text=i18n.tr('make_elbow', context)).shape = 'ELBOW'
    draw_continuation(layout, context)
    header, panel = layout.panel('pipeworks_fitting_parameters', default_closed=True)
    header.label(text=i18n.tr('fitting_parameters', context))
    if panel:
        dimensions(panel, settings, context)
        i18n.prop(panel, settings, 'template_length', context)
    box = layout.box()
    box.label(text=i18n.tr('my_fittings', context))
    box.operator('line_pipe.copy_fitting_prompt', text=i18n.tr('copy_fitting_prompt', context), icon='COPYDOWN')
    box.operator('line_pipe.save_fitting', text=i18n.tr('save_fitting', context), icon='ADD')
    row = box.row(align=True)
    row.operator('line_pipe.export_fitting', text=i18n.tr('export_fitting', context))
    row.operator('line_pipe.import_fitting', text=i18n.tr('import_fitting', context))
    for family, (name, variants) in library_families().items():
        try:
            available = sorted(variants.items(), key=lambda entry: counts_for(entry[1]))
        except (TypeError, KeyError):
            continue
        entry = box.box()
        entry.label(text=name, icon='MESH_DATA')
        for identifier, item in available:
            counts = counts_for(item)
            label = (i18n.tr('edge_count', context, count=counts[0]) if len(counts) == 1 else
                     i18n.tr('asset_sizes', context, counts=', '.join(map(str, counts))))
            row = entry.row(align=True)
            row.operator('line_pipe.insert_fitting', text=label).identifier = identifier
            if item.get('procedural'):
                row.label(text=i18n.tr('procedural_fitting', context))
            if len(counts) > 1:
                for port in item['ports']:
                    entry.label(text=f"{port['key']} · {i18n.tr('edge_count', context, count=port['sides'])}")
        if all(len(counts_for(item)) == 1 for item in variants.values()):
            entry.operator('line_pipe.save_fitting', text=i18n.tr('save_variant', context), icon='ADD').family = family


def draw_port_overlay():
    context = bpy.context
    if not context.scene or not context.region_data:
        return
    if context.scene.line_pipe_settings.tool_mode != 'PORTS' or not ports.is_pipe(context.active_object):
        return
    try:
        entries = ports.world_ports(context.active_object)
    except ValueError:
        return
    gpu.state.blend_set('ALPHA')
    try:
        for port in entries:
            color = (0.25, .9, .75, 1) if port.enabled else (.45, .45, .45, .8)
            side = port.direction.cross(port.radial)
            points = []
            count = min(port.sides, 144)
            for index in range(count):
                angle = math.tau * index / count
                position = port.position + port.diameter / 2 * (math.cos(angle) * port.radial + math.sin(angle) * side)
                points.append(view3d_utils.location_3d_to_region_2d(context.region, context.region_data, position))
            segments = [point for a, b in zip(points, points[1:] + points[:1]) if a is not None and b is not None
                        for point in (a, b)]
            if segments:
                operators.lines(segments, color, 2)
            center = view3d_utils.location_3d_to_region_2d(context.region, context.region_data, port.position)
            if center is not None:
                operators.screen_text(f'{port.key} · {port.sides}', center, color)
    finally:
        gpu.state.line_width_set(1)
        gpu.state.blend_set('NONE')


def register_overlay():
    global _overlay
    if not bpy.app.background:
        _overlay = bpy.types.SpaceView3D.draw_handler_add(draw_port_overlay, (), 'WINDOW', 'POST_PIXEL')


def unregister_overlay():
    global _overlay
    if _overlay is not None:
        bpy.types.SpaceView3D.draw_handler_remove(_overlay, 'WINDOW')
        _overlay = None


CLASSES = (PW_OT_mark_ports, PW_OT_toggle_port, PW_OT_make_fitting, PW_OT_save_fitting,
           PW_OT_insert_fitting, PW_OT_export_fitting, PW_OT_import_fitting,
           PW_OT_choose_continuation, PW_MT_continuation, PW_OT_copy_fitting_prompt)
