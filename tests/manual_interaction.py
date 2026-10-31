"""Disposable installed-ZIP viewport for hardware-input inspection."""
import importlib
import json
import os
from pathlib import Path
import tomllib
import bpy
from mathutils import Euler

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'verification' / 'manual-interaction'
for key in ('BLENDER_USER_CONFIG', 'BLENDER_USER_SCRIPTS', 'BLENDER_USER_EXTENSIONS'):
    assert Path(os.environ[key]).is_relative_to(OUT) and Path(os.environ[key]).is_dir()
assert Path(bpy.utils.user_resource('CONFIG')).is_relative_to(OUT)
version = tomllib.loads((ROOT / 'line_pipe/blender_manifest.toml').read_text())['version']
bpy.ops.extensions.package_install_files(filepath=str(ROOT / 'dist' / ('pipeworks-' + version + '.zip')),
                                         repo='user_default', enable_on_install=True)
addon = importlib.import_module('bl_ext.user_default.line_pipe')
assert addon._registered
bpy.context.preferences.view.show_splash = False
bpy.context.preferences.filepaths.temporary_directory = str(OUT)
area = next(a for a in bpy.context.screen.areas if a.type == 'VIEW_3D')
region = next(r for r in area.regions if r.type == 'WINDOW')
space = area.spaces.active
space.show_region_ui = True
space.region_3d.view_rotation = Euler((1.25, 0, .35)).to_quaternion()
space.region_3d.view_distance = 12
space.region_3d.view_location = (0, 0, 0)
space.region_3d.view_perspective = 'PERSP'
for obj in tuple(bpy.context.scene.objects):
    bpy.data.objects.remove(obj, do_unlink=True)
bpy.ops.mesh.primitive_cube_add(size=2, location=(-3, 0, 0))
bpy.context.object.name = 'Disposable Start Surface'
warp_count = 0
input_events = []
original_wrap = addon.operators.LP_OT_draw.wrap_pointer


def wrapped(self, event):
    global warp_count
    original_wrap(self, event)
    if self._warp_pending is not None:
        warp_count += 1


addon.operators.LP_OT_draw.wrap_pointer = wrapped


class PW_OT_input_monitor(bpy.types.Operator):
    bl_idname = 'wm.pipeworks_input_monitor'
    bl_label = 'PipeWorks Test Input Monitor'

    def invoke(self, context, event):
        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}

    def modal(self, context, event):
        if event.type not in {'TIMER', 'MOUSEMOVE', 'INBETWEEN_MOUSEMOVE'}:
            input_events.append(dict(type=event.type, value=event.value, shift=event.shift,
                                     ctrl=event.ctrl, alt=event.alt, oskey=event.oskey))
        return {'PASS_THROUGH'}


bpy.utils.register_class(PW_OT_input_monitor)
with bpy.context.temp_override(area=area, region=region):
    bpy.ops.wm.pipeworks_input_monitor('INVOKE_DEFAULT')


def tick():
    next(r for r in area.regions if r.type == 'UI').active_panel_category = 'PipeWorks'
    session = addon.operators.session
    route = session.route if session else None
    state = dict(installed_module=addon.__name__, version=version, session=bool(session),
                 keymaps=[dict(type=item.type, shift=item.shift, ctrl=item.ctrl, active=item.active)
                          for _, item in addon._keymaps],
                 input_events=input_events[-30:],
                 mode=session._start_mode if session else None, length=route.length if route else None,
                 points=[list(p) for p in route.points] if route else [],
                 tip=list(route.tip) if route else None, turning=route.turning if route else False,
                 heading=list(route.heading) if route else None,
                 pending_warp=list(session._warp_pending) if session and session._warp_pending is not None else None,
                 follow=bpy.context.scene.line_pipe_settings.follow_tip,
                 guides=bpy.context.scene.line_pipe_settings.show_guides, warps=warp_count,
                 colors=addon.data.guide_colors(), language=addon.i18n.language(),
                 config=bpy.utils.user_resource('CONFIG'),
                 view_location=list(space.region_3d.view_location),
                 rotation=list(space.region_3d.view_rotation), distance=space.region_3d.view_distance)
    (OUT / 'live.json').write_text(json.dumps(state, indent=2))
    command = OUT / 'command.json'
    if command.exists():
        request = json.loads(command.read_text())
        command.unlink()
        if request['command'] == 'quit':
            bpy.ops.wm.quit_blender()
            return None
        if request['command'] == 'capture':
            name = Path(request['name']).name
            bpy.ops.screen.screenshot(filepath=str(OUT / name))
    return .2


bpy.app.timers.register(tick, first_interval=2)
