from textwrap import wrap

import bpy

from . import bl_info, low_high_fbx, push_to_unreal


class VIEW3D_PT_thren_tools(bpy.types.Panel):
    bl_label = f"{bl_info['name']} v{'.'.join(map(str, bl_info['version']))}"
    bl_idname = "VIEW3D_PT_thren_tools"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "THREN"

    def draw(self, context):
        scene = context.scene
        disk = self.layout.box()
        disk.label(text=low_high_fbx.EXPORT_OT_low_high_fbx.bl_label)
        disk.prop(scene, "low_high_fbx_filename")
        disk.prop(scene, "low_high_fbx_output_folder")
        disk.operator("export_mesh.low_high_fbx", text="Export FBX", icon='EXPORT')

        push = self.layout.box()
        push.label(text=push_to_unreal.EXPORT_OT_thren_push_to_unreal.bl_label)
        push.prop(scene, "thren_push_filename")
        push.prop(scene, "thren_destination")
        if scene.thren_destination == 'WITCH_LAIR':
            push.prop(scene, "thren_prop_folder")
        try:
            folder = push_to_unreal.destination_folder(scene, push_to_unreal.push_name(context))
        except ValueError as error:
            push.label(text=str(error), icon='ERROR')
        else:
            width = max(1, int((context.region.width / context.preferences.system.ui_scale - 44) / 8))
            path = push.column(align=True)
            for line in wrap(f"{folder}/", width=width):
                path.label(text=line)
        push.operator("export_mesh.thren_push_to_unreal", text="Push to Unreal", icon='EXPORT')


def register():
    bpy.utils.register_class(VIEW3D_PT_thren_tools)


def unregister():
    bpy.utils.unregister_class(VIEW3D_PT_thren_tools)
