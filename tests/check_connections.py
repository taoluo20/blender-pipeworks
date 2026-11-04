"""Disposable connection, converted-mesh and rotated-group acceptance checks."""
import json
import math
from pathlib import Path
import sys
import time
import bpy
import bmesh
from mathutils import Matrix, Euler, Vector

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'verification/connections'
OUT.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(ROOT))
import line_pipe as addon
from line_pipe import geometry, ports, connections as c, connection_geometry as cg, data
checks, timings = [], []


def check(name, condition):
    assert condition, name
    checks.append(name)
    print('PASS CONNECTION:', name, flush=True)


def refused(name, callback, key):
    before = len(bpy.data.objects), len(bpy.data.meshes), len(bpy.data.curves), len(bpy.context.scene.line_pipe_connections.links)
    try: callback()
    except ports.ConnectionError as error: check(name, str(error) == key)
    else: raise AssertionError(name + ' was accepted')
    check(name + ' is atomic', before == (len(bpy.data.objects), len(bpy.data.meshes), len(bpy.data.curves), len(bpy.context.scene.line_pipe_connections.links)))


def near(a, b): return (Vector(a)-Vector(b)).length < 3e-5
def matrix_near(a, b): return max(abs(a[r][col]-b[r][col]) for r in range(4) for col in range(4)) < 3e-5


def native(points, radius=.4, diameter=.2, mesh=False):
    obj = geometry.create(bpy.context)
    data._updating = True
    try: obj.line_pipe.diameter, obj.line_pipe.bend_radius = diameter, radius
    finally: data._updating = False
    geometry.update(obj, points, diameter, radius, 32, 16, store=True)
    obj['_line_pipe_dimensions'] = [diameter, radius, 32, 16]
    if mesh:
        for selected in bpy.context.selected_objects: selected.select_set(False)
        obj.select_set(True); bpy.context.view_layer.objects.active = obj
        bpy.ops.line_pipe.mesh()
    return obj


def reset():
    bpy.context.scene.line_pipe_connections.links.clear()
    for obj in list(bpy.context.scene.objects):
        block = obj.data
        bpy.data.objects.remove(obj, do_unlink=True)
        if block and block.users == 0 and isinstance(block, (bpy.types.Mesh, bpy.types.Curve)): c.discard(block)


def solid(obj, label):
    bpy.context.view_layer.update()
    mesh = cg.evaluated_mesh(obj, bpy.context.evaluated_depsgraph_get())
    try:
        result = cg.topology(mesh)
        check(label + ' closed manifold', result['nonmanifold'] == 0)
        check(label + ' has no degenerate faces', result['degenerate'] == 0)
        check(label + ' positive solid volume', result['volume'] > 0)
        check(label + ' no nonadjacent triangle crossings', not cg.self_intersections(mesh))
    finally: bpy.data.meshes.remove(mesh)


def legacy_elbow(radius=.5):
    recipe = dict(kind='ORTHOGONAL', points=[[0,0,0],[0,0,radius],[radius,0,radius]],
                  diameter=.2, bore=.16, radius=radius, smooth=True, sides=32, steps=16)
    obj = bpy.data.objects.new('Legacy elbow', cg.mesh_from_recipe(recipe))
    bpy.context.collection.objects.link(obj)
    obj['pipe_component'] = dict(enabled=True, uid='old-' + obj.name, group_id='old-network', kind=1,
        diameter=.2, wall=.02, bend_radius=radius, segments=32,
        ports=[dict(key='P1', position=[0,0,0], direction=[0,0,-1], radial=[1,0,0], diameter=.2),
               dict(key='P2', position=[radius,0,radius], direction=[1,0,0], radial=[0,0,-1], diameter=.2)])
    return obj


