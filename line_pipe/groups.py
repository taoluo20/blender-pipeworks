# SPDX-License-Identifier: GPL-3.0-or-later
"""Scene-saved name/group drafts and synchronized list/viewport selection."""
import json
import math
import string
import uuid
from dataclasses import dataclass
import bpy
import blf
from bpy.props import BoolProperty, CollectionProperty, EnumProperty, IntProperty, PointerProperty, StringProperty
from . import i18n, ports, connections, connection_ops, operators

OUTPUT = '_pipeworks_group_output_v1'
COLLECTION = '_pipeworks_list_collection_v1'
_pending = {}
_signatures = {}
_selection_signatures = {}
_drag = None
_box = None
_box_start = None
TEMPLATES = {'GROUP_PIPE': '{group}_{type}_{index:03d}', 'PIPE': 'Pipe_{index:03d}',
             'GROUP': 'Group_{index:03d}', 'ORIGINAL': '{name}_{index:03d}'}


@dataclass(frozen=True)
class Member:
    uid: str
    source: object


def state_for(scene):
    return scene.line_pipe_groups


def changed(self, context):
    state = state_for(self.id_data)
    if not state.syncing:
        state.dirty = True


def start_row_drag(self, context):
    if _drag is None and _box is None and connection_ops.ready(context):
        bpy.ops.line_pipe.group_drag('INVOKE_DEFAULT', True, uid=self.uid)


def start_row_selection(self, context):
    global _box_start
    if _drag or _box or _box_start or not connection_ops.ready(context):
        return
    uid, window, area, region = self.uid, context.window, context.area, context.region

    def begin():
        global _box_start
        _box_start = None
        if window not in bpy.context.window_manager.windows[:] or area not in window.screen.areas[:]:
            return None
        with bpy.context.temp_override(window=window, area=area, region=region):
            bpy.ops.line_pipe.group_box_select('INVOKE_DEFAULT', True, uid=uid)
        return None

    # Let the native row button install its handler before taking over the gesture.
    _box_start = begin
    bpy.app.timers.register(begin, first_interval=0)


def selection_changed(self, context):
    state = state_for(self.id_data)
    if state.syncing or context.scene != self.id_data:
        return
    selected = set(context.selected_objects)
    members = set(objects(state, self))
    selected = selected | members if self.selected else selected - members
    select_objects(context, selected, self.source)


def set_active(state, index):
    syncing = state.syncing
    state.syncing = True
    try:
        state.active_index = index
    finally:
        state.syncing = syncing


def sync_selection(context):
    state = state_for(context.scene)
    selected = set(context.selected_objects)
    syncing = state.syncing
    state.syncing = True
    try:
        for row in state.items:
            members = objects(state, row)
            row.selected = bool(members) and all(obj in selected for obj in members)
        active = state.items[state.active_index] if 0 <= state.active_index < len(state.items) else None
        if not active or context.active_object not in objects(state, active) or not active.selected:
            index = next((i for i, row in enumerate(state.items) if row.source == context.active_object), None)
            if index is not None:
                state.active_index = index
    finally:
        state.syncing = syncing


def select_objects(context, chosen, active=None):
    chosen = {obj for obj in chosen if obj.name in context.view_layer.objects and obj.visible_get() and not obj.hide_select}
    for obj in context.view_layer.objects:
        if obj.select_get() != (obj in chosen):
            obj.select_set(obj in chosen)
    if active not in chosen:
        active = context.active_object if context.active_object in chosen else next(iter(sorted(chosen, key=lambda obj: obj.name)), None)
    context.view_layer.objects.active = active
    sync_selection(context)
    from . import editing
    editing.sync_editor(context)
    for window in context.window_manager.windows:
        for area in window.screen.areas:
            area.tag_redraw()


def select_rows(context, uids, mode='REPLACE', initial=None):
    state = state_for(context.scene)
    rows = [row for row in state.items if row.uid in uids]
    members = {obj for row in rows for obj in objects(state, row)}
    previous = set(context.selected_objects) if initial is None else set(initial)
    chosen = previous | members if mode == 'ADD' else previous - members if mode == 'SUBTRACT' else members
    select_objects(context, chosen, next((row.source for row in rows if row.source in chosen), None))


def preset_changed(self, context):
    if self.presets in TEMPLATES:
        self.template = TEMPLATES[self.presets]


def template_changed(self, context):
    if self.presets in TEMPLATES and self.template != TEMPLATES[self.presets]:
        self.presets = 'CUSTOM'


class PW_GroupRow(bpy.types.PropertyGroup):
    uid: StringProperty()
    parent_uid: StringProperty()
    kind: EnumProperty(items=[('GROUP', 'Group', ''), ('PIPE', 'Pipe', '')], default='PIPE')
    source: PointerProperty(type=bpy.types.Object)
    collection: PointerProperty(type=bpy.types.Collection)
    original_name: StringProperty()
    original_group: StringProperty()
    name: StringProperty(name='Name', description='Stage a name until Apply to Blender', update=changed)
    selected: BoolProperty(name='Select', description='Include this row in list operations', default=False, update=selection_changed)
    expanded: BoolProperty(name='Expand Group', default=True)
    drag_handle: EnumProperty(name='Move', items=[('IDLE', '', ''), ('DRAG', '', '')],
                              get=lambda self: 0, set=lambda self, value: None,
                              update=start_row_drag, options={'SKIP_SAVE'})
    selection_handle: EnumProperty(name='Select', items=[('IDLE', '', ''), ('DRAG', '', '')],
                                   get=lambda self: 0, set=lambda self, value: None,
                                   update=start_row_selection, options={'SKIP_SAVE'})


