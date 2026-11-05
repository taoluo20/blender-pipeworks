"""Staged group, naming, evaluated merge and persistence checks in disposable scenes."""
import importlib
import json
from pathlib import Path
import sys
import bpy
from mathutils import Matrix, Vector

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'verification/groups'
OUT.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(ROOT))
import line_pipe as addon
from line_pipe import groups as g, ports, geometry, connections as c, data
addon.register()
checks = []


def check(name, condition):
    assert condition, name
    checks.append(name)
    print('PASS GROUPS:', name, flush=True)


def reset():
    g.unregister_callbacks()
    bpy.context.scene.line_pipe_connections.links.clear()
    bpy.context.scene.line_pipe_groups.items.clear()
    for obj in tuple(bpy.context.scene.objects):
        block = obj.data
        bpy.data.objects.remove(obj, do_unlink=True)
        if isinstance(block, (bpy.types.Mesh, bpy.types.Curve)):
            c.discard(block)


def pipe(name, location=(0, 0, 0), mesh=False):
    obj = geometry.create(bpy.context, mesh=mesh)
    obj.name = name
    geometry.update(obj, [(0, 0, 0), (2, 0, 0)], .2, .4, 24, 12, store=True)
    obj.location = location
    return obj


def snapshot():
    return [(obj.as_pointer(), obj.name, obj.data.as_pointer() if obj.data else None, tuple(obj.matrix_world),
             tuple(col.as_pointer() for col in obj.users_collection), dict(obj))
            for obj in bpy.context.scene.objects]


def pair():
    reset()
    a, b = pipe('Pipe A'), pipe('Pipe B', (0, 2, 0), mesh=True)
    bpy.context.view_layer.update()
    g.refresh(bpy.context.scene, reset=True)
    state = g.state_for(bpy.context.scene)
    return a, b, state


def refusal(name, callback, key):
    before = snapshot(), len(bpy.data.meshes), len(bpy.data.curves), len(bpy.context.scene.line_pipe_connections.links)
    try:
        callback()
    except ports.ConnectionError as error:
        check(name, str(error) == key)
    else:
        raise AssertionError(name + ' was accepted')
    after = snapshot(), len(bpy.data.meshes), len(bpy.data.curves), len(bpy.context.scene.line_pipe_connections.links)
    check(name + ' preserves all sources', before == after)


a, b, state = pair()
before = snapshot()
check('default apply mode is real Mesh merge', state.apply_mode == 'MERGE')
check('discover separate scene pipes as rows', len(state.items) == 2)
ra, rb = list(state.items)
a_uid, b_uid = ra.uid, rb.uid
group = g.group_rows(bpy.context, [ra, rb])
group.name = 'Cooling'
check('virtual merge leaves Blender objects untouched', snapshot() == before)
check('group contains both source pointers', g.objects(state, group) == [a, b])
group.expanded = False
check('collapse hides children', [row.uid for row in g.visible_rows(state)] == [group.uid])
state.search = 'Pipe B'
check('search reveals matching children and parent', [row.name for row in g.visible_rows(state)] == ['Cooling', 'Pipe B'])
state.search, group.expanded = '', True
state.template_scope, state.template, state.start_index = 'PIPES', '{group}_{index:03d}', 7
planned = g.template_names(bpy.context.scene)
check('template previews group names and padded sequence', [name for _, name in planned] == ['Cooling_007', 'Cooling_008'])
bpy.ops.line_pipe.group_list(action='TEMPLATE')
check('template edits only staging names', snapshot() == before and [row.name for row in g.children(state, group.uid)] == ['Cooling_007', 'Cooling_008'])
state.template = '{bad.field}'
refusal('invalid template is atomic', lambda: g.template_names(bpy.context.scene), 'groups_bad_template')
state.template = '{index:03d}'
state.presets = 'PIPE'
check('choosing a preset immediately updates the template', state.template == 'Pipe_{index:03d}')
state.template_zh = 'Custom_{index:02d}'
check('editing the template switches the preset to Custom', state.presets == 'CUSTOM' and state.template == 'Custom_{index:02d}')
state.items[1].name, state.items[2].name = 'Alpha', 'Beta'
aux = g.add_row(state, 'Auxiliary', kind='GROUP')
aux_uid, group_uid = aux.uid, group.uid
g.move_row(state, a_uid, aux_uid)
check('drag a pipe into another staged group', g.objects(state, g.find(state, aux_uid)) == [a] and g.objects(state, g.find(state, group_uid)) == [b])
g.move_row(state, aux_uid, group_uid, 'BEFORE')
check('reorder whole group blocks', [row.uid for row in state.items if not row.parent_uid] == [aux_uid, group_uid])
g.move_row(state, aux_uid, group_uid, 'INTO')
group = g.find(state, group_uid)
check('merge groups only in staging', len(g.children(state, group_uid)) == 2 and g.find(state, aux_uid) is None and snapshot() == before)
member_ids = [row.uid for row in g.children(state, group_uid)]
g.move_row(state, member_ids[1], member_ids[0], 'BEFORE')
check('reorder pipes within group', [row.uid for row in g.children(state, group_uid)] == list(reversed(member_ids)))

