"""Blender scene and naming operations for the stRenamer draft add-on.

The naming functions mirror the Maya version. Scene access and undo are handled
through Blender objects and undoable operators instead of ``maya.cmds``.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Callable, Iterable, Sequence

import bpy


class RenameMode(str, Enum):
    NONE = "NONE"
    UPPER = "UPPER"
    LOWER = "LOWER"
    NUMBER = "NUMBER"


@dataclass(frozen=True)
class RenameConfig:
    mode: RenameMode = RenameMode.NONE
    base_name: str = ""
    prefix: str = ""
    suffix: str = ""
    search_text: str = ""
    replace_text: str = ""
    start_number: int = 1
    padding: int = 2
    sequence_letters: bool = True
    alphabet_start: str = "A"
    refer: bool = False
    category: str = "SELECTED"


def excel_letters(index: int, alphabet: str) -> str:
    """Return Excel-style letters from a zero-based index (A..Z, AA...)."""
    if index < 0:
        raise ValueError("Sequence index cannot be negative")
    if not alphabet:
        raise ValueError("Alphabet cannot be empty")

    result: list[str] = []
    base = len(alphabet)
    value = index
    while True:
        value, remainder = divmod(value, base)
        result.append(alphabet[remainder])
        if value == 0:
            break
        value -= 1
    return "".join(reversed(result))


def build_uppercase_name(
    index: int, start_char: str = "A", sequence: bool = True
) -> str:
    alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    start = start_char.upper()
    start_index = alphabet.index(start) if start in alphabet else 0
    return excel_letters(start_index + index, alphabet) if sequence else start


def build_lowercase_name(
    index: int, start_char: str = "a", sequence: bool = True
) -> str:
    alphabet = "abcdefghijklmnopqrstuvwxyz"
    start = start_char.lower()
    start_index = alphabet.index(start) if start in alphabet else 0
    return excel_letters(start_index + index, alphabet) if sequence else start


def build_number_name(index: int, start_value: int, pad_width: int) -> str:
    return str(start_value + index).zfill(max(1, pad_width))


def read_ui_config(settings) -> RenameConfig:
    """Copy the Scene PropertyGroup into a DCC-independent config value."""
    return RenameConfig(
        mode=RenameMode(settings.mode),
        base_name=settings.base_name,
        prefix=settings.prefix,
        suffix=settings.suffix,
        search_text=settings.search_text,
        replace_text=settings.replace_text,
        start_number=settings.start_number,
        padding=settings.padding,
        sequence_letters=(
            settings.upper_sequence
            if settings.mode == RenameMode.UPPER.value
            else settings.lower_sequence
            if settings.mode == RenameMode.LOWER.value
            else True
        ),
        alphabet_start=(
            settings.upper_start
            if settings.mode == RenameMode.UPPER.value
            else settings.lower_start
            if settings.mode == RenameMode.LOWER.value
            else "A"
        ),
        refer=settings.refer,
        category=settings.category,
    )


def get_selected_objects(context) -> list[bpy.types.Object]:
    """Return selected objects in Blender's reported selection order."""
    return list(context.selected_objects or [])


def get_hierarchy_objects(context) -> list[bpy.types.Object]:
    """Return selected roots and descendants in parent-first depth-first order."""
    roots = get_selected_objects(context)
    selected = set(roots)
    # If both a parent and child are selected, visit the top selected ancestor
    # once, which preserves the Maya utility's deduplicated hierarchy behavior.
    roots = [obj for obj in roots if not any(parent in selected for parent in _ancestors(obj))]
    ordered: list[bpy.types.Object] = []
    seen: set[bpy.types.Object] = set()

    def visit(obj: bpy.types.Object) -> None:
        if obj in seen:
            return
        seen.add(obj)
        ordered.append(obj)
        for child in obj.children:
            visit(child)

    for root in roots:
        visit(root)
    return ordered


def _ancestors(obj: bpy.types.Object) -> Iterable[bpy.types.Object]:
    parent = obj.parent
    while parent is not None:
        yield parent
        parent = parent.parent


def get_objects_for_category(context, category: str) -> list[bpy.types.Object]:
    if category == "HIERARCHY":
        return get_hierarchy_objects(context)
    if category == "ALL":
        return list(context.scene.objects)
    # Blender enforces scene-wide unique object names, so a Duplicates scope
    # has no equivalent for objects. Non-object datablocks are outside this draft.
    return get_selected_objects(context)