class PW_GroupState(bpy.types.PropertyGroup):
    items: CollectionProperty(type=PW_GroupRow)
    active_index: IntProperty(default=0)
    dirty: BoolProperty(default=False)
    syncing: BoolProperty(default=False, options={'HIDDEN', 'SKIP_SAVE'})
    initialized: BoolProperty(default=False)
    search: StringProperty(name='Search', options={'TEXTEDIT_UPDATE'})
    selection_mode: EnumProperty(name='Selection', default='REPLACE', items=[
        ('REPLACE', 'Set', 'Set', 'groups_selection_set'),
        ('ADD', 'Add', 'Add', 'groups_selection_add'),
        ('SUBTRACT', 'Remove', 'Remove', 'groups_selection_remove')])
    apply_mode: EnumProperty(name='Apply As', description='groups_apply_mode_tip', default='MERGE', items=[
        ('MERGE', 'Mesh Objects', 'Mesh Objects', 'groups_mesh_mode'),
        ('COLLECTION', 'Collections', 'Collections', 'groups_collection_mode')])
    show_templates: BoolProperty(default=False)
    template: StringProperty(name='Name Template', description='groups_template_tip', default='{group}_{type}_{index:03d}', update=template_changed)
    template_scope: EnumProperty(name='Rename', default='SELECTED', items=[
        ('SELECTED', 'Selected Rows', 'Selected Rows', 'groups_selected'),
        ('PIPES', 'All Pipes', 'All Pipes', 'groups_pipes'),
        ('GROUPS', 'All Groups', 'All Groups', 'groups_groups'),
        ('ALL', 'All Rows', 'All Rows', 'groups_all')])
    start_index: IntProperty(name='Start Number', default=1, min=0)
    presets: EnumProperty(name='Preset', default='GROUP_PIPE', update=preset_changed, items=[
        ('GROUP_PIPE', 'Group + Pipe Number', 'Group + Pipe Number', 'groups_preset_group'),
        ('PIPE', 'Pipe Number', 'Pipe Number', 'groups_preset_pipe'),
        ('GROUP', 'Group Number', 'Group Number', 'groups_preset_number'),
        ('ORIGINAL', 'Original Name + Number', 'Original Name + Number', 'groups_preset_original'),
        ('CUSTOM', 'Custom Template', 'Custom Template', 'groups_preset_custom')])


def find(state, uid):
    return next((row for row in state.items if row.uid == uid), None)


def children(state, uid):
    return [row for row in state.items if row.parent_uid == uid]


def objects(state, row):
    return [item.source for item in children(state, row.uid) if item.source] if row.kind == 'GROUP' else ([row.source] if row.source else [])


def add_row(state, name, source=None, parent='', kind='PIPE', original_group=''):
    row = state.items.add()
    row.uid, row.kind, row.parent_uid = uuid.uuid4().hex, kind, parent
    row.source, row.name, row.original_name = source, name, source.name if source else name
    row.original_group = original_group
    return row


def reorder(state, uids):
    active = state.items[state.active_index].uid if 0 <= state.active_index < len(state.items) else ''
    for index, uid in enumerate(uids):
        current = next(i for i, row in enumerate(state.items) if row.uid == uid)
        state.items.move(current, index)
    set_active(state, next((i for i, row in enumerate(state.items) if row.uid == active), 0))


def normalize(state, roots=None):
    roots = roots if roots is not None else [row.uid for row in state.items if not row.parent_uid]
    order = []
    for uid in roots:
        order.append(uid)
        order.extend(row.uid for row in children(state, uid))
    assert len(order) == len(state.items) and len(set(order)) == len(order)
    reorder(state, order)


def refresh(scene, reset=False):
    state = state_for(scene)
    if state.initialized and not state.dirty and any(
            row.source and row.original_group != ports.group_id(row.source) for row in state.items):
        reset = True
    known = {row.source for row in state.items if row.source}
    candidates = [obj for obj in scene.objects if (reset or obj not in known) and ports.is_pipe(obj)]
    renamed = any(row.source and row.original_name != row.source.name for row in state.items)
    if state.initialized and not reset and not candidates and not renamed:
        return
    state.syncing = True
    try:
        if reset:
            state.items.clear()
        by_group = {}
        for obj in candidates:
            by_group.setdefault(ports.group_id(obj), []).append(obj)
        for key, members in by_group.items():
            group = next((row for row in state.items if row.kind == 'GROUP' and row.original_group == key), None)
            managed = next((c for obj in members for c in obj.users_collection if c.get(COLLECTION) == key), None)
            if not group and (len(members) > 1 or managed):
                name = managed.name if managed else 'Group %03d' % (1 + sum(row.kind == 'GROUP' for row in state.items))
                group = add_row(state, name, kind='GROUP', original_group=key)
                group.collection = managed
            for obj in sorted(members, key=lambda obj: obj.name.casefold()):
                add_row(state, obj.name, obj, group.uid if group else '', original_group=key)
        for row in state.items:
            if row.source:
                if row.name == row.original_name:
                    row.name = row.source.name
                row.original_name = row.source.name
        normalize(state)
        state.initialized = True
        if reset:
            state.dirty = False
    finally:
        state.syncing = False


