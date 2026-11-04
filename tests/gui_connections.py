"""Installed-ZIP viewport picking, roll preview, context-menu and Undo checks."""
import importlib
import json
import math
import os
from pathlib import Path
import sys
import traceback
import tomllib
import bpy
from mathutils import Euler, Matrix, Vector
from bpy_extras import view3d_utils

ROOT = Path(__file__).resolve().parents[1]
MANUAL = '--manual' in sys.argv
OUT = ROOT / 'verification' / ('connections-manual' if MANUAL else 'connections-ui')
for key in ('BLENDER_USER_CONFIG','BLENDER_USER_SCRIPTS','BLENDER_USER_EXTENSIONS'):
    assert Path(os.environ[key]).is_relative_to(OUT) and Path(os.environ[key]).is_dir()
assert Path(bpy.utils.user_resource('CONFIG')).is_relative_to(OUT)
version = tomllib.loads((ROOT/'line_pipe/blender_manifest.toml').read_text())['version']
bpy.ops.extensions.package_install_files(filepath=str(ROOT/'dist'/('pipeworks-'+version+'.zip')),
                                         repo='user_default',enable_on_install=True)
addon = importlib.import_module('bl_ext.user_default.line_pipe')
from_module = addon.__name__
c = importlib.import_module(from_module+'.connections')
ports = importlib.import_module(from_module+'.ports')
ops = addon.connection_ops
bpy.context.preferences.view.show_splash=False
bpy.context.preferences.filepaths.temporary_directory=str(OUT)
window=bpy.context.window
area=next(a for a in window.screen.areas if a.type=='VIEW_3D')
region=next(r for r in area.regions if r.type=='WINDOW')
space=area.spaces.active
space.show_region_ui=True
space.region_3d.view_rotation=Euler((1.25,0,.35)).to_quaternion()
space.region_3d.view_location=(0,0,1)
space.region_3d.view_distance=12
space.region_3d.view_perspective='PERSP'
space.shading.color_type='OBJECT'
for obj in tuple(bpy.context.scene.objects):bpy.data.objects.remove(obj,do_unlink=True)
checks,events,measurements=[],[],{}
pointer=[500,400]


def check(name,value):
    assert value,name
    checks.append(name);print('PASS CONNECTION UI:',name,flush=True)


def native(name,points,location,radius=.4,sides=24):
    obj=addon.geometry.create(bpy.context);obj.name=name
    addon.data._updating=True
    try:
        obj.line_pipe.bend_radius=radius
        obj.line_pipe.radial_segments=sides
    finally:addon.data._updating=False
    addon.geometry.update(obj,points,.2,radius,sides,16,store=True)
    obj['_line_pipe_dimensions']=[.2,radius,sides,16]
    obj.location=location
    return obj


moving=native('Moving Pipe',[(0,0,0),(1.5,0,0),(1.5,0,1.5)],(2,0,0))
anchor=native('Anchor Pipe',[(0,0,0),(0,0,2),(1.5,0,2)],(-2,0,0),.25,60)
moving.color=(.92,.53,.13,1);anchor.color=(.18,.55,.8,1)
names=moving.name,anchor.name
original={o.name:o.matrix_world.copy() for o in (moving,anchor)}
bpy.context.view_layer.update()
original={o.name:o.matrix_world.copy() for o in (moving,anchor)}
for obj in bpy.context.selected_objects:obj.select_set(False)
moving.select_set(True);bpy.context.view_layer.objects.active=moving
bpy.context.scene.line_pipe_settings.tool_mode='CONNECT'
if MANUAL:
    bpy.ops.line_pipe.mesh()
    bpy.context.scene.line_pipe_connections.source=moving
    bpy.context.scene.line_pipe_connections.source_port='END'


