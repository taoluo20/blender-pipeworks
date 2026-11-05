# SPDX-License-Identifier: GPL-3.0-or-later
"""One parameter editor for the exact viewport/list selection and generated bridges."""
import json
from types import SimpleNamespace
import bpy
from bpy.props import BoolProperty, EnumProperty, FloatProperty, IntProperty, StringProperty
from mathutils import Vector
from . import connections, connection_geometry as cg, data, geometry, i18n, ports
from .model import bend_floor

FIELDS = (*data.DIMENSIONS, *data.PROFILE, 'free_sides', 'route_length')
_editor_signatures = {}


def targets(context):
    return sorted((obj for obj in context.selected_objects if ports.is_pipe(obj)), key=lambda obj: obj.name)


def supported(obj):
    return bool(obj and not obj.get(ports.CUSTOM) and (obj.get('line_pipe_route_v1') or obj.get(connections.PATH)))


def recipe(obj):
    if not supported(obj):
        raise ports.ConnectionError('edited_recipe')
    if obj.get('line_pipe_route_v1'):
        state = obj.line_pipe
        return dict(kind='ORTHOGONAL', points=json.loads(obj['line_pipe_route_v1']), smooth=True,
                    diameter=state.diameter, radius=state.bend_radius, sides=state.radial_segments,
                    steps=state.bend_steps, bore=data.bore(state),
                    **json.loads(obj.get(geometry.SWEEP_FRAMES, '{}')))
    return json.loads(obj[connections.PATH])


def values(obj):
    current = recipe(obj)
    scale = connections.uniform_scale(obj)
    diameter, bore = current['diameter'], current.get('bore', 0)
    profile = json.loads(obj.get('_pipeworks_wall_values', 'null'))
    if profile is None:
        profile = [bore > 0, 'FREE', (diameter-bore)/2 if bore else .02, '10']
    return dict(diameter=diameter*scale, bend_radius=current['radius']*scale,
                radial_segments=current['sides'], bend_steps=current.get('steps', 16),
                hollow=profile[0], wall_mode=profile[1], wall=profile[2]*scale, wall_preset=profile[3],
                free_sides=obj.line_pipe.free_sides or current['sides'] not in ports.STANDARD_SIDES,
                route_length=geometry.centerline_length([Vector(p) for p in current['points']])*scale)


def reference(context):
    selected = targets(context)
    return next((obj for obj in selected if obj == context.active_object and supported(obj)),
                next((obj for obj in selected if supported(obj)), None))


def planned_port(scene, obj, key, recipes):
    current = ports.read(scene, obj, key, False)
    if obj not in recipes:
        return current
    changed = recipes[obj]
    local = ports.local_ports(obj)
    index = next(i for i, spec in enumerate(local) if spec['key'] == key)
    centers, tangents, _ = cg.samples(changed)
    end = 0 if index == 0 else -1
    scale = connections.uniform_scale(obj)
    current.position = obj.matrix_world @ centers[end]
    current.direction = (obj.matrix_world.to_3x3() @ (-tangents[end] if index == 0 else tangents[end])).normalized()
    current.diameter = changed['diameter']*scale
    current.bore = changed.get('bore', 0)*scale
    current.sides = changed['sides']
    return current


def same_profile(a, b):
    return (abs(a.diameter-b.diameter) < max(a.diameter, b.diameter)*1e-4
            and (not a.bore or not b.bore or abs(a.bore-b.bore) < max(a.diameter, b.diameter)*1e-4)
            and a.sides == b.sides)