def request_refresh(scene):
    key = scene.as_pointer()
    if key in _pending or _drag or _box or operators.session:
        return

    def update():
        _pending.pop(key, None)
        try:
            if hasattr(bpy.types.Scene, 'line_pipe_groups') and scene.name in bpy.data.scenes and not _drag and not _box and not operators.session:
                signature = tuple((obj.as_pointer(), obj.name, obj.type, obj.get(ports.UID), obj.get(ports.GROUP),
                                   obj.get(ports.CUSTOM) or obj.get('line_pipe_ports_v1') or obj.get(ports.PORTS),
                                   ports.value(ports.legacy(obj), 'group_id', '')) for obj in scene.objects)
                if not state_for(scene).initialized or _signatures.get(key) != signature:
                    refresh(scene)
                    _signatures[key] = signature
                if bpy.context.scene == scene:
                    selected = (tuple(sorted(obj.as_pointer() for obj in bpy.context.selected_objects)),
                                bpy.context.active_object.as_pointer() if bpy.context.active_object else 0)
                    if _selection_signatures.get(key) != selected:
                        sync_selection(bpy.context)
                        _selection_signatures[key] = selected
                    from . import editing
                    editing.sync_editor(bpy.context)
        except ReferenceError:
            pass
        return None

    _pending[key] = update
    bpy.app.timers.register(update, first_interval=.1)


def visible_rows(state):
    groups = {row.uid: row for row in state.items if row.kind == 'GROUP'}
    query = state.search.casefold().strip()
    matching_groups = {row.parent_uid for row in state.items if query and query in row.name.casefold()}
    return [row for row in state.items if (
        (not row.parent_uid or query or groups.get(row.parent_uid) and groups[row.parent_uid].expanded)
        and (not query or query in row.name.casefold() or row.uid in matching_groups
             or row.parent_uid in groups and query in groups[row.parent_uid].name.casefold()))]


def selected_rows(context):
    state = state_for(context.scene)
    selected = [row for row in state.items if row.selected]
    if not selected:
        selected = [row for row in state.items if row.source and row.source in context.selected_objects]
    return [row for row in selected if not row.parent_uid or not any(parent.uid == row.parent_uid for parent in selected)]


def group_rows(context, selected=None):
    state = state_for(context.scene)
    selected = selected if selected is not None else selected_rows(context)
    if not selected:
        raise ports.ConnectionError('groups_choose_rows')
    members = [item for row in selected for item in (children(state, row.uid) if row.kind == 'GROUP' else [row])]
    root_order = [row.uid for row in state.items if not row.parent_uid]
    insert = min((root_order.index(row.uid if not row.parent_uid else row.parent_uid) for row in selected), default=len(root_order))
    group = add_row(state, 'Group %03d' % (1 + sum(row.kind == 'GROUP' for row in state.items)), kind='GROUP')
    uid = group.uid
    syncing = state.syncing
    state.syncing = True
    for row in members:
        row.parent_uid, row.selected = uid, False
    state.syncing = syncing
    removed = {row.uid for row in selected if row.kind == 'GROUP'}
    for index in reversed(range(len(state.items))):
        if state.items[index].uid in removed:
            state.items.remove(index)
    roots = [row for row in root_order if row not in removed and find(state, row) and not find(state, row).parent_uid]
    roots.insert(min(insert, len(roots)), uid)
    normalize(state, roots)
    set_active(state, next(i for i, row in enumerate(state.items) if row.uid == uid))
    select_rows(context, [uid])
    state.dirty = True
    return find(state, uid)


def move_row(state, source_uid, target_uid, placement='INTO'):
    source, target = find(state, source_uid), find(state, target_uid)
    if not source or not target or source == target or target.parent_uid == source.uid:
        return False
    if placement == 'INTO' and target.kind == 'GROUP':
        moved = children(state, source.uid) if source.kind == 'GROUP' else [source]
        for item in moved:
            item.parent_uid = target.uid
        if source.kind == 'GROUP':
            index = next(i for i, row in enumerate(state.items) if row.uid == source_uid)
            state.items.remove(index)
            target = find(state, target_uid)
        target.expanded = True
        normalize(state)
    else:
        if source.kind == 'GROUP':
            target = find(state, target.parent_uid) if target.parent_uid else target
            parent = ''
        else:
            parent = target.parent_uid
        source.parent_uid = parent
        peers = [row.uid for row in state.items if row.parent_uid == parent and row.uid != source_uid]
        index = peers.index(target.uid) + (placement == 'AFTER')
        peers.insert(index, source_uid)
        if parent:
            ordered = [row.uid for row in state.items]
            positions = [i for i, uid in enumerate(ordered) if find(state, uid).parent_uid == parent]
            for i, uid in zip(positions, peers):
                ordered[i] = uid
            reorder(state, ordered)
            normalize(state)
        else:
            normalize(state, peers)
    state.dirty = True
    active_uid = source_uid if find(state, source_uid) else target_uid
    set_active(state, next((i for i, row in enumerate(state.items) if row.uid == active_uid), 0))
    return True


def ungroup(state, uid):
    row = find(state, uid)
    if not row:
        return
    if row.kind == 'PIPE':
        row.parent_uid = ''
    else:
        for item in children(state, uid):
            item.parent_uid = ''
        state.items.remove(next(i for i, item in enumerate(state.items) if item.uid == uid))
    normalize(state)
    state.dirty = True


def clean_name(name):
    value = name.strip()
    if not value:
        raise ports.ConnectionError('groups_empty_name')
    return value.encode('utf8')[:63].decode('utf8', errors='ignore')


def unique_name(name, reserved):
    name = clean_name(name)
    candidate, index = name, 1
    while candidate in reserved:
        suffix = '.%03d' % index
        candidate = name.encode('utf8')[:63-len(suffix)].decode('utf8', errors='ignore') + suffix
        index += 1
    reserved.add(candidate)
    return candidate