addon.register()
for source_key, target_key in (('START','START'),('START','END'),('END','START'),('END','END')):
    reset()
    a = native([(0,0,0),(2,0,0),(2,2,0)])
    extra = native([(0,0,0),(0,0,1)])
    extra[ports.GROUP] = ports.group_id(a)
    b = native([(0,0,0),(0,0,2)])
    a.matrix_world = Matrix.Translation((4,-2,3)) @ Euler((.3,.7,-.5)).to_matrix().to_4x4()
    extra.matrix_world = Matrix.Translation((6,1,1))
    b.matrix_world = Matrix.Translation((-1,3,2)) @ Euler((-.4,.2,1.1)).to_matrix().to_4x4()
    bpy.context.view_layer.update()
    old = {o:o.matrix_world.copy() for o in (a,extra,b)}
    blocks = a.data, extra.data, b.data
    before_relative = a.matrix_world.inverted() @ extra.matrix_world
    c.direct_plan(bpy.context.scene, a, source_key, b, target_key, math.pi/3)
    check(source_key+target_key+' planning is read-only', all(matrix_near(o.matrix_world,m) for o,m in old.items()))
    c.direct(bpy.context, a, source_key, b, target_key, math.pi/3)
    pa, pb = ports.read(bpy.context.scene,a,source_key,False), ports.read(bpy.context.scene,b,target_key,False)
    check(source_key+target_key+' centers coincide', near(pa.position,pb.position))
    check(source_key+target_key+' outward normals oppose', pa.direction.dot(pb.direction) < -.99999)
    check(source_key+target_key+' selected roll snaps to a matching vertex',
          abs(addon.port_rings.phase_offset(pb.radial, pa.radial, -pb.direction, pa.sides)) < 1e-4
          and abs(bpy.context.scene.line_pipe_connections.links[-1].roll - 5*math.tau/32) < 1e-6)
    check(source_key+target_key+' moves whole source group rigidly', matrix_near(a.matrix_world.inverted() @ extra.matrix_world,before_relative))
    check(source_key+target_key+' anchor and data unchanged', matrix_near(b.matrix_world,old[b]) and blocks == (a.data,extra.data,b.data))
    check(source_key+target_key+' groups and occupancy merge', ports.group_id(a)==ports.group_id(b)==ports.group_id(extra)
          and ports.occupied(bpy.context.scene,a,source_key) and ports.occupied(bpy.context.scene,b,target_key))
    refused('occupied endpoint',lambda:c.direct(bpy.context,a,source_key,b,target_key),'occupied_port')

reset()
a = native([(0,0,0),(2,0,0),(2,2,0)], mesh=True)
b = native([(0,0,0),(0,0,2)])
b.location = (4,0,0); bpy.context.view_layer.update()
check('converted mesh retains both ports without the old mesh registry', a.type=='MESH' and len(ports.world_ports(a))==2)
c.direct(bpy.context,a,'END',b,'START')
check('converted mesh docks to an editable drawn curve', near(ports.read(bpy.context.scene,a,'END',False).position,ports.read(bpy.context.scene,b,'START',False).position))
a.line_pipe.bend_radius = .25
solid(a,'converted mesh parameter rebuild')
check('converted mesh keeps endpoint metadata after parameter rebuild', len(ports.world_ports(a))==2)

reset()
bare=native([(0,0,0),(2,0,0),(2,2,0)],radius=.35,mesh=True)
del bare['line_pipe_ports_v1'];del bare['line_pipe_route_v1']
count=c.detect_mesh_ports(bare)
check('bare bent mesh recovers two genuine ports',count==2)
check('bare circular elbow recovers verified curvature',abs(c.recipe_for(bare)['radius']-.35)<2e-4)
straight=native([(0,0,0),(0,0,2)],mesh=True)
del straight['line_pipe_ports_v1'];del straight['line_pipe_route_v1']
check('bare solid cylinder recovers two ends',c.detect_mesh_ports(straight)==2)
check('a long straight pipe needs no roll control',not c.can_roll(bpy.context.scene,straight))

for smooth in (True,False):
    reset()
    a=native([(0,0,0),(1,0,0)])
    b=native([(1.25,0,0),(2.25,0,0)])
    bpy.context.view_layer.update()
    turn=Euler((.36,.2,.4)).to_matrix().to_4x4()
    a.matrix_world=turn @ a.matrix_world;b.matrix_world=turn @ b.matrix_world
    bpy.context.view_layer.update()
    bridge=c.bridge(bpy.context,a,'END',b,'START',.4,smooth,5)
    check('short facing gap remains straight '+str(smooth),len(c.recipe_for(bridge)['points'])==2)
    check('short facing gap preserves length '+str(smooth),
          abs((ports.world_ports(bridge)[1].position-ports.world_ports(bridge)[0].position).length-.25)<1e-5)
    solid(bridge,'short straight '+str(smooth))

cases = [
    ('straight',[(3,0,0),(4,0,0)],'START'),
    ('offset S',[(4,2,0),(5,2,0)],'START'),
    ('spatial 90',[(4,2,3),(4,2,4)],'START'),
    ('U',[(0,2,0),(1,2,0)],'END'),
    ('return detour',[(2,0,0),(3,0,0)],'END'),
]
for smooth in (True,False):
    for label, points, key in cases:
        reset()
        a = native([(0,0,0),(1,0,0)])
        b = native(points)
        bpy.context.view_layer.update()
        matrices = a.matrix_world.copy(), b.matrix_world.copy()
        pa,pb = ports.read(bpy.context.scene,a,'END'),ports.read(bpy.context.scene,b,key)
        started = time.perf_counter()
        bridge = c.bridge(bpy.context,a,'END',b,key,.3,smooth,10)
        timings.append((label,smooth,time.perf_counter()-started))
        ends = ports.world_ports(bridge)
        check(label+str(smooth)+' fixed endpoint positions', near(ends[0].position,pa.position) and near(ends[1].position,pb.position))
        check(label+str(smooth)+' tangent-aligned endpoints', ends[0].direction.dot(pa.direction)<-.99999 and ends[1].direction.dot(pb.direction)<-.99999)
        check(label+str(smooth)+' original pipes remain fixed', matrix_near(a.matrix_world,matrices[0]) and matrix_near(b.matrix_world,matrices[1]))
        solid(bridge,label+str(smooth))

