"""Build a disposable, self-authored integration example; no source scenes are read."""
from pathlib import Path
import sys
import math
import bpy
from mathutils import Matrix, Euler, Vector

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import line_pipe as addon
from line_pipe import geometry,connections as c,ports,data
addon.register()
for obj in tuple(bpy.context.scene.objects):bpy.data.objects.remove(obj,do_unlink=True)


def pipe(name,points,offset=(0,0,0),radius=.35,color=(.7,.7,.7,1),mesh=False,sides=60):
    obj=geometry.create(bpy.context);obj.name=name
    data._updating=True
    try:
        obj.line_pipe.bend_radius=radius
        obj.line_pipe.radial_segments=sides
    finally:data._updating=False
    geometry.update(obj,[Vector(p)+Vector(offset) for p in points],.2,radius,sides,16,store=True)
    obj['_line_pipe_dimensions']=[.2,radius,sides,16];obj.color=color
    if mesh:
        for selected in bpy.context.selected_objects:selected.select_set(False)
        obj.select_set(True);bpy.context.view_layer.objects.active=obj
        bpy.ops.line_pipe.mesh()
    return obj


blue=(.16,.46,.73,1);orange=(.87,.46,.11,1);green=(.21,.64,.41,1)
anchor=pipe('01 Direct | Anchor',[(0,0,0),(0,0,2)],(-7,0,0),color=blue)
moving=pipe('01 Direct | Docked and rolled',[(0,0,0),(1.5,0,0),(1.5,0,1.5)],(-4,0,0),color=orange)
bpy.context.view_layer.update()
c.direct(bpy.context,moving,'END',anchor,'END',math.radians(35))

for label,offset,smooth in [('02 Smooth',(-3,0,0),True),('03 Angular',(3,0,0),False)]:
    a=pipe(label+' | A',[(0,0,0),(1,0,0)],offset,color=blue)
    b=pipe(label+' | B',[(4,2,0),(5,2,0)],offset,color=blue)
    bpy.context.view_layer.update()
    bridge=c.bridge(bpy.context,a,'END',b,'START',.35,smooth,10)
    bridge.name=label+' | Generated bridge';bridge.color=orange

matched=pipe('04 Curvature | Matched group',[(0,0,0),(2,0,0),(2,0,2)],(-5,5,0),radius=.6,color=green,mesh=True)
reference=pipe('04 Curvature | Reference group R 0.25',[(0,0,0),(2,0,0),(2,0,2)],(0,5,0),radius=.25,color=blue)
matched.rotation_euler=(0,.2,.25);reference.rotation_euler=(.1,-.15,-.3)
bpy.context.view_layer.update()
for obj in bpy.context.selected_objects:obj.select_set(False)
reference.select_set(True);matched.select_set(True);bpy.context.view_layer.objects.active=matched
c.sync_curvature(bpy.context)

trial=pipe('TRY | Moving Mesh',[(0,0,0),(1.5,0,0),(1.5,0,1.5)],(-2,-5,0),color=orange,mesh=True,sides=24)
trial_target=pipe('TRY | Anchor Curve',[(0,0,0),(0,0,2),(1.5,0,2)],(3,-5,0),radius=.25,color=blue)
state=bpy.context.scene.line_pipe_connections
state.source=trial;state.source_port='END';state.target=trial_target;state.target_port='END'
state.distance=10;state.radius=.35;state.smooth=True
bpy.context.scene.line_pipe_settings.tool_mode='CONNECT'
for obj in bpy.context.selected_objects:obj.select_set(False)
trial.select_set(True);bpy.context.view_layer.objects.active=trial
for screen in bpy.data.screens:
    for area in screen.areas:
        if area.type=='VIEW_3D':
            space=area.spaces.active;space.show_region_ui=True
            space.shading.color_type='OBJECT'
            space.region_3d.view_rotation=Euler((1.23,0,.3)).to_quaternion()
            space.region_3d.view_location=(0,0,1)
            space.region_3d.view_distance=23
            space.region_3d.view_perspective='PERSP'
text=bpy.data.texts.new('PipeWorks - Read Me')
text.write('''PipeWorks 0.4.0 connection example

01: whole-group rigid docking with roll.
02: smooth fixed-end bridging. 03: angular fixed-end bridging.
04: independently rotated groups matched to the first selected reference radius.
TRY: 24-edge moving Mesh and 60-edge reference Curve, preset in Connect.
Choose Direct Connection to preview roll, or Distance Connection to generate a bridge.
Undo returns to this free pair. Groups tab or object context menu matches curvature.
Ctrl+P starts drawing; B returns the pointer at each bend; navigation feedback is 50%.

简体中文
01：整组直接吸附并滚转。02：平滑距离补管。03：折线距离补管。
04：两个独立旋转的组，按先选的基准组统一曲率。
TRY：24 边移动 Mesh 和 60 边基准 Curve，连接页已选好两个端口。
点直接连接预览滚转，或点距离连接生成补管；撤销可恢复。
分组页或物体右键菜单提供统一曲率。Ctrl+P 画管，B 回位，导航反馈为 50%。
''')
out=ROOT/'examples';out.mkdir(exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=str(out/'pipeworks-connections-0.4.0.blend'))
print('CONNECTION_EXAMPLE_OK',len(state.links),'links',flush=True)
