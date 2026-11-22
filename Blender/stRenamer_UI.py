"""Blender sidebar UI for the stRenamer draft add-on."""

import sys
from pathlib import Path

import bpy

_FILE = globals().get("__file__")
_FOLDER = str(Path(_FILE).resolve().parent) if _FILE else ""
if _FOLDER and _FOLDER not in sys.path:
    sys.path.insert(0, _FOLDER)

import stRenamer_UTIL as rename_util


bl_info = {
    "name": "stRenamer",
    "author": "Sean Teo",
    "version": (0, 1, 0),
    "blender": (4, 2, 0),
    "location": "View3D > Sidebar > stRenamer",
    "description": "Batch rename Blender objects with stRenamer naming modes",
    "category": "3D View",
}


class STRENNER_PT_panel(bpy.types.Panel):
    bl_label = "stRenamer"
    bl_idname = "STRENNER_PT_panel"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "stRenamer"

    def draw(self, context):
        layout = self.layout
        settings = context.scene.st_renamer_settings
        config = rename_util.read_ui_config(settings)
        objects = rename_util.get_objects_for_category(context, config.category)

        preview = layout.box()
        preview.label(text="Name Preview")
        if objects:
            source = objects[0]
            preview.label(text=f"Current: {source.name}")
            if config.refer and len(objects) > 1 and config.search_text:
                proposed = source.name.replace(
                    config.search_text, config.replace_text
                )
                preview.label(text=f"Refer target: {objects[1].name}")
            else:
                proposed = rename_util._make_batch_name(
                    0, source, source.name, config
                )
            preview.label(text=f"New: {proposed}")
        else:
            preview.label(text="No objects in this category")

        layout.prop(settings, "category")
        layout.prop(settings, "mode")

        if settings.mode == "UPPER":
            row = layout.row(align=True)
            row.prop(settings, "upper_start")
            row.prop(settings, "upper_sequence")
        elif settings.mode == "LOWER":
            row = layout.row(align=True)
            row.prop(settings, "lower_start")
            row.prop(settings, "lower_sequence")
        elif settings.mode == "NUMBER":
            row = layout.row(align=True)
            row.prop(settings, "start_number")
            row.prop(settings, "padding")
        layout.prop(settings, "base_name")

        row = layout.row(align=True)
        row.prop(settings, "prefix")
        row.operator("strenamer.add_prefix", text="Add")
        row = layout.row(align=True)
        row.prop(settings, "suffix")
        row.operator("strenamer.add_suffix", text="Add")
        layout.operator("strenamer.rename", text="Rename", icon="OUTLINER_OB_FONT")

        layout.separator()
        layout.label(text="Search & Replace")
        layout.prop(settings, "search_text")
        layout.prop(settings, "replace_text")
        layout.prop(settings, "refer")
        layout.operator("strenamer.replace", text="Replace")

        layout.separator()
        layout.operator("strenamer.reset", text="Reset to Default")


def register() -> None:
    rename_util.register()
    bpy.utils.register_class(STRENNER_PT_panel)


def unregister() -> None:
    bpy.utils.unregister_class(STRENNER_PT_panel)
    rename_util.unregister()


if __name__ == "__main__":
    register()