reset()
a=native([(0,0,0),(1,0,0)])
b=native([(5,2,2),(6,2,2)])
b.rotation_euler=(.2,.6,.7); bpy.context.view_layer.update()
for smooth in (True,False):
    bridge=c.bridge(bpy.context,a,'END',b,'START',.3,smooth,20)
    solid(bridge,'skew '+str(smooth))
    c.disconnect(bpy.context,bridge)

reset()
a=native([(0,0,0),(1,0,0)])
b=native([(10,0,0),(11,0,0)])
bpy.context.view_layer.update()
refused('distance range',lambda:c.bridge(bpy.context,a,'END',b,'START',.3,True,2),'connection_range')
refused('unsafe radius',lambda:c.bridge(bpy.context,a,'END',b,'START',.01,True,20),'bad_radius')

reset()
old=legacy_elbow()
check('unloaded old Pipe Assembly file exposes P1 and P2', [p.key for p in ports.world_ports(old)]==['P1','P2'])
check('old wall gives genuine bore', abs(ports.world_ports(old)[0].bore-.16)<1e-6)
old_b=legacy_elbow();old_b.location=(3,1,1);bpy.context.view_layer.update()
hollow=c.bridge(bpy.context,old,'P2',old_b,'P1',.3,True,10)
check('legacy hollow meshes connect without requiring the old addon',abs(ports.world_ports(hollow)[0].bore-.16)<1e-6)
solid(hollow,'legacy hollow bridge')

reset()
old=legacy_elbow();old.location=(3,1,0)
drawn=native([(0,0,0),(1,0,0)])
bpy.context.view_layer.update()
mixed=c.bridge(bpy.context,drawn,'END',old,'P1',.3,True,10)
check('solid drawing connects to a same-diameter hollow legacy part',c.recipe_for(mixed)['bore']==0)
solid(mixed,'solid to legacy bridge')

reset()
a=native([(0,0,0),(1,0,0),(1,1,0)],radius=.2)
b=native([(3,2,0),(4,2,0)],radius=.2)
turn=Euler((.27,.61,-.38)).to_matrix().to_4x4()
a.matrix_world=turn;b.matrix_world=turn @ b.matrix_world
bpy.context.view_layer.update()
bridge=c.bridge(bpy.context,a,'END',b,'START',.25,True,10)
check('rotated orthogonal groups keep orthogonal bridge axes',bool(c.group_recipes(bpy.context.scene,a)))
record=bpy.context.scene.line_pipe_connections.links[-1]
record_id=record.uid
b.matrix_world=Matrix.Translation((0,0,1)) @ b.matrix_world
bpy.context.view_layer.update();bpy.context.view_layer.objects.active=bridge
before=len(bpy.data.objects)
c.update_bridges(bpy.context)
check('updating bridge keeps connection identity and object count',record.uid==record_id and len(bpy.data.objects)==before)
check('updated bridge reaches moved target',near(ports.world_ports(bridge)[1].position,ports.read(bpy.context.scene,b,'START',False).position))
state=bpy.context.scene.line_pipe_connections
state.smooth=False;state.radius=.3;state.distance=10
c.update_bridges(bpy.context,True)
check('existing bridge can switch to angular bends',not c.recipe_for(bridge)['smooth'])
solid(bridge,'updated angular bridge')
state.source_zh=a;state.target_zh=b;state.source_port_zh='END'
check('Chinese pointer and endpoint aliases share values',state.source==a and state.target==b and state.source_port=='END')