def template_names(scene):
    state = state_for(scene)
    chosen = [row for row in state.items if (
        state.template_scope == 'ALL' or state.template_scope == 'SELECTED' and row.selected
        or state.template_scope == 'PIPES' and row.kind == 'PIPE'
        or state.template_scope == 'GROUPS' and row.kind == 'GROUP')]
    if not chosen:
        raise ports.ConnectionError('groups_choose_rows')
    allowed = {'group', 'type', 'name', 'index', 'diameter'}
    try:
        used = set()
        for _, field, spec, conversion in string.Formatter().parse(state.template):
            if field is not None and (field not in allowed or '{' in spec or '}' in spec or conversion):
                raise ValueError(field)
            if field:
                used.add(field)
        result = []
        planned_groups = {}
        names = {row.name for row in state.items if row not in chosen}
        for index, row in enumerate(chosen, state.start_index):
            parent = find(state, row.parent_uid)
            diameter = max((port.diameter for obj in objects(state, row) for port in ports.world_ports(obj)), default=0) if 'diameter' in used else 0
            values = dict(group=planned_groups.get(parent.uid, parent.name) if parent else 'Group', type='Group' if row.kind == 'GROUP' else 'Pipe',
                          name=row.original_name, index=index, diameter=diameter)
            name = unique_name(state.template.format(**values), names)
            result.append((row.uid, name))
            if row.kind == 'GROUP':
                planned_groups[row.uid] = name
        return result
    except (ValueError, KeyError, IndexError, AttributeError, OverflowError) as error:
        if isinstance(error, ports.ConnectionError):
            raise
        raise ports.ConnectionError('groups_bad_template') from error


def plan_apply(context, mode):
    scene, state = context.scene, state_for(context.scene)
    units = []
    sources = [row.source for row in state.items if row.kind == 'PIPE']
    if not sources or any(obj is None or obj.name not in scene.objects for obj in sources):
        raise ports.ConnectionError('groups_missing_source')
    if len(set(sources)) != len(sources):
        raise ports.ConnectionError('groups_duplicate_source')
    if any(obj.library or not obj.is_editable or len(obj.users_scene) != 1 for obj in sources):
        raise ports.ConnectionError('groups_readonly')
    object_names = {obj.name for obj in bpy.data.objects if obj not in sources}
    own_collections = {row.collection for row in state.items if row.collection}
    if any(col.library or not col.is_editable for col in own_collections):
        raise ports.ConnectionError('groups_readonly')
    collection_names = {col.name for col in bpy.data.collections if col not in own_collections}
    for row in state.items:
        if row.parent_uid:
            continue
        members = children(state, row.uid) if row.kind == 'GROUP' else [row]
        if not members:
            raise ports.ConnectionError('groups_empty_group', name=row.name)
        merge = mode == 'MERGE' and row.kind == 'GROUP'
        unit = dict(uid=row.uid, kind=row.kind, collection=row.collection, merge=merge,
                    name=unique_name(row.name, object_names if merge or row.kind == 'PIPE' else collection_names))
        if not merge:
            unit['names'] = {item.uid: unique_name(item.name, object_names) for item in members} if row.kind == 'GROUP' else {row.uid: unit['name']}
        unit['members'] = [Member(item.uid, item.source) for item in members]
        units.append(unit)
    membership = {item.source: unit for unit in units for item in unit['members']}
    for obj, unit in membership.items():
        if unit['merge'] and any(child not in membership or membership[child] is not unit for child in obj.children):
            raise ports.ConnectionError('groups_external_child')
    for link in scene.line_pipe_connections.links:
        for role in ('source', 'target'):
            obj = getattr(link, role)
            unit = membership.get(obj)
            if unit and unit['merge'] and getattr(link, role + '_port') not in {spec['key'] for spec in ports.local_ports(obj)}:
                raise ports.ConnectionError('missing_port')
        connector = membership.get(link.connector)
        if connector and connector['merge'] and (
                membership.get(link.source) is not connector or membership.get(link.target) is not connector):
            raise ports.ConnectionError('groups_partial_bridge')
    return units, membership


def output_ports(context, unit, membership):
    disabled = set()
    for link in context.scene.line_pipe_connections.links:
        if (membership.get(link.source) is unit and membership.get(link.target) is unit
                and (not link.connector or membership.get(link.connector) is unit)):
            disabled.update(((link.source, link.source_port), (link.target, link.target_port)))
            if link.connector:
                disabled.update((link.connector, spec['key']) for spec in ports.local_ports(link.connector))
    specs, mapping = [], {}
    for index, item in enumerate(unit['members'], 1):
        for spec in ports.local_ports(item.source):
            port = (ports.read(context.scene, item.source, spec['key'], False) if spec['enabled']
                    else ports.world_port(item.source, spec))
            key = '%03d_%s' % (index, port.key)
            mapping[item.source, port.key] = key
            specs.append(dict(key=key, position=list(port.position), direction=list(port.direction),
                              radial=list(port.radial), inner_radial=list(port.inner_radial) if port.inner_radial is not None else list(port.radial),
                              diameter=port.diameter, bore=port.bore, sides=port.sides, interface=port.interface,
                              enabled=port.enabled and (item.source, port.key) not in disabled))
    return specs, mapping


