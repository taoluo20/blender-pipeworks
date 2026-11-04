# SPDX-License-Identifier: GPL-3.0-or-later
import bpy
import uuid
import json
import math
import gpu
from bpy.props import BoolProperty, CollectionProperty, EnumProperty, FloatProperty, IntProperty, PointerProperty, StringProperty
from bpy_extras import view3d_utils
from mathutils import Vector
from . import ports, connections, i18n, operators

picker = None
preview = None
_enum_cache = {}


def endpoints(context):
    settings = context.scene.line_pipe_connections
    source = settings.source or context.active_object
    if not source or not settings.target:
        raise ports.ConnectionError('choose_endpoints')
    return source, settings.source_port, settings.target, settings.target_port


def operator_endpoints(operator, context):
    if operator.source_name:
        source, target = context.scene.objects.get(operator.source_name), context.scene.objects.get(operator.target_name)
        if not source or not target: raise ports.ConnectionError('choose_endpoints')
        return source, operator.source_key, target, operator.target_key
    values = endpoints(context)
    operator.source_name, operator.source_key = values[0].name, values[1]
    operator.target_name, operator.target_key = values[2].name, values[3]
    return values


def port_items(self, context, role):
    obj = getattr(self, role) or (context.active_object if context and role == 'source' else None)
    keys = tuple(p['key'] for p in ports.local_ports(obj)) if ports.is_pipe(obj) else ()
    language = i18n.language(context)
    cache_key = keys, language
    if cache_key not in _enum_cache:
        _enum_cache[cache_key] = [(key, i18n.tr('conn_start' if key == 'START' else 'conn_end', context)
                                 if key in {'START', 'END'} else key, key) for key in keys] or [('NONE', '-', '')]
    return _enum_cache[cache_key]


def source_items(self, context): return port_items(self, context, 'source')
def target_items(self, context): return port_items(self, context, 'target')


def pointer_changed(role, alias=False):
    def update(self, context):
        origin, dest = (role + '_zh', role) if alias else (role, role + '_zh')
        if getattr(self, dest) != getattr(self, origin): setattr(self, dest, getattr(self, origin))
    return update


class PW_Link(bpy.types.PropertyGroup):
    uid: StringProperty()
    source: PointerProperty(type=bpy.types.Object)
    source_port: StringProperty()
    target: PointerProperty(type=bpy.types.Object)
    target_port: StringProperty()
    connector: PointerProperty(type=bpy.types.Object)
    mode: StringProperty()
    roll: FloatProperty(subtype='ANGLE')
    radius: FloatProperty(default=.4)
    smooth: BoolProperty(default=True)
    max_distance: FloatProperty(default=5)
    sides: IntProperty(default=32)


class PW_ConnectionSettings(bpy.types.PropertyGroup):
    source: PointerProperty(type=bpy.types.Object, name='Moving Pipe', update=pointer_changed('source'))
    source_zh: PointerProperty(type=bpy.types.Object, name='移动管道', update=pointer_changed('source', True))
    target: PointerProperty(type=bpy.types.Object, name='Anchor Pipe', update=pointer_changed('target'))
    target_zh: PointerProperty(type=bpy.types.Object, name='固定管道', update=pointer_changed('target', True))
    source_port: EnumProperty(name='Moving Port', items=source_items)
    target_port: EnumProperty(name='Anchor Port', items=target_items)
    roll: FloatProperty(name='Roll', description='conn_roll_tip', subtype='ANGLE', default=0)
    distance: FloatProperty(name='Maximum Distance', description='conn_distance_tip', default=5, min=.001, unit='LENGTH')
    radius: FloatProperty(name='Bend Radius', description='conn_radius_tip', default=.4, min=.00001, unit='LENGTH')
    smooth: BoolProperty(name='Smooth Bends', description='conn_smooth_tip', default=True)
    sides: IntProperty(name='Radial Segments', description='sides_tip', default=32, min=3, max=ports.MAX_SIDES)
    mesh_axis: EnumProperty(name='Cylinder Axis', description='conn_axis_tip',
                           items=[(a,a,a) for a in 'XYZ'], default='Z')
    links: CollectionProperty(type=PW_Link)


def ready(context):
    return context.mode == 'OBJECT' and operators.session is None and picker is None and preview is None


