bl_info = {
    "name": "THREN Tools",
    "author": "MatthieuHernandez",
    "version": (1, 0, 8),
    "blender": (5, 3, 0),
    "location": "View3D > Sidebar > THREN",
    "description": "Export low/high FBX files and push Static Meshes to Unreal",
    "category": "Import-Export",
}

from . import low_high_fbx, panel, push_to_unreal


def register():
    low_high_fbx.register()
    push_to_unreal.register()
    panel.register()


def unregister():
    panel.unregister()
    push_to_unreal.unregister()
    low_high_fbx.unregister()