def pair():return tuple(bpy.context.scene.objects.get(name) for name in names)
def near_matrix(a,b):return max(abs(a[r][col]-b[r][col]) for r in range(4) for col in range(4))<3e-5
def event(kind,value='NOTHING',x=None,y=None,**kwargs):
    if x is not None:pointer[:]=[int(x),int(y)]
    window.event_simulate(type=kind,value=value,x=pointer[0],y=pointer[1],**kwargs)


def click_port(obj,key):
    port=next(p for p in ports.world_ports(obj) if p.key==key)
    point=view3d_utils.location_3d_to_region_2d(region,space.region_3d,port.position)
    event('MOUSEMOVE',x=region.x+point.x,y=region.y+point.y)
    event('LEFTMOUSE','PRESS');event('LEFTMOUSE','RELEASE')


def aligned():
    a,b=pair();pa,pb=ports.read(bpy.context.scene,a,'END',False),ports.read(bpy.context.scene,b,'END',False)
    return (pa.position-pb.position).length<3e-5 and pa.direction.dot(pb.direction)<-.99999


def select_pair():
    a,b=pair()
    for obj in bpy.context.selected_objects:obj.select_set(False)
    b.select_set(True);a.select_set(True);bpy.context.view_layer.objects.active=a


def reset_pose():
    for obj in pair():obj.matrix_world=original[obj.name]
    bpy.context.view_layer.update()


def capture(name):bpy.ops.screen.screenshot(filepath=str(OUT/(name+'.png')))


menu_seen=[]
original_menu=addon.connection_ui.context_menu
def traced_menu(self,context):
    menu_seen.append(True);original_menu(self,context)
if not MANUAL:
    bpy.types.VIEW3D_MT_object_context_menu.remove(original_menu)
    bpy.types.VIEW3D_MT_object_context_menu.append(traced_menu)


def finish():
    bpy.types.VIEW3D_MT_object_context_menu.remove(traced_menu)
    bpy.types.VIEW3D_MT_object_context_menu.append(original_menu)
    (OUT/'results.json').write_text(json.dumps(dict(checks=checks,measurements=measurements,installed_module=from_module),indent=2))
    bpy.ops.wm.quit_blender()


def setup_bridge():
    reset_pose()
    a,b=pair()
    state=bpy.context.scene.line_pipe_connections
    state.source=a;state.source_port='END';state.target=b;state.target_port='END'
    state.distance=10;state.radius=.3;state.smooth=True


def configure_continuation(use_library):
    settings = bpy.context.scene.line_pipe_settings
    if use_library:
        settings.hollow = False
        settings.diameter = .2
        settings.free_sides = False
        settings.radial_segments = 24
        settings.template_length = .8
        saved = addon.fittings.create_fitting(bpy.context, 'ELBOW')
        settings.continuation_fitting = addon.fittings.add_to_library(bpy.context, saved)
        addon.geometry.remove(saved)
        if use_library != 'MISSING':
            settings.free_sides = True
            settings.radial_segments = 37
            saved = addon.fittings.create_fitting(bpy.context, 'ELBOW')
            addon.fittings.add_to_library(bpy.context, saved, settings.continuation_fitting)
            addon.geometry.remove(saved)
        if use_library == 'AUTHORED':
            settings.hollow = True
            settings.diameter = .36
            settings.wall = .025
            generated = addon.fittings.create_fitting(bpy.context, 'ELBOW')
            saved = bpy.data.objects.new('Authored two-mouth elbow', generated.data.copy())
            bpy.context.collection.objects.link(saved)
            addon.geometry.remove(generated)
            addon.fittings.select_object(bpy.context, saved)
            addon.fittings.mark_ports(bpy.context)
            settings.continuation_fitting = addon.fittings.add_to_library(bpy.context, saved)
            addon.geometry.remove(saved)
    else:
        settings.continuation_fitting = 'CYLINDER'
    settings.start_mode = 'COORDINATES'
    settings.origin = (-3, -3, 0)
    settings.direction = 'X'
    settings.diameter = .36
    settings.bend_radius = .45
    settings.hollow = bool(use_library)
    settings.wall = .025
    settings.free_sides = True
    settings.radial_segments = 37
    measurements['before_objects'] = len(bpy.context.scene.objects)
    measurements['before_links'] = len(bpy.context.scene.line_pipe_connections.links)