def failure(operator, context, error):
    key = str(error)
    operator.report({'ERROR'}, i18n.tr(key, context, **getattr(error, 'details', {}))
                    if key in i18n.MESSAGES else i18n.tr('error', context, error=key))
    return {'CANCELLED'}


class PW_OT_connect_direct(bpy.types.Operator):
    bl_idname = 'line_pipe.connect_direct'
    bl_label = 'Direct Connection'
    bl_options = {'REGISTER', 'UNDO'}
    roll: FloatProperty(name='Roll', description='conn_roll_tip', subtype='ANGLE', default=0)

    @classmethod
    def description(cls, context, properties): return i18n.tr('conn_direct_tip', context)
    @classmethod
    def poll(cls, context):
        return context.mode == 'OBJECT' and operators.session is None and picker is None

    def invoke(self, context, event):
        global preview
        try:
            self.roll = context.scene.line_pipe_connections.roll
            self._objects = operator_endpoints(self, context)
            planned = connections.direct_plan(context.scene, *self._objects, self.roll)
            self._original = {obj: obj.matrix_world.copy() for obj in planned}
            self._can_roll = connections.can_roll(context.scene, self._objects[0])
            if not self._can_roll:
                self.roll = 0
                planned = connections.direct_plan(context.scene, *self._objects, 0)
            connections.set_matrices(planned)
            self._error = ''
            preview = self
            return context.window_manager.invoke_props_dialog(self, width=360, title=i18n.tr('conn_direct', context))
        except Exception as error:
            self.restore()
            return failure(self, context, error)

    def restore(self):
        global preview
        if hasattr(self, '_original'):
            connections.set_matrices({o: m for o, m in self._original.items() if o.name in bpy.data.objects})
        if preview is self: preview = None

    def check(self, context):
        try:
            connections.set_matrices(self._original)
            connections.set_matrices(connections.direct_plan(context.scene, *self._objects, self.roll))
            self._error = ''
        except Exception as error:
            self._error = (i18n.tr(str(error), context, **getattr(error, 'details', {}))
                           if str(error) in i18n.MESSAGES else str(error))
        return True

    def draw(self, context):
        row = self.layout.row(); row.enabled = getattr(self, '_can_roll', True)
        row.prop(self, 'roll_zh' if i18n.language(context) == 'ZH' else 'roll', text=i18n.tr('conn_roll', context))
        if getattr(self, '_error', ''):
            self.layout.label(text=self._error, icon='ERROR')

    def execute(self, context):
        try:
            objects = operator_endpoints(self, context)
            if preview is self: self.restore()
            link = connections.direct(context, *objects, self.roll)
            context.scene.line_pipe_connections.roll = link.roll
            self.report({'INFO'}, i18n.tr('conn_done', context))
            return {'FINISHED'}
        except Exception as error:
            if preview is self: self.restore()
            return failure(self, context, error)

    def cancel(self, context): self.restore()


class PW_OT_connect_distance(bpy.types.Operator):
    bl_idname = 'line_pipe.connect_distance'
    bl_label = 'Distance Connection'
    bl_options = {'REGISTER', 'UNDO'}
    radius: FloatProperty(name='Bend Radius', default=.4, min=.00001, unit='LENGTH')
    distance: FloatProperty(name='Maximum Distance', default=5, min=.001, unit='LENGTH')
    smooth: BoolProperty(name='Smooth Bends', default=True)
    sides: IntProperty(default=32, min=3, max=ports.MAX_SIDES, options={'HIDDEN'})

    @classmethod
    def description(cls, context, properties): return i18n.tr('conn_bridge_tip', context)
    @classmethod
    def poll(cls, context): return ready(context)

    def execute(self, context):
        try:
            settings = context.scene.line_pipe_connections
            for key in ('radius', 'smooth', 'distance'):
                if not self.properties.is_property_set(key): setattr(self, key, getattr(settings, key))
            connections.bridge(context, *operator_endpoints(self, context), self.radius, self.smooth, self.distance)
            self.report({'INFO'}, i18n.tr('conn_done', context))
            return {'FINISHED'}
        except Exception as error: return failure(self, context, error)


