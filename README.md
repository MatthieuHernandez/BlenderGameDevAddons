# BlenderGameDevAddons
A collection of custom Blender add-ons made to simplify video game development.


## Installation


1. Download the `.py` file for the extensions you want to install:
   1. Open the file in the GitHub repository.
   2. Click the Download raw file button (top-right corner of the file preview).
   3. Save the file to your computer.
2. In Blender, go to **Edit → Preferences → Add-ons → Install from Disk** (*small arrow in the upper-right corner*).
3. Select the `.py` file and enable the add-on.

:warning: **Updating an add-on:** Remove the previous version before installing the new version.

## Add-ons

### Low/High FBX Exporter

Exports a `_low.fbx` file for each selected mesh with Multiresolution disabled. Meshes with a Multiresolution modifier also get a `_high.fbx` file with Multiresolution enabled.

The files are saved in the `Export` folder next to the `.blend` file.

#### Usage

1. Select one or more meshes in Object Mode.
2. Press `N` in the 3D Viewport to open the sidebar.
3. Open the **FBX Export** tab and click **Export Low + High FBX**.
