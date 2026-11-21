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

Combines the selected meshes and creates or updates a single Static Mesh in the THREN Unreal project. Materials used by the meshes become Unreal material slots.

#### Usage

1. Open the THREN project in Unreal and keep only that Unreal Editor instance open during the push.
2. Select one or more meshes in Object Mode.
3. Press `N` in the 3D Viewport and open the **THREN** sidebar tab. Enter a **File Name**, such as `SM_Lantern`, for the combined FBX and Static Mesh. The first selected mesh alphabetically supplies the pivot, persistent ID and default file name.
4. Pick **Shared** or **WitchLair** and check the displayed destination. Leave **Prop Folder** blank to use the FBX name without `SM_`.
5. Click **Push to Unreal**. Save the Blender file again after the first push to persist the object's THREN ID. For later pushes, keep the same first mesh alphabetically, export name and destination.

Use letters, digits and underscores for the export name and prop folder. The exporter replaces unsupported characters in material slot names with underscores.
