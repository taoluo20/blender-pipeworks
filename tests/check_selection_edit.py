"""Exact selection, group editing, generated bridges and batch refusal checks."""
import json
from pathlib import Path
import sys
from types import SimpleNamespace
import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'verification/selection-edit'
OUT.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(ROOT))
import line_pipe as addon
from line_pipe import data, editing as e, geometry, groups as g, ports, connections as c
addon.register()
checks = []


def check(name, condition):
    assert condition, name
    checks.append(name)
    print('PASS SELECTION EDIT:', name, flush=True)


def reset():
    g.unregister_callbacks()
    bpy.context.scene.line_pipe_connections.links.clear()
    bpy.context.scene.line_pipe_groups.items.clear()
    for obj in tuple(bpy.context.scene.objects):
        block = obj.data
        bpy.data.objects.remove(obj, do_unlink=True)
        if isinstance(block, (bpy.types.Mesh, bpy.types.Curve)):
            c.discard(block)


def pipe(name, x=0, mesh=False, points=None):
    obj = geometry.create(bpy.context, mesh=mesh)
    obj.name = name
    data.store_parameters(obj, .2, .4, 32, 16, [False, 'FREE', .02, '10'])
    geometry.update(obj, points or [(0, 0, 0), (2, 0, 0), (2, 0, 2)], .2, .4, 32, 16, store=True)
    obj.location.x += x
    bpy.context.view_layer.update()
    return obj


def choose(objects):
    g.select_objects(bpy.context, set(objects), objects[-1] if objects else None)


def snapshot():
    return ([(obj.name, obj.data.as_pointer(), geometry.mesh_signature(obj.data) if obj.type == 'MESH' else
              [(tuple(p.co), tuple(p.handle_left), tuple(p.handle_right)) for p in obj.data.splines[0].bezier_points],
              tuple(obj.matrix_world), e.values(obj) if e.supported(obj) else None) for obj in bpy.context.scene.objects],
            len(bpy.data.meshes), len(bpy.data.curves))


def refusal(name, objects, changes, key):
    before = snapshot()
    try:
        e.update_objects(bpy.context, objects, changes)
    except ValueError as error:
        check(name + ' gives precise error', str(error) == key)
    else:
        raise AssertionError(name + ' was accepted')
    check(name + ' changes no objects or data blocks', snapshot() == before)


def near(a, b):
    return (Vector(a)-Vector(b)).length < 2e-5


reset()
pipes = [pipe('Pipe %d' % index, index*4, mesh=index % 2 == 0) for index in range(5)]
editor = bpy.context.scene.line_pipe_edit
choose(pipes[:2])
unselected = [obj.data for obj in pipes[2:]]
editor.diameter = .3
check('two selected pipes share one diameter control', all(abs(e.values(obj)['diameter']-.3) < 1e-6 for obj in pipes[:2]))
check('other three pipes keep their data and dimensions', [obj.data for obj in pipes[2:]] == unselected
      and all(abs(e.values(obj)['diameter']-.2) < 1e-6 for obj in pipes[2:]))
choose(pipes[1:4])
editor.bend_radius_zh = .65
editor.bend_steps = 24
editor.free_sides = True
editor.radial_segments_zh = 37
check('three selected pipes share radius and resolution controls', all(
    abs(e.values(obj)['bend_radius']-.65) < 1e-6 and e.values(obj)['bend_steps'] == 24
    and all(ports.read(bpy.context.scene, obj, key, False).sides == 37 for key in ('START', 'END')) for obj in pipes[1:4]))
check('first and fifth pipes stay outside the three-object edit', pipes[0].line_pipe.radial_segments == 32 and pipes[4].line_pipe.radial_segments == 32)
choose([pipes[4]])
pipes[4].scale = (2, 2, 2)
bpy.context.view_layer.update()
editor.diameter = .4
check('shared editor uses physical scene-space diameter', abs(ports.read(bpy.context.scene, pipes[4], 'START').diameter-.4) < 1e-6)
g.refresh(bpy.context.scene, reset=True)
state = g.state_for(bpy.context.scene)
group = g.group_rows(bpy.context, [row for row in state.items if row.source in pipes[:2]])
uid = group.uid
g.select_rows(bpy.context, [uid])
check('selecting a staged group selects exactly its two pipes', set(e.targets(bpy.context)) == set(pipes[:2]))
editor.bend_radius = .55
check('group edit updates every member without applying names or merging',
      len(bpy.context.scene.objects) == 5 and all(abs(e.values(obj)['bend_radius']-.55) < 1e-6 for obj in pipes[:2]))
child = next(row for row in state.items if row.source == pipes[0])
child.selected = False
check('deselecting one child preserves its selected sibling', set(e.targets(bpy.context)) == {pipes[1]} and not g.find(state, uid).selected)
child.selected_zh = True
check('checkbox addition restores full group selection', set(e.targets(bpy.context)) == set(pipes[:2]) and g.find(state, uid).selected)
choose(pipes[2:])
g.sync_selection(bpy.context)
check('viewport selection replaces stale list flags', all(row.selected == (row.source in pipes[2:]) for row in state.items))
g.select_rows(bpy.context, [next(row.uid for row in state.items if row.source == pipes[0])], 'ADD')
check('list additive selection preserves viewport members', len(e.targets(bpy.context)) == 4)
g.select_rows(bpy.context, [next(row.uid for row in state.items if row.source == pipes[3])], 'SUBTRACT')
check('list subtractive selection removes only its pipe', set(e.targets(bpy.context)) == {pipes[0], pipes[2], pipes[4]})