def build_output(context, unit, membership):
    specs, mapping = output_ports(context, unit, membership)
    temporary, meshes = [], []
    try:
        depsgraph = context.evaluated_depsgraph_get()
        for item in unit['members']:
            obj = item.source
            mesh = bpy.data.meshes.new_from_object(obj.evaluated_get(depsgraph), preserve_all_data_layers=True, depsgraph=depsgraph)
            meshes.append(mesh)
            if not mesh.vertices or not mesh.polygons:
                raise ports.ConnectionError('groups_empty_mesh')
            mesh.transform(obj.matrix_world)
            if obj.matrix_world.determinant() < 0:
                mesh.flip_normals()
            for index, slot in enumerate(obj.material_slots):
                if slot.link == 'OBJECT' and slot.material:
                    mesh.materials[index] = slot.material
            part = bpy.data.objects.new('_PW_group_staging', mesh)
            context.scene.collection.objects.link(part)
            temporary.append(part)
        with context.temp_override(active_object=temporary[0], object=temporary[0],
                                   selected_objects=temporary, selected_editable_objects=temporary):
            if len(temporary) > 1:
                bpy.ops.object.join()
        result = temporary[0]
        result[ports.CUSTOM] = json.dumps(specs)
        result[ports.UID] = uuid.uuid4().hex
        result[ports.GROUP] = result[ports.UID]
        result[OUTPUT] = json.dumps([item.source.name for item in unit['members']])
        result.color = unit['members'][0].source.color
        return result, mapping
    except Exception:
        for obj in temporary:
            try:
                if obj.name in bpy.data.objects:
                    bpy.data.objects.remove(obj, do_unlink=True)
            except ReferenceError:
                pass
        raise
    finally:
        for mesh in meshes:
            try:
                if mesh.users == 0:
                    bpy.data.meshes.remove(mesh)
            except ReferenceError:
                pass


def apply(context, mode):
    scene, state = context.scene, state_for(context.scene)
    units, membership = plan_apply(context, mode)
    staged = []
    selected, active = list(context.selected_objects), context.active_object
    try:
        # Build every evaluated output before renaming, removing or regrouping sources.
        for unit in units:
            if unit['merge']:
                unit['output'], unit['port_map'] = build_output(context, unit, membership)
                staged.append(unit['output'])
    except Exception:
        for obj in staged:
            block = obj.data
            bpy.data.objects.remove(obj, do_unlink=True)
            connections.discard(block)
        raise
    for obj in membership:
        obj.name = '_PW_rename_' + uuid.uuid4().hex
    if mode == 'COLLECTION':
        for unit in units:
            if unit['collection']:
                unit['collection'].name = '_PW_collection_' + uuid.uuid4().hex
    for unit in units:
        row = find(state, unit['uid'])
        if unit['merge']:
            unit['output'].name = unit['name']
        elif row.kind == 'GROUP':
            collection = row.collection
            if not collection:
                collection = bpy.data.collections.new(unit['name'])
                scene.collection.children.link(collection)
                row.collection = collection
            collection.name, collection[COLLECTION] = unit['name'], row.uid
            for item in unit['members']:
                obj = item.source
                if obj.name not in collection.objects:
                    collection.objects.link(obj)
                for prior in tuple(obj.users_collection):
                    if prior != collection:
                        prior.objects.unlink(obj)
                obj.name, obj[ports.GROUP] = unit['names'][item.uid], row.uid
        else:
            row.source.name = unit['name']
    links = scene.line_pipe_connections.links
    for index in reversed(range(len(links))):
        link = links[index]
        source_unit, target_unit = membership.get(link.source), membership.get(link.target)
        if (source_unit and source_unit is target_unit and source_unit['merge']
                and (not link.connector or membership.get(link.connector) is source_unit)):
            links.remove(index)
            continue
        for role, unit in (('source', source_unit), ('target', target_unit)):
            if unit and unit['merge']:
                obj, key = getattr(link, role), getattr(link, role + '_port')
                setattr(link, role + '_port', unit['port_map'][obj, key])
                setattr(link, role, unit['output'])
    endpoint_state = scene.line_pipe_connections
    for role in ('source', 'target'):
        obj = getattr(endpoint_state, role)
        unit = membership.get(obj)
        if unit and unit['merge']:
            key = getattr(endpoint_state, role + '_port')
            setattr(endpoint_state, role, unit['output'])
            wanted = unit['port_map'].get((obj, key))
            if wanted:
                setattr(endpoint_state, role + '_port', wanted)
    replacements = {obj: unit['output'] if unit['merge'] else obj for obj, unit in membership.items()}
    selected_outputs = {replacements.get(obj, obj) for obj in selected}
    active_output = replacements.get(active, active) if active else None
    state.syncing = True
    try:
        for unit in units:
            row = find(state, unit['uid'])
            row.name = unit['name']
            if unit['merge']:
                for item in unit['members']:
                    obj, block = item.source, item.source.data
                    bpy.data.objects.remove(obj, do_unlink=True)
                    connections.discard(block)
                for index in reversed(range(len(state.items))):
                    if state.items[index].parent_uid == unit['uid']:
                        state.items.remove(index)
                row = find(state, unit['uid'])
                row.kind, row.source, row.parent_uid = 'PIPE', unit['output'], ''
                row.collection = None
                row.original_name = row.name
            else:
                for item in unit['members']:
                    member = find(state, item.uid)
                    member.name = member.original_name = item.source.name
        for row in state.items:
            row.original_group = ports.group_id(row.source) if row.source else row.uid
        for obj in context.selected_objects:
            obj.select_set(False)
        for obj in selected_outputs:
            obj.select_set(True)
        if active_output:
            context.view_layer.objects.active = active_output
        normalize(state)
        state.dirty = False
    finally:
        state.syncing = False
    context.view_layer.update()
    return len(units)


