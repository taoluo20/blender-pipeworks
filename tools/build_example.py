"""Build a separate acceptance scene without modifying any user blend files."""
import json
import math
import pathlib
import sys
import bpy
from mathutils import Euler

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import line_pipe
from line_pipe import geometry
line_pipe.register()
for obj in tuple(bpy.context.scene.objects):
    bpy.data.objects.remove(obj, do_unlink=True)
scene = bpy.context.scene
scene.name = 'PipeWorks'
scene.unit_settings.system = 'METRIC'
scene.cursor.location = (-2, -1, .4)


def pipe(name, points, diameter, radius, color):
    obj = geometry.create(bpy.context)
    obj.name = name
    obj.line_pipe.diameter, obj.line_pipe.bend_radius = diameter, radius
    geometry.update(obj, points, diameter, radius, 32, 20, store=True)
    obj.line_pipe.bend_steps = 20
    obj['_line_pipe_dimensions'] = [diameter, radius, 32, 20]
    obj.color = (*color, 1)
    material = bpy.data.materials.new(name + ' Material')
    material.diffuse_color = (*color, 1)
    material.use_nodes = True
    bsdf = material.node_tree.nodes.get('Principled BSDF')
    bsdf.inputs['Base Color'].default_value = (*color, 1)
    bsdf.inputs['Metallic'].default_value = .35
    bsdf.inputs['Roughness'].default_value = .28
    obj.data.materials.append(material)
    return obj


main = pipe('Spatial Solid Pipe', [(-2, 1, .5), (0, 1, .5), (0, 1, 2.5), (2.8, 1, 2.5),
                                  (2.8, -1, 2.5), (2.8, -1, 1)], .24, .5, (.07, .55, .43))
pipe('Planar Solid Pipe', [(-2, 2.1, .55), (-2, 2.1, 2.5), (-.8, 2.1, 2.5), (-.8, 2.1, 3.7),
                         (2.8, 2.1, 3.7)], .16, .35, (.7, .34, .13))
bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 3.0, 1.5))
wall = bpy.context.object
wall.name = 'Wall - Surface Start'
wall.scale = (7, .2, 4.6)
wall.color = (.29, .32, .35, 1)
bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
wall.select_set(False)
main.select_set(True)
bpy.context.view_layer.objects.active = main
settings = scene.line_pipe_settings
settings.diameter, settings.bend_radius = .24, .5
settings.direction, settings.start_mode = 'AUTO', 'POINT'
for screen in bpy.data.screens:
    for area in screen.areas:
        if area.type == 'VIEW_3D':
            space = area.spaces.active
            space.show_region_ui = True
            space.shading.type = 'SOLID'
            space.shading.color_type = 'OBJECT'
            space.shading.light = 'STUDIO'
            space.overlay.show_floor = True
            space.region_3d.view_location = (.4, .2, 1.8)
            space.region_3d.view_rotation = Euler((math.radians(82), 0, math.radians(12)), 'XYZ').to_quaternion()
            space.region_3d.view_distance = 10
            space.region_3d.view_perspective = 'PERSP'
out = ROOT / 'examples'
out.mkdir(exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=str(out / 'pipeworks-example.blend'))
print('LINE_PIPE_EXAMPLE_READY', flush=True)
