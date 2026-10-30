# SPDX-License-Identifier: GPL-3.0-or-later
"""Local language selection without changing Blender's application language."""
import bpy

MESSAGES = {
    'title': ('PipeWorks', 'PipeWorks · 管道工坊'),
    'draw': ('Draw Pipe', '绘制管道'),
    'settings': ('Pipe', '管道'),
    'active': ('Selected Pipe', '所选管道'),
    'diameter': ('Diameter', '直径'),
    'bend_radius': ('Bend Radius', '弯曲半径'),
    'radial_segments': ('Radial Segments', '圆周分段'),
    'bend_steps': ('Bend Segments', '弯头分段'),
    'start_mode': ('Start From', '起点方式'),
    'origin': ('Position', '起点坐标'),
    'direction': ('Initial Direction', '初始方向'),
    'custom_direction': ('Direction Vector', '方向向量'),
    'surface_offset': ('Surface Offset', '表面偏移'),
    'face_index': ('Face Index', '面编号'),
    'turn_key': ('Turn Key', '转弯按键'),
    'language': ('Language', '语言'),
    'mesh': ('Convert to Mesh', '转换为网格'),
    'waiting': ('Click to place the starting point', '单击放置起点'),
    'surface_wait': ('Click a mesh face to start', '单击网格表面开始'),
    'quick_wait': ('Hold P + click: surface start | Release P: start at (0, 0, 0) | Esc: cancel',
                   '按住 P 并单击：表面起点 | 松开 P：从 (0, 0, 0) 起画 | Esc：取消'),
    'drawing': ('Move: extend | Hold {turn_key}: turn | Enter: finish | Backspace: undo bend | Esc: cancel',
                '移动：延长 | 按住 {turn_key}：转弯 | Enter：完成 | 退格：撤回弯头 | Esc：取消'),
    'initial': ('Move: choose +/-X, +/-Y, +/-Z | Hold {turn_key}: turn | Enter: finish | Esc: cancel',
                '移动：选择 X/Y/Z 正负六向 | 按住 {turn_key}：转弯 | Enter：完成 | Esc：取消'),
    'six_axes': ('Mouse: 6 Axes', '鼠标六轴定向'),
    'turning': ('Move to choose a bend | Release {turn_key}: confirm | Esc: cancel',
                '移动选择转弯方向 | 松开 {turn_key}：确定 | Esc：取消'),
    'too_short': ('Extend the straight segment to at least {length:.3f} before turning',
                  '转弯前请将直线段延长至至少 {length:.3f}'),
    'empty': ('Extend the pipe before finishing', '请先延长管道再完成'),
    'miss': ('No mesh face under the pointer', '鼠标下没有网格表面'),
    'bad_face': ('Select a mesh with a valid face index', '请选择网格并输入有效面编号'),
    'bad_direction': ('Direction vector must be nonzero', '方向向量不能为零'),
    'bad_radius': ('Bend radius must exceed half the diameter', '弯曲半径必须大于直径的一半'),
    'fit': ('The route is too short for that bend radius', '现有线段不足以容纳该弯曲半径'),
    'busy': ('A pipe is already being drawn', '已有管道正在绘制'),
    'error': ('Pipe operation failed: {error}', '管道操作失败：{error}'),
    'done': ('Pipe completed', '管道铺设完成'),
    'point': ('Point', '放置点'),
    'surface': ('Surface', '点击表面'),
    'coordinates': ('Coordinates', '输入坐标'),
    'cursor': ('3D Cursor', '三维游标'),
    'face': ('Selected Mesh Face', '所选网格的面'),
    'normal': ('Surface Normal', '表面法线'),
    'custom': ('Custom Vector', '自定义向量'),
    'draw_tip': ('Place a start point and draw a solid pipe', '放置起点并绘制实心管道'),
    'language_tip': ('Switch the complete interface to Chinese or English', '切换整个界面的中文或英文'),
    'mesh_tip': ('Create an independent solid mesh from the selected pipe', '将所选管道转换为独立实心网格'),
    'size_tip': ('Outside diameter in scene units', '以场景单位计的圆柱外径'),
    'radius_tip': ('Centerline bend radius; must exceed the pipe radius', '中心线弯曲半径，必须大于圆柱半径'),
    'sides_tip': ('Number of sides around the circular cross section', '圆形截面的圆周分段数'),
    'steps_tip': ('Number of segments in each quarter-circle bend', '每个四分之一圆弯头的分段数'),
    'start_tip': ('Choose how to place the first point', '选择第一个点的放置方式'),
    'origin_tip': ('World-space starting position', '世界空间中的起点坐标'),
    'direction_tip': ('Mouse selects six world axes; P always uses automatic six-axis selection',
                      '根据鼠标选择世界六轴方向，P 快捷起画始终使用鼠标六轴定向'),
    'vector_tip': ('World-space initial direction vector', '世界空间中的初始方向向量'),
    'offset_tip': ('Distance from the clicked face along its outward normal', '从点击的表面沿朝外法线偏移的距离'),
    'face_tip': ('Zero-based polygon index on the active mesh', '活动网格的面编号，从零开始'),
    'key_tip': ('Hold this key to preview a bend, then release to confirm', '按住此键预览弯头，松开确认'),
}


def language(context=None):
    context = context or bpy.context
    addon = context.preferences.addons.get(__package__)
    if addon:
        return addon.preferences.language
    scene = getattr(context, 'scene', None)
    return scene.line_pipe_settings.language if scene and hasattr(scene, 'line_pipe_settings') else 'EN'


def tr(key, context=None, **values):
    return MESSAGES[key][language(context) == 'ZH'].format(**values)


def text(key, lang):
    return MESSAGES[key][lang == 'ZH']


def prop(layout, data, key, context):
    suffix = '_zh' if language(context) == 'ZH' else ''
    layout.prop(data, key + suffix, text=tr(key, context))


def add_chinese_properties(cls, tips):
    """RNA aliases share values but have their own localized hover descriptions."""
    def accessors(key, ids=None):
        def get_value(self):
            value = getattr(self, key)
            return ids.index(value) if ids is not None else value

        def set_value(self, value):
            setattr(self, key, ids[value] if ids is not None else value)
        return get_value, set_value

    for key, tip in tips.items():
        definition = cls.__annotations__[key]
        kwargs = dict(definition.keywords)
        kwargs.pop('update', None)
        kwargs['name'] = text(key, 'ZH')
        kwargs['description'] = text(tip, 'ZH')
        if definition.function == bpy.props.EnumProperty:
            items = kwargs['items']
            kwargs['items'] = [(item[0], text(item[3], 'ZH') if len(item) > 3 else item[1],
                                text(item[3], 'ZH') if len(item) > 3 else item[2]) for item in items]
            definition.keywords['items'] = [item[:3] for item in items]
            kwargs.pop('default', None)
            kwargs['get'], kwargs['set'] = accessors(key, [i[0] for i in items])
        else:
            kwargs.pop('default', None)
            kwargs['get'], kwargs['set'] = accessors(key)
        cls.__annotations__[key + '_zh'] = definition.function(**kwargs)
