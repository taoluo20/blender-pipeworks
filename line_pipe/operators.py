# SPDX-License-Identifier: GPL-3.0-or-later
import json
import math
import bpy
import blf
import gpu
from bpy.props import BoolProperty
from bpy_extras import view3d_utils
from gpu_extras.batch import batch_for_shader
from mathutils import Vector
from . import data, geometry, i18n
from .model import Route, WORLD_AXES, choose_initial_direction, initial_directions, choose_sector, turn_directions

session = None


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
        if settings.bend_radius <= settings.diameter / 2:
            self.report({'ERROR'}, i18n.tr('bad_radius', context))
            return {'CANCELLED'}
        self.area = context.area
        self.region = next(r for r in self.area.regions if r.type == 'WINDOW')
        self.rv3d = context.space_data.region_3d
        self.window = context.window
        self.route = None
        self.obj = None
        self._aborted = False
        self._cleaned = False
        self._handles = []
        self._navigation = False
        self._needs_rebase = True
        self._notice = ''
        self._notice_until = 0
        self._selected = list(context.selected_objects)
        self._active = context.active_object
        self._turn_key = settings.turn_key
        self._diameter, self._radius = settings.diameter, settings.bend_radius
        self._sides, self._steps = settings.radial_segments, settings.bend_steps
        self._start_mode = 'QUICK' if self.quick_start else settings.start_mode
        try:
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
        self.obj = geometry.create(context)
        self.obj.location = origin
        self.obj.hide_render = True
        for selected in context.selected_objects:
            selected.select_set(False)
        self.obj.select_set(True)
        context.view_layer.objects.active = self.obj
        self._needs_rebase = True

    def mouse(self, event):
        return Vector((event.mouse_x - self.region.x, event.mouse_y - self.region.y))

    def inside(self, event):
        p = self.mouse(event)
        return 0 <= p.x < self.region.width and 0 <= p.y < self.region.height

    def project(self, position):
        return view3d_utils.location_3d_to_region_2d(self.region, self.rv3d, position)

    def rebase(self, event):
        self._mouse_base = self.mouse(event)
        self._length_base = self.route.length
        if self.route.choosing_initial:
            inv_view = self.rv3d.view_rotation.inverted()
            self._initial_directions = initial_directions(lambda axis: (inv_view @ axis).xy)
            origin = self.route.points[0]
            a = view3d_utils.region_2d_to_location_3d(self.region, self.rv3d, self._mouse_base, origin)
            b = view3d_utils.region_2d_to_location_3d(self.region, self.rv3d, self._mouse_base + Vector((0, 1)), origin)
            pixel_size = (b - a).length
            self._initial_scales = {key: pixel_size / max((inv_view @ axis).xy.length, .2)
                                    for key, axis in WORLD_AXES.items()}
            self._initial_choice = next((key for key, axis in WORLD_AXES.items()
                                         if axis.dot(self.route.heading) > .999 and self.route.length > 0), None)
            self._initial_base = (self._initial_directions[self._initial_choice] *
                                  (self.route.length / self._initial_scales[self._initial_choice])
                                  if self._initial_choice else Vector((0, 0)))
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
        # Convert screen displacement at the live tip's depth, without perspective
        # drift from recomputing the reference plane on every mouse event.
        depth = self.route.points[-1] + self.route.heading * self._length_base
        a = view3d_utils.region_2d_to_location_3d(self.region, self.rv3d, self._mouse_base, depth)
        b = view3d_utils.region_2d_to_location_3d(self.region, self.rv3d, self._mouse_base + Vector((0, 1)), depth)
        pixel_size = (b - a).length
        screen_direction = self.rv3d.view_rotation.inverted() @ self.route.heading
        projected = Vector((screen_direction.x, screen_direction.y))
        if projected.length > .15:
            distance = delta.dot(projected.normalized()) * pixel_size / projected.length
        else:
            distance = delta.y * pixel_size
        self.route.extend(self._length_base + distance)

    def begin_turn(self, context, event):
        if not self.route.begin_turn():
            self.notice(context, 'too_short', length=self.route.turn_minimum)
            return
        self._turn_mouse = self.mouse(event)
        inv_view = self.rv3d.view_rotation.inverted()
        self._directions = turn_directions(self.route.u, self.route.v,
                                           lambda value: (inv_view @ value).xy)

    def notice(self, context, key, **values):
        import time
        self._notice = i18n.tr(key, context, **values)
        self._notice_until = time.monotonic() + 2.5
        self.status(context)

    def status(self, context):
        import time
        if self._notice and time.monotonic() < self._notice_until:
            message = self._notice
        else:
            key = ('turning' if self.route.turning else 'initial' if self.route.choosing_initial else 'drawing') if self.route else (
                'quick_wait' if self._start_mode == 'QUICK' else
                'surface_wait' if self._start_mode == 'SURFACE' else 'waiting')
            message = i18n.tr(key, context, turn_key=self._turn_key) if key in ('turning', 'initial', 'drawing') else i18n.tr(key, context)
        self.area.header_text_set(message)
        context.workspace.status_text_set(message)

    def refresh(self):
        if self.route:
            geometry.update(self.obj, self.route.route_points(), self._diameter, self._radius,
                            self._sides, self._steps)
        self.area.tag_redraw()

    def modal(self, context, event):
        if self._aborted:
            return {'CANCELLED'}
        try:
            if not any(area == self.area for area in context.screen.areas) or self.area.spaces.active.type != 'VIEW_3D':
                self.cleanup(context, cancel=True)
                return {'CANCELLED'}
            if event.type in {'ESC', 'RIGHTMOUSE', 'WINDOW_DEACTIVATE'}:
                self.cleanup(context, cancel=True)
                return {'CANCELLED'}
            if event.type == 'TIMER':
                self.status(context)
                return {'RUNNING_MODAL'}
            if event.type == 'MIDDLEMOUSE':
                self._navigation = event.value == 'PRESS'
                self._needs_rebase = True
                return {'PASS_THROUGH'}
            if event.type in {'WHEELUPMOUSE', 'WHEELDOWNMOUSE', 'TRACKPADPAN', 'TRACKPADZOOM', 'NDOF_MOTION'}:
                self._needs_rebase = True
                return {'PASS_THROUGH'}
            if self._navigation:
                return {'PASS_THROUGH'}
            if self._start_mode == 'QUICK' and self.route is None and event.type == 'P' and event.value == 'RELEASE':
                self.start(context, Vector((0, 0, 0)), direction(context.scene.line_pipe_settings))
                self.rebase(event)
                self.refresh()
            elif self.route and event.type == self._turn_key and event.value == 'RELEASE':
                self.route.release_turn()
                self.rebase(event)
                self.refresh()
            elif event.type in {'RET', 'NUMPAD_ENTER'} and event.value == 'PRESS':
                if not self.route or self.route.length <= 1e-7:
                    self.notice(context, 'empty')
                    return {'RUNNING_MODAL'}
                self.route.release_turn()
                for key, value in zip(data.DIMENSIONS, (self._diameter, self._radius, self._sides, self._steps)):
                    setattr(self.obj.line_pipe, key, value)
                geometry.update(self.obj, self.route.route_points(False), self._diameter, self._radius,
                                self._sides, self._steps, store=True)
                self.obj['_line_pipe_dimensions'] = [self._diameter, self._radius, self._sides, self._steps]
                self.obj.hide_render = False
                self.cleanup(context, cancel=False)
                self.report({'INFO'}, i18n.tr('done', context))
                return {'FINISHED'}
            elif event.type == 'BACK_SPACE' and event.value == 'PRESS' or (
                    event.type == 'Z' and event.ctrl and event.value == 'PRESS'):
                if self.route:
                    self.route.undo()
                    self.rebase(event)
                    self.refresh()
            elif not self.inside(event):
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
            elif event.type == self._turn_key and event.value == 'PRESS' and not event.is_repeat:
                self.begin_turn(context, event)
            elif event.type == 'MOUSEMOVE':
                if self._needs_rebase:
                    self.rebase(event)
                elif self.route.turning:
                    sector = choose_sector(self.mouse(event) - self._turn_mouse)
                    self.route.candidate = None
                    if sector:
                        self.route.choose(self._directions[sector])
                else:
                    self.extension(event)
                self.refresh()
            self.status(context)
            return {'RUNNING_MODAL'}
        except Exception as error:
            self.cleanup(context, cancel=True)
            self.report({'ERROR'}, self.message(context, error))
            return {'CANCELLED'}

    def draw_world(self):
        if bpy.context.area != self.area or not self.route:
            return
        try:
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
                          (1, .7, .13, 1) if selected else (.6, .7, .75, .45), 4 if selected else 2)
        finally:
            gpu.state.line_width_set(1)
            gpu.state.depth_test_set('NONE')
            gpu.state.blend_set('NONE')

    def draw_screen(self):
        if bpy.context.area != self.area or not self.route:
            return
        initial = self.route.choosing_initial and hasattr(self, '_initial_directions')
        if not self.route.turning and not initial:
            return
        gpu.state.blend_set('ALPHA')
        try:
            center = self._mouse_base - self._initial_base if initial else self._turn_mouse
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
                color = ({'X': (.95, .3, .3, .9), 'Y': (.35, .85, .4, .9), 'Z': (.35, .6, 1, .9)}[sector[1]]
                         if initial else (.7, .8, .85, .85))
                lines([tuple(v) for v in vertices], (1, .7, .13, 1) if selected else color, 3)
                label = sector if initial else '/'.join(('%+.1f' % value) for value in heading) if max(abs(v) for v in heading) < .99 else (
                    ('+' if heading[max(range(3), key=lambda i: abs(heading[i]))] > 0 else '-') +
                    'XYZ'[max(range(3), key=lambda i: abs(heading[i]))])
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
        session = None
        for handle in self._handles:
            bpy.types.SpaceView3D.draw_handler_remove(handle, 'WINDOW')
        if hasattr(self, '_timer'):
            context.window_manager.event_timer_remove(self._timer)
        if any(area == self.area for area in context.screen.areas):
            self.area.header_text_set(None)
            self.area.tag_redraw()
        context.workspace.status_text_set(None)
        if cancel:
            geometry.remove(self.obj)
            for obj in self._selected:
                if obj.name in context.view_layer.objects:
                    obj.select_set(True)
            if self._active and self._active.name in context.view_layer.objects:
                context.view_layer.objects.active = self._active

    def cancel(self, context):
        self.cleanup(context, cancel=True)


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
        context.object.line_pipe.enabled = False
        return {'FINISHED'}


def abort(_=None):
    if session:
        operation = session
        operation._aborted = True
        operation.cleanup(bpy.context, cancel=True)


CLASSES = (LP_OT_language, LP_OT_draw, LP_OT_mesh)
