# SPDX-License-Identifier: GPL-3.0-or-later
"""PipeWorks: interactive solid pipes, with compatible line_pipe saved data."""
import bpy
from bpy.app.handlers import persistent
from bpy.props import PointerProperty
from . import data, operators, ui

bl_info = {
    'name': 'PipeWorks', 'author': 'O_Pisces', 'version': (0, 1, 1),
    'blender': (5, 2, 0), 'location': 'View3D > Sidebar > PipeWorks',
    'description': 'Draw solid procedural pipes with hold-to-turn routing', 'category': 'Add Curve',
}
_registered = False
_keymaps = []
CLASSES = data.CLASSES + operators.CLASSES + ui.CLASSES


@persistent
def before_scene_change(_):
    operators.abort()


def register():
    global _registered
    if _registered:
        return
    for cls in CLASSES:
        bpy.utils.register_class(cls)
    bpy.types.Scene.line_pipe_settings = PointerProperty(type=data.LP_Settings)
    bpy.types.Object.line_pipe = PointerProperty(type=data.LP_Object)
    keyconfig = bpy.context.window_manager.keyconfigs.addon
    if keyconfig:
        keymap = keyconfig.keymaps.new(name='3D View', space_type='VIEW_3D')
        item = keymap.keymap_items.new('line_pipe.draw', type='P', value='PRESS')
        item.properties.quick_start = True
        _keymaps.append((keymap, item))
    for handlers in (bpy.app.handlers.save_pre, bpy.app.handlers.load_pre, bpy.app.handlers.undo_pre):
        if before_scene_change not in handlers:
            handlers.append(before_scene_change)
    _registered = True


def unregister():
    global _registered
    if not _registered:
        return
    operators.abort()
    for keymap, item in _keymaps:
        keymap.keymap_items.remove(item)
    _keymaps.clear()
    for handlers in (bpy.app.handlers.save_pre, bpy.app.handlers.load_pre, bpy.app.handlers.undo_pre):
        if before_scene_change in handlers:
            handlers.remove(before_scene_change)
    del bpy.types.Object.line_pipe
    del bpy.types.Scene.line_pipe_settings
    for cls in reversed(CLASSES):
        bpy.utils.unregister_class(cls)
    _registered = False