def update_objects(context, selected, changes):
    selected = list(dict.fromkeys(selected))
    if not selected:
        raise ports.ConnectionError('groups_choose_rows')
    if set(changes)-set(FIELDS):
        raise ValueError('Unknown pipe parameter')
    ports.editable(selected)
    recipes, settings = {}, {}
    for obj in selected:
        prior = recipe(obj)
        if obj.get('line_pipe_route_v1'):
            intact = geometry.editable_route(obj)
        else:
            intact = (obj.type == 'MESH' and not obj.data.shape_keys
                      and not any(mod.show_viewport for mod in obj.modifiers)
                      and geometry.generated_mesh_intact(obj))
            if intact and not obj.get(geometry.MESH_SIGNATURE):
                expected = cg.mesh_from_recipe(prior)
                try:
                    intact = geometry.mesh_signature(obj.data) == geometry.mesh_signature(expected)
                finally:
                    connections.discard(expected)
        if not intact:
            raise ports.ConnectionError('edited_recipe')
        scale = connections.uniform_scale(obj)
        desired = dict(values(obj), **changes)
        local = dict(desired, diameter=desired['diameter']/scale,
                     bend_radius=desired['bend_radius']/scale, wall=desired['wall']/scale)
        bore = data.bore(SimpleNamespace(**local))
        if local['bend_radius'] < bend_floor(local['diameter']):
            raise ports.ConnectionError('bad_radius')
        if obj.type == 'CURVE' and bore:
            raise ports.ConnectionError('hollow_bake_first')
        changed = dict(prior, diameter=local['diameter'], radius=local['bend_radius'],
                       sides=local['radial_segments'], steps=local['bend_steps'], bore=bore)
        if 'route_length' in changes:
            specs = ports.local_ports(obj)
            used = [p.get('occupied') or ports.occupied(context.scene, obj, p['key']) for p in specs]
            if all(used):
                raise ports.ConnectionError('length_both_ports')
            points = [Vector(p) for p in changed['points']]
            pivot = points[-1] if used[-1] else points[0]
            factor = desired['route_length']/scale/geometry.centerline_length(points)
            changed['points'] = [list(pivot+(point-pivot)*factor) for point in points]
        recipes[obj], settings[obj] = changed, local
    links = context.scene.line_pipe_connections.links
    for link in links:
        related = {link.source, link.target, link.connector}
        if not related.intersection(recipes):
            continue
        a = planned_port(context.scene, link.source, link.source_port, recipes)
        b = planned_port(context.scene, link.target, link.target_port, recipes)
        # Existing solid-to-hollow connections remain valid unless their profile changes.
        profile_changed = any(obj in recipes and any(
            abs(recipe(obj).get(key, 0)-recipes[obj].get(key, 0)) > 1e-8
            for key in ('diameter', 'bore', 'sides')) for obj in related if obj)
        if profile_changed:
            profiles = [a, b]
            if link.connector:
                profiles.extend(planned_port(context.scene, link.connector, key, recipes)
                                for key in ('START', 'END'))
            if any(not same_profile(profiles[0], port) for port in profiles[1:]):
                raise ports.ConnectionError('edit_connected_profile')
        if link.connector in recipes and set(changes) != {'free_sides'}:
            obj = link.connector
            scale = connections.uniform_scale(obj)
            prior = recipes[obj]
            generated = connections.bridge_recipe(context.scene, a, b, prior['radius']*scale,
                                                   prior.get('smooth', True), link.max_distance)
            inverse = obj.matrix_world.inverted()
            generated['points'] = [list(inverse @ Vector(p)) for p in generated['points']]
            for key in ('start_radial', 'end_radial', 'start_inner', 'end_inner'):
                if key in generated:
                    generated[key] = list((inverse.to_3x3() @ Vector(generated[key])).normalized())
            generated.update(diameter=generated['diameter']/scale, bore=generated['bore']/scale,
                             radius=prior['radius'], steps=prior.get('steps', 16))
            recipes[obj] = generated
    staged = []
    try:
        if set(changes) != {'free_sides'}:
            for obj, changed in recipes.items():
                staged.append((obj, changed, connections.stage_recipe(obj, changed)))
    except Exception:
        for _, _, block in staged:
            connections.discard(block)
        raise
    for obj, changed, block in staged:
        old = connections.swap_data(obj, block)
        if obj.type == 'CURVE':
            geometry.set_sweep_profile(obj, changed['diameter'], changed['sides'])
        if obj.get('line_pipe_route_v1'):
            geometry.store_route(obj, [Vector(p) for p in changed['points']], changed['diameter'], changed['sides'], changed['bore'])
        else:
            connections.store_path(obj, changed)
        if obj.type == 'MESH':
            geometry.remember_mesh(obj)
        connections.discard(old)
        obj.update_tag()
    for obj, local in settings.items():
        changed = recipes[obj]
        data.store_parameters(obj, changed['diameter'], changed['radius'], changed['sides'], changed.get('steps', 16),
                              [local[key] for key in data.PROFILE], local['free_sides'])
    for link in links:
        if link.connector in recipes:
            changed = recipes[link.connector]
            link.radius = changed['radius']*connections.uniform_scale(link.connector)
            link.smooth, link.sides = changed.get('smooth', True), changed['sides']
        elif link.source in recipes:
            link.sides = recipes[link.source]['sides']
    context.view_layer.update()
    return len(selected)


class PW_EditSettings(bpy.types.PropertyGroup):
    error: StringProperty(options={'HIDDEN', 'SKIP_SAVE'})
    syncing: BoolProperty(options={'HIDDEN', 'SKIP_SAVE'})


def sync_editor(context, force=False):
    if not hasattr(context.scene, 'line_pipe_edit'):
        return
    editor = context.scene.line_pipe_edit
    if editor.syncing:
        return
    obj = reference(context)
    if obj is None:
        return
    current = values(obj)
    signature = (tuple(o.as_pointer() for o in targets(context)), obj.as_pointer(), tuple(current.items()))
    key = context.scene.as_pointer()
    if not force and _editor_signatures.get(key) == signature:
        return
    editor.syncing = True
    try:
        for field, value in current.items():
            setattr(editor, field, value)
            setattr(editor, field + '_zh', value)
        _editor_signatures[key] = signature
    finally:
        editor.syncing = False


