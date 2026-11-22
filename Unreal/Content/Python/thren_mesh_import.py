"""Import a THREN Static Mesh handoff in the Unreal Editor."""

import json
from pathlib import Path
import re
import uuid

import unreal


ASSET_TAG = "THRENAssetId"
ROOT = "/Game/THREN"
DESTINATION = re.compile(rf"{ROOT}(?:/[^/\\:\x00-\x1f]+)*")


def _find_existing(asset_id, requested_path):
    assets = unreal.EditorAssetLibrary
    if assets.does_asset_exist(requested_path):
        occupant = assets.load_asset(requested_path)
        if isinstance(occupant, unreal.StaticMesh) and str(assets.get_metadata_tag(occupant, ASSET_TAG)) == asset_id:
            if occupant.get_path_name() == f"{requested_path}.{requested_path.rsplit('/', 1)[-1]}":
                return occupant
            raise ValueError(f"Asset has moved to {occupant.get_path_name()}")
        raise ValueError(f"Destination is occupied by a different asset: {requested_path}")

    # Inspect package metadata directly. Custom metadata may be absent from registry tags.
    registry = unreal.AssetRegistryHelpers.get_asset_registry()
    for data in registry.get_assets_by_path(ROOT, recursive=True):
        if str(data.asset_class_path.asset_name) != "StaticMesh":
            continue
        mesh = data.get_asset()
        if mesh and str(assets.get_metadata_tag(mesh, ASSET_TAG)) == asset_id:
            raise ValueError(f"Destination changed for this asset: {mesh.get_path_name()} -> {requested_path}")
    return None


def _slot_name(slot):
    imported_name = str(slot.get_editor_property("imported_material_slot_name"))
    if imported_name and imported_name.casefold() != "none":
        return imported_name
    return str(slot.get_editor_property("material_slot_name"))


def _assigned_materials(mesh):
    assigned = {}
    if mesh is not None:
        for slot in mesh.get_editor_property("static_materials"):
            material = slot.get_editor_property("material_interface")
            if material and material.get_path_name() != "/Engine/EngineMaterials/DefaultMaterial.DefaultMaterial":
                name = _slot_name(slot)
                if name.casefold() in assigned:
                    raise ValueError(f"Cannot identify duplicate assigned slot: {name}")
                assigned[name.casefold()] = (name, material)
    return assigned


def _check_slots(assigned, incoming):
    missing = [name for key, (name, _) in assigned.items() if key not in incoming]
    if missing:
        raise ValueError("Assigned material slots missing from incoming mesh: " + ", ".join(missing))


def push(manifest_path):
    """Validate a handoff, then import or update the Static Mesh in place."""
    manifest = Path(manifest_path)
    data = json.loads(manifest.read_text(encoding="utf-8"))
    asset_id = str(uuid.UUID(data["asset_id"]))
    name, folder = data["name"], data["destination"]
    if (not re.fullmatch(r"[A-Za-z0-9_]+", name)
            or not DESTINATION.fullmatch(folder)
            or {".", ".."}.intersection(folder.split("/"))):
        raise ValueError(f"Invalid THREN mesh destination: {folder}/{name}")
    source = manifest.with_suffix(".fbx")
    if source.stem != name or not source.is_file():
        raise ValueError(f"Missing FBX for {name}: {source}")

    package_path = f"{folder}/{name}"
    object_path = f"{package_path}.{name}"
    assets = unreal.EditorAssetLibrary
    existing = _find_existing(asset_id, package_path)
    assigned = _assigned_materials(existing)
    expected_slots = {slot.casefold(): slot for slot in data["slots"]}
    _check_slots(assigned, expected_slots)

    if not assets.does_directory_exist(folder) and not assets.make_directory(folder):
        raise RuntimeError(f"Could not create {folder}")

    options = unreal.FbxImportUI()
    options.set_editor_property("automated_import_should_detect_type", False)
    options.set_editor_property("mesh_type_to_import", unreal.FBXImportType.FBXIT_STATIC_MESH)
    options.set_editor_property("import_mesh", True)
    options.set_editor_property("import_as_skeletal", False)
    options.set_editor_property("import_materials", False)
    options.set_editor_property("import_textures", False)
    options.set_editor_property("import_animations", False)
    mesh_options = options.get_editor_property("static_mesh_import_data")
    mesh_options.set_editor_property("generate_lightmap_u_vs", False)
    mesh_options.set_editor_property("transform_vertex_to_absolute", True)
    mesh_options.set_editor_property("reorder_material_to_fbx_order", False)

    task = unreal.AssetImportTask()
    task.set_editor_property("filename", str(source))
    task.set_editor_property("destination_path", folder)
    task.set_editor_property("destination_name", name)
    task.set_editor_property("automated", True)
    task.set_editor_property("replace_existing", existing is not None)
    task.set_editor_property("replace_existing_settings", False)
    task.set_editor_property("save", False)
    task.set_editor_property("options", options)
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])

    imported = task.get_objects()
    if len(imported) != 1 or not isinstance(imported[0], unreal.StaticMesh):
        raise RuntimeError(f"Expected one imported Static Mesh at {object_path}")
    mesh = imported[0]
    if mesh.get_path_name() != object_path or (existing is not None and mesh != existing):
        raise RuntimeError(f"Import did not update the expected asset in place: {object_path}")

    slots = mesh.get_editor_property("static_materials")
    imported_slots = {_slot_name(slot).casefold(): index for index, slot in enumerate(slots)}
    lost_slots = [name for key, name in expected_slots.items() if key not in imported_slots]
    if lost_slots:
        raise RuntimeError("Unreal import did not preserve these FBX slots: " + ", ".join(lost_slots))
    for key, (_, material) in assigned.items():
        mesh.set_material(imported_slots[key], material)
    assets.set_metadata_tag(mesh, ASSET_TAG, asset_id)
    if not assets.save_loaded_asset(mesh, only_if_is_dirty=False):
        raise RuntimeError(f"Could not save {object_path}")
    return object_path
