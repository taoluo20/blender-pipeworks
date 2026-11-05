# SPDX-License-Identifier: GPL-3.0-or-later
import json
from types import SimpleNamespace
import bpy
from bpy.props import BoolProperty, EnumProperty, FloatProperty, FloatVectorProperty, IntProperty, StringProperty
from . import geometry, i18n, ports
from .model import bend_floor

_updating = False
_preset_drag = None
DIMENSIONS = ('diameter', 'bend_radius', 'radial_segments', 'bend_steps')
PROFILE = ('hollow', 'wall_mode', 'wall', 'wall_preset')
GUIDE_IDLE = (1.0, 1.0, 1.0, 1.0)
GUIDE_ACTIVE = (1.0, .7, .13, 1.0)


def save_preferences():
    preferences = bpy.context.preferences
    if preferences.use_preferences_save and preferences.addons.get(__package__):
        bpy.ops.wm.save_userpref()


def cancel_preferences_save():
    if bpy.app.timers.is_registered(save_preferences):
        bpy.app.timers.unregister(save_preferences)


def guide_colors_changed(self, context):
    for window in context.window_manager.windows:
        for area in window.screen.areas:
            area.tag_redraw()
    if isinstance(self, bpy.types.AddonPreferences):
        context.preferences.is_dirty = True
        if context.preferences.use_preferences_save:
            cancel_preferences_save()
            bpy.app.timers.register(save_preferences, first_interval=.5)


def guide_color_properties():
    # Overlay shaders consume display-space RGBA; COLOR_GAMMA keeps native Hex identical.
    return {key: FloatVectorProperty(name=i18n.text(key, 'EN'), description=i18n.text(key + '_tip', 'EN'),
                                    size=4, subtype='COLOR_GAMMA', min=0, max=1, default=default,
                                    options=set(), update=guide_colors_changed)
            for key, default in (('guide_idle', GUIDE_IDLE), ('guide_active', GUIDE_ACTIVE))}


def guide_preferences(context=None):
    context = context or bpy.context
    addon = context.preferences.addons.get(__package__)
    return addon.preferences if addon else context.window_manager.line_pipe_colors


def guide_colors(context=None):
    preferences = guide_preferences(context)
    return (tuple(getattr(preferences, 'guide_idle', GUIDE_IDLE)),
            tuple(getattr(preferences, 'guide_active', GUIDE_ACTIVE)))


def draw_guide_colors(layout, context):
    preferences = guide_preferences(context)
    row = layout.row()
    row.label(text=i18n.tr('guide_colors', context))
    row.operator('line_pipe.reset_guide_colors', text='', icon='LOOP_BACK')
    for key in ('guide_idle', 'guide_active'):
        i18n.prop(layout, preferences, key, context)


def changed(self, context):
    global _updating
    obj = self.id_data
    if _updating or not isinstance(obj, bpy.types.Object) or not obj.get('line_pipe_route_v1'):
        return
    try:
        _updating = True
        if self.bend_radius < bend_floor(self.diameter):
            raise ValueError('bad_radius')
        previous = obj.get('_line_pipe_dimensions', ())
        if obj.get(ports.CUSTOM) or not geometry.generated_mesh_intact(obj):
            raise ValueError('edited_recipe')
        if obj.type == 'CURVE' and self.hollow:
            raise ValueError('hollow_bake_first')
        prior_ports = ports.local_ports(obj)
        if (previous and (abs(self.diameter - previous[0]) > 1e-8 or self.radial_segments != previous[2])
                or prior_ports and abs(bore(self) - prior_ports[0]['bore']) > 1e-8):
            geometry.require_free_profile(obj, context.scene)
        bore(self)
        geometry.rebuild(obj)
        self.error = ''
        obj['_line_pipe_dimensions'] = [getattr(self, key) for key in DIMENSIONS]
        obj['_pipeworks_wall_values'] = json.dumps(profile_values(obj))
    except ValueError as error:
        for key, value in zip(DIMENSIONS, obj.get('_line_pipe_dimensions', ())):
            setattr(self, key, int(value) if key in DIMENSIONS[2:] else value)
        for key, value in zip(PROFILE, json.loads(obj.get('_pipeworks_wall_values', '[false, "FREE", 0.02, "10"]'))):
            setattr(self, key, value)
        self.error = str(error) if str(error) in i18n.MESSAGES else 'fit'
    finally:
        _updating = False


