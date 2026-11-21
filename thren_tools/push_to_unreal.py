import importlib
import json
import os
from pathlib import Path
import re
import tempfile
import uuid

import addon_utils
import bpy


SHARED_FOLDER = "/Game/THREN/Shared/Meshes"
WITCH_LAIR_PROPS = "/Game/THREN/World/WitchLair/Environment/Props"
ASSET_ID = "thren_asset_id"


def destination_folder(scene, mesh_name=""):
    if scene.thren_destination == 'SHARED':
        return SHARED_FOLDER
    prop = scene.thren_prop_folder.strip() or mesh_name.removeprefix("SM_")
    if prop and not re.fullmatch(r"[A-Za-z0-9_]+", prop):
        raise ValueError("Use letters, digits and underscores in the prop folder")
    return f"{WITCH_LAIR_PROPS}/{prop or '<Prop_name>'}/Meshes"


def push_name(context):
    anchor = reference_mesh(context)
    return context.scene.thren_push_filename.strip() or (anchor.name if anchor is not None else "")


def target(context):
    if reference_mesh(context) is None:
        raise ValueError("Select at least one mesh")
    name = push_name(context)
    if not re.fullmatch(r"[A-Za-z0-9_]+", name):
        raise ValueError("Use letters, digits and underscores in the FBX name")
    folder = destination_folder(context.scene, name)
    if "<Prop_name>" in folder:
        raise ValueError("Enter a prop folder name")
    return folder, name


def reference_mesh(context):
    return min(
        (obj for obj in context.selected_objects if obj.type == 'MESH'),
        key=lambda obj: (obj.name.casefold(), obj.name),
        default=None,
    )


def send2ue_functions(context):
    modules = {addon.module for addon in context.preferences.addons}
    modules.add("send2ue")
    for module in sorted(modules):
        if module.rsplit(".", 1)[-1] == "send2ue" and addon_utils.check(module)[1]:
            exporter = importlib.import_module(f"{module}.core.export")
            transport = importlib.import_module(f"{module}.dependencies.unreal")
            return exporter.export_fbx_file, transport.run_commands
    raise RuntimeError("Install and enable Send to Unreal in Blender")


def mesh_id(obj):
    asset_id = obj.get(ASSET_ID)
    if asset_id:
        if any(other != obj and other.get(ASSET_ID) == asset_id for other in bpy.data.objects):
            raise ValueError("Duplicate THREN asset ID. Remove it from the copied object")
        return str(uuid.UUID(asset_id))
    source = os.path.normcase(os.path.normpath(bpy.data.filepath))
    asset_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"thren:{source}#{obj.name}"))
    obj[ASSET_ID] = asset_id
    return asset_id


def export_game_mesh(context, anchor, filepath, export_fbx):
    selection = context.selected_objects
    objects = [obj for obj in selection if obj.type == 'MESH']
    modifiers = [(mod, mod.show_viewport) for obj in objects for mod in obj.modifiers if mod.type == 'MULTIRES']
    meshes = []
    temporary_names = []
    export_materials = []
    renamed_materials = []
    active = context.view_layer.objects.active
    try:
        for mod, _ in modifiers:
            mod.show_viewport = False
        context.view_layer.update()
        graph = context.evaluated_depsgraph_get()
        origin = anchor.evaluated_get(graph).matrix_world.translation.copy()
        export_objects = []
        for obj in objects:
            evaluated = obj.evaluated_get(graph)
            transform = evaluated.matrix_world.copy()
            transform.translation -= origin
            mesh = bpy.data.meshes.new_from_object(evaluated, preserve_all_data_layers=True, depsgraph=graph)
            meshes.append(mesh)
            for index, slot in enumerate(evaluated.material_slots):
                mesh.materials[index] = slot.material
            copy = bpy.data.objects.new(obj.name, mesh)
            temporary_names.append(copy.name)
            export_objects.append((copy, transform))
            if obj == anchor:
                export_obj = copy

        for obj in selection:
            obj.select_set(False)
        for copy, transform in export_objects:
            context.scene.collection.objects.link(copy)
            copy.matrix_world = transform
            copy.select_set(True)
        context.view_layer.objects.active = export_obj
        context.view_layer.update()
        if len(export_objects) > 1 and 'FINISHED' not in bpy.ops.object.join():
            raise RuntimeError("Could not combine the selected meshes")

        # Export only slots represented by polygons in the evaluated geometry.
        mesh = export_obj.data
        used = sorted({polygon.material_index for polygon in mesh.polygons})
        slots = []
        for index in used:
            material = mesh.materials[index] if index < len(mesh.materials) else None
            if material:
                name = re.sub(r"[^A-Za-z0-9_]+", "_", material.name.strip())
                if not name:
                    raise ValueError("Exported material slot names cannot be empty")
                slots.append((index, material, name))
        names = [name for _, _, name in slots]
        if len({name.casefold() for name in names}) != len(names):
            raise ValueError("Exported material slot names must be unique")
        if not mesh.polygons:
            raise ValueError("The game mesh has no faces")

        for index, material, name in slots:
            if material.name == name:
                continue
            # Free the exact FBX name if an unused local material already owns it.
            existing = bpy.data.materials.get((name, None))
            if existing is not None:
                renamed_materials.append((existing, name))
                existing.name = f"THREN_{uuid.uuid4().hex}"
            export_material = material.copy()
            export_materials.append(export_material)
            export_material.name = name
            if export_material.name != name:
                raise ValueError(f"Could not assign exported material slot name: {name}")
            mesh.materials[index] = export_material

        export_fbx(str(filepath), {
            "use_mesh_modifiers": False,
            "bake_anim": False,
            "mesh_smooth_type": 'FACE',
            "axis_forward": 'Y',
            "axis_up": 'Z',
            "apply_unit_scale": True,
            "apply_scale_options": 'FBX_SCALE_NONE',
        })
        if not filepath.is_file() or not filepath.stat().st_size:
            raise RuntimeError("FBX export failed")
        return names
    finally:
        for name in temporary_names:
            copy = bpy.data.objects.get(name)
            if copy is not None:
                bpy.data.objects.remove(copy, do_unlink=True)
        for obj in selection:
            obj.select_set(True)
        context.view_layer.objects.active = active
        for mesh in meshes:
            bpy.data.meshes.remove(mesh)
        for material in export_materials:
            bpy.data.materials.remove(material)
        for material, name in renamed_materials:
            material.name = name
        for mod, viewport in modifiers:
            mod.show_viewport = viewport
        context.view_layer.update()