saved_names = [(row.uid, row.name, row.parent_uid) for row in state.items]
path = OUT / 'pending-groups.blend'
bpy.ops.wm.save_as_mainfile(filepath=str(path), check_existing=False)
bpy.ops.wm.open_mainfile(filepath=str(path))
state = g.state_for(bpy.context.scene)
check('pending edits survive save and reopen', [(row.uid, row.name, row.parent_uid) for row in state.items] == saved_names and state.dirty)
check('save does not apply staging names', {obj.name for obj in bpy.context.scene.objects} == {'Pipe A', 'Pipe B'})
a, b = bpy.data.objects['Pipe A'], bpy.data.objects['Pipe B']
group = next(row for row in state.items if row.kind == 'GROUP')
group.name = 'Cooling'
g.apply(bpy.context, 'COLLECTION')
check('Collection mode retains separate curve and mesh objects', len(bpy.context.scene.objects) == 2 and a.type == 'CURVE' and b.type == 'MESH')
check('Collection mode synchronizes staged object names', {a.name, b.name} == {'Alpha', 'Beta'})
check('Collection mode syncs real group and collection name', len(a.users_collection) == 1 and a.users_collection[0] == b.users_collection[0] and a.users_collection[0].name == 'Cooling')
check('Collection apply clears pending flag', not state.dirty)
g.refresh(bpy.context.scene, reset=True)
check('reset discovers applied group label', next(row.name for row in state.items if row.kind == 'GROUP') == 'Cooling')

a, b, state = pair()
red = bpy.data.materials.new('Group Test Red')
blue = bpy.data.materials.new('Group Test Blue')
a.data.materials.append(red)
b.data.materials.append(blue)
a.matrix_world = Matrix.Translation((1, 2, 3)) @ Matrix.Rotation(.5, 4, 'Z')
b.matrix_world = Matrix.Translation((-2, -1, 1)) @ Matrix.Scale(1.5, 4)
bpy.context.view_layer.update()
g.refresh(bpy.context.scene, reset=True)
group = g.group_rows(bpy.context, list(state.items))
group.name = 'Combined Pipes'
state.template_scope, state.template = 'PIPES', '{name}_D{diameter:.2f}'
check('diameter template uses world-space scene units', [name for _, name in g.template_names(bpy.context.scene)] == ['Pipe A_D0.20', 'Pipe B_D0.30'])
expected_ports = [port.position.copy() for obj in (a, b) for port in ports.world_ports(obj)]
expected_bounds = [obj.matrix_world @ Vector(point) for obj in (a, b) for point in obj.bound_box]
for obj in bpy.context.selected_objects:
    obj.select_set(False)