def hierarchy_depth(obj: bpy.types.Object) -> int:
    return sum(1 for _ in _ancestors(obj))


def deepest_first(objects: Sequence[bpy.types.Object]) -> list[bpy.types.Object]:
    unique = list(dict.fromkeys(objects))
    return sorted(unique, key=hierarchy_depth, reverse=True)


def _rename_objects(
    objects: Sequence[bpy.types.Object],
    name_factory: Callable[[int, bpy.types.Object], str],
) -> list[bpy.types.Object]:
    """Rename in child-first order; the calling Blender operator owns undo."""
    original_positions = {obj: index for index, obj in enumerate(objects)}
    renamed: list[bpy.types.Object] = []
    for obj in deepest_first(objects):
        index = original_positions[obj]
        try:
            obj.name = name_factory(index, obj)
            renamed.append(obj)
        except (TypeError, ValueError, RuntimeError) as error:
            print(f"stRenamer: Could not rename '{obj.name}': {error}")
    return renamed


def _make_batch_name(
    index: int,
    obj: bpy.types.Object,
    original_name: str,
    config: RenameConfig,
) -> str:
    if config.mode == RenameMode.NONE:
        if config.base_name:
            base_name = config.base_name if index == 0 else f"{config.base_name}_{index}"
        else:
            base_name = original_name
        name = f"{config.prefix}{base_name}{config.suffix}"
    elif config.mode == RenameMode.UPPER:
        sequence = build_uppercase_name(
            index, config.alphabet_start, config.sequence_letters
        )
        name = f"{config.prefix}{config.base_name}{sequence}{config.suffix}"
    elif config.mode == RenameMode.LOWER:
        sequence = build_lowercase_name(
            index, config.alphabet_start, config.sequence_letters
        )
        name = f"{config.prefix}{config.base_name}{sequence}{config.suffix}"
    else:
        sequence = build_number_name(index, config.start_number, config.padding)
        name = f"{config.prefix}{config.base_name}{sequence}{config.suffix}"

    if config.search_text:
        name = name.replace(config.search_text, config.replace_text)
    return name


def rename_selected(context, settings) -> list[bpy.types.Object]:
    config = read_ui_config(settings)
    objects = get_objects_for_category(context, config.category)
    original_names = {obj: obj.name for obj in objects}
    return _rename_objects(
        objects,
        lambda index, obj: _make_batch_name(
            index, obj, original_names[obj], config
        ),
    )


def add_prefix(context, settings) -> list[bpy.types.Object]:
    config = read_ui_config(settings)
    if not config.prefix:
        return []
    objects = get_objects_for_category(context, config.category)
    original_names = {obj: obj.name for obj in objects}
    return _rename_objects(
        objects, lambda _index, obj: f"{config.prefix}{original_names[obj]}"
    )


def add_suffix(context, settings) -> list[bpy.types.Object]:
    config = read_ui_config(settings)
    if not config.suffix:
        return []
    objects = get_objects_for_category(context, config.category)
    original_names = {obj: obj.name for obj in objects}
    return _rename_objects(
        objects, lambda _index, obj: f"{original_names[obj]}{config.suffix}"
    )


def apply_search_replace(
    objects: Iterable[bpy.types.Object], search_text: str, replace_text: str
) -> list[bpy.types.Object]:
    if not search_text:
        return []
    matching = [obj for obj in objects if search_text in obj.name]
    original_names = {obj: obj.name for obj in matching}
    return _rename_objects(
        matching,
        lambda _index, obj: original_names[obj].replace(search_text, replace_text),
    )


def replace_name(context, settings) -> list[bpy.types.Object]:
    config = read_ui_config(settings)
    objects = get_objects_for_category(context, config.category)
    if config.refer:
        if not config.search_text:
            return []
        if len(objects) < 2 or config.search_text not in objects[0].name:
            return []

        target = objects[1]
        target.name = objects[0].name.replace(
            config.search_text, config.replace_text
        )
        # Keep the Maya Refer behavior of ending with the source and target selected.
        for obj in context.selected_objects:
            obj.select_set(False)
        objects[0].select_set(True)
        target.select_set(True)
        context.view_layer.objects.active = target
        return [target]
    return apply_search_replace(
        objects, config.search_text, config.replace_text
    )


