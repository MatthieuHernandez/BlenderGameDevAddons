import importlib
import json
import os
from pathlib import Path
import re
import tempfile
import uuid

import addon_utils
import bpy


THREN_ROOT = "/Game/THREN"
SHARED_FOLDER = f"{THREN_ROOT}/Shared/Meshes"
WITCH_LAIR_PROPS = f"{THREN_ROOT}/World/WitchLair/Environment/Props"
FOREST_FOLDER = f"{THREN_ROOT}/World/Forest"
DESTINATIONS = {
    'SHARED': ("Shared", SHARED_FOLDER, "thren_shared_folder"),
    'WITCH_LAIR': ("WitchLair", WITCH_LAIR_PROPS, "thren_prop_folder"),
    'FOREST': ("Forest", FOREST_FOLDER, "thren_forest_folder"),
}
ASSET_ID = "thren_asset_id"


def destination_folder(scene):
    _, default_base, folder_property = DESTINATIONS[scene.thren_destination]
    base = scene.thren_selected_directory or default_base
    folder = getattr(scene, folder_property).strip()
    if folder and not re.fullmatch(r"[A-Za-z0-9_]+", folder):
        raise ValueError("Use letters, digits and underscores in Folder Name")

    if folder:
        return f"{base}/{folder}/Meshes"
    return base if base.rsplit("/", 1)[-1].casefold() == "meshes" else f"{base}/Meshes"


def content_path(package_path):
    return "/Content/" + package_path.removeprefix("/Game/")


def selected_meshes(context):
    return sorted(
        (obj for obj in context.selected_objects if obj.type == 'MESH'),
        key=lambda obj: (obj.name.casefold(), obj.name),
    )


def static_mesh_name(obj):
    name = re.sub(r"[^A-Za-z0-9_]+", "_", obj.name.strip())
    if name[:3].upper() == "SM_":
        name = name[3:]
    if not name.strip("_"):
        raise ValueError(f"Cannot build a Static Mesh name from {obj.name!r}")
    return f"SM_{name}"


def send2ue_functions(context):
    modules = {addon.module for addon in context.preferences.addons}
    modules.add("send2ue")
    for module in sorted(modules):
        if module.rsplit(".", 1)[-1] == "send2ue" and addon_utils.check(module)[1]:
            exporter = importlib.import_module(f"{module}.core.export")
            transport = importlib.import_module(f"{module}.dependencies.unreal")
            return exporter.export_fbx_file, transport.run_commands
    raise RuntimeError("Install and enable Send to Unreal in Blender")


def unreal_content_directory(send):
    marker = "THREN_CONTENT_DIRECTORY:"
    response = send([
        "import json, unreal",
        "from pathlib import Path",
        "content = Path(unreal.Paths.project_content_dir()).resolve()",
        f"print({marker!r} + json.dumps(str(content)))",
    ])
    for line in (response or "").splitlines():
        if line.startswith(marker):
            return Path(json.loads(line[len(marker):]))
    raise RuntimeError(response or "Unreal did not return its project Content directory")


class THREN_OT_select_unreal_directory(bpy.types.Operator):
    bl_idname = "thren.select_unreal_directory"
    bl_label = "Select Directory"
    bl_description = "Choose an existing directory in the open Unreal project"

    directory: bpy.props.StringProperty(subtype='DIR_PATH', options={'SKIP_SAVE'})
    filter_folder: bpy.props.BoolProperty(default=True, options={'HIDDEN', 'SKIP_SAVE'})
    root: bpy.props.StringProperty(options={'HIDDEN', 'SKIP_SAVE'})
    destination: bpy.props.StringProperty(options={'HIDDEN', 'SKIP_SAVE'})

    def invoke(self, context, event):
        self.destination = context.scene.thren_destination
        try:
            _, send = send2ue_functions(context)
            _, package_root, _ = DESTINATIONS[self.destination]
            root = (unreal_content_directory(send) / THREN_ROOT.removeprefix("/Game/")).resolve()
            if not root.is_dir():
                raise ValueError(f"Directory unavailable on this computer: {root}")
        except Exception as error:
            self.report({'ERROR'}, str(error))
            return {'CANCELLED'}

        self.root = str(root)
        start = root / package_root.removeprefix(f"{THREN_ROOT}/")
        self.directory = str(start if start.is_dir() else root) + os.sep
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

    def execute(self, context):
        scene = context.scene
        try:
            if not self.root or scene.thren_destination != self.destination:
                raise ValueError("Open Select Directory again for the current destination")
            chosen = Path(bpy.path.abspath(self.directory)).resolve()
            root = Path(self.root)
            if not chosen.is_dir() or not chosen.is_relative_to(root):
                raise ValueError(f"Choose an existing directory under {root}")
            scene.thren_selected_directory = "/".join((THREN_ROOT, *chosen.relative_to(root).parts))
        except (ValueError, OSError) as error:
            self.report({'ERROR'}, str(error))
            return {'CANCELLED'}
        return {'FINISHED'}


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