def bore(settings):
    if not settings.hollow:
        return 0
    wall = (settings.wall if settings.wall_mode == 'FREE'
            else settings.diameter * int(settings.wall_preset) / 100)
    if not 0 < wall < settings.diameter / 2:
        raise ports.ConnectionError('invalid_wall')
    return settings.diameter - 2 * wall


def profile():
    return {
        'free_sides': BoolProperty(name='Custom Edge Count', default=False),
        'hollow': BoolProperty(name='Hollow Pipe', default=False, update=changed),
        'wall_mode': EnumProperty(name='Wall Thickness Mode',
            items=[('FREE', 'Free', '', 'wall_free'), ('PRESET', 'Preset', '', 'wall_standard')],
            default='FREE', update=changed),
        'wall': FloatProperty(name='Wall Thickness', default=.02, min=.00000001,
                              unit='LENGTH', subtype='DISTANCE', update=changed),
        'wall_preset': EnumProperty(name='Preset Thickness', items=[
            ('5', '5% of diameter', '', 'wall_5'), ('10', '10% of diameter', '', 'wall_10'),
            ('15', '15% of diameter', '', 'wall_15')], default='10', update=changed),
    }


def profile_values(obj):
    return [getattr(obj.line_pipe, key) for key in PROFILE]


def store_parameters(obj, diameter, radius, sides, steps, profile, free_sides=False):
    global _updating
    previous = _updating
    _updating = True
    try:
        for key, value in zip((*DIMENSIONS, *PROFILE), (diameter, radius, sides, steps, *profile)):
            setattr(obj.line_pipe, key, value)
        obj.line_pipe.free_sides = free_sides
        obj.line_pipe.error = ''
    finally:
        _updating = previous
    obj['_line_pipe_dimensions'] = [getattr(obj.line_pipe, key) for key in DIMENSIONS]
    obj['_pipeworks_wall_values'] = json.dumps(profile_values(obj))


def set_route_length(settings, length):
    if not settings.id_data.get('line_pipe_route_v1'):
        return
    try:
        if abs(length - geometry.route_length(settings.id_data)) > 1e-7:
            geometry.resize_route(settings.id_data, bpy.context.scene, length)
        settings.error = ''
    except ValueError as error:
        settings.error = str(error) if str(error) in i18n.MESSAGES else 'fit'


def generation_sides(settings):
    sides = settings.radial_segments
    return sides if settings.free_sides or sides in ports.STANDARD_SIDES else ports.DEFAULT_SIDES


def sides_menu(layout, settings, context, slider=False):
    i18n.prop(layout, settings, 'free_sides', context)
    if settings.free_sides:
        i18n.prop(layout, settings, 'radial_segments', context, slider=slider)
    else:
        row = layout.row()
        row.label(text=i18n.tr('radial_segments', context))
        row.context_pointer_set('pipeworks_profile', settings)
        count = generation_sides(settings) if isinstance(settings.id_data, bpy.types.Scene) else settings.radial_segments
        if _preset_drag is not None and _preset_drag.settings == settings:
            count = _preset_drag.count
        controls = row.row(align=True)
        controls.use_property_split = False
        key = 'line_pipe_preset_drag_zh' if i18n.language(context) == 'ZH' else 'line_pipe_preset_drag'
        controls.prop_enum(context.window_manager, key, 'DRAG', text=str(count))
        arrow = controls.row(align=True)
        arrow.ui_units_x = 1.25
        arrow.operator_menu_enum('line_pipe.set_sides', 'count', text='', icon='TRIA_DOWN')