class STRENNER_PG_Settings(bpy.types.PropertyGroup):
    mode: bpy.props.EnumProperty(
        name="Variable",
        items=[
            ("NONE", "None", "Use the current name or a supplied base name"),
            ("UPPER", "A–Z", "Append an Excel-style uppercase sequence"),
            ("LOWER", "a–z", "Append an Excel-style lowercase sequence"),
            ("NUMBER", "0–9", "Append an incrementing number"),
        ],
        default="NONE",
    )
    category: bpy.props.EnumProperty(
        name="Category",
        items=[
            ("SELECTED", "Selected", "Rename selected objects"),
            ("HIERARCHY", "Hierarchy", "Rename selected objects and descendants"),
            ("ALL", "All", "Rename all objects in the current scene"),
        ],
        default="SELECTED",
    )
    base_name: bpy.props.StringProperty(name="New Name", default="")
    prefix: bpy.props.StringProperty(name="Prefix", default="")
    suffix: bpy.props.StringProperty(name="Suffix", default="")
    search_text: bpy.props.StringProperty(name="Search for", default="")
    replace_text: bpy.props.StringProperty(name="Replace with", default="")
    start_number: bpy.props.IntProperty(name="Start No.", default=1)
    padding: bpy.props.IntProperty(name="Padding", default=2, min=1)
    upper_start: bpy.props.EnumProperty(
        name="Alphabet", items=[(chr(code), chr(code), "") for code in range(65, 91)], default="A"
    )
    lower_start: bpy.props.EnumProperty(
        name="Alphabet", items=[(chr(code), chr(code), "") for code in range(97, 123)], default="a"
    )
    upper_sequence: bpy.props.BoolProperty(name="Sequence Letters", default=True)
    lower_sequence: bpy.props.BoolProperty(name="Sequence Letters", default=True)
    refer: bpy.props.BoolProperty(name="Refer", default=False)


def _report_renamed(operator, renamed: Sequence[bpy.types.Object]) -> None:
    if renamed:
        operator.report({"INFO"}, f"Renamed {len(renamed)} object(s)")
    else:
        operator.report({"WARNING"}, "No objects were renamed")


class STRENNER_OT_rename(bpy.types.Operator):
    bl_idname = "strenamer.rename"
    bl_label = "Rename"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        renamed = rename_selected(
            context, context.scene.st_renamer_settings
        )
        _report_renamed(self, renamed)
        return {"FINISHED"}


class STRENNER_OT_add_prefix(bpy.types.Operator):
    bl_idname = "strenamer.add_prefix"
    bl_label = "Add Prefix"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        renamed = add_prefix(context, context.scene.st_renamer_settings)
        _report_renamed(self, renamed)
        return {"FINISHED"}


class STRENNER_OT_add_suffix(bpy.types.Operator):
    bl_idname = "strenamer.add_suffix"
    bl_label = "Add Suffix"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        renamed = add_suffix(context, context.scene.st_renamer_settings)
        _report_renamed(self, renamed)
        return {"FINISHED"}


class STRENNER_OT_replace(bpy.types.Operator):
    bl_idname = "strenamer.replace"
    bl_label = "Replace"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        renamed = replace_name(context, context.scene.st_renamer_settings)
        _report_renamed(self, renamed)
        return {"FINISHED"}


class STRENNER_OT_reset(bpy.types.Operator):
    bl_idname = "strenamer.reset"
    bl_label = "Reset to Default"

    def execute(self, context):
        settings = context.scene.st_renamer_settings
        settings.mode = "NONE"
        settings.category = "SELECTED"
        settings.base_name = ""
        settings.prefix = ""
        settings.suffix = ""
        settings.search_text = ""
        settings.replace_text = ""
        settings.start_number = 1
        settings.padding = 2
        settings.upper_start = "A"
        settings.lower_start = "a"
        settings.upper_sequence = True
        settings.lower_sequence = True
        settings.refer = False
        return {"FINISHED"}


CLASSES = (
    STRENNER_PG_Settings,
    STRENNER_OT_rename,
    STRENNER_OT_add_prefix,
    STRENNER_OT_add_suffix,
    STRENNER_OT_replace,
    STRENNER_OT_reset,
)


def register() -> None:
    for cls in CLASSES:
        bpy.utils.register_class(cls)
    bpy.types.Scene.st_renamer_settings = bpy.props.PointerProperty(
        type=STRENNER_PG_Settings
    )


def unregister() -> None:
    if hasattr(bpy.types.Scene, "st_renamer_settings"):
        del bpy.types.Scene.st_renamer_settings
    for cls in reversed(CLASSES):
        bpy.utils.unregister_class(cls)