def extend_in_heading():
    drawing = addon.operators.session
    mouse = drawing._mouse_base + drawing._extension_scale.normalized() * 110
    event('MOUSEMOVE', x=region.x + mouse.x, y=region.y + mouse.y)


def fitted_profile():
    drawing = addon.operators.session
    if drawing is None or len(drawing._insertions) != 1:
        return False
    scene = bpy.context.scene
    fitting = drawing._insertions[0].fitting
    inlet, outlet = (ports.read(scene, fitting, key) for key in ('START', 'END'))
    return (inlet.sides == 37 and abs(inlet.diameter - .36) < 1e-6
            and abs(inlet.bore - .31) < 1e-6
            and (drawing.route.tip - outlet.position).length < 1e-5
            and drawing.route.heading.dot(outlet.direction) > .9999
            and abs(inlet.direction.dot(outlet.direction)) < 1e-4)


def check_fitting_prompts():
    previous = bpy.context.window_manager.clipboard
    preferences = bpy.context.preferences.addons[from_module].preferences
    language = preferences.language
    try:
        for lang, phrase in [('EN', 'Fitting I want'), ('ZH', '我想要的管件')]:
            preferences.language = lang
            assert bpy.ops.line_pipe.copy_fitting_prompt() == {'FINISHED'}
            prompt = bpy.context.window_manager.clipboard
            check('AI fitting prompt copies the full ' + lang + ' specification',
                  phrase in prompt and '576' in prompt and '60' in prompt and len(prompt) > 500)
    finally:
        preferences.language = language
        bpy.context.window_manager.clipboard = previous