def dimensions(default_sides=ports.DEFAULT_SIDES):
    return {
        'diameter': FloatProperty(name='Diameter', description=i18n.text('size_tip', 'EN'),
                                  default=.2, min=.0001, soft_max=10, subtype='DISTANCE', unit='LENGTH', update=changed),
        'bend_radius': FloatProperty(name='Radius Limit', description=i18n.text('radius_tip', 'EN'),
                                     default=.4, min=.0001, soft_max=10, subtype='DISTANCE', unit='LENGTH', update=changed),
        'radial_segments': IntProperty(name='Radial Segments', description=i18n.text('sides_tip', 'EN'),
                                       default=default_sides, min=3, max=ports.MAX_SIDES, soft_max=576, update=changed),
        'bend_steps': IntProperty(name='Bend Segments', description=i18n.text('steps_tip', 'EN'),
                                  default=16, min=4, max=64, update=changed),
    }


class LP_Settings(bpy.types.PropertyGroup):
    tool_mode: EnumProperty(name='Tool', items=[('DRAW', 'Draw', 'Draw', 'tool_draw'),
        ('CONNECT', 'Connect', 'Connect', 'tool_connect'), ('GROUPS', 'Groups', 'Groups', 'tool_groups'), ('PORTS', 'Ports', 'Ports', 'tool_ports'),
        ('LIBRARY', 'Library', 'Library', 'tool_library')], default='DRAW')
    language: EnumProperty(items=[('EN', 'English', ''), ('ZH', '中文', '')], default='EN')
    start_mode: EnumProperty(name='Start From', description=i18n.text('start_tip', 'EN'), items=[
        ('POINT', 'Point', 'Point', 'point'), ('SURFACE', 'Surface', 'Surface', 'surface'),
        ('COORDINATES', 'Coordinates', 'Coordinates', 'coordinates'),
        ('CURSOR', '3D Cursor', '3D Cursor', 'cursor'),
        ('FACE', 'Selected Mesh Face', 'Selected Mesh Face', 'face')], default='POINT')
    origin: FloatVectorProperty(name='Position', description=i18n.text('origin_tip', 'EN'),
                                subtype='TRANSLATION', unit='LENGTH')
    direction: EnumProperty(name='Initial Direction', description=i18n.text('direction_tip', 'EN'), items=[
        ('NORMAL', 'Surface Normal', 'Surface Normal', 'normal'),
        ('X', '+X', '+X'), ('NX', '-X', '-X'), ('Y', '+Y', '+Y'), ('NY', '-Y', '-Y'),
        ('Z', '+Z', '+Z'), ('NZ', '-Z', '-Z'),
        ('CUSTOM', 'Custom Vector', 'Custom Vector', 'custom'),
        ('AUTO', 'Mouse: 6 Axes', 'Mouse: 6 Axes', 'six_axes')], default='AUTO')
    custom_direction: FloatVectorProperty(name='Direction Vector', description=i18n.text('vector_tip', 'EN'),
                                          default=(1, 0, 0), subtype='XYZ')
    surface_offset: FloatProperty(name='Surface Offset', description=i18n.text('offset_tip', 'EN'),
                                  default=0, subtype='DISTANCE', unit='LENGTH')
    face_index: IntProperty(name='Face Index', description=i18n.text('face_tip', 'EN'), default=0, min=0)
    turn_key: EnumProperty(name='Turn Key', description=i18n.text('key_tip', 'EN'), default='B',
                           items=[(key, key, key) for key in ('B', 'T', 'F', 'C', 'V')])
    follow_tip: BoolProperty(name='Follow Tip', description=i18n.text('follow_tip_tip', 'EN'), default=False)
    template_length: FloatProperty(name='Fitting Length', default=2., min=.0001, subtype='DISTANCE', unit='LENGTH')
    continuation_fitting: StringProperty(default='CYLINDER')
    show_guides: BoolProperty(name='Show Guides', description=i18n.text('guides_tip', 'EN'), default=True)


LP_Settings.__annotations__.update(dimensions(), **profile())


