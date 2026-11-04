# SPDX-License-Identifier: GPL-3.0-or-later
from . import i18n, ports, connections, connection_ops


def draw_connections(layout, context, groups_only=False):
    if not groups_only:
        layout.use_property_split = True
        layout.use_property_decorate = False
        layout.enabled = connection_ops.ready(context)
        state = context.scene.line_pipe_connections
        suffix = '_zh' if i18n.language(context) == 'ZH' else ''
        if context.active_object and context.active_object.type == 'MESH' and not ports.is_pipe(context.active_object):
            layout.operator('line_pipe.detect_ports',text=i18n.tr('conn_detect',context))
        layout.operator('line_pipe.pick_port', text=i18n.tr('pick_pair', context), icon='EYEDROPPER').role = 'pair'
        for role in ('target', 'source'):
            box = layout.box()
            box.label(text=i18n.tr('first_port' if role == 'target' else 'second_port', context))
            box.prop(state, role + suffix, text=i18n.tr('conn_' + role, context))
            row = box.row(align=True)
            row.prop(state, role + '_port' + suffix, text=i18n.tr('conn_' + role + '_port', context))
            op = row.operator('line_pipe.pick_port', text='', icon='EYEDROPPER')
            op.role = role
            obj = getattr(state, role)
            spec = next((p for p in ports.local_ports(obj) if p['key'] == getattr(state, role + '_port')), None)
            if spec:
                box.label(text=i18n.tr('edge_count', context, count=spec['sides']))
        row = layout.row()
        row.enabled = connections.can_roll(context.scene, state.source or context.active_object) if ports.is_pipe(state.source or context.active_object) else False
        i18n.prop(row, state, 'roll', context)
        if ports.is_pipe(state.target):
            spec = next((p for p in ports.local_ports(state.target) if p['key'] == state.target_port), None)
            if spec:
                layout.label(text=i18n.tr('roll_step', context, degrees=360 / spec['sides']))
        row = layout.row(); row.scale_y = 1.2
        row.operator('line_pipe.connect_direct', text=i18n.tr('conn_direct', context))
        box = layout.box()
        for key in ('distance', 'radius', 'smooth'): i18n.prop(box, state, key, context)
        box.operator('line_pipe.connect_distance', text=i18n.tr('conn_bridge', context))
    else:
        layout.enabled = connection_ops.ready(context)
        obj = context.active_object
        state = context.scene.line_pipe_connections
        if ports.is_pipe(obj):
            layout.separator()
            layout.label(text=i18n.tr('conn_groups', context))
            layout.label(text=i18n.tr('conn_group_count', context, count=len(ports.members(context.scene, obj))))
            row = layout.row(align=True)
            row.operator('line_pipe.group_pipes', text=i18n.tr('conn_group', context))
            row.operator('line_pipe.group_pipes', text=i18n.tr('conn_ungroup', context)).separate = True
            layout.operator('line_pipe.group_pipes', text=i18n.tr('conn_select_group', context)).select = True
            layout.operator('line_pipe.sync_curvature', text=i18n.tr('conn_curvature', context))
            layout.operator('line_pipe.disconnect', text=i18n.tr('conn_disconnect', context))
            layout.operator('line_pipe.update_connections', text=i18n.tr('conn_update', context))
            if obj.get(connections.PATH):
                layout.operator('line_pipe.update_connections', text=i18n.tr('conn_apply', context)).use_settings = True
        if obj and obj.type == 'MESH':
            if not ports.is_pipe(obj):
                layout.operator('line_pipe.detect_ports',text=i18n.tr('conn_detect',context))
                i18n.prop(layout, state, 'mesh_axis', context)
                layout.operator('line_pipe.register_cylinder', text=i18n.tr('conn_register', context))
            layout.operator('line_pipe.repair_mesh', text=i18n.tr('conn_repair', context))


def context_menu(self, context):
    if not ports.is_pipe(context.active_object):
        if context.active_object and context.active_object.type=='MESH':
            self.layout.operator('line_pipe.detect_ports',text=i18n.tr('conn_detect',context))
        return
    layout = self.layout
    layout.separator()
    layout.operator('line_pipe.sync_curvature', text=i18n.tr('conn_curvature', context))
    layout.operator('line_pipe.connect_direct', text=i18n.tr('conn_direct', context))
    layout.operator('line_pipe.connect_distance', text=i18n.tr('conn_bridge', context))


CLASSES = ()