class PW_OT_group_list(bpy.types.Operator):
    bl_idname = 'line_pipe.group_list'
    bl_label = 'Pipe Groups'
    bl_options = {'REGISTER', 'UNDO'}
    action: StringProperty()
    uid: StringProperty(options={'HIDDEN'})
    target: StringProperty(options={'HIDDEN'})
    placement: StringProperty(default='INTO', options={'HIDDEN'})

    @classmethod
    def description(cls, context, properties):
        key = 'groups_action_' + properties.action.lower()
        return i18n.tr(key if key in i18n.MESSAGES else 'tool_groups', context)

    @classmethod
    def poll(cls, context):
        return connection_ops.ready(context) and _drag is None and _box is None

    def execute(self, context):
        state = state_for(context.scene)
        try:
            row = find(state, self.uid) if self.uid else (state.items[state.active_index] if state.items else None)
            if self.action == 'REFRESH':
                refresh(context.scene)
            elif self.action == 'RESET':
                refresh(context.scene, reset=True)
            elif self.action == 'ADD':
                add_row(state, 'Group %03d' % (1 + sum(item.kind == 'GROUP' for item in state.items)), kind='GROUP')
                set_active(state, len(state.items)-1)
                state.dirty = True
            elif self.action == 'GROUP':
                group_rows(context)
            elif self.action == 'UNGROUP':
                checked = [item for item in state.items if item.selected]
                selected = [item.uid for item in checked if not any(parent.uid == item.parent_uid for parent in checked)] or ([row.uid] if row else [])
                for uid in selected:
                    ungroup(state, uid)
            elif self.action == 'MOVE':
                move_row(state, self.uid, self.target, self.placement)
            elif self.action in {'UP', 'DOWN'} and row:
                peers = [item for item in state.items if item.parent_uid == row.parent_uid]
                index = next(i for i, item in enumerate(peers) if item.uid == row.uid)
                target = index + (-1 if self.action == 'UP' else 1)
                if 0 <= target < len(peers):
                    move_row(state, row.uid, peers[target].uid, 'BEFORE' if self.action == 'UP' else 'AFTER')
            elif self.action == 'SELECT':
                select_rows(context, [row.uid] if row else [])
            elif self.action == 'VIEWPORT':
                sync_selection(context)
            elif self.action == 'TEMPLATE':
                planned = template_names(context.scene)
                for uid, name in planned:
                    find(state, uid).name = name
            elif self.action == 'PRESET':
                preset_changed(state, context)
            return {'FINISHED'}
        except Exception as error:
            return connection_ops.failure(self, context, error)


class PW_OT_group_apply(bpy.types.Operator):
    bl_idname = 'line_pipe.group_apply'
    bl_label = 'Apply to Blender'
    bl_options = {'REGISTER', 'UNDO'}
    mode: EnumProperty(items=[('MERGE', 'Mesh Objects', ''), ('COLLECTION', 'Collections', '')], default='MERGE')

    @classmethod
    def description(cls, context, properties):
        return i18n.tr('groups_apply_tip', context)

    @classmethod
    def poll(cls, context):
        return connection_ops.ready(context) and _drag is None and _box is None

    def execute(self, context):
        try:
            count = apply(context, self.mode)
            state_for(context.scene).apply_mode = self.mode
            self.report({'INFO'}, i18n.tr('groups_applied', context, count=count))
            return {'FINISHED'}
        except Exception as error:
            return connection_ops.failure(self, context, error)


