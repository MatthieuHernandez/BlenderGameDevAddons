import bpy
import os
from bpy.types import Operator
from unittest.mock import patch


DEFAULT_OUTPUT_FOLDER = "Export"


class EXPORT_OT_low_high_fbx(Operator):
    bl_idname = "export_mesh.low_high_fbx"
    bl_label = "Export Low/High FBX"
    bl_description = "Export all selected objects together as low and high FBX files"
    bl_options = {'REGISTER'}

    @classmethod
    def poll(cls, context):
        return context.mode == 'OBJECT' and bool(context.selected_objects)

    def execute(self, context):
        if not bpy.data.filepath:
            self.report({'ERROR'}, "Save your .blend file before exporting")
            return {'CANCELLED'}

        output_folder = context.scene.low_high_fbx_output_folder or DEFAULT_OUTPUT_FOLDER
        export_dir = os.path.join(os.path.dirname(bpy.data.filepath), bpy.path.abspath(output_folder))
        selection = context.selected_objects
        active = context.view_layer.objects.active
        fallback_name = (active if active in selection else selection[0]).name
        name = bpy.path.clean_name(context.scene.low_high_fbx_filename.strip() or fallback_name)

        try:
            os.makedirs(export_dir, exist_ok=True)
            self.export_selection(context, selection, export_dir, name)
        except Exception as exc:
            self.report({'ERROR'}, str(exc))
            return {'CANCELLED'}

        self.report({'INFO'}, f"Exported {name}_low.fbx and {name}_high.fbx to {export_dir}")
        return {'FINISHED'}

    def export_selection(self, context, selection, export_dir, name):
        from io_scene_fbx import export_fbx_bin

        modifiers = [mod for obj in selection for mod in obj.modifiers if mod.type == 'MULTIRES']
        states = [(m, m.show_viewport, m.show_render) for m in modifiers]
        write_object = export_fbx_bin.fbx_data_object_elements

        def write_suffixed_object(root, obj, scene_data):
            # This is the exporter wrapper's name, independent of the Blender object.
            original_name = obj.name
            obj.name = f"{original_name}_{suffix}"
            try:
                return write_object(root, obj, scene_data)
            finally:
                obj.name = original_name

        try:
            for suffix, enabled in (("low", False), ("high", True)):
                for mod in modifiers:
                    mod.show_viewport = enabled
                    mod.show_render = enabled

                context.view_layer.update()
                filepath = os.path.join(export_dir, f"{name}_{suffix}.fbx")
                with patch.object(export_fbx_bin, "fbx_data_object_elements", write_suffixed_object):
                    result = bpy.ops.export_scene.fbx(
                        filepath=filepath,
                        use_selection=True,
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


def register():
    bpy.types.Scene.low_high_fbx_output_folder = bpy.props.StringProperty(
        name="Output Folder",
        description="Folder for both FBX files. Relative paths start from the blend file's folder",
        subtype='DIR_PATH',
        default=DEFAULT_OUTPUT_FOLDER,
    )
    bpy.types.Scene.low_high_fbx_filename = bpy.props.StringProperty(
        name="File Name",
        description="Base name for both FBX files, without the suffix or extension. Leave blank to use the selected object's name",
    )
    bpy.utils.register_class(EXPORT_OT_low_high_fbx)


def unregister():
    bpy.utils.unregister_class(EXPORT_OT_low_high_fbx)
    del bpy.types.Scene.low_high_fbx_filename
    del bpy.types.Scene.low_high_fbx_output_folder
