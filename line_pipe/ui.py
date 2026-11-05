# SPDX-License-Identifier: GPL-3.0-or-later
import bpy
from . import data, i18n, operators, ports


def dimensions(layout, settings, context):
    for key in ('diameter', 'bend_radius', 'bend_steps'):
        i18n.prop(layout, settings, key, context)
    data.sides_menu(layout, settings, context)
    if settings.id_data == context.scene or settings.id_data.type == 'MESH':
        i18n.prop(layout, settings, 'hollow', context)
        if settings.hollow:
            i18n.prop(layout, settings, 'wall_mode', context)
            i18n.prop(layout, settings, 'wall' if settings.wall_mode == 'FREE' else 'wall_preset', context)


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
        row = layout.row(align=True)
        row.use_property_split = False
        mode_property = 'tool_mode_zh' if i18n.language(context) == 'ZH' else 'tool_mode'
        for value, key in (('DRAW', 'tool_draw'), ('CONNECT', 'tool_connect'), ('GROUPS', 'tool_groups')):
            row.prop_enum(settings, mode_property, value, text=i18n.tr(key, context))
        row = layout.row(align=True)
        row.use_property_split = False
        for value, key in (('PORTS', 'tool_ports'), ('LIBRARY', 'tool_library')):
            row.prop_enum(settings, mode_property, value, text=i18n.tr(key, context))
        if settings.tool_mode in {'PORTS', 'LIBRARY'}:
            from . import fittings
            (fittings.draw_ports if settings.tool_mode == 'PORTS' else fittings.draw_library)(layout, context)
            return
        if settings.tool_mode != 'DRAW':
            from . import connection_ui
            connection_ui.draw_connections(layout, context, settings.tool_mode == 'GROUPS')
            return
        from . import fittings
        row = layout.row()
        row.enabled = operators.session is None
        fittings.draw_continuation(row, context)
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


class LP_PT_selection(bpy.types.Panel):
    bl_label = ''
    bl_idname = 'LP_PT_selection'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'PipeWorks'
    bl_parent_id = 'LP_PT_main'

    @classmethod
    def poll(cls, context):
        from . import editing
        return (operators.session is None and context.mode == 'OBJECT'
                and context.scene.line_pipe_settings.tool_mode != 'GROUPS' and bool(editing.targets(context)))

    def draw_header(self, context):
        self.layout.label(text=i18n.tr('edit_title', context))

    def draw(self, context):
        from . import editing
        editing.draw(self.layout, context)


CLASSES = (LP_PT_main, LP_PT_selection)