class PW_UL_groups(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        row = layout.row(align=True)
        row.use_property_split = False
        row.prop(item, 'selected_zh' if i18n.language(context) == 'ZH' else 'selected', text='')
        row.prop_enum(item, 'drag_handle_zh' if i18n.language(context) == 'ZH' else 'drag_handle',
                      'DRAG', text='', icon='GRIP')
        if item.parent_uid:
            row.separator(factor=1)
        if item.kind == 'GROUP':
            row.prop(item, 'expanded_zh' if i18n.language(context) == 'ZH' else 'expanded', text='', icon='TRIA_DOWN' if item.expanded else 'TRIA_RIGHT', emboss=False)
        name_icon = ('OUTLINER_COLLECTION' if item.kind == 'GROUP' else 'ERROR' if not item.source
                     else 'OUTLINER_OB_CURVE' if item.source.type == 'CURVE' else 'OUTLINER_OB_MESH')
        name = row.row(align=True)
        name.prop_enum(item, 'selection_handle_zh' if i18n.language(context) == 'ZH' else 'selection_handle',
                       'DRAG', text=item.name, icon=name_icon)
        if item.kind == 'GROUP':
            count = row.row(align=True)
            count.ui_units_x = 1.2
            count.label(text=str(len(children(data, item.uid))))
        elif item.name != item.original_name:
            row.label(text='', icon='DOT')

    def filter_items(self, context, data, propname):
        visible = {row.uid for row in visible_rows(data)}
        return [self.bitflag_filter_item if row.uid in visible else 0 for row in data.items], []


class PW_OT_group_drag(bpy.types.Operator):
    bl_idname = 'line_pipe.group_drag'
    bl_label = 'Move Pipe Group'
    bl_options = {'INTERNAL', 'UNDO'}
    uid: StringProperty(options={'HIDDEN'})

    @classmethod
    def description(cls, context, properties):
        return i18n.tr('groups_drag_tip', context)

    def invoke(self, context, event):
        global _drag
        if _drag or _box or not connection_ops.ready(context):
            return {'CANCELLED'}
        self.scene, self.area, self.window = context.scene, context.area, context.window
        self.region = next(region for region in self.area.regions if region.type == 'UI')
        state = state_for(self.scene)
        visible = visible_rows(state)
        self.index = next((i for i, row in enumerate(visible) if row.uid == self.uid), -1)
        if self.index < 0:
            return {'CANCELLED'}
        set_active(state, next(i for i, row in enumerate(state.items) if row.uid == self.uid))
        self.y, self.x = event.mouse_prev_press_y, event.mouse_prev_press_x
        self.height = 20 * context.preferences.system.ui_scale
        self.target, self.placement = '', 'AFTER'
        self.pointer = (event.mouse_x - self.region.x, event.mouse_y - self.region.y)
        self.handle = bpy.types.SpaceView3D.draw_handler_add(self.draw_overlay, (), 'UI', 'POST_PIXEL')
        self.window.cursor_modal_set('SCROLL_Y')
        context.window_manager.modal_handler_add(self)
        _drag = self
        return {'RUNNING_MODAL'}

    def draw_overlay(self):
        if bpy.context.area != self.area or not self.target:
            return
        state = state_for(self.scene)
        target = find(state, self.target)
        if target:
            label = i18n.tr('groups_drop_' + self.placement.lower(), name=target.name)
            blf.size(0, 12)
            blf.color(0, 1, .8, .3, 1)
            blf.position(0, 12, max(12, self.pointer[1] + 20), 0)
            blf.draw(0, label)

    def cleanup(self):
        global _drag
        if getattr(self, 'handle', None):
            bpy.types.SpaceView3D.draw_handler_remove(self.handle, 'UI')
            self.handle = None
        self.window.cursor_modal_restore()
        self.area.tag_redraw()
        if _drag is self:
            _drag = None

    def modal(self, context, event):
        if _drag is not self:
            return {'CANCELLED'}
        if event.type in {'ESC', 'RIGHTMOUSE', 'WINDOW_DEACTIVATE'} or self.area not in context.screen.areas[:]:
            self.cleanup()
            return {'CANCELLED'}
        state = state_for(self.scene)
        release = event.type == 'LEFTMOUSE' and event.value == 'RELEASE'
        previous_release = (event.type != 'TIMER' and event.type_prev == 'LEFTMOUSE'
                            and event.value_prev == 'RELEASE')
        if event.type in {'MOUSEMOVE', 'INBETWEEN_MOUSEMOVE'} or release or previous_release:
            x = event.mouse_prev_x if previous_release and not release else event.mouse_x
            y = event.mouse_prev_y if previous_release and not release else event.mouse_y
            visible = visible_rows(state)
            delta = (self.y - y) / self.height
            index = self.index + math.floor(delta + .5)
            self.pointer = (x - self.region.x, y - self.region.y)
            self.target = visible[index].uid if (0 <= index < len(visible)
                and self.region.x <= x < self.region.x + self.region.width
                and self.region.y <= y < self.region.y + self.region.height) else ''
            target = find(state, self.target)
            fraction = delta - round(delta)
            self.placement = ('INTO' if target and target.kind == 'GROUP' and abs(fraction) < .28
                              else 'BEFORE' if fraction < 0 else 'AFTER')
            self.area.tag_redraw()
        if release or previous_release:
            target, placement = self.target, self.placement
            self.cleanup()
            passthrough = {'PASS_THROUGH'} if previous_release and not release else set()
            if target:
                move_row(state, self.uid, target, placement)
                return {'FINISHED'} | passthrough
            return {'CANCELLED'} | passthrough
        return {'RUNNING_MODAL'}


class PW_OT_group_box_select(bpy.types.Operator):
    bl_idname = 'line_pipe.group_box_select'
    bl_label = 'Box Select Pipes'
    bl_options = {'INTERNAL', 'UNDO', 'BLOCKING', 'MODAL_PRIORITY'}
    uid: StringProperty(options={'HIDDEN', 'SKIP_SAVE'})

    @classmethod
    def description(cls, context, properties):
        return i18n.tr('groups_box_tip', context)

    def invoke(self, context, event):
        global _box
        if _box or _drag or not connection_ops.ready(context):
            return {'CANCELLED'}
        if event.type == 'LEFTMOUSE' and event.value == 'RELEASE':
            select_rows(context, [self.uid], state_for(context.scene).selection_mode)
            return {'FINISHED'}
        self.area, self.window = context.area, context.window
        self.region = next(region for region in self.area.regions if region.type == 'UI')
        state = state_for(context.scene)
        self.rows = [row.uid for row in visible_rows(state)]
        if self.uid not in self.rows:
            return {'CANCELLED'}
        self.index = self.rows.index(self.uid)
        self.origin = (event.mouse_prev_press_x, event.mouse_prev_press_y)
        self.pointer = self.origin
        self.height = 20*context.preferences.system.ui_scale
        self.initial = set(context.selected_objects)
        self.mode = state.selection_mode
        self.handle = bpy.types.SpaceView3D.draw_handler_add(self.draw_overlay, (), 'UI', 'POST_PIXEL')
        set_active(state, next(i for i, row in enumerate(state.items) if row.uid == self.uid))
        self.window.cursor_modal_set('CROSSHAIR')
        context.window_manager.modal_handler_add(self)
        _box = self
        return {'RUNNING_MODAL'}

    def draw_overlay(self):
        if bpy.context.area != self.area or self.pointer == self.origin:
            return
        x0, y0 = self.origin[0]-self.region.x, self.origin[1]-self.region.y
        x1, y1 = self.pointer[0]-self.region.x, self.pointer[1]-self.region.y
        operators.lines([(x0, y0), (x1, y0), (x1, y0), (x1, y1),
                         (x1, y1), (x0, y1), (x0, y1), (x0, y0)], (1, .8, .3, 1), 1)

    def cleanup(self):
        global _box
        if self.handle is not None:
            bpy.types.SpaceView3D.draw_handler_remove(self.handle, 'UI')
            self.handle = None
        self.window.cursor_modal_restore()
        self.area.tag_redraw()
        if _box is self:
            _box = None

    def modal(self, context, event):
        if _box is not self:
            return {'CANCELLED', 'PASS_THROUGH'}
        # RNA button updates can invoke with the previous event's modifier flags.
        if event.ctrl or event.shift:
            self.mode = 'SUBTRACT' if event.ctrl else 'ADD'
        if (event.type in {'ESC', 'RIGHTMOUSE', 'WINDOW_DEACTIVATE'}
                or self.area not in context.screen.areas[:] or self.area.type != 'VIEW_3D'):
            self.cleanup()
            return {'CANCELLED', 'PASS_THROUGH'} if event.type == 'ESC' else {'CANCELLED'}
        release = event.type == 'LEFTMOUSE' and event.value == 'RELEASE'
        if event.type in {'MOUSEMOVE', 'INBETWEEN_MOUSEMOVE'} or release:
            self.pointer = (event.mouse_x, event.mouse_y)
            self.area.tag_redraw()
        if release:
            index = max(0, min(len(self.rows)-1, self.index+round((self.origin[1]-self.pointer[1])/self.height)))
            low, high = sorted((self.index, index))
            select_rows(context, self.rows[low:high+1], self.mode, self.initial)
            self.cleanup()
            return {'FINISHED', 'PASS_THROUGH'}
        return {'RUNNING_MODAL'}


def draw_groups(layout, context):
    state = state_for(context.scene)
    request_refresh(context.scene)
    layout.use_property_split = False
    layout.enabled = connection_ops.ready(context) and _drag is None
    row = layout.row(align=True)
    row.prop(state, 'search_zh' if i18n.language(context) == 'ZH' else 'search', text='', icon='VIEWZOOM', placeholder=i18n.tr('search', context))
    mode = row.row(align=True)
    mode.ui_units_x = 3.2
    mode.prop(state, 'selection_mode_zh' if i18n.language(context) == 'ZH' else 'selection_mode', text='')
    for action, icon in (('REFRESH', 'FILE_REFRESH'), ('RESET', 'LOOP_BACK')):
        row.operator('line_pipe.group_list', text='', icon=icon).action = action
    row = layout.row()
    row.template_list('PW_UL_groups', '', state, 'items', state, 'active_index', rows=max(4, min(10, len(visible_rows(state)))))
    col = row.column(align=True)
    for action, icon in (('ADD', 'NEWFOLDER'), ('GROUP', 'LINKED'), ('UNGROUP', 'UNLINKED'),
                         ('UP', 'TRIA_UP'), ('DOWN', 'TRIA_DOWN'), ('VIEWPORT', 'RESTRICT_SELECT_OFF')):
        col.operator('line_pipe.group_list', text='', icon=icon).action = action
    if 0 <= state.active_index < len(state.items):
        active = state.items[state.active_index]
        layout.prop(active, 'name_zh' if i18n.language(context) == 'ZH' else 'name', text=i18n.tr('name', context))
    from . import editing
    if editing.targets(context):
        layout.separator()
        layout.label(text=i18n.tr('edit_title', context))
        editing.draw(layout.column(), context)
        layout.separator()
    row = layout.row(align=True)
    row.prop(state, 'show_templates_zh' if i18n.language(context) == 'ZH' else 'show_templates', text=i18n.tr('groups_templates', context),
             icon='TRIA_DOWN' if state.show_templates else 'TRIA_RIGHT', emboss=False)
    status = row.row()
    status.ui_units_x = 4.3
    status.label(text=i18n.tr('groups_pending' if state.dirty else 'groups_synced', context), icon='DOT' if state.dirty else 'CHECKMARK')
    if state.show_templates:
        col = layout.column(align=True)
        row = col.row(align=True)
        i18n.prop(row, state, 'presets', context)
        i18n.prop(col, state, 'template', context)
        i18n.prop(col, state, 'template_scope', context)
        i18n.prop(col, state, 'start_index', context)
        try:
            sample = template_names(context.scene)
            col.label(text=sample[0][1], icon='SORTALPHA')
        except ValueError:
            pass
        col.operator('line_pipe.group_list', text=i18n.tr('groups_rename', context), icon='SORTALPHA').action = 'TEMPLATE'
    i18n.prop(layout, state, 'apply_mode', context)
    op = layout.operator('line_pipe.group_apply', text=i18n.tr('groups_apply', context), icon='CHECKMARK')
    op.mode = state.apply_mode


def abort():
    global _box_start
    if _box_start:
        if bpy.app.timers.is_registered(_box_start):
            bpy.app.timers.unregister(_box_start)
        _box_start = None
    if _drag:
        _drag.cleanup()
    if _box:
        _box.cleanup()


def unregister_callbacks():
    abort()
    for timer in tuple(_pending.values()):
        if bpy.app.timers.is_registered(timer):
            bpy.app.timers.unregister(timer)
    _pending.clear()
    _signatures.clear()
    _selection_signatures.clear()


for cls, tips in (
    (PW_GroupRow, {'name': 'groups_name_tip', 'selected': 'groups_select_tip', 'expanded': 'groups_expand_tip',
                   'drag_handle': 'groups_drag_tip', 'selection_handle': 'groups_box_tip'}),
    (PW_GroupState, {'search': 'groups_search_tip', 'apply_mode': 'groups_apply_mode_tip',
                     'selection_mode': 'groups_selection_mode_tip',
                     'show_templates': 'groups_templates_tip',
                     'template': 'groups_template_tip', 'template_scope': 'groups_scope_tip',
                     'start_index': 'groups_start_tip', 'presets': 'groups_preset_tip'}),
):
    i18n.add_chinese_properties(cls, tips)
    for key, tip in tips.items():
        cls.__annotations__[key].keywords['description'] = i18n.text(tip, 'EN')


CLASSES = (PW_GroupRow, PW_GroupState, PW_OT_group_list, PW_OT_group_apply, PW_UL_groups, PW_OT_group_drag,
           PW_OT_group_box_select)
