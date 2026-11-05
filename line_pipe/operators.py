# SPDX-License-Identifier: GPL-3.0-or-later
import json
import math
from dataclasses import dataclass
import bpy
import blf
import gpu
from bpy.props import BoolProperty
from bpy_extras import view3d_utils
from gpu_extras.batch import batch_for_shader
from mathutils import Vector
from . import data, geometry, i18n
from .model import (Route, WORLD_AXES, choose_initial_direction, initial_directions,
                    choose_sector, turn_directions, fillet_radii, bend_floor)

session = None
GUIDE_IDLE = data.GUIDE_IDLE
GUIDE_ACTIVE = data.GUIDE_ACTIVE
NAVIGATION_GAIN = .5
NATIVE_NAVIGATION = {'VIEW3D_OT_rotate', 'VIEW3D_OT_move', 'VIEW3D_OT_zoom', 'VIEW3D_OT_dolly'}


@dataclass
class Insertion:
    preview: object
    route: Route
    drawn: bool
    fitting: object
    ports: tuple[str, str]


class LP_OT_reset_guide_colors(bpy.types.Operator):
    bl_idname = 'line_pipe.reset_guide_colors'
    bl_label = 'Restore Default Arrow Colors'

    @classmethod
    def description(cls, context, properties):
        return i18n.tr('reset_guide_colors_tip', context)

    def execute(self, context):
        preferences = data.guide_preferences(context)
        preferences.guide_idle, preferences.guide_active = GUIDE_IDLE, GUIDE_ACTIVE
        return {'FINISHED'}


class LP_OT_language(bpy.types.Operator):
    bl_idname = 'line_pipe.language'
    bl_label = 'Language'

    @classmethod
    def description(cls, context, properties):
        return i18n.tr('language_tip', context)

    def execute(self, context):
        language = 'ZH' if i18n.language(context) == 'EN' else 'EN'
        context.scene.line_pipe_settings.language = language
        addon = context.preferences.addons.get(__package__)
        if addon:
            addon.preferences.language = language
            if context.preferences.use_preferences_save:
                bpy.ops.wm.save_userpref()
        for window in context.window_manager.windows:
            for area in window.screen.areas:
                area.tag_redraw()
        return {'FINISHED'}


def direction(settings, normal=None):
    axes = {'X': (1, 0, 0), 'NX': (-1, 0, 0), 'Y': (0, 1, 0), 'NY': (0, -1, 0),
            'Z': (0, 0, 1), 'NZ': (0, 0, -1)}
    if settings.direction == 'AUTO':
        return Vector((1, 0, 0))
    if settings.direction == 'NORMAL':
        return Vector(normal) if normal is not None else Vector((1, 0, 0))
    return Vector(settings.custom_direction) if settings.direction == 'CUSTOM' else Vector(axes[settings.direction])


def selected_face(context, settings):
    obj = context.active_object
    if not obj or obj.type != 'MESH' or settings.face_index >= len(obj.data.polygons):
        raise ValueError('bad_face')
    face = obj.data.polygons[settings.face_index]
    normal = (obj.matrix_world.to_3x3().inverted().transposed() @ face.normal).normalized()
    return obj.matrix_world @ face.center + normal * settings.surface_offset, normal


def lines(vertices, color, width=2):
    shader = gpu.shader.from_builtin('UNIFORM_COLOR')
    shader.bind()
    shader.uniform_float('color', color)
    gpu.state.line_width_set(width)
    batch_for_shader(shader, 'LINES', {'pos': vertices}).draw(shader)


def axis_label(heading):
    for key, axis in WORLD_AXES.items():
        if heading.dot(axis) > .999:
            return key
    return ' / '.join('%+.2f' % value for value in heading)


def screen_text(text, position, color=(.95, .95, .95, 1)):
    blf.size(0, 13)
    blf.color(0, *color)
    blf.position(0, position[0], position[1], 0)
    blf.draw(0, text)


def format_length(value, units):
    return (format(value, '.6g') if units.system == 'NONE' else
            bpy.utils.units.to_string(units.system, 'LENGTH', value * units.scale_length, precision=6))