def parameter_changed(key, alias=False):
    def update(self, context):
        if self.syncing:
            return
        try:
            update_objects(context, targets(context), {key: getattr(self, key + ('_zh' if alias else ''))})
            self.error = ''
        except ValueError as error:
            self.error = str(error) if str(error) in i18n.MESSAGES else 'fit'
        sync_editor(context, force=True)
    return update


definitions = dict(data.dimensions(), **data.profile())
definitions['route_length'] = FloatProperty(
    name='Route Length', description=i18n.text('route_length_tip', 'EN'), unit='LENGTH', subtype='DISTANCE',
    min=.000001, default=1.)
for key, definition in definitions.items():
    for language, suffix in (('EN', ''), ('ZH', '_zh')):
        kwargs = dict(definition.keywords, update=parameter_changed(key, language == 'ZH'))
        kwargs['name'] = i18n.text(key, language)
        kwargs['description'] = i18n.text(dict(data.tips, route_length='route_length_tip')[key], language)
        if definition.function in {FloatProperty, IntProperty}:
            kwargs['description'] += ' ' + i18n.text('edit_drag_tip', language)
        if definition.function == EnumProperty:
            kwargs['items'] = [(item[0], i18n.text(item[3], language) if len(item) > 3 else item[1],
                                i18n.text(item[3], language) if len(item) > 3 else item[2]) for item in kwargs['items']]
        PW_EditSettings.__annotations__[key + suffix] = definition.function(**kwargs)


def draw(layout, context):
    from . import connection_ops, groups
    selected = targets(context)
    groups.request_refresh(context.scene)
    if not selected:
        return
    editor = context.scene.line_pipe_edit
    layout.use_property_split = True
    layout.use_property_decorate = False
    layout.label(text=i18n.tr('edit_count', context, count=len(selected)), icon='RESTRICT_SELECT_OFF')
    unsupported = [obj for obj in selected if not supported(obj)]
    if unsupported:
        layout.label(text=i18n.tr('edited_recipe', context), icon='ERROR')
        return
    col = layout.column()
    col.enabled = connection_ops.ready(context) and groups._drag is None and groups._box is None
    try:
        rows = [values(obj) for obj in selected]
        mixed = any(any(row[key] != rows[0][key] for key in data.DIMENSIONS) for row in rows[1:])
        col.label(text=i18n.tr('edit_mixed', context) if mixed else '', icon='DOT' if mixed else 'NONE')
        for key in ('diameter', 'bend_radius', 'bend_steps'):
            i18n.prop(col, editor, key, context, slider=True)
        data.sides_menu(col, editor, context, slider=True)
        if all(obj.type == 'MESH' for obj in selected):
            i18n.prop(col, editor, 'hollow', context)
            if editor.hollow:
                i18n.prop(col, editor, 'wall_mode', context)
                if editor.wall_mode == 'FREE':
                    i18n.prop(col, editor, 'wall', context, slider=True)
                else:
                    i18n.prop(col, editor, 'wall_preset', context)
        i18n.prop(col, editor, 'route_length', context)
        if editor.error:
            col.label(text=i18n.tr(editor.error, context), icon='ERROR')
        if any(obj.type == 'CURVE' for obj in selected):
            col.operator('line_pipe.selection_mesh', text=i18n.tr('mesh', context), icon='MESH_DATA')
    except ValueError as error:
        col.label(text=i18n.tr(str(error) if str(error) in i18n.MESSAGES else 'fit', context), icon='ERROR')


class PW_OT_selection_mesh(bpy.types.Operator):
    bl_idname = 'line_pipe.selection_mesh'
    bl_label = 'Convert Selected Pipes to Mesh'
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def description(cls, context, properties):
        return i18n.tr('edit_mesh_tip', context)

    def execute(self, context):
        selected = targets(context)
        curves = [obj for obj in selected if obj.type == 'CURVE']
        try:
            if not curves or any(not geometry.editable_route(obj) for obj in curves):
                raise ports.ConnectionError('edited_recipe')
            ports.editable(curves)
            active = context.active_object
            with context.temp_override(object=curves[0], active_object=curves[0],
                                       selected_objects=curves, selected_editable_objects=curves):
                bpy.ops.object.convert(target='MESH')
            for obj in curves:
                geometry.remember_mesh(obj)
                obj.line_pipe.enabled = False
            if active and active.name in context.view_layer.objects:
                context.view_layer.objects.active = active
            return {'FINISHED'}
        except ValueError as error:
            from . import connection_ops
            return connection_ops.failure(self, context, error)


def abort():
    _editor_signatures.clear()


CLASSES = (PW_EditSettings, PW_OT_selection_mesh)