a.select_set(True)
bpy.context.view_layer.objects.active = a
g.apply(bpy.context, 'MERGE')
result = bpy.context.scene.objects['Combined Pipes']
check('Mesh mode creates one actual Mesh object', len(bpy.context.scene.objects) == 1 and result.type == 'MESH' and len(result.data.polygons) > 0)
check('merged Mesh retains both materials', {material for material in result.data.materials} == {red, blue})
actual_ports = list(ports.world_ports(result))
check('merged external ports retain world positions', all(any((actual.position-expected).length < 1e-5 for actual in actual_ports) for expected in expected_ports))
check('merged custom mouths can still be read for connection', all(ports.read(bpy.context.scene, result, port.key, False).sides == 24 for port in actual_ports))
check('merged output remains recognized as a pipe', ports.is_pipe(result) and result.get(g.OUTPUT))
check('selection maps to merged output', bpy.context.active_object == result and result.select_get())
check('applied group collapses to one mesh row', len(state.items) == 1 and state.items[0].source == result and not state.dirty)

a, b, state = pair()
outside = pipe('Outside', (0, 4, 0))
link = c.new_link(bpy.context.scene, a, 'START', outside, 'END', 'DIRECT')
internal = c.new_link(bpy.context.scene, a, 'END', b, 'START', 'DIRECT')
g.refresh(bpy.context.scene)
group = g.group_rows(bpy.context, [row for row in state.items if row.source in {a, b}])
group.name = 'Connected Output'
g.apply(bpy.context, 'MERGE')
result = bpy.context.scene.objects['Connected Output']
links = bpy.context.scene.line_pipe_connections.links
check('internal links are baked and external link survives', len(links) == 1 and links[0].source == result and links[0].target == outside)
check('external port keys are remapped', links[0].source_port in {spec['key'] for spec in ports.local_ports(result)})
check('internal mouths stay disabled after baking', sum(not spec['enabled'] for spec in ports.local_ports(result)) == 2)

a, b, state = pair()
g.group_rows(bpy.context, list(state.items))
outside = pipe('Outside', (0, 4, 0))
c.new_link(bpy.context.scene, a, 'MISSING', outside, 'END', 'DIRECT')
refusal('stale link keys are rejected before rename or merge', lambda: g.apply(bpy.context, 'MERGE'), 'missing_port')

a, b, state = pair()
group = g.group_rows(bpy.context, list(state.items))
group.name = 'Keep Before Error'
original_builder = g.build_output
def broken_builder(*args):
    raise ports.ConnectionError('groups_empty_mesh')
g.build_output = broken_builder
try:
    refusal('evaluation failure is atomic', lambda: g.apply(bpy.context, 'MERGE'), 'groups_empty_mesh')
finally:
    g.build_output = original_builder
extra = bpy.data.objects.new('Dependent Child', None)
bpy.context.scene.collection.objects.link(extra)
extra.parent = a
refusal('external child is refused before merge', lambda: g.apply(bpy.context, 'MERGE'), 'groups_external_child')
extra.parent = None
bpy.data.objects.remove(extra, do_unlink=True)
other = bpy.data.scenes.new('Shared Scene Test')
other.collection.objects.link(a)
refusal('cross-scene object is refused atomically', lambda: g.apply(bpy.context, 'COLLECTION'), 'groups_readonly')
other.collection.objects.unlink(a)
bpy.data.scenes.remove(other)
empty = g.add_row(state, 'Empty', kind='GROUP')
refusal('empty Mesh group is refused atomically', lambda: g.apply(bpy.context, 'MERGE'), 'groups_empty_group')
g.ungroup(state, empty.uid)
g.refresh(bpy.context.scene, reset=True)
check('reset discards pending grouping and names', len(state.items) == 2 and not state.dirty and {row.name for row in state.items} == {'Pipe A', 'Pipe B'})

a, b, state = pair()
ra, rb = [row.uid for row in state.items]
g.find(state, ra).name, g.find(state, rb).name = 'Pipe B', 'Pipe A'
g.apply(bpy.context, 'COLLECTION')
check('swapped object names are synchronized exactly', a.name == 'Pipe B' and b.name == 'Pipe A')

