# BlenderGameDevAddons

## Installation

1. Download `BlenderGameDevAddons_vX.Y.Z.zip` from the [latest GitHub release](https://github.com/MatthieuHernandez/BlenderGameDevAddons/releases/latest).
2. Drag and drop the ZIP into Blender and confirm the installation. The archive includes **THREN Tools** (`thren_tools`) and **Send to Unreal** (`send2ue`).
3. Restart Blender.
4. To use **Push Mesh to Unreal**, follow the [Send to Unreal Quickstart](https://poly-hammer.github.io/BlenderTools/send2ue/introduction/quickstart/) to configure the THREN Unreal Engine project.
5. Copy `Unreal/Content/Python/thren_mesh_import.py` to `Content/Python/` in the THREN Unreal project. Enable **Python Editor Script Plugin**, **Editor Scripting Utilities**, and **Enable Remote Execution**.

Steps 4 and 5 are a one-time setup for each Unreal project. You can skip both steps if the project is already configured.

## THREN Tools

### Export Low/High FBX

Exports the selection together in two files. The `_low.fbx` file has Multiresolution disabled, and the `_high.fbx` file has it enabled.

By default, the files are saved in the `Export` folder next to the `.blend` file.

#### Usage

1. Select one or more meshes in Object Mode.
2. Press `N` in the 3D Viewport to open the sidebar.
3. In the **THREN** tab, enter a base name in **File Name**. Leave the field blank to use the active selected object's name or the first selected object's name.
4. Set **Output Folder** if you want a different destination. Relative paths are resolved from the folder containing the `.blend` file.
5. Click **Export FBX**.

### Push Mesh to Unreal

Exports each selected mesh to its own FBX and creates or updates one Static Mesh per object in the THREN Unreal project. Each asset uses the Blender object's name with the `SM_` prefix. Each mesh keeps its own pivot, persistent ID and material slots.

#### Usage

1. Open the THREN project in Unreal and keep only that Unreal Editor instance open during the push.
2. Select one or more meshes in Object Mode.
3. Press `N` in the 3D Viewport and open the **THREN** sidebar tab.
4. Pick **Shared**, **WitchLair**, or **Forest** to set the base directory. Use **Select Directory** to choose a different base anywhere under `/Content/THREN/`.
5. Enter a **Folder Name** to import into `<base>/<folder_name>/Meshes`. Leave it blank to use `<base>/Meshes`. If the base is already named `Meshes`, the push uses it directly.
6. Click **Push to Unreal**. Save the Blender file again after the first push to persist each object's THREN ID. For later pushes, keep each object's name and destination the same.

Use letters, digits and underscores in the prop folder. The exporter replaces unsupported characters in object and material slot names with underscores.


---
#### Package the add-on (for development purposes only)
```
git archive --format=zip --output=BlenderGameDevAddons_vX.Y.Z.zip HEAD send2ue thren_tools
```

or

```
Compress-Archive -Path .\send2ue, .\thren_tools -DestinationPath .\BlenderGameDevAddons_vX.Y.Z.zip -Force
```