class LP_Object(bpy.types.PropertyGroup):
    enabled: BoolProperty(default=False)
    error: StringProperty(options={'HIDDEN'})
    route_length: FloatProperty(name='Route Length', description=i18n.text('route_length_tip', 'EN'),
                                subtype='DISTANCE', unit='LENGTH', min=.000001,
                                get=lambda self: geometry.route_length(self.id_data), set=set_route_length)


LP_Object.__annotations__.update(dimensions(32), **profile())
tips = {'diameter': 'size_tip', 'bend_radius': 'radius_tip', 'radial_segments': 'sides_tip', 'bend_steps': 'steps_tip'}
tips.update({key: key + '_tip' for key in ('free_sides', *PROFILE)})
i18n.add_chinese_properties(LP_Object, tips)
i18n.add_chinese_properties(LP_Object, {'route_length': 'route_length_tip'})
i18n.add_chinese_properties(LP_Settings, dict(tips, start_mode='start_tip', origin='origin_tip', direction='direction_tip',
                                           custom_direction='vector_tip', surface_offset='offset_tip',
                                           face_index='face_tip', turn_key='key_tip',
                                           follow_tip='follow_tip_tip', show_guides='guides_tip', template_length='template_length_tip'))
i18n.add_chinese_properties(LP_Settings, {'tool_mode': 'tool_mode_tip'})


class LP_GuideColors(bpy.types.PropertyGroup):
    """Session fallback for source imports that have no enabled add-on entry."""


class LP_Preferences(bpy.types.AddonPreferences):
    bl_idname = __package__
    language: EnumProperty(name='Language', items=[('EN', 'English', ''), ('ZH', '中文', '')], default='EN')

    def draw(self, context):
        self.layout.operator('line_pipe.language', text='中文' if self.language == 'EN' else 'English', icon='WORLD')
        draw_guide_colors(self.layout, context)


for cls in (LP_GuideColors, LP_Preferences):
    cls.__annotations__ = dict(getattr(cls, '__annotations__', {}), **guide_color_properties())
    i18n.add_chinese_properties(cls, {'guide_idle': 'guide_idle_tip', 'guide_active': 'guide_active_tip'})


class LP_OT_set_sides(bpy.types.Operator):
    bl_idname = 'line_pipe.set_sides'
    bl_label = 'Preset Edge Count'
    bl_options = {'UNDO'}
    count: EnumProperty(items=[(str(n), str(n), str(n)) for n in ports.STANDARD_SIDES])

    @classmethod
    def description(cls, context, properties):
        return i18n.tr('sides_tip', context)

    def execute(self, context):
        settings = getattr(context, 'pipeworks_profile', context.scene.line_pipe_settings)
        settings.radial_segments = int(self.count)
        return {'FINISHED'}


def start_preset_drag(_wm, context):
    # The enum row receives the press without Blender's checkbox drag handling.
    # Its temporary value starts the gesture; the preset is applied on release.
    if _preset_drag is None and getattr(context, 'pipeworks_profile', None) is not None:
        bpy.ops.line_pipe.drag_sides('INVOKE_DEFAULT', True)


def preset_drag_property(language):
    label = i18n.text('radial_segments', language)
    return EnumProperty(name=label, description=i18n.text('preset_drag_tip', language),
                        items=[('IDLE', label, '', 0), ('DRAG', label, '', 1)],
                        get=lambda _wm: 0, set=lambda _wm, _value: None,
                        update=start_preset_drag, options={'SKIP_SAVE'})