def export_game_mesh(context, obj, filepath, export_fbx):
    selection = context.selected_objects
    modifiers = [(mod, mod.show_viewport) for mod in obj.modifiers if mod.type == 'MULTIRES']
    mesh = None
    export_obj = None
    export_materials = []
    renamed_materials = []
    active = context.view_layer.objects.active
    try:
        for mod, _ in modifiers:
            mod.show_viewport = False
        context.view_layer.update()
        graph = context.evaluated_depsgraph_get()
        evaluated = obj.evaluated_get(graph)
        transform = evaluated.matrix_world.copy()
        transform.translation.zero()
        mesh = bpy.data.meshes.new_from_object(evaluated, preserve_all_data_layers=True, depsgraph=graph)
        for index, slot in enumerate(evaluated.material_slots):
            mesh.materials[index] = slot.material
        export_obj = bpy.data.objects.new(filepath.stem, mesh)
        for selected in selection:
            selected.select_set(False)
        context.scene.collection.objects.link(export_obj)
        export_obj.matrix_world = transform
        export_obj.select_set(True)
        context.view_layer.objects.active = export_obj
        context.view_layer.update()
        # Export only slots represented by polygons in the evaluated geometry.
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
        if export_obj is not None:
            bpy.data.objects.remove(export_obj, do_unlink=True)
        for selected in selection:
            selected.select_set(True)
        context.view_layer.objects.active = active
        if mesh is not None:
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
        return context.mode == 'OBJECT' and any(obj.type == 'MESH' for obj in context.selected_objects)

    def execute(self, context):
        try:
            if not bpy.data.filepath:
                raise ValueError("Save your .blend file before pushing")
            meshes = selected_meshes(context)
            folder = destination_folder(context.scene)
            jobs = [(obj, static_mesh_name(obj)) for obj in meshes]
            if len({name.casefold() for _, name in jobs}) != len(jobs):
                raise ValueError("Selected objects must produce distinct Static Mesh names")
            export_fbx, send = send2ue_functions(context)
            with tempfile.TemporaryDirectory(prefix="thren_push_") as directory:
                manifests = []
                for obj, name in jobs:
                    fbx = Path(directory) / f"{name}.fbx"
                    manifest = fbx.with_suffix(".json")
                    slots = export_game_mesh(context, obj, fbx, export_fbx)
                    manifest.write_text(json.dumps({
                        "asset_id": mesh_id(obj), "name": name, "destination": folder, "slots": slots,
                    }, indent=2), encoding="utf-8")
                    manifests.append(str(manifest))
                response = send([
                    "import runpy, unreal",
                    "from pathlib import Path",
                    "importer = (Path(unreal.Paths.project_content_dir()) / 'Python' / 'thren_mesh_import.py').resolve()",
                    "if not importer.is_file():",
                    "    raise FileNotFoundError(f'Install the THREN importer in the open Unreal project: {importer}')",
                    "push = runpy.run_path(str(importer))['push']",
                    f"for manifest in {manifests!r}:",
                    "    print(push(manifest))",
                    "print('THREN_PUSH_OK')",
                ])
                if "THREN_PUSH_OK" not in (response or "").splitlines():
                    raise RuntimeError(response or "Unreal did not confirm the import")
        except Exception as error:
            self.report({'ERROR'}, str(error))
            return {'CANCELLED'}
        self.report({'INFO'}, f"Pushed {len(jobs)} Static Mesh asset(s) to {content_path(folder)}")
        return {'FINISHED'}


def clear_selected_directory(scene, _context):
    scene.thren_selected_directory = ""


def register():
    bpy.types.Scene.thren_selected_directory = bpy.props.StringProperty(options={'HIDDEN'})
    bpy.types.Scene.thren_destination = bpy.props.EnumProperty(
        name="Destination",
        items=[(key, label, "") for key, (label, _, _) in DESTINATIONS.items()],
        update=clear_selected_directory,
    )
    for _, _, folder_property in DESTINATIONS.values():
        setattr(bpy.types.Scene, folder_property, bpy.props.StringProperty(
            name="Folder Name",
            description="Add Folder Name/Meshes under the base directory",
        ))
    bpy.utils.register_class(THREN_OT_select_unreal_directory)
    bpy.utils.register_class(EXPORT_OT_thren_push_to_unreal)


def unregister():
    bpy.utils.unregister_class(EXPORT_OT_thren_push_to_unreal)
    bpy.utils.unregister_class(THREN_OT_select_unreal_directory)
    for _, _, folder_property in DESTINATIONS.values():
        delattr(bpy.types.Scene, folder_property)
    del bpy.types.Scene.thren_destination
    del bpy.types.Scene.thren_selected_directory