class PW_OT_sync_curvature(bpy.types.Operator):
    bl_idname = 'line_pipe.sync_curvature'
    bl_label = 'Match Group Curvature'
    bl_options = {'REGISTER', 'UNDO'}
    reference_name: StringProperty(options={'HIDDEN'})
    selection_names: StringProperty(options={'HIDDEN'})

    @classmethod
    def description(cls, context, properties): return i18n.tr('conn_curvature_tip', context)
    @classmethod
    def poll(cls, context):
        return ready(context) and ports.is_pipe(context.active_object) and len({ports.group_id(o) for o in context.selected_objects if ports.is_pipe(o)}) == 2

    def execute(self, context):
        try:
            if not self.reference_name:
                self.reference_name = context.active_object.name
                self.selection_names = json.dumps([o.name for o in context.selected_objects if ports.is_pipe(o)])
            active = context.scene.objects.get(self.reference_name)
            selected = [context.scene.objects.get(n) for n in json.loads(self.selection_names)]
            if not active or any(o is None for o in selected): raise ports.ConnectionError('select_two_groups')
            radius, count = connections.sync_curvature(context, active, selected)
            self.report({'INFO'}, i18n.tr('conn_curvature_done', context, count=count, radius=radius))
            return {'FINISHED'}
        except Exception as error: return failure(self, context, error)


class PW_OT_group_pipes(bpy.types.Operator):
    bl_idname = 'line_pipe.group_pipes'
    bl_label = 'Group Selected Pipes'
    bl_options = {'REGISTER', 'UNDO'}
    separate: BoolProperty(default=False, options={'HIDDEN'})
    select: BoolProperty(default=False, options={'HIDDEN'})

    @classmethod
    def poll(cls, context): return ready(context) and ports.is_pipe(context.active_object)
    def execute(self, context):
        objects = [o for o in context.selected_objects if ports.is_pipe(o)]
        if self.select:
            objects = ports.members(context.scene, context.active_object)
            for obj in context.selected_objects: obj.select_set(False)
            for obj in objects: obj.select_set(True)
        else:
            if self.separate and any(ports.occupied(context.scene, obj, p['key']) or p.get('occupied', False)
                                     for obj in objects for p in ports.local_ports(obj)):
                return failure(self, context, ports.ConnectionError('separate_connected'))
            if not self.separate:
                objects = list({member for obj in objects for member in ports.members(context.scene, obj)})
            group = uuid.uuid4().hex
            for obj in objects:
                ports.ensure_identity(obj)
                obj[ports.GROUP] = obj[ports.UID] if self.separate else group
        return {'FINISHED'}


class PW_OT_disconnect(bpy.types.Operator):
    bl_idname = 'line_pipe.disconnect'
    bl_label = 'Disconnect Pipe'
    bl_options = {'REGISTER', 'UNDO'}
    @classmethod
    def poll(cls, context): return ready(context) and ports.is_pipe(context.active_object)
    def execute(self, context):
        connections.disconnect(context, context.active_object)
        return {'FINISHED'}


class PW_OT_repair_mesh(bpy.types.Operator):
    bl_idname = 'line_pipe.repair_mesh'
    bl_label = 'Repair Pipe Mesh'
    bl_options = {'REGISTER', 'UNDO'}
    @classmethod
    def description(cls, context, properties): return i18n.tr('conn_repair_tip', context)
    @classmethod
    def poll(cls, context): return ready(context) and context.active_object is not None and context.active_object.type == 'MESH'
    def execute(self, context):
        try:
            connections.repair_mesh(context.active_object)
            self.report({'INFO'}, i18n.tr('conn_mesh_done', context))
            return {'FINISHED'}
        except Exception as error: return failure(self, context, error)


class PW_OT_update_connections(bpy.types.Operator):
    bl_idname = 'line_pipe.update_connections'
    bl_label = 'Update Distance Connections'
    bl_options = {'REGISTER', 'UNDO'}
    use_settings: BoolProperty(default=False, options={'HIDDEN'})
    @classmethod
    def poll(cls, context): return ready(context) and ports.is_pipe(context.active_object)
    def execute(self, context):
        try:
            count = connections.update_bridges(context, self.use_settings)
            self.report({'INFO'}, i18n.tr('conn_update_done', context, count=count))
            return {'FINISHED'}
        except Exception as error: return failure(self, context, error)