class LP_OT_drag_sides(bpy.types.Operator):
    bl_idname = 'line_pipe.drag_sides'
    bl_label = 'Drag Preset Edge Count'
    bl_options = {'INTERNAL', 'UNDO'}

    def invoke(self, context, event):
        global _preset_drag
        settings = getattr(context, 'pipeworks_profile', None)
        if (settings is None or settings.free_sides
                or event.type != 'LEFTMOUSE' or event.value not in {'PRESS', 'DOUBLE_CLICK'}):
            return {'CANCELLED'}
        initial = (generation_sides(settings) if isinstance(settings.id_data, bpy.types.Scene)
                   else settings.radial_segments)
        counts = sorted(set(ports.STANDARD_SIDES) | {initial})
        self.drag = SimpleNamespace(settings=settings, area=context.area, window=context.window,
                                    origin=event.mouse_prev_press_x,
                                    step=max(1, round(24 * context.preferences.system.ui_scale)),
                                    initial=initial, count=initial, counts=counts, index=counts.index(initial))
        self.drag.live = settings.bl_rna.identifier == 'PW_EditSettings'
        self.drag.committed = False
        if self.drag.live:
            from . import editing
            self.drag.original = [(obj.name, current['radial_segments'], current['free_sides'])
                                  for obj in editing.targets(context) for current in [editing.values(obj)]]
            settings.radial_segments = initial
            if settings.error:
                return {'CANCELLED'}
        self.drag.window.cursor_modal_set('SCROLL_X')
        context.window_manager.modal_handler_add(self)
        _preset_drag = self.drag
        return {'RUNNING_MODAL'}

    def modal(self, context, event):
        drag = self.drag
        if _preset_drag is not drag:
            return {'CANCELLED'}
        if drag.area not in drag.window.screen.areas[:] or event.type in {'ESC', 'RIGHTMOUSE', 'WINDOW_DEACTIVATE'}:
            self.cancel(context)
            return {'CANCELLED', 'PASS_THROUGH'} if event.type == 'ESC' else {'CANCELLED'}
        release = event.type == 'LEFTMOUSE' and event.value == 'RELEASE'
        # A fast click-drag can release while Blender is installing the modal handler.
        previous_release = not drag.live and event.type_prev == 'LEFTMOUSE' and event.value_prev == 'RELEASE'
        if event.type in {'MOUSEMOVE', 'INBETWEEN_MOUSEMOVE'} or release or previous_release:
            x = event.mouse_prev_x if previous_release and not release else event.mouse_x
            offset = int((x - drag.origin) / drag.step)
            index = max(0, min(drag.index + offset, len(drag.counts) - 1))
            drag.count = drag.counts[index]
            if drag.live and drag.settings.radial_segments != drag.count:
                drag.settings.radial_segments = drag.count
                drag.count = drag.settings.radial_segments
            drag.area.tag_redraw()
        if release or previous_release:
            passthrough = {'PASS_THROUGH'} if previous_release and not release else set()
            if drag.live:
                drag.committed = True
                self.cancel(context)
                return {'FINISHED', 'PASS_THROUGH'}
            self.cancel(context)
            if drag.count == drag.initial:
                return {'CANCELLED'} | passthrough
            drag.settings.radial_segments = drag.count
            if drag.settings.radial_segments != drag.count:
                self.report({'WARNING'}, i18n.tr(drag.settings.error or 'fit', context))
                return {'CANCELLED'} | passthrough
            return {'FINISHED'} | passthrough
        return {'RUNNING_MODAL'}

    def cancel(self, context):
        if _preset_drag is getattr(self, 'drag', None):
            abort_preset_drag()


def abort_preset_drag():
    global _preset_drag
    drag, _preset_drag = _preset_drag, None
    if drag is not None and getattr(drag, 'live', False) and not drag.committed:
        from . import editing
        original = {}
        flags = {}
        for name, count, free in drag.original:
            obj = bpy.context.scene.objects.get(name)
            if obj:
                original.setdefault(count, []).append(obj)
                flags.setdefault(free, []).append(obj)
        # Restore connected edge rings together before restoring per-object UI modes.
        for count, objects in original.items():
            editing.update_objects(bpy.context, objects, {'radial_segments': count})
        for free, objects in flags.items():
            editing.update_objects(bpy.context, objects, {'free_sides': free})
        editing.sync_editor(bpy.context, force=True)
    if drag is not None and drag.window in bpy.context.window_manager.windows[:]:
        drag.window.cursor_modal_restore()
        if drag.area in drag.window.screen.areas[:]:
            drag.area.tag_redraw()


CLASSES = (LP_Settings, LP_Object, LP_GuideColors, LP_Preferences, LP_OT_set_sides, LP_OT_drag_sides)