reset()
source=native([(0,0,0),(2,0,0),(2,2,0)],radius=.6,mesh=True)
other=native([(0,0,0),(0,2,0),(0,2,2)],radius=.6)
other[ports.GROUP]=ports.group_id(source)
ref=native([(0,0,0),(2,0,0),(2,2,0)],radius=.25)
transform=Matrix.Translation((4,3,-2)) @ Euler((.4,.6,.3)).to_matrix().to_4x4()
source.matrix_world=transform; other.matrix_world=transform @ Matrix.Translation((0,0,3))
ref.matrix_world=Matrix.Translation((-5,1,2)) @ Euler((-.5,.2,.8)).to_matrix().to_4x4()
bpy.context.view_layer.update()
snapshots={o:(o.matrix_world.copy(),[(p.position.copy(),p.direction.copy()) for p in ports.world_ports(o)]) for o in (source,other,ref)}
for o in bpy.context.selected_objects:o.select_set(False)
ref.select_set(True);source.select_set(True);bpy.context.view_layer.objects.active=source
radius,count=c.sync_curvature(bpy.context)
check('rotated groups use reference curvature', abs(radius-.25)<1e-5 and count==2)
for obj in (source,other,ref):
    check('curvature keeps pose '+obj.name,matrix_near(obj.matrix_world,snapshots[obj][0]))
    check('curvature keeps endpoints '+obj.name,all(near(p.position,pos) and p.direction.dot(n)>.99999 for p,(pos,n) in zip(ports.world_ports(obj),snapshots[obj][1])))
    check('curvature radius '+obj.name,abs(c.recipe_for(obj)['radius']-.25)<1e-6)
    solid(obj,'curvature '+obj.name)

old=legacy_elbow(.6);old[ports.GROUP]=ports.group_id(source)
old.matrix_world=transform @ Matrix.Translation((0,4,0));bpy.context.view_layer.update()
c.sync_curvature(bpy.context)
check('legacy mesh curvature preserves original port keys',[p.key for p in ports.world_ports(old)]==['P1','P2'])
solid(old,'legacy curvature')

badrecipe=dict(kind='POLYLINE',points=[[0,0,0],[2,0,0],[3,1,0]],diameter=.2,bore=0,radius=.3,smooth=False,sides=32,steps=16)
bad=bpy.data.objects.new('Non-orthogonal pipe',cg.mesh_from_recipe(badrecipe));bpy.context.collection.objects.link(bad);c.store_path(bad,badrecipe)
ports.ensure_identity(bad);bad[ports.GROUP]=ports.group_id(source)
refused('nonorthogonal group',lambda:c.sync_curvature(bpy.context),'nonorthogonal_group')

reset()
short=native([(0,0,0),(.15,0,0),(.15,.15,0)],radius=.1,diameter=.1)
ref=native([(0,0,0),(2,0,0),(2,2,0)],radius=.5,diameter=.1)
for o in bpy.context.selected_objects:o.select_set(False)
ref.select_set(True);short.select_set(True);bpy.context.view_layer.objects.active=short
refused('curvature clearance',lambda:c.sync_curvature(bpy.context),'curvature_clearance')

reset()
a=native([(0,0,0),(1,0,0)],mesh=True)
vertices,faces=[],[]
for polygon in a.data.polygons:
    start=len(vertices)
    vertices.extend(tuple(a.data.vertices[i].co) for i in polygon.vertices)
    faces.append(tuple(reversed(range(start,len(vertices)))))
broken=bpy.data.meshes.new('Unwelded and inverted faces')
broken.from_pydata(vertices,[],faces);broken.update()
original=a.data;a.data=broken;c.discard(original)
refused('broken source refused before connection',lambda:ports.read(bpy.context.scene,a,'END'),'bad_existing_mesh')
shared=bpy.data.objects.new('Shared copy',a.data);bpy.context.collection.objects.link(shared)
oldmesh=shared.data
c.repair_mesh(a)
check('repair preserves shared original geometry',a.data!=oldmesh and shared.data==oldmesh)
check('repair welds formerly separate face vertices',len(a.data.vertices)<len(oldmesh.vertices)
      and cg.topology(oldmesh)['nonmanifold']>0)
solid(a,'repaired mesh')
openmesh=a.data.copy()
bm=bmesh.new();bm.from_mesh(openmesh);bm.faces.ensure_lookup_table()
bmesh.ops.delete(bm,geom=[bm.faces[0]],context='FACES_ONLY');bm.to_mesh(openmesh);bm.free()
openpipe=bpy.data.objects.new('Missing face',openmesh);bpy.context.collection.objects.link(openpipe)
refused('unrepairable hole',lambda:c.repair_mesh(openpipe),'mesh_needs_remodel')
check('failed repair keeps exact original data',openpipe.data==openmesh)
b=native([(3,0,0),(4,0,0)])
c.bridge(bpy.context,a,'END',b,'START',.3,True,5)
count=len(bpy.context.scene.line_pipe_connections.links)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'connections-roundtrip.blend'))
bpy.ops.wm.open_mainfile(filepath=str(OUT/'connections-roundtrip.blend'))
check('save and reopen retain endpoint links',len(bpy.context.scene.line_pipe_connections.links)==count)
check('saved link pointers resolve',all(r.source and r.target and r.connector for r in bpy.context.scene.line_pipe_connections.links))
(OUT/'results.json').write_text(json.dumps(dict(count=len(checks),checks=checks,timings=timings),indent=2))
print('CONNECTION TOTAL',len(checks),flush=True)
addon.unregister()