class LP_OT_draw(bpy.types.Operator):
    bl_idname = 'line_pipe.draw'
    bl_label = 'Draw Pipe'
    bl_options = {'REGISTER', 'UNDO', 'BLOCKING'}
    quick_start: BoolProperty(default=False, options={'HIDDEN', 'SKIP_SAVE'})

    @classmethod
    def description(cls, context, properties):
        return i18n.tr('draw_tip', context)

    @classmethod
    def poll(cls, context):
        return context.area and context.area.type == 'VIEW_3D' and context.mode == 'OBJECT'

    def invoke(self, context, event):
        global session
        if session:
            self.report({'WARNING'}, i18n.tr('busy', context))
            return {'CANCELLED'}
        settings = context.scene.line_pipe_settings
        if settings.bend_radius < bend_floor(settings.diameter):
            self.report({'ERROR'}, i18n.tr('bad_radius', context))
            return {'CANCELLED'}
        settings.tool_mode = 'DRAW'
        self.area = context.area
        self.region = next(r for r in self.area.regions if r.type == 'WINDOW')
        self.rv3d = context.space_data.region_3d
        self.window = context.window
        self.route = None
        self.obj = None
        self._insertions = []
        self._aborted = False
        self._cleaned = False
        self._handles = []
        self._needs_rebase = True
        self._view_state = self.view_state()
        self._warp_pending = None
        self._navigation_timer = None
        self._navigation_feedback = None
        self._follow = settings.follow_tip
        self._follow_offset = Vector((0, 0, 0))
        self._start_mouse = self.mouse(event)
        self._notice = ''
        self._notice_until = 0
        self._selected = list(context.selected_objects)
        self._active = context.active_object
        self._turn_key = settings.turn_key
        self._diameter, self._radius = settings.diameter, settings.bend_radius
        self._sides, self._steps = data.generation_sides(settings), settings.bend_steps
        self._free_sides = settings.free_sides
        self._fitting_id = settings.continuation_fitting
        self._start_mode = 'QUICK' if self.quick_start else settings.start_mode
        try:
            self._bore = data.bore(settings)
            self._wall_profile = tuple(getattr(settings, key) for key in data.PROFILE)
            if self.quick_start:
                pass
            elif settings.start_mode == 'CURSOR':
                self.start(context, context.scene.cursor.location, direction(settings))
            elif settings.start_mode == 'COORDINATES':
                self.start(context, settings.origin, direction(settings))
            elif settings.start_mode == 'FACE':
                origin, normal = selected_face(context, settings)
                self.start(context, origin, direction(settings, normal))
            elif direction(settings).length < 1e-7 and settings.direction == 'CUSTOM':
                raise ValueError('bad_direction')
            self._handles.append(bpy.types.SpaceView3D.draw_handler_add(self.draw_world, (), 'WINDOW', 'POST_VIEW'))
            self._handles.append(bpy.types.SpaceView3D.draw_handler_add(self.draw_screen, (), 'WINDOW', 'POST_PIXEL'))
            self._timer = context.window_manager.event_timer_add(.12, window=context.window)
            session = self
            context.window_manager.modal_handler_add(self)
            self.status(context)
            self.area.tag_redraw()
            return {'RUNNING_MODAL'}
        except Exception as error:
            self.cleanup(context, cancel=True)
            self.report({'ERROR'}, self.message(context, error))
            return {'CANCELLED'}

    def message(self, context, error):
        key = str(error)
        return i18n.tr(key, context) if key in i18n.MESSAGES else i18n.tr('error', context, error=key)

    def start(self, context, origin, heading):
        self.route = Route(origin, heading, self._diameter, self._radius,
                           axis_initial=self.quick_start or context.scene.line_pipe_settings.direction == 'AUTO')
        self.obj = geometry.create(context, mesh=bool(self._bore))
        self.obj.location = origin
        self.obj.hide_render = True
        for selected in context.selected_objects:
            selected.select_set(False)
        self.obj.select_set(True)
        context.view_layer.objects.active = self.obj
        self._needs_rebase = True
        if self._follow:
            self.rv3d.view_location = self.route.tip
            self._view_state = self.view_state()

    def view_state(self):
        return (tuple(self.rv3d.view_rotation), tuple(self.rv3d.view_location),
                self.rv3d.view_distance, self.rv3d.view_perspective)

    def sync_view(self, context):
        state = self.view_state()
        if state != self._view_state:
            self._needs_rebase = True
            self._warp_pending = None
            if self.route:
                self._follow_offset = self.rv3d.view_location - self.route.tip
                if self.route.turning:
                    self.route.candidate = None
            self._view_state = state
        follow = context.scene.line_pipe_settings.follow_tip
        if follow != self._follow:
            self._follow = follow
            self._needs_rebase = True
            self._warp_pending = None
            if follow and self.route:
                self._follow_offset = Vector((0, 0, 0))
                self.rv3d.view_location = self.route.tip
                self._view_state = self.view_state()

    def follow(self):
        if self._follow and self.route:
            self.rv3d.view_location = self.route.tip + self._follow_offset
            self._view_state = self.view_state()

    def wrap_pointer(self, event):
        if not self._follow:
            return
        p = self.mouse(event)
        target = p.copy()
        left, right = self.viewport_bounds()
        margin = 24
        if right - left < margin * 6 or self.region.height < margin * 6:
            return
        for axis, low, high in ((0, left, right), (1, 0, self.region.height)):
            if p[axis] < low + margin:
                target[axis] = high - margin * 2
            elif p[axis] > high - margin:
                target[axis] = low + margin * 2
        target = Vector((round(target.x), round(target.y)))
        if (target - p).length > 1:
            # Shift the anchor with the cursor so the synthetic move adds no length.
            self._mouse_base += target - p
            self._warp_pending = target
            self.window.cursor_warp(int(self.region.x + target.x), int(self.region.y + target.y))

    def viewport_bounds(self):
        left, right = 0, self.region.width
        space = self.area.spaces.active
        for region in self.area.regions:
            if ((region.type == 'UI' and space.show_region_ui or
                 region.type == 'TOOLS' and space.show_region_toolbar) and region.width > 1):
                if region.x <= self.region.x:
                    left = max(left, region.x + region.width - self.region.x)
                else:
                    right = min(right, region.x - self.region.x)
        return left, right

    def mouse(self, event):
        return Vector((event.mouse_x - self.region.x, event.mouse_y - self.region.y))

    def inside(self, event):
        p = self.mouse(event)
        left, right = self.viewport_bounds()
        return left <= p.x < right and 0 <= p.y < self.region.height

    def project(self, position):
        return view3d_utils.location_3d_to_region_2d(self.region, self.rv3d, position)

    def guide_center(self, anchor):
        left, right = self.viewport_bounds()
        if anchor is None:
            return Vector(((left + right) / 2, self.region.height / 2))
        margin_x = min(100, (right - left) / 2)
        margin_y = min(100, self.region.height / 2)
        return Vector((max(left + margin_x, min(right - margin_x, anchor.x)),
                       max(margin_y, min(self.region.height - margin_y, anchor.y))))

    def rebase(self, event):
        self.follow()
        self.rv3d.update()
        # A fast key release can arrive before cursor_warp's OS mouse move.
        # Rebase at the destination and keep ignoring that pending synthetic move.
        self._mouse_base = (self._warp_pending.copy() if self._warp_pending is not None
                            else self.mouse(event))
        self._length_base = self.route.length
        depth = self.route.tip
        a = view3d_utils.region_2d_to_location_3d(self.region, self.rv3d, self._mouse_base, depth)
        b = view3d_utils.region_2d_to_location_3d(self.region, self.rv3d, self._mouse_base + Vector((0, 1)), depth)
        pixel_size = (b - a).length
        inv_view = self.rv3d.view_rotation.inverted()
        projected = (inv_view @ self.route.heading).xy
        self._extension_scale = (projected.normalized() * pixel_size / projected.length
                                 if projected.length > .15 else Vector((0, pixel_size)))
        if self.route.choosing_initial:
            self._initial_directions = initial_directions(lambda axis: (inv_view @ axis).xy)
            self._initial_scales = {key: pixel_size / max((inv_view @ axis).xy.length, .2)
                                    for key, axis in WORLD_AXES.items()}
            self._initial_choice = next((key for key, axis in WORLD_AXES.items()
                                         if axis.dot(self.route.heading) > .999 and self.route.length > 0), None)
            self._initial_base = (self._initial_directions[self._initial_choice] *
                                  (self.route.length / self._initial_scales[self._initial_choice])
                                  if self._initial_choice else Vector((0, 0)))
        if self.route.turning:
            self._turn_mouse = self._mouse_base.copy()
            self._directions = turn_directions(self.route.u, self.route.v, lambda value: (inv_view @ value).xy)
        self._needs_rebase = False

    def extension(self, event):
        delta = self.mouse(event) - self._mouse_base
        if self.route.choosing_initial:
            displacement = self._initial_base + delta
            choice = choose_initial_direction(displacement, self._initial_directions, self._initial_choice)
            if choice is None:
                self.route.extend(0)
                self._initial_choice = None
            else:
                self.route.aim_initial(choice, displacement.dot(self._initial_directions[choice]) * self._initial_scales[choice])
                self._initial_choice = choice
            return
        # Navigation rebases this scale; following the tip does not change it.
        self.route.extend(self._length_base + delta.dot(self._extension_scale))

    def native_navigation_active(self):
        return any(op and op.bl_idname in NATIVE_NAVIGATION for op in self.window.modal_operators)

    def queue_navigation_feedback(self, context, event):
        if not self.route or not self.inside(event) or self._navigation_timer or self._navigation_feedback:
            return
        self.rebase(event)
        self._navigation_button = event.type
        self._navigation_mouse = self.mouse(event)
        self._navigation_length = self.route.length
        self._navigation_scale = self._extension_scale.copy()

        def attach():
            self._navigation_timer = None
            if session is self and not self._cleaned and self.native_navigation_active():
                with bpy.context.temp_override(window=self.window, area=self.area, region=self.region):
                    bpy.ops.line_pipe.navigation_feedback('INVOKE_DEFAULT')
            return None

        # Native viewport operators consume their mouse moves. Attach above that
        # handler after the original mouse press has reached Blender's keymap.
        self._navigation_timer = attach
        bpy.app.timers.register(attach, first_interval=0)

    def navigation_feedback(self, event):
        if not self.route or self.route.turning:
            return
        delta = self.mouse(event) - self._navigation_mouse
        self.route.extend(self._navigation_length + NAVIGATION_GAIN * delta.dot(self._navigation_scale))
        # Leave camera movement entirely to native navigation, including with Follow Tip on.
        geometry.update(self.obj, self.route.route_points(), self._diameter, self._radius,
                        self._sides, self._steps, bore=self._bore)
        self.area.tag_redraw()

    def begin_turn(self, context, event):
        if self.route.turning:
            return
        if not self.route.begin_turn():
            self.notice(context, 'too_short', length=self.route.turn_minimum)
            return
        self._notice = ''
        self.rv3d.update()
        # Share the guides' safe visible anchor, including when the tip is offscreen.
        center = self.guide_center(self.project(self.route.tip))
        self._turn_mouse = Vector((round(center.x), round(center.y)))
        self._warp_pending = self._turn_mouse.copy()
        self.window.cursor_warp(int(self.region.x + self._turn_mouse.x),
                                int(self.region.y + self._turn_mouse.y))
        inv_view = self.rv3d.view_rotation.inverted()
        self._directions = turn_directions(self.route.u, self.route.v,
                                           lambda value: (inv_view @ value).xy)

    def notice(self, context, key, **values):
        import time
        self._notice = (key, values)
        self._notice_until = time.monotonic() + 2.5
        self.status(context)

    def status(self, context):
        import time
        if self._notice and time.monotonic() < self._notice_until:
            key, values = self._notice
            message = i18n.tr(key, context, **values)
        else:
            key = ('navigating' if self._navigation_feedback else
                   'turning' if self.route.turning else 'initial' if self.route.choosing_initial else 'drawing') if self.route else (
                'quick_wait' if self._start_mode == 'QUICK' else
                'surface_wait' if self._start_mode == 'SURFACE' else 'waiting')
            message = i18n.tr(key, context, turn_key=self._turn_key) if key in ('turning', 'initial', 'drawing') else i18n.tr(key, context)
        self.area.header_text_set(message)
        context.workspace.status_text_set(message)

    def refresh(self):
        if self.route:
            self.follow()
            geometry.update(self.obj, self.route.route_points(), self._diameter, self._radius,
                            self._sides, self._steps, bore=self._bore)
        self.area.tag_redraw()

    def freeze_segment(self):
        dimensions = (self._diameter, self._radius, self._sides, self._steps)
        geometry.update(self.obj, self.route.route_points(False), *dimensions, store=True, bore=self._bore)
        data.store_parameters(self.obj, *dimensions, self._wall_profile, self._free_sides)

    def insert_fitting(self, context, event):
        from . import connections, fittings, ports
        drawn = self.route is not None and self.route.length > 1e-7
        if self.route is None or (not drawn and not self._insertions):
            self.notice(context, 'continuation_needs_pipe')
            return
        if self.route.turning:
            self.notice(context, 'continuation_finish_bend')
            return

        part, preview = None, None
        try:
            part = fittings.fitted_continuation(context, self._fitting_id, self._diameter, self._bore, self._sides)
            part.hide_render = True
            if drawn:
                self.freeze_segment()
            reference = self.obj if drawn else self._insertions[-1].fitting
            reference_key = 'END' if drawn else self._insertions[-1].ports[1]
            fitting_keys = fittings.continuation_keys(part)
            context.view_layer.update()
            anchor = ports.read(context.scene, reference, reference_key)
            inlet = ports.read(context.scene, part, fitting_keys[0])
            ports.compatible(inlet, anchor)
            matrices, _ = connections.docking_matrices(context.scene, inlet, anchor, 0)
            connections.set_matrices(matrices)
            outlet = ports.read(context.scene, part, fitting_keys[1])
            next_route = Route(outlet.position, outlet.direction, self._diameter, self._radius)
            preview = geometry.create(context, mesh=True)
            preview.location = outlet.position
            preview.hide_render = True
            frames = {'start_radial': list(outlet.radial)}
            if outlet.bore:
                frames['start_inner'] = list(outlet.inner_radial)
            preview[geometry.SWEEP_FRAMES] = json.dumps(frames)
        except (ValueError, RuntimeError, OSError) as error:
            geometry.remove(preview)
            geometry.remove(part)
            key = str(error)
            self.notice(context, key if key in i18n.MESSAGES else 'error',
                        error=key, **getattr(error, 'details', {}))
            return

        self._insertions.append(Insertion(self.obj, self.route, drawn, part, fitting_keys))
        self.obj, self.route = preview, next_route
        fittings.select_object(context, preview)
        self.follow()
        self.rebase(event)
        self.notice(context, 'continuation_added', name=fittings.continuation_name(self._fitting_id, context))

    def undo_segment(self, context):
        if self.route.turning or self.route.history or not self._insertions:
            self.route.undo()
            return
        from . import fittings
        last = self._insertions.pop()
        geometry.remove(self.obj)
        geometry.remove(last.fitting)
        self.obj, self.route = last.preview, last.route
        fittings.select_object(context, self.obj)
        self._notice = ''

    def finish(self, context):
        from . import connections, fittings, port_rings, ports
        drawn = self.route is not None and self.route.length > 1e-7
        if not drawn and not self._insertions:
            self.notice(context, 'empty')
            return {'RUNNING_MODAL'}
        if drawn:
            self.route.release_turn()
            self.freeze_segment()

        chain = []
        for insertion in self._insertions:
            if insertion.drawn:
                chain.append((insertion.preview, 'START', 'END'))
            chain.append((insertion.fitting, *insertion.ports))
        if drawn:
            chain.append((self.obj, 'START', 'END'))
        if self._insertions:
            context.view_layer.update()
            joints = []
            for (reference, _, outlet), (moving, inlet, _) in zip(chain, chain[1:]):
                a = ports.read(context.scene, reference, outlet)
                b = ports.read(context.scene, moving, inlet)
                ports.compatible(a, b)
                if (a.sides != b.sides or (a.position - b.position).length > max(2e-5, a.diameter * 1e-4)
                        or a.direction.dot(b.direction) > -.9999
                        or abs(port_rings.phase_offset(a.radial, b.radial, a.direction, a.sides)) > 1e-4
                        or a.bore and abs(port_rings.phase_offset(
                            a.inner_radial, b.inner_radial, a.direction, a.sides)) > 1e-4):
                    raise ports.ConnectionError('continuation_join')
                joints.append((a, b))
            links = context.scene.line_pipe_connections.links
            count = len(links)
            try:
                for a, b in joints:
                    record = connections.new_link(context.scene, b.obj, b.key, a.obj, a.key, 'DIRECT')
                    record.sides = a.sides
                group = ports.group_id(chain[0][0])
                for obj, _, _ in chain:
                    obj[ports.GROUP] = group
            except Exception:
                while len(links) > count:
                    links.remove(len(links) - 1)
                raise

        for insertion in self._insertions:
            if not insertion.drawn:
                geometry.remove(insertion.preview)
        if not drawn:
            geometry.remove(self.obj)
        self._insertions.clear()
        self.obj, _, outlet = chain[-1]
        for obj, _, _ in chain:
            obj.hide_render = False
        fittings.select_object(context, self.obj)
        context.scene.line_pipe_connections.source = self.obj
        context.scene.line_pipe_connections.source_port = outlet
        self.cleanup(context, cancel=False)
        self.report({'INFO'}, i18n.tr('done', context))
        return {'FINISHED'}

    def modal(self, context, event):
        if self._aborted:
            return {'CANCELLED'}
        try:
            if not any(area == self.area for area in context.screen.areas) or self.area.spaces.active.type != 'VIEW_3D':
                self.cleanup(context, cancel=True)
                return {'CANCELLED'}
            if event.type in {'ESC', 'WINDOW_DEACTIVATE'} or event.type == 'RIGHTMOUSE' and not event.alt:
                self.cleanup(context, cancel=True)
                return {'CANCELLED'}
            self.sync_view(context)
            if event.type == 'TIMER':
                self.status(context)
                self.area.tag_redraw()
                return {'RUNNING_MODAL'}
            if event.type == 'MIDDLEMOUSE' or event.alt and event.type in {'LEFTMOUSE', 'RIGHTMOUSE'}:
                if event.value == 'PRESS':
                    self.queue_navigation_feedback(context, event)
                self._needs_rebase = True
                return {'PASS_THROUGH'}
            if event.type in {'LEFT_ALT', 'RIGHT_ALT'} or (
                    event.type in {'MOUSEMOVE', 'INBETWEEN_MOUSEMOVE'} and event.alt):
                # Alt navigation and axis gestures need moves to reach the native keymap.
                # Native operators can consume the initiating button's release.
                self._needs_rebase = True
                return {'PASS_THROUGH'}
            if event.type in {'WHEELUPMOUSE', 'WHEELDOWNMOUSE', 'TRACKPADPAN', 'TRACKPADZOOM', 'NDOF_MOTION'}:
                self._needs_rebase = True
                return {'PASS_THROUGH'}
            if event.type == 'F' and event.ctrl and event.value == 'PRESS' and not event.is_repeat:
                settings = context.scene.line_pipe_settings
                settings.follow_tip = not settings.follow_tip
                self.sync_view(context)
                self.area.tag_redraw()
            elif event.type == 'E' and event.value == 'PRESS' and not event.is_repeat and not event.ctrl:
                self.insert_fitting(context, event)
            elif self._start_mode == 'QUICK' and self.route is None:
                if event.type == 'MOUSEMOVE' and self.inside(event):
                    delta = self.mouse(event) - self._start_mouse
                    if abs(delta.x) >= 32 and abs(delta.x) >= abs(delta.y):
                        if delta.x < 0:
                            self.start(context, Vector((0, 0, 0)), direction(context.scene.line_pipe_settings))
                            self.rebase(event)
                            self.refresh()
                        else:
                            self._start_mode = 'SURFACE'
                self.area.tag_redraw()
            elif self.route and event.type == self._turn_key and event.value == 'RELEASE':
                self.route.release_turn()
                self.rebase(event)
                self.refresh()
            elif event.type in {'RET', 'NUMPAD_ENTER'} and event.value == 'PRESS':
                try:
                    return self.finish(context)
                except ValueError as error:
                    if not self._insertions:
                        raise
                    key = str(error)
                    self.notice(context, key if key in i18n.MESSAGES else 'error', error=key)
                    return {'RUNNING_MODAL'}
            elif event.type == 'BACK_SPACE' and event.value == 'PRESS' or (
                    event.type == 'Z' and event.ctrl and event.value == 'PRESS'):
                if self.route:
                    self.undo_segment(context)
                    self.rebase(event)
                    self.refresh()
            elif self.route and event.type == self._turn_key and event.value == 'PRESS' and not event.is_repeat and not event.ctrl:
                # The turn key must also recover a pointer that has left the viewport.
                if self._needs_rebase:
                    self.rebase(event)
                self.begin_turn(context, event)
            elif not self.inside(event) and not (self.route and self._follow and
                    event.type == 'MOUSEMOVE' and not self.route.turning):
                return {'PASS_THROUGH'}
            elif not self.route:
                if event.type == 'LEFTMOUSE' and event.value == 'PRESS':
                    mouse = self.mouse(event)
                    settings = context.scene.line_pipe_settings
                    if self._start_mode in {'SURFACE', 'QUICK'}:
                        origin = view3d_utils.region_2d_to_origin_3d(self.region, self.rv3d, mouse)
                        ray = view3d_utils.region_2d_to_vector_3d(self.region, self.rv3d, mouse)
                        hit, point, normal, _, _, _ = context.scene.ray_cast(context.evaluated_depsgraph_get(), origin, ray)
                        if not hit:
                            self.notice(context, 'miss')
                            return {'RUNNING_MODAL'}
                        point += normal * settings.surface_offset
                    else:
                        point = view3d_utils.region_2d_to_location_3d(self.region, self.rv3d, mouse, context.scene.cursor.location)
                        normal = None
                    self.start(context, point, direction(settings, normal))
                    self.rebase(event)
                    self.refresh()
            elif event.type == 'MOUSEMOVE':
                if self._warp_pending is not None:
                    target = self._warp_pending
                    self._warp_pending = None
                    if (self.mouse(event) - target).length <= 1:
                        return {'RUNNING_MODAL'}
                if self._needs_rebase:
                    self.rebase(event)
                elif self.route.turning:
                    sector = choose_sector(self.mouse(event) - self._turn_mouse)
                    self.route.candidate = None
                    if sector:
                        self.route.choose(self._directions[sector])
                else:
                    self.extension(event)
                    self.wrap_pointer(event)
                self.refresh()
            self.status(context)
            return {'RUNNING_MODAL'}
        except Exception as error:
            self.cleanup(context, cancel=True)
            self.report({'ERROR'}, self.message(context, error))
            return {'CANCELLED'}

    def draw_world(self):
        if (bpy.context.area != self.area or not self.route or
                not bpy.context.scene.line_pipe_settings.show_guides):
            return
        try:
            idle, active = data.guide_colors()
            gpu.state.blend_set('ALPHA')
            gpu.state.depth_test_set('NONE')
            points = self.route.route_points()
            vertices = [tuple(p) for pair in zip(points, points[1:]) for p in pair]
            if vertices:
                lines(vertices, (0.15, .85, .68, .8))
            if self.route.turning:
                tip = self.route.tip
                distance = max(self._radius * 1.8, self._diameter * 3)
                for heading in self._directions.values():
                    selected = self.route.candidate is not None and heading.dot(self.route.candidate) > .99
                    lines([tuple(tip), tuple(tip + heading * distance)],
                          active if selected else idle, 4 if selected else 2)
        finally:
            gpu.state.line_width_set(1)
            gpu.state.depth_test_set('NONE')
            gpu.state.blend_set('NONE')

    def draw_screen(self):
        if bpy.context.area != self.area:
            return
        idle, active = data.guide_colors()
        if self._start_mode == 'QUICK' and not self.route:
            left, right = self.viewport_bounds()
            center = Vector((max(left + 160, min(right - 160, self._start_mouse.x)),
                             max(65, min(self.region.height - 65, self._start_mouse.y))))
            gpu.state.blend_set('ALPHA')
            try:
                for sign, key in ((-1, 'origin_choice'), (1, 'surface_choice')):
                    end = center + Vector((sign * 90, 0))
                    lines([tuple(center + Vector((sign * 16, 0))), tuple(end), tuple(end),
                           tuple(end + Vector((-sign * 10, 6))), tuple(end),
                           tuple(end + Vector((-sign * 10, -6)))], idle, 3)
                    label = i18n.tr(key)
                    blf.size(0, 13)
                    text_width = blf.dimensions(0, label)[0]
                    screen_text(label, (center.x + sign * 85 - text_width / 2, center.y + 18))
            finally:
                gpu.state.line_width_set(1)
                gpu.state.blend_set('NONE')
            return
        if not self.route or not bpy.context.scene.line_pipe_settings.show_guides:
            return
        initial = self.route.choosing_initial and hasattr(self, '_initial_directions')
        settings = bpy.context.scene.unit_settings
        length = format_length(self.route.length, settings)
        screen_text(i18n.tr('live_length', length=length), (24, 70))
        radii = fillet_radii(self.route.route_points(), self._radius, self._diameter / 2)
        if radii:
            screen_text(i18n.tr('live_radius', radius=format_length(radii[-1], settings)), (24, 26))
        if self.route.turning:
            screen_text(i18n.tr('bend_angle' if self.route.candidate is not None else 'no_bend'), (24, 48))
        if not self.route.turning and not initial:
            return
        gpu.state.blend_set('ALPHA')
        try:
            anchor = self.project(self.route.points[0] if initial else self.route.tip)
            if anchor is None:
                return
            center = self.guide_center(anchor)
            if (center - anchor).length > 1:
                lines([tuple(anchor), tuple(center)], idle, 1)
            arrows = ({key: value * 80 for key, value in self._initial_directions.items()} if initial else
                      {'RIGHT': (65, 0), 'LEFT': (-65, 0), 'UP': (0, 65), 'DOWN': (0, -65)})
            for sector, delta in arrows.items():
                d = Vector(delta).normalized()
                end = center + Vector(delta)
                perpendicular = Vector((-d.y, d.x))
                vertices = [center + d * 22, end, end, end - d * 10 + perpendicular * 6,
                            end, end - d * 10 - perpendicular * 6]
                heading = WORLD_AXES[sector] if initial else self._directions[sector]
                selected = self._initial_choice == sector if initial else (
                    self.route.candidate is not None and self.route.candidate.dot(heading) > .99)
                lines([tuple(v) for v in vertices], active if selected else idle, 3)
                label = sector if initial else axis_label(heading)
                blf.size(0, 12)
                blf.color(0, .95, .95, .95, 1)
                blf.position(0, end.x - 10, end.y + 12, 0)
                blf.draw(0, label)
        finally:
            gpu.state.line_width_set(1)
            gpu.state.blend_set('NONE')

    def cleanup(self, context, cancel):
        global session
        if self._cleaned:
            return
        self._cleaned = True
        self._warp_pending = None
        if self._navigation_timer and bpy.app.timers.is_registered(self._navigation_timer):
            bpy.app.timers.unregister(self._navigation_timer)
        self._navigation_timer = None
        if self._navigation_feedback:
            self._navigation_feedback.done = True
            self._navigation_feedback = None
        session = None
        for handle in self._handles:
            bpy.types.SpaceView3D.draw_handler_remove(handle, 'WINDOW')
        self._handles.clear()
        if hasattr(self, '_timer'):
            context.window_manager.event_timer_remove(self._timer)
            del self._timer
        if any(area == self.area for area in context.screen.areas):
            self.area.header_text_set(None)
            self.area.tag_redraw()
        context.workspace.status_text_set(None)
        if cancel:
            geometry.remove(self.obj)
            for insertion in reversed(self._insertions):
                geometry.remove(insertion.fitting)
                geometry.remove(insertion.preview)
            self._insertions.clear()
            for obj in self._selected:
                if obj.name in context.view_layer.objects:
                    obj.select_set(True)
            if self._active and self._active.name in context.view_layer.objects:
                context.view_layer.objects.active = self._active

    def cancel(self, context):
        self.cleanup(context, cancel=True)