class PW_OT_register_cylinder(bpy.types.Operator):
    bl_idname = 'line_pipe.register_cylinder'
    bl_label = 'Register Mesh Cylinder'
    bl_options = {'REGISTER', 'UNDO'}
    @classmethod
    def poll(cls, context): return ready(context) and context.active_object is not None and context.active_object.type == 'MESH'
    def execute(self, context):
        try:
            connections.register_cylinder(context.active_object, context.scene.line_pipe_connections.mesh_axis)
            return {'FINISHED'}
        except Exception as error: return failure(self, context, error)


class PW_OT_detect_ports(bpy.types.Operator):
    bl_idname = 'line_pipe.detect_ports'
    bl_label = 'Detect Mesh Ports'
    bl_options = {'REGISTER', 'UNDO'}
    @classmethod
    def poll(cls, context): return ready(context) and context.active_object is not None and context.active_object.type == 'MESH'
    def execute(self, context):
        try:
            from . import fittings
            count = fittings.mark_ports(context)
            context.scene.line_pipe_settings.tool_mode = 'PORTS'
            self.report({'INFO'},i18n.tr('conn_detect_done',context,count=count))
            return {'FINISHED'}
        except Exception as error:return failure(self,context,error)


class PW_OT_pick_port(bpy.types.Operator):
    bl_idname = 'line_pipe.pick_port'
    bl_label = 'Pick Pipe Port'
    bl_options = {'INTERNAL'}
    role: EnumProperty(items=[('source', 'Moving', ''), ('target', 'Anchor', ''), ('pair', 'Both Ports', '')])

    @classmethod
    def description(cls, context, properties):
        return i18n.tr('pick_pair_tip' if properties.role == 'pair' else 'conn_pick_' + properties.role, context)
    @classmethod
    def poll(cls, context): return ready(context) and context.area and context.area.type == 'VIEW_3D'
    def invoke(self, context, event):
        global picker
        self.area, self.region = context.area, next(r for r in context.area.regions if r.type == 'WINDOW')
        self.rv3d = context.space_data.region_3d
        self.hover = None
        self.first = None
        self._custom_profiles = {}
        for obj in context.visible_objects:
            if obj.get(ports.CUSTOM):
                for spec in ports.local_ports(obj):
                    try:
                        self._custom_profiles.setdefault(obj, []).append(ports.measured(obj, spec))
                    except ports.ConnectionError:
                        pass
        self._handles = [bpy.types.SpaceView3D.draw_handler_add(self.draw_overlay, (), 'WINDOW', 'POST_PIXEL')]
        picker = self
        context.window_manager.modal_handler_add(self)
        self.area.header_text_set(i18n.tr('conn_pick_' + ('target' if self.role == 'pair' else self.role), context))
        return {'RUNNING_MODAL'}

    def candidates(self):
        for obj in bpy.context.scene.objects:
            if not ports.is_pipe(obj) or not obj.visible_get(): continue
            try:
                candidates = ([ports.world_port(obj, spec) for spec in self._custom_profiles.get(obj, ())]
                              if obj.get(ports.CUSTOM) else ports.world_ports(obj))
                for port in candidates:
                    if (not port.enabled or port.legacy_occupied or ports.occupied(bpy.context.scene, obj, port.key)
                            or self.first and self.first.obj == port.obj):
                        continue
                    point = view3d_utils.location_3d_to_region_2d(self.region, self.rv3d, port.position)
                    if point is not None: yield port, point
            except ValueError: continue

    def modal(self, context, event):
        if picker is not self: return {'CANCELLED'}
        if self.area not in context.screen.areas[:] or self.area.type != 'VIEW_3D':
            self.cleanup(); return {'CANCELLED'}
        if event.type in {'ESC', 'RIGHTMOUSE', 'WINDOW_DEACTIVATE'}:
            self.cleanup(); return {'CANCELLED'}
        if event.type in {'MIDDLEMOUSE', 'WHEELUPMOUSE', 'WHEELDOWNMOUSE'} or event.alt:
            return {'PASS_THROUGH'}
        if event.type in {'MOUSEMOVE', 'LEFTMOUSE'}:
            mouse = Vector((event.mouse_x-self.region.x, event.mouse_y-self.region.y))
            candidates = [(p, (point-mouse).length) for p, point in self.candidates()]
            nearest = min(candidates, key=lambda x: x[1], default=None)
            self.hover = nearest[0] if nearest and nearest[1] < 28 else None
            if event.type == 'LEFTMOUSE' and event.value == 'PRESS' and self.hover:
                settings = context.scene.line_pipe_connections
                if self.role == 'pair':
                    if self.first is None:
                        self.first, self.hover = self.hover, None
                        self.area.header_text_set(i18n.tr('conn_pick_source', context))
                        self.area.tag_redraw()
                        return {'RUNNING_MODAL'}
                    settings.target, settings.target_port = self.first.obj, self.first.key
                    settings.source, settings.source_port = self.hover.obj, self.hover.key
                else:
                    setattr(settings, self.role, self.hover.obj)
                    setattr(settings, self.role + '_port', self.hover.key)
                self.cleanup()
                return {'FINISHED'}
            self.area.tag_redraw()
        return {'RUNNING_MODAL'}

    def draw_overlay(self):
        try:
            gpu.state.blend_set('ALPHA')
            self.draw_ports()
        finally:
            gpu.state.line_width_set(1)
            gpu.state.blend_set('NONE')

    def draw_ports(self):
        if bpy.context.area != self.area: return
        candidates = list(self.candidates())
        if self.first is not None:
            point = view3d_utils.location_3d_to_region_2d(self.region, self.rv3d, self.first.position)
            if point is not None:
                candidates.append((self.first, point))
        for port, point in candidates:
            selected = self.hover is not None and self.hover.obj == port.obj and self.hover.key == port.key
            color = (.25, .9, .75, 1) if port is self.first else (1, .7, .13, 1) if selected else (1, 1, 1, .85)
            vertices = []
            for j in range(24):
                a, b = math.tau*j/24, math.tau*(j+1)/24
                vertices.extend([(point.x+12*math.cos(a), point.y+12*math.sin(a)),
                                 (point.x+12*math.cos(b), point.y+12*math.sin(b))])
            operators.lines(vertices, color, 3 if selected else 2)
            operators.screen_text(f'{port.obj.name} · {port.key} · {port.sides}', (point.x+16, point.y+6), color)

    def cleanup(self):
        global picker
        for handle in self._handles: bpy.types.SpaceView3D.draw_handler_remove(handle, 'WINDOW')
        self._handles.clear(); self.area.header_text_set(None); self.area.tag_redraw()
        if picker is self: picker = None