reset()
a = pipe('Source', points=[(0, 0, 0), (1, 0, 0)])
b = pipe('Target', points=[(4, 2, 0), (5, 2, 0)])
bridge = c.bridge(bpy.context, a, 'END', b, 'START', .3, True, 20)
outside = pipe('Unselected', 10)
check('automatic bridge appears among editable pipes', e.supported(bridge))
del bridge[geometry.MESH_SIGNATURE]
choose([bridge])
fixed = [obj.data for obj in (a, b, outside)]
endpoints = [port.position.copy() for port in ports.world_ports(bridge)]
editor.bend_radius = .5
editor.bend_steps = 24
check('bridge-only edit updates the stored radius and tessellation',
      abs(c.recipe_for(bridge)['radius']-.5) < 1e-6 and c.recipe_for(bridge)['steps'] == 24)
check('older unsigned automatic bridges become safely editable', geometry.generated_mesh_intact(bridge, require_signature=True))
check('bridge edit preserves both attached pipes and unselected geometry', fixed == [obj.data for obj in (a, b, outside)])
check('bridge endpoints stay on their original mouths', all(near(port.position, point) for port, point in zip(ports.world_ports(bridge), endpoints)))
g.refresh(bpy.context.scene, reset=True)
state = g.state_for(bpy.context.scene)
network = next(row for row in state.items if row.kind == 'GROUP')
network_uid = network.uid
g.select_rows(bpy.context, [network_uid])
check('connected group selection includes its generated bridge', set(e.targets(bpy.context)) == {a, b, bridge})
editor.diameter = .3
editor.radial_segments = 48
check('whole-group profile edits include the automatic bridge', all(
      abs(port.diameter-.3) < 1e-6 and port.sides == 48 for obj in (a, b, bridge) for port in ports.world_ports(obj)))
check('outside object keeps its original profile', abs(outside.line_pipe.diameter-.2) < 1e-6 and outside.line_pipe.radial_segments == 32)
record = bpy.context.scene.line_pipe_connections.links[0]
check('bridge link settings follow the shared editor', record.sides == 48 and abs(record.radius-.5) < 1e-6)
refusal('partial connected profile', [a, b], {'diameter': .4}, 'edit_connected_profile')
refusal('fixed bridge length', [bridge], {'route_length': 10}, 'length_both_ports')
choose([a, b, bridge])
bpy.ops.line_pipe.selection_mesh()
check('batch Mesh conversion retains object identities and all selected pipes', all(obj.type == 'MESH' for obj in (a, b, bridge))
      and set(e.targets(bpy.context)) == {a, b, bridge} and record.source == a and record.target == b)
editor.hollow_zh = True
editor.wall = .025
check('whole-group hollow and wall edits keep connected profiles consistent', all(
      abs(ports.read(bpy.context.scene, obj, key, False).bore-.25) < 1e-5 for obj in (a, b, bridge) for key in ('START', 'END')))
for obj in (a, b, bridge):
    result = addon.connection_geometry.topology(obj.data)
    check(obj.name + ' remains a closed positive-volume mesh', result['nonmanifold'] == 0 and result['volume'] > 0)
a.line_pipe.free_sides = b.line_pipe.free_sides = True
bridge.line_pipe.free_sides = False
data._preset_drag = SimpleNamespace(live=True, committed=False, window=None, original=[
    (obj.name, e.values(obj)['radial_segments'], e.values(obj)['free_sides']) for obj in (a, b, bridge)])
editor.radial_segments = 72
data.abort_preset_drag()
check('cancel restores connected rings and different custom-count flags together', all(
    e.values(obj)['radial_segments'] == 48 for obj in (a, b, bridge))
    and a.line_pipe.free_sides and b.line_pipe.free_sides and not bridge.line_pipe.free_sides)
refusal('invalid radius for batch', [a, b, bridge], {'bend_radius': .05}, 'bad_radius')
refusal('invalid wall for batch', [a, b, bridge], {'wall': .2}, 'invalid_wall')
before = snapshot()
choose([bridge])
editor.diameter = .5
check('live editor reports refused partial edits without changes', editor.error == 'edit_connected_profile' and snapshot() == before)
choose([a, b, bridge])
editor.bend_radius = .45
check('successful edit clears previous error', not editor.error)

reset()
one, two = pipe('Atomic A', mesh=True), pipe('Atomic B', 4, mesh=True)
original_builder = c.stage_recipe
attempts = []


def fail_second(obj, planned):
    attempts.append(obj)
    if len(attempts) == 2:
        raise ports.ConnectionError('invalid_mesh')
    return original_builder(obj, planned)


c.stage_recipe = fail_second
try:
    refusal('second-object build failure', [one, two], {'bend_radius': .6}, 'invalid_mesh')
finally:
    c.stage_recipe = original_builder
two.data.vertices[0].co.y += .01
refusal('authored mesh batch', [one, two], {'bend_radius': .6}, 'edited_recipe')
choose([one])
editor.bend_radius = .52
bpy.ops.wm.save_as_mainfile(filepath=str(OUT / 'selection-edit.blend'), check_existing=False)
bpy.ops.wm.open_mainfile(filepath=str(OUT / 'selection-edit.blend'))
check('shared edited parameters and geometry survive save/reopen', abs(e.values(bpy.data.objects['Atomic A'])['bend_radius']-.52) < 1e-6)
(OUT / 'results.json').write_text(json.dumps(dict(checks=checks), indent=2))
print('SELECTION EDIT TOTAL', len(checks), flush=True)
addon.unregister()