if not MANUAL:
    events.extend([
        lambda:bpy.ops.ed.undo_push(message='Before PipeWorks connection'),
        lambda:bpy.ops.line_pipe.pick_port('INVOKE_DEFAULT',role='pair'),
        lambda:click_port(pair()[1],'END'),
        lambda:check('first viewport click stages the reference without committing the pair',
                     ops.picker is not None and ops.picker.first.obj==pair()[1] and ops.picker.first.key=='END'),
        lambda:click_port(pair()[0],'END'),
        lambda:check('second click commits moving and reference in the correct order',
                     bpy.context.scene.line_pipe_connections.source==pair()[0]
                     and bpy.context.scene.line_pipe_connections.source_port=='END'
                     and bpy.context.scene.line_pipe_connections.target==pair()[1]
                     and bpy.context.scene.line_pipe_connections.target_port=='END' and ops.picker is None),
        lambda:bpy.ops.line_pipe.connect_direct('INVOKE_DEFAULT'),
        lambda:check('direct dialog previews alignment without a link',ops.preview is not None and aligned()
                     and pair()[0].line_pipe.radial_segments==24 and len(bpy.context.scene.line_pipe_connections.links)==0),
        lambda:event('ESC','PRESS'),
        lambda:check('cancel restores exact source and anchor poses',ops.preview is None and
                     all(near_matrix(o.matrix_world,original[o.name]) for o in pair())),
        lambda:bpy.ops.line_pipe.connect_direct('INVOKE_DEFAULT'),
        lambda:setattr(ops.preview,'roll',math.pi/4),
        lambda:ops.preview.check(bpy.context),
        lambda:capture('direct-roll-preview'),
        lambda:event('RET','PRESS'),
        lambda:check('confirm creates exactly one direct link',aligned() and len(bpy.context.scene.line_pipe_connections.links)==1),
        lambda:check('confirmed roll snaps to the first port’s vertex grid',
                     abs(bpy.context.scene.line_pipe_connections.links[0].roll-math.radians(48))<1e-6),
        lambda:check('second pipe uses the first pipe’s edge count',
                     pair()[0].line_pipe.radial_segments==60 and pair()[1].line_pipe.radial_segments==60),
        lambda:bpy.ops.ed.undo(),
        lambda:check('native Undo restores direct placement',len(bpy.context.scene.line_pipe_connections.links)==0
                     and pair()[0].line_pipe.radial_segments==24
                     and all(near_matrix(o.matrix_world,original[o.name]) for o in pair())),
        lambda:bpy.ops.ed.redo(),
        lambda:check('native Redo restores direct link and pose',len(bpy.context.scene.line_pipe_connections.links)==1 and aligned()),
        lambda:c.disconnect(bpy.context,pair()[0]),setup_bridge,
        lambda:bpy.ops.ed.undo_push(message='Before fixed-end bridge'),
        lambda:bpy.ops.line_pipe.connect_distance('EXEC_DEFAULT',True),
        lambda:check('distance operator leaves original poses fixed',all(near_matrix(o.matrix_world,original[o.name]) for o in pair())),
        lambda:check('distance operator creates mesh and saved link',len(bpy.context.scene.line_pipe_connections.links)==1
                     and bpy.context.scene.line_pipe_connections.links[0].connector.type=='MESH'),
        lambda:capture('smooth-distance'),
        lambda:bpy.ops.ed.undo(),
        lambda:check('native Undo removes bridge and occupancy',len(bpy.context.scene.line_pipe_connections.links)==0),
        lambda:bpy.ops.ed.redo(),
        lambda:check('native Redo regenerates one bridge',len(bpy.context.scene.line_pipe_connections.links)==1),
        lambda:c.disconnect(bpy.context,pair()[0]),reset_pose,
        lambda:[o.__setitem__(ports.GROUP,o.get(ports.UID)) for o in pair()],select_pair,
        lambda:event('RIGHTMOUSE','PRESS',x=region.x+region.width*.4,y=region.y+region.height*.4),
        lambda:check('native context menu includes integration actions',bool(menu_seen)),
        lambda:capture('context-menu-english'),lambda:event('ESC','PRESS'),
        lambda:setattr(pair()[0].line_pipe,'bend_radius',.6),
        lambda:bpy.ops.ed.undo_push(message='Before group curvature'),
        lambda:bpy.ops.line_pipe.sync_curvature('EXEC_DEFAULT',True),
        lambda:check('curvature operator matches the first selected reference',abs(pair()[0].line_pipe.bend_radius-.25)<1e-6),
        lambda:bpy.ops.ed.undo(),
        lambda:check('native Undo restores previous group curvature',abs(pair()[0].line_pipe.bend_radius-.6)<1e-6),
        lambda:bpy.ops.ed.redo(),
        lambda:check('native Redo restores matched group curvature',abs(pair()[0].line_pipe.bend_radius-.25)<1e-6),
        lambda:setattr(bpy.context.scene.line_pipe_settings,'tool_mode','GROUPS'),
        lambda:bpy.ops.line_pipe.language(),
        lambda:capture('connections-chinese'),
        lambda:check('Chinese tooltips cover both connection modes', '移动' in bpy.types.PW_OT_connect_direct.description(bpy.context,None)
                     if hasattr(bpy.types,'PW_OT_connect_direct') else addon.i18n.tr('conn_direct_tip').startswith('移动')),
        lambda:bpy.ops.line_pipe.language(),
        lambda:bpy.ops.line_pipe.pick_port('INVOKE_DEFAULT',role='target'),
        lambda:event('ESC','PRESS'),
        lambda:check('picker cancel removes modal drawing handles',ops.picker is None),
        lambda:setattr(bpy.context.scene.line_pipe_settings,'hollow',True),
        lambda:setattr(bpy.context.scene.line_pipe_settings,'start_mode','CURSOR'),
        lambda:setattr(bpy.context.scene.line_pipe_settings,'direction','X'),
        lambda:event('MOUSEMOVE',x=region.x+region.width*.32,y=region.y+region.height*.5),
        lambda:bpy.ops.line_pipe.draw('INVOKE_DEFAULT'),
        lambda:event('MOUSEMOVE',x=region.x+region.width*.42,y=region.y+region.height*.5),
        lambda:event('MOUSEMOVE',x=region.x+region.width*.53,y=region.y+region.height*.5),
        lambda:check('hollow drawing previews a moving mesh',addon.operators.session is not None
                     and addon.operators.session.route.length > .05 and addon.operators.session.obj.type=='MESH'),
        lambda:event('RET','PRESS'),
        lambda:check('hollow drawing commits the default 60-edge bore',addon.operators.session is None
                     and bpy.context.active_object.line_pipe.hollow
                     and abs(ports.read(bpy.context.scene,bpy.context.active_object,'END').bore-.16)<1e-6
                     and ports.read(bpy.context.scene,bpy.context.active_object,'END').sides==60),
        lambda:setattr(bpy.context.scene.line_pipe_settings,'tool_mode','PORTS'),
        lambda:bpy.ops.line_pipe.mark_ports(),
        lambda:capture('marked-hollow-ports'),
        lambda:setattr(bpy.context.scene.line_pipe_settings,'tool_mode','LIBRARY'),
        check_fitting_prompts,
        lambda:bpy.ops.line_pipe.save_fitting(),
        lambda:capture('fitting-library'),
        lambda:configure_continuation(True),
        lambda:bpy.ops.ed.undo_push(message='Before drawing with E'),
        lambda:event('MOUSEMOVE',x=region.x+region.width*.35,y=region.y+region.height*.5),
        lambda:bpy.ops.line_pipe.draw('INVOKE_DEFAULT',True),
        lambda:event('MOUSEMOVE',x=region.x+region.width*.36,y=region.y+region.height*.5),
        extend_in_heading,
        lambda:event('E','PRESS'),
        lambda:event('E','RELEASE'),
        lambda:check('E inserts a saved elbow fitted to the current hollow profile and resumes at its outlet',fitted_profile()),
        lambda:event('E','PRESS'),
        lambda:event('E','RELEASE'),
        lambda:check('E can attach directly to an existing fitting',len(addon.operators.session._insertions)==2),
        lambda:event('BACK_SPACE','PRESS'),
        lambda:check('Backspace retracts the last fitting and restores the preceding outlet',fitted_profile()),
        extend_in_heading,
        lambda:check('mouse extends from the fitted outlet',addon.operators.session.route.length>.05),
        lambda:event('RET','PRESS'),
        lambda:check('Enter saves three editable pieces and two joints',
                     addon.operators.session is None and len(bpy.context.scene.objects)==measurements['before_objects']+3
                     and len(bpy.context.scene.line_pipe_connections.links)==measurements['before_links']+2),
        lambda:capture('continued-library-elbow'),
        lambda:bpy.ops.ed.undo(),
        lambda:check('Undo retracts the entire continued drawing',
                     len(bpy.context.scene.objects)==measurements['before_objects']
                     and len(bpy.context.scene.line_pipe_connections.links)==measurements['before_links']),
        lambda:bpy.ops.ed.redo(),
        lambda:check('Redo restores the continued drawing and its joints',
                     len(bpy.context.scene.objects)==measurements['before_objects']+3
                     and len(bpy.context.scene.line_pipe_connections.links)==measurements['before_links']+2),
        lambda:configure_continuation(False),
        lambda:event('MOUSEMOVE',x=region.x+region.width*.35,y=region.y+region.height*.5),
        lambda:bpy.ops.line_pipe.draw('INVOKE_DEFAULT',True),
        lambda:event('MOUSEMOVE',x=region.x+region.width*.36,y=region.y+region.height*.5),
        extend_in_heading,
        lambda:event('E','PRESS'),
        lambda:event('E','RELEASE'),
        lambda:check('E attaches a cylinder to the solid Curve preview',len(addon.operators.session._insertions)==1),
        lambda:event('ESC','PRESS'),
        lambda:check('Escape removes all provisional objects and leaves existing joints',
                     addon.operators.session is None and len(bpy.context.scene.objects)==measurements['before_objects']
                     and len(bpy.context.scene.line_pipe_connections.links)==measurements['before_links']),
        lambda:configure_continuation('MISSING'),
        lambda:event('MOUSEMOVE',x=region.x+region.width*.35,y=region.y+region.height*.5),
        lambda:bpy.ops.line_pipe.draw('INVOKE_DEFAULT',True),
        lambda:event('MOUSEMOVE',x=region.x+region.width*.36,y=region.y+region.height*.5),
        extend_in_heading,
        lambda:event('E','PRESS'),
        lambda:event('E','RELEASE'),
        lambda:check('Missing library size gives a notice and keeps the drawing intact',
                     addon.operators.session._notice[0]=='continuation_variant_missing'
                     and not addon.operators.session._insertions
                     and addon.operators.session.route.length>.05
                     and len(bpy.context.scene.objects)==measurements['before_objects']+1),
        lambda:event('ESC','PRESS'),
        lambda:configure_continuation('AUTHORED'),
        lambda:event('MOUSEMOVE',x=region.x+region.width*.35,y=region.y+region.height*.5),
        lambda:bpy.ops.line_pipe.draw('INVOKE_DEFAULT',True),
        lambda:event('MOUSEMOVE',x=region.x+region.width*.36,y=region.y+region.height*.5),
        extend_in_heading,
        lambda:event('E','PRESS'),
        lambda:event('E','RELEASE'),
        lambda:check('Authored mesh resumes from its named outlet',
                     len(addon.operators.session._insertions)==1
                     and addon.operators.session._insertions[0].ports==('P1','P2')),
        lambda:event('E','PRESS'),
        lambda:event('E','RELEASE'),
        lambda:event('RET','PRESS'),
        lambda:check('Authored mouths commit consecutive fittings and saved link keys',
                     addon.operators.session is None
                     and len(bpy.context.scene.objects)==measurements['before_objects']+3
                     and len(bpy.context.scene.line_pipe_connections.links)==measurements['before_links']+2),
        finish,
    ])


