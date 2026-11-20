bl_info = {
    "name": "Low/High FBX Exporter",
    "author": "Community",
    "version": (1, 0, 0),
    "blender": (4, 2, 0),
    "location": "View3D > Sidebar > FBX Export",
    "description": "Export a low FBX and a high FBX when Multiresolution is present",
    "category": "Import-Export",
}

import bpy
import os
from bpy.types import Operator, Panel


class EXPORT_OT_low_high_fbx(Operator):
    bl_idname = "export_mesh.low_high_fbx"
    bl_label = "Export Low + High FBX"
    bl_description = "Export a low FBX for each selected mesh and a high FBX for meshes with Multiresolution"
    bl_options = {'REGISTER'}

    @classmethod
    def poll(cls, context):
        return context.mode == 'OBJECT' and any(obj.type == 'MESH' for obj in context.selected_objects)

    def execute(self, context):
        if not bpy.data.filepath:
            self.report({'ERROR'}, "Save your .blend file before exporting")
            return {'CANCELLED'}

        export_dir = os.path.join(os.path.dirname(bpy.data.filepath), "Export")
        previous_selection = list(context.selected_objects)
        previous_active = context.view_layer.objects.active
        meshes = [obj for obj in previous_selection if obj.type == 'MESH']
        file_count = 0

        try:
            os.makedirs(export_dir, exist_ok=True)
            bpy.ops.object.select_all(action='DESELECT')
            for obj in meshes:
                obj.select_set(True)
                context.view_layer.objects.active = obj
                file_count += self.export_mesh(context, obj, export_dir)
                obj.select_set(False)
        except Exception as exc:
            self.report({'ERROR'}, str(exc))
            return {'CANCELLED'}
        finally:
            bpy.ops.object.select_all(action='DESELECT')
            for selected in previous_selection:
                selected.select_set(True)
            context.view_layer.objects.active = previous_active
            context.view_layer.update()

        self.report({'INFO'}, f"Exported {file_count} FBX file(s) to {export_dir}")
        return {'FINISHED'}

    def export_mesh(self, context, obj, export_dir):
        modifiers = [m for m in obj.modifiers if m.type == 'MULTIRES']
        variants = [("low", False)]
        if modifiers:
            variants.append(("high", True))

        states = [(m, m.show_viewport, m.show_render) for m in modifiers]

        try:
            for suffix, enabled in variants:
                for mod in modifiers:
                    mod.show_viewport = enabled
                    mod.show_render = enabled

                context.view_layer.update()
                filepath = os.path.join(export_dir, f"{bpy.path.clean_name(obj.name)}_{suffix}.fbx")
                result = bpy.ops.export_scene.fbx(
                    filepath=filepath,
                    use_selection=True,
                    object_types={'MESH'},
                    use_mesh_modifiers=True,
                    use_mesh_modifiers_render=False,
                    bake_anim=False,
                )
                if 'FINISHED' not in result:
                    raise RuntimeError(f"FBX export failed: {filepath}")
        finally:
            for mod, viewport, render in states:
                mod.show_viewport = viewport
                mod.show_render = render
            context.view_layer.update()

        return len(variants)


class VIEW3D_PT_low_high_fbx(Panel):
    bl_label = "Low/High FBX Exporter"
    bl_idname = "VIEW3D_PT_low_high_fbx"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "FBX Export"

    def draw(self, context):
        layout = self.layout
        layout.operator("export_mesh.low_high_fbx", icon='EXPORT')
        layout.label(text="Output: //Export/")


classes = (EXPORT_OT_low_high_fbx, VIEW3D_PT_low_high_fbx)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)


if __name__ == "__main__":
    register()