a, b, state = pair()
group1 = g.group_rows(bpy.context, [state.items[0]])
uid1 = group1.uid
g.find(state, uid1).name = 'First Group'
remaining = next(row for row in state.items if row.source == b)
group2 = g.group_rows(bpy.context, [remaining])
uid2 = group2.uid
g.find(state, uid2).name = 'Second Group'
g.apply(bpy.context, 'COLLECTION')
g.find(state, uid1).name, g.find(state, uid2).name = 'Second Group', 'First Group'
g.apply(bpy.context, 'COLLECTION')
check('managed collection names can swap without suffix drift', a.users_collection[0].name == 'Second Group' and b.users_collection[0].name == 'First Group')
g.apply(bpy.context, 'MERGE')
check('multiple groups apply without invalid row references', len(state.items) == 2 and all(row.source and row.source.type == 'MESH' for row in state.items))
check('multiple merged outputs receive exact group names', {row.source.name for row in state.items} == {'First Group', 'Second Group'})

a, b, state = pair()
third = pipe('Pipe C', (0, 4, 0))
fourth = pipe('Pipe D', (0, 6, 0))
g.refresh(bpy.context.scene)
g.group_rows(bpy.context, [row for row in state.items if row.source in {a, b}])
g.group_rows(bpy.context, [row for row in state.items if row.source in {third, fourth}])
original_builder = g.build_output
built = []
def fail_second(*args):
    if built:
        raise ports.ConnectionError('groups_empty_mesh')
    result = original_builder(*args)
    built.append(result)
    return result
g.build_output = fail_second
try:
    refusal('later group evaluation failure rolls back all staged meshes', lambda: g.apply(bpy.context, 'MERGE'), 'groups_empty_mesh')
finally:
    g.build_output = original_builder

a, b, state = pair()
b.location = (4, 0, 0)
bpy.context.view_layer.update()
bridge = c.bridge(bpy.context, a, 'END', b, 'START')
g.refresh(bpy.context.scene, reset=True)
group = next(row for row in state.items if row.kind == 'GROUP')
group_uid = group.uid
bridge_uid = next(row.uid for row in state.items if row.source == bridge)
g.ungroup(state, bridge_uid)
g.group_rows(bpy.context, [g.find(state, bridge_uid)])
refusal('partial bridge merge is rejected before any changes', lambda: g.apply(bpy.context, 'MERGE'), 'groups_partial_bridge')
g.refresh(bpy.context.scene, reset=True)
g.apply(bpy.context, 'MERGE')
check('full bridge group bakes into one Mesh', len(bpy.context.scene.objects) == 1 and len(bpy.context.scene.line_pipe_connections.links) == 0)
result = next(iter(bpy.context.scene.objects))
check('baked bridge only exposes its two external mouths', sum(spec['enabled'] for spec in ports.local_ports(result)) == 2)

a, b, state = pair()
a[ports.GROUP] = b[ports.GROUP] = 'external-real-group'
g.refresh(bpy.context.scene)
check('clean list follows externally changed real group membership', len(state.items) == 3 and state.items[0].kind == 'GROUP' and not state.dirty)
state.items[0].name = 'Keep My Draft'
a[ports.GROUP], b[ports.GROUP] = 'external-split-a', 'external-split-b'
g.refresh(bpy.context.scene)
check('refresh preserves draft grouping when real groups change', state.items[0].name == 'Keep My Draft' and len(state.items) == 3)

a, b, state = pair()
group = g.group_rows(bpy.context, list(state.items))
state.active_index = next(i for i, row in enumerate(state.items) if row.uid == group.uid)
for obj in bpy.context.selected_objects:
    obj.select_set(False)
a.select_set(True)
bpy.context.view_layer.objects.active = a
bpy.ops.line_pipe.group_list(action='UNGROUP')
check('Ungroup uses the active list group rather than an unrelated viewport selection', len(state.items) == 2 and all(not row.parent_uid for row in state.items))

for lang in ('EN', 'ZH'):
    bpy.context.scene.line_pipe_settings.language = lang
    check('localized apply mode ' + lang, len(i18n_value := addon.i18n.tr('groups_apply')) > 0)
check('Chinese RNA aliases share template and mode', hasattr(state, 'template_zh') and state.apply_mode_zh == state.apply_mode)
g.unregister_callbacks()
(OUT / 'results.json').write_text(json.dumps(dict(checks=checks, count=len(checks)), indent=2), encoding='utf8')
print('GROUPS PASS', len(checks), 'assertions', flush=True)