def abort():
    if picker: picker.cleanup()
    if preview: preview.restore()


for cls, tips in ((PW_ConnectionSettings, dict(roll='conn_roll_tip', distance='conn_distance_tip',
        radius='conn_radius_tip', smooth='conn_smooth_tip', sides='sides_tip', mesh_axis='conn_axis_tip')),
        (PW_OT_connect_distance, dict(distance='conn_distance_tip', radius='conn_radius_tip', smooth='conn_smooth_tip')),
        (PW_OT_connect_direct, dict(roll='conn_roll_tip'))):
    for key, tip in tips.items():
        cls.__annotations__[key].keywords['description'] = i18n.text(tip, 'EN')
    i18n.add_chinese_properties(cls, tips)


for cls in (PW_OT_connect_direct, PW_OT_connect_distance):
    cls.__annotations__.update({key: StringProperty(options={'HIDDEN'}) for key in
                               ('source_name', 'source_key', 'target_name', 'target_key')})


def port_alias(role, getter):
    def get(self):
        items = port_items(self, bpy.context, role)
        return next((i for i, item in enumerate(items) if item[0] == getattr(self, role + '_port')), 0)
    def set(self, index):
        setattr(self, role + '_port', port_items(self, bpy.context, role)[index][0])
    return get if getter else set


for role, callback, label in (('source', source_items, '移动端口'), ('target', target_items, '固定端口')):
    PW_ConnectionSettings.__annotations__[role + '_port_zh'] = EnumProperty(
        name=label, items=callback, get=port_alias(role, True), set=port_alias(role, False))


CLASSES = (PW_Link, PW_ConnectionSettings, PW_OT_connect_direct, PW_OT_connect_distance, PW_OT_sync_curvature,
           PW_OT_group_pipes, PW_OT_disconnect, PW_OT_repair_mesh, PW_OT_update_connections,
           PW_OT_register_cylinder, PW_OT_detect_ports, PW_OT_pick_port)