class LP_OT_navigation_feedback(bpy.types.Operator):
    """Observe native navigation without consuming its events or changing its keymap."""
    bl_idname = 'line_pipe.navigation_feedback'
    bl_label = 'Pipe Navigation Feedback'
    bl_options = {'INTERNAL'}

    def invoke(self, context, event):
        self.owner = session
        if not self.owner or not self.owner.native_navigation_active():
            return {'CANCELLED'}
        self.done = False
        self.owner._navigation_feedback = self
        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}

    def modal(self, context, event):
        owner = self.owner
        if (self.done or session is not owner or owner._cleaned or
                not owner.native_navigation_active() or
                event.type in {'ESC', 'WINDOW_DEACTIVATE'} or
                event.type == owner._navigation_button and event.value == 'RELEASE'):
            if owner._navigation_feedback is self:
                owner._navigation_feedback = None
                owner._needs_rebase = True
            return {'FINISHED', 'PASS_THROUGH'}
        if event.type == 'MOUSEMOVE':
            try:
                owner.navigation_feedback(event)
            except Exception as error:
                owner.cleanup(context, cancel=True)
                owner.report({'ERROR'}, owner.message(context, error))
                return {'FINISHED', 'PASS_THROUGH'}
        return {'PASS_THROUGH'}


class LP_OT_mesh(bpy.types.Operator):
    bl_idname = 'line_pipe.mesh'
    bl_label = 'Convert to Mesh'
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def description(cls, context, properties):
        return i18n.tr('mesh_tip', context)

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return session is None and context.mode == 'OBJECT' and obj and obj.type == 'CURVE' and obj.line_pipe.enabled

    def execute(self, context):
        obj = context.active_object
        # Native conversion preserves evaluated solid geometry and object transforms.
        with context.temp_override(selected_objects=[obj], selected_editable_objects=[obj]):
            bpy.ops.object.convert(target='MESH')
            geometry.remember_mesh(context.active_object)
        context.object.line_pipe.enabled = False
        return {'FINISHED'}


def abort(_=None):
    if session:
        operation = session
        operation._aborted = True
        operation.cleanup(bpy.context, cancel=True)


CLASSES = (LP_OT_language, LP_OT_reset_guide_colors, LP_OT_draw, LP_OT_navigation_feedback, LP_OT_mesh)
