# SPDX-License-Identifier: GPL-3.0-or-later
"""PipeWorks: draw pipes, connect ports and match group bend radii."""
import bpy
from bpy.app.handlers import persistent
from bpy.props import PointerProperty
from . import data, operators, ui, connection_ops, connection_ui, fittings

bl_info = {
    'name': 'PipeWorks', 'author': 'O_Pisces', 'version': (0, 5, 1),
    'blender': (5, 2, 0), 'location': 'View3D > Sidebar > PipeWorks',
    'description': 'Draw pipes, connect ports and match group bend radii', 'category': 'Add Curve',
}
_registered = False
_keymaps = []
CLASSES = data.CLASSES + operators.CLASSES + ui.CLASSES + connection_ops.CLASSES + connection_ui.CLASSES + fittings.CLASSES


@persistent
def before_scene_change(_):
    data.abort_preset_drag()
    connection_ops.abort()
    operators.abort()


def register():
    global _registered
    if _registered:
        return
    for cls in CLASSES:
        bpy.utils.register_class(cls)
    bpy.types.Scene.line_pipe_settings = PointerProperty(type=data.LP_Settings)
    bpy.types.Object.line_pipe = PointerProperty(type=data.LP_Object)
    bpy.types.WindowManager.line_pipe_colors = PointerProperty(type=data.LP_GuideColors)
    bpy.types.WindowManager.line_pipe_preset_drag = data.preset_drag_property('EN')
    bpy.types.WindowManager.line_pipe_preset_drag_zh = data.preset_drag_property('ZH')
    bpy.types.Scene.line_pipe_connections = PointerProperty(type=connection_ops.PW_ConnectionSettings)
    bpy.types.VIEW3D_MT_object_context_menu.append(connection_ui.context_menu)
    keyconfig = bpy.context.window_manager.keyconfigs.addon
    if keyconfig:
        keymap = keyconfig.keymaps.new(name='Object Mode', space_type='EMPTY')
        item = keymap.keymap_items.new('line_pipe.draw', type='P', value='PRESS', ctrl=True, head=True)
        item.properties.quick_start = True
        _keymaps.append((keymap, item))
    for handlers in (bpy.app.handlers.save_pre, bpy.app.handlers.load_pre, bpy.app.handlers.undo_pre):
        if before_scene_change not in handlers:
            handlers.append(before_scene_change)
    fittings.register_overlay()
    _registered = True


def unregister():
    global _registered
    if not _registered:
        return
    data.abort_preset_drag()
    connection_ops.abort()
    operators.abort()
    fittings.unregister_overlay()
    data.cancel_preferences_save()
    for keymap, item in _keymaps:
        keymap.keymap_items.remove(item)
    _keymaps.clear()
    for handlers in (bpy.app.handlers.save_pre, bpy.app.handlers.load_pre, bpy.app.handlers.undo_pre):
        if before_scene_change in handlers:
            handlers.remove(before_scene_change)
    del bpy.types.Object.line_pipe
    del bpy.types.Scene.line_pipe_settings
    del bpy.types.WindowManager.line_pipe_colors
    del bpy.types.WindowManager.line_pipe_preset_drag
    del bpy.types.WindowManager.line_pipe_preset_drag_zh
    del bpy.types.Scene.line_pipe_connections
    bpy.types.VIEW3D_MT_object_context_menu.remove(connection_ui.context_menu)
    for cls in reversed(CLASSES):
        bpy.utils.unregister_class(cls)
    _registered = False
