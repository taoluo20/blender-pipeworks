# SPDX-License-Identifier: GPL-3.0-or-later
import bpy
from bpy.props import BoolProperty, EnumProperty, FloatProperty, FloatVectorProperty, IntProperty, StringProperty
from . import geometry, i18n
from .model import bend_floor

_updating = False
DIMENSIONS = ('diameter', 'bend_radius', 'radial_segments', 'bend_steps')
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
        geometry.rebuild(obj)
        self.error = ''
        obj['_line_pipe_dimensions'] = [getattr(self, key) for key in DIMENSIONS]
    except ValueError as error:
        for key, value in zip(DIMENSIONS, obj.get('_line_pipe_dimensions', ())):
            setattr(self, key, int(value) if key in DIMENSIONS[2:] else value)
        self.error = 'bad_radius' if str(error) == 'bad_radius' else 'fit'
    finally:
        _updating = False


def dimensions():
    return {
        'diameter': FloatProperty(name='Diameter', description=i18n.text('size_tip', 'EN'),
                                  default=.2, min=.0001, soft_max=10, subtype='DISTANCE', unit='LENGTH', update=changed),
        'bend_radius': FloatProperty(name='Radius Limit', description=i18n.text('radius_tip', 'EN'),
                                     default=.4, min=.0001, soft_max=10, subtype='DISTANCE', unit='LENGTH', update=changed),
        'radial_segments': IntProperty(name='Radial Segments', description=i18n.text('sides_tip', 'EN'),
                                       default=32, min=8, max=128, update=changed),
        'bend_steps': IntProperty(name='Bend Segments', description=i18n.text('steps_tip', 'EN'),
                                  default=16, min=4, max=64, update=changed),
    }


class LP_Settings(bpy.types.PropertyGroup):
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
    show_guides: BoolProperty(name='Show Guides', description=i18n.text('guides_tip', 'EN'), default=True)


LP_Settings.__annotations__.update(dimensions())


class LP_Object(bpy.types.PropertyGroup):
    enabled: BoolProperty(default=False)
    error: StringProperty(options={'HIDDEN'})


LP_Object.__annotations__.update(dimensions())
tips = {'diameter': 'size_tip', 'bend_radius': 'radius_tip', 'radial_segments': 'sides_tip', 'bend_steps': 'steps_tip'}
i18n.add_chinese_properties(LP_Object, tips)
i18n.add_chinese_properties(LP_Settings, dict(tips, start_mode='start_tip', origin='origin_tip', direction='direction_tip',
                                           custom_direction='vector_tip', surface_offset='offset_tip',
                                           face_index='face_tip', turn_key='key_tip',
                                           follow_tip='follow_tip_tip', show_guides='guides_tip'))


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


CLASSES = (LP_Settings, LP_Object, LP_GuideColors, LP_Preferences)