class EXPORT_OT_thren_push_to_unreal(bpy.types.Operator):
    bl_idname = "export_mesh.thren_push_to_unreal"
    bl_label = "Push Mesh to Unreal"

    @classmethod
    def poll(cls, context):
        return context.mode == 'OBJECT' and reference_mesh(context) is not None

    def execute(self, context):
        try:
            if not bpy.data.filepath:
                raise ValueError("Save your .blend file before pushing")
            folder, name = target(context)
            export_fbx, send = send2ue_functions(context)
            anchor = reference_mesh(context)
            asset_id = mesh_id(anchor)
            with tempfile.TemporaryDirectory(prefix="thren_push_") as directory:
                fbx = Path(directory) / f"{name}.fbx"
                manifest = fbx.with_suffix(".json")
                slots = export_game_mesh(context, anchor, fbx, export_fbx)
                manifest.write_text(json.dumps({
                    "asset_id": asset_id, "name": name, "destination": folder, "slots": slots,
                }, indent=2), encoding="utf-8")
                response = send([
                    "import runpy, unreal",
                    "from pathlib import Path",
                    "importer = (Path(unreal.Paths.project_content_dir()) / 'Python' / 'thren_mesh_import.py').resolve()",
                    "if not importer.is_file():",
                    "    raise FileNotFoundError(f'Install the THREN importer in the open Unreal project: {importer}')",
                    f"runpy.run_path(str(importer))['push']({str(manifest)!r})",
                    "print('THREN_PUSH_OK')",
                ])
                if "THREN_PUSH_OK" not in (response or "").splitlines():
                    raise RuntimeError(response or "Unreal did not confirm the import")
        except Exception as error:
            self.report({'ERROR'}, str(error))
            return {'CANCELLED'}
        self.report({'INFO'}, f"Pushed {folder}/{name}")
        return {'FINISHED'}


def register():
    bpy.types.Scene.thren_destination = bpy.props.EnumProperty(
        name="Destination",
        items=[('SHARED', "Shared", ""), ('WITCH_LAIR', "WitchLair", "")],
    )
    bpy.types.Scene.thren_prop_folder = bpy.props.StringProperty(
        name="Prop Folder", description="Leave blank to use the FBX name without SM_",
    )
    bpy.types.Scene.thren_push_filename = bpy.props.StringProperty(
        name="File Name",
        description="Name of the FBX and Static Mesh. Leave blank to use the first selected mesh name alphabetically",
    )
    bpy.utils.register_class(EXPORT_OT_thren_push_to_unreal)


def unregister():
    bpy.utils.unregister_class(EXPORT_OT_thren_push_to_unreal)
    del bpy.types.Scene.thren_push_filename
    del bpy.types.Scene.thren_prop_folder
    del bpy.types.Scene.thren_destination