def tick():
    try:
        next(r for r in area.regions if r.type=='UI').active_panel_category='PipeWorks'
        with bpy.context.temp_override(window=window,area=area,region=region):
            if events:events.pop(0)()
            command=OUT/'command.json'
            if MANUAL and command.exists():
                request=json.loads(command.read_text());command.unlink()
                if request['command']=='quit':bpy.ops.wm.quit_blender();return None
                if request['command']=='capture':capture(request['name'])
        if MANUAL:
            state=bpy.context.scene.line_pipe_connections
            (OUT/'live.json').write_text(json.dumps(dict(source=state.source.name if state.source else None,
                source_port=state.source_port,target=state.target.name if state.target else None,target_port=state.target_port,
                picker=bool(ops.picker),preview=bool(ops.preview),links=len(state.links),language=addon.i18n.language())))
    except Exception:
        (OUT/'failure.txt').write_text(traceback.format_exc());traceback.print_exc()
        capture('failure')
        (OUT/'failure-state.json').write_text(json.dumps(dict(preview=bool(ops.preview),
            roll=ops.preview.roll if ops.preview else None, aligned=aligned(),links=len(bpy.context.scene.line_pipe_connections.links),
            operators=[op.bl_idname if op else None for op in window.modal_operators])))
        if not MANUAL:bpy.ops.wm.quit_blender();return None
    return .25

bpy.app.timers.register(tick,first_interval=3)
