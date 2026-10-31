# SPDX-License-Identifier: GPL-3.0-or-later
import bpy
from . import data, i18n, operators


def dimensions(layout, settings, context):
    for key in ('diameter', 'bend_radius', 'radial_segments', 'bend_steps'):
        i18n.prop(layout, settings, key, context)


class LP_PT_main(bpy.types.Panel):
    bl_label = 'PipeWorks'
    bl_idname = 'LP_PT_main'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'PipeWorks'

    def draw_header(self, context):
        self.layout.label(text='', icon='CURVE_PATH')

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False
        row = layout.row()
        row.label(text=i18n.tr('title', context))
        row.operator('line_pipe.language', text='中文' if i18n.language(context) == 'EN' else 'English', icon='WORLD')
        settings = context.scene.line_pipe_settings
        i18n.prop(layout, settings, 'follow_tip', context)
        i18n.prop(layout, settings, 'show_guides', context)
        data.draw_guide_colors(layout, context)
        col = layout.column()
        col.enabled = operators.session is None and context.mode == 'OBJECT'
        dimensions(col, settings, context)
        col.separator()
        i18n.prop(col, settings, 'start_mode', context)
        if settings.start_mode == 'COORDINATES':
            i18n.prop(col, settings, 'origin', context)
        if settings.start_mode == 'FACE':
            i18n.prop(col, settings, 'face_index', context)
        if settings.start_mode in {'SURFACE', 'FACE'}:
            i18n.prop(col, settings, 'surface_offset', context)
        if operators.session and operators.session.route and operators.session.route.axis_initial:
            row = col.row()
            row.label(text=i18n.tr('direction', context))
            row.label(text=i18n.tr('six_axes', context))
        else:
            i18n.prop(col, settings, 'direction', context)
        if settings.direction == 'CUSTOM':
            i18n.prop(col, settings, 'custom_direction', context)
        i18n.prop(col, settings, 'turn_key', context)
        col.separator()
        row = col.row()
        row.scale_y = 1.3
        row.operator('line_pipe.draw', text=i18n.tr('draw', context), icon='CURVE_PATH')
        obj = context.active_object
        if obj and obj.type == 'CURVE' and obj.line_pipe.enabled and obj.get('line_pipe_route_v1'):
            layout.separator()
            col = layout.column()
            col.enabled = operators.session is None
            col.label(text=i18n.tr('active', context), icon='OUTLINER_OB_CURVE')
            dimensions(col, obj.line_pipe, context)
            if obj.line_pipe.error:
                key = obj.line_pipe.error
                col.label(text=i18n.tr(key, context), icon='ERROR')
            col.operator('line_pipe.mesh', text=i18n.tr('mesh', context), icon='MESH_DATA')


CLASSES = (LP_PT_main,)
