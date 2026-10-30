# SPDX-License-Identifier: GPL-3.0-or-later
import bpy
from bpy.props import BoolProperty, EnumProperty, FloatProperty, FloatVectorProperty, IntProperty, StringProperty
from . import geometry, i18n

_updating = False
DIMENSIONS = ('diameter', 'bend_radius', 'radial_segments', 'bend_steps')


def changed(self, context):
    global _updating
    obj = self.id_data
    if _updating or not isinstance(obj, bpy.types.Object) or not obj.get('line_pipe_route_v1'):
        return
    try:
        _updating = True
        if self.bend_radius <= self.diameter / 2:
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
        'bend_radius': FloatProperty(name='Bend Radius', description=i18n.text('radius_tip', 'EN'),
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


LP_Settings.__annotations__.update(dimensions())


class LP_Object(bpy.types.PropertyGroup):
    enabled: BoolProperty(default=False)
    error: StringProperty(options={'HIDDEN'})


LP_Object.__annotations__.update(dimensions())
tips = {'diameter': 'size_tip', 'bend_radius': 'radius_tip', 'radial_segments': 'sides_tip', 'bend_steps': 'steps_tip'}
i18n.add_chinese_properties(LP_Object, tips)
i18n.add_chinese_properties(LP_Settings, dict(tips, start_mode='start_tip', origin='origin_tip', direction='direction_tip',
                                           custom_direction='vector_tip', surface_offset='offset_tip',
                                           face_index='face_tip', turn_key='key_tip'))


class LP_Preferences(bpy.types.AddonPreferences):
    bl_idname = __package__
    language: EnumProperty(name='Language', items=[('EN', 'English', ''), ('ZH', '中文', '')], default='EN')

    def draw(self, context):
        self.layout.operator('line_pipe.language', text='中文' if self.language == 'EN' else 'English', icon='WORLD')


CLASSES = (LP_Settings, LP_Object, LP_Preferences)
