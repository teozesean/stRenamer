from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Callable, Iterable, Sequence

import maya.cmds as cmds

DEFAULT_CAMERA_TRANSFORMS = frozenset(
    {"|front", "|persp", "|side", "|top"}
)


class RenameMode(str, Enum):
    NONE = "none"
    UPPER = "upper"
    LOWER = "lower"
    NUMBER = "number"


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
    category: int = 1


def excel_letters(index: int, alphabet: str) -> str:
    """Return A-Z/AA-AZ style letters from a zero-based index."""
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
    if not sequence:
        return start_char.upper()
    alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    start_index = (
        alphabet.index(start_char.upper())
        if start_char.upper() in alphabet
        else 0
    )
    return excel_letters(start_index + index, alphabet)


def build_lowercase_name(
    index: int, start_char: str = "a", sequence: bool = True
) -> str:
    if not sequence:
        return start_char.lower()
    alphabet = "abcdefghijklmnopqrstuvwxyz"
    start_index = (
        alphabet.index(start_char.lower())
        if start_char.lower() in alphabet
        else 0
    )
    return excel_letters(start_index + index, alphabet)


def build_number_name(index: int, start_value: int, pad_width: int) -> str:
    return str(start_value + index).zfill(max(1, pad_width))


def get_short_name(full_name: str) -> str:
    return full_name.rpartition("|")[-1]


def get_selected_objects() -> list[str]:
    selected = cmds.ls(selection=True, long=True) or []
    transforms: list[str] = []

    for obj in selected:
        node_type = cmds.nodeType(obj)
        if node_type == "transform":
            if obj not in transforms:
                transforms.append(obj)
            continue

        parents = cmds.listRelatives(obj, parent=True, fullPath=True) or []
        for parent in parents:
            if cmds.nodeType(parent) == "transform" and parent not in transforms:
                transforms.append(parent)

    return transforms


def read_ui_config() -> RenameConfig:
    mode_index = cmds.radioButtonGrp("Variable_BtnGrp", query=True, select=True)
    mode = {
        1: RenameMode.NONE,
        2: RenameMode.UPPER,
        3: RenameMode.LOWER,
        4: RenameMode.NUMBER,
    }.get(mode_index, RenameMode.NONE)

    return RenameConfig(
        mode=mode,
        base_name=cmds.textFieldGrp("Variable_tfGrp", query=True, text=True) or "",
        prefix=cmds.textField("Prefix_tf00", query=True, text=True) or "",
        suffix=cmds.textField("Suffix_tf00", query=True, text=True) or "",
        search_text=cmds.textFieldGrp("Search_tf00", query=True, text=True) or "",
        replace_text=cmds.textFieldGrp("Replace_tf00", query=True, text=True) or "",
        start_number=cmds.intFieldGrp("padding_tf", query=True, value1=True),
        padding=cmds.intFieldGrp("padding_tf", query=True, value2=True),
        sequence_letters=(
            bool(cmds.checkBox("uppercase_checkbox00", query=True, value=True))
            if mode == RenameMode.UPPER
            else bool(cmds.checkBox("lowercase_checkbox00", query=True, value=True))
            if mode == RenameMode.LOWER
            else True
        ),
        alphabet_start=(
            cmds.optionMenuGrp("upper_optMenuGrp", query=True, value=True)
            if mode == RenameMode.UPPER
            else cmds.optionMenuGrp("lower_optMenuGrp", query=True, value=True)
            if mode == RenameMode.LOWER
            else "A"
        ) or "A",
        refer=bool(cmds.checkBox("refer_checkbox00", query=True, value=True)),
        category=cmds.radioButtonGrp("categoryCommand", query=True, select=True) or 1,
    )


def reset_to_default() -> None:
    cmds.radioButtonGrp("categoryCommand", edit=True, select=1)
    cmds.radioButtonGrp("Variable_BtnGrp", edit=True, select=1)
    cmds.checkBox("uppercase_checkbox00", edit=True, value=True)
    cmds.checkBox("lowercase_checkbox00", edit=True, value=True)
    cmds.textFieldGrp("Variable_tfGrp", edit=True, text="")
    cmds.textField("Prefix_tf00", edit=True, text="")
    cmds.textField("Suffix_tf00", edit=True, text="")
    cmds.textFieldGrp("Search_tf00", edit=True, text="")
    cmds.textFieldGrp("Replace_tf00", edit=True, text="")
    cmds.optionMenuGrp("upper_optMenuGrp", edit=True, select=1)
    cmds.optionMenuGrp("lower_optMenuGrp", edit=True, select=1)
    cmds.intFieldGrp("padding_tf", edit=True, value1=1, value2=2)
    cmds.checkBox("refer_checkbox00", edit=True, value=False)
    variable_visibility()
    refresh_preview()


def variable_visibility() -> None:
    mode = cmds.radioButtonGrp("Variable_BtnGrp", query=True, select=True)

    cmds.separator("Variable_separator01", edit=True, visible=(mode == 1))
    cmds.rowColumnLayout("Variable_col02", edit=True, visible=(mode == 2))
    cmds.optionMenuGrp("upper_optMenuGrp", edit=True, visible=(mode == 2))
    cmds.checkBox("uppercase_checkbox00", edit=True, visible=(mode == 2))
    cmds.rowColumnLayout("Variable_col03", edit=True, visible=(mode == 3))
    cmds.optionMenuGrp("lower_optMenuGrp", edit=True, visible=(mode == 3))
    cmds.checkBox("lowercase_checkbox00", edit=True, visible=(mode == 3))
    cmds.intFieldGrp("padding_tf", edit=True, visible=(mode == 4))


def refresh_preview() -> None:
    selected = get_selected_objects()
    if not selected:
        cmds.textField(
            "Current_Name_Result",
            edit=True,
            text="--------------------Nothing selected--------------------",
        )
        cmds.textField(
            "New_Name_Result",
            edit=True,
            text="       Check for duplicates first to avoid errors",
        )
        return

    current_name = get_short_name(selected[0])
    cmds.textField("Current_Name_Result", edit=True, text=current_name)

    config = read_ui_config()
    preview = current_name

    if config.mode == RenameMode.NONE:
        if config.base_name:
            preview = f"{config.prefix}{config.base_name}{config.suffix}"
        elif config.prefix or config.suffix:
            preview = f"{config.prefix}{current_name}{config.suffix}"
    elif config.mode == RenameMode.UPPER:
        letter = build_uppercase_name(
            0, config.alphabet_start, config.sequence_letters
        )
        preview = f"{config.prefix}{config.base_name}{letter}{config.suffix}"
    elif config.mode == RenameMode.LOWER:
        letter = build_lowercase_name(
            0, config.alphabet_start, config.sequence_letters
        )
        preview = f"{config.prefix}{config.base_name}{letter}{config.suffix}"
    elif config.mode == RenameMode.NUMBER:
        number = build_number_name(0, config.start_number, config.padding)
        preview = f"{config.prefix}{config.base_name}{number}{config.suffix}"

    if config.search_text:
        preview = preview.replace(config.search_text, config.replace_text)

    cmds.textField("New_Name_Result", edit=True, text=preview)


def get_objects_for_category(category: int) -> list[str]:
    if category == 1:
        return get_selected_objects()

    if category == 2:
        return get_hierarchy_objects()

    if category == 3:
        transforms = cmds.ls(type="transform", long=True) or []
        return [
            obj for obj in transforms
            if obj not in DEFAULT_CAMERA_TRANSFORMS
        ]

    if category == 4:
        return get_duplicate_objects()

    return get_selected_objects()


def get_hierarchy_objects() -> list[str]:
    """Return selected transforms and descendants in parent-first DAG order."""
    roots = get_selected_objects()
    ordered: list[str] = []
    seen: set[str] = set()

    def visit(obj: str) -> None:
        if obj in seen:
            return
        seen.add(obj)
        ordered.append(obj)
        children = cmds.listRelatives(
            obj, children=True, type="transform", fullPath=True
        ) or []
        for child in children:
            visit(child)

    for root in roots:
        visit(root)
    return ordered


def get_duplicate_objects() -> list[str]:
    transforms = cmds.ls(type="transform", long=True) or []
    counts: dict[str, int] = {}
    for obj in transforms:
        name = get_short_name(obj)
        counts[name] = counts.get(name, 0) + 1

    return [obj for obj in transforms if counts[get_short_name(obj)] > 1]


def select_duplicates() -> list[str]:
    duplicates = get_duplicate_objects()
    if duplicates:
        cmds.select(duplicates, replace=True)
        cmds.warning(f"{len(duplicates)} duplicate names found.")
    else:
        cmds.warning("No duplicate names found.")
    cmds.radioButtonGrp("categoryCommand", edit=True, select=1)
    return duplicates


def _rename_objects(
    objects: Sequence[str],
    name_factory: Callable[[int, str], str],
) -> list[str]:
    """Rename a batch as one undoable action, retaining sequence indices."""
    renamed: list[str] = []
    original_positions = {obj: index for index, obj in enumerate(objects)}

    cmds.undoInfo(openChunk=True, chunkName="stRenamer Rename")
    try:
        for obj in deepest_first(objects):
            index = original_positions[obj]
            try:
                renamed.append(cmds.rename(obj, name_factory(index, obj)))
            except RuntimeError as error:
                cmds.warning(f"Could not rename '{obj}': {error}")
    finally:
        cmds.undoInfo(closeChunk=True)
    return renamed


def rename_selected() -> list[str]:
    config = read_ui_config()
    objects = get_objects_for_category(config.category)
    if not objects:
        cmds.warning("No objects matched the selected category.")
        return []

    def apply_search_replace_to_name(name: str) -> str:
        if config.search_text:
            return name.replace(config.search_text, config.replace_text)
        return name

    if config.mode == RenameMode.NONE:
        def make_name(index: int, obj: str) -> str:
            current_name = get_short_name(obj)
            if config.base_name:
                base_name = (
                    config.base_name if index == 0
                    else f"{config.base_name}_{index}"
                )
            else:
                base_name = current_name
            name = f"{config.prefix}{base_name}{config.suffix}"
            return apply_search_replace_to_name(name)

        renamed = _rename_objects(objects, make_name)

    elif config.mode == RenameMode.UPPER:
        def make_uppercase_name(index: int, _obj: str) -> str:
            sequence_name = build_uppercase_name(
                index, config.alphabet_start, config.sequence_letters
            )
            name = f"{config.prefix}{config.base_name}{sequence_name}{config.suffix}"
            return apply_search_replace_to_name(name)

        renamed = _rename_objects(
            objects,
            make_uppercase_name,
        )

    elif config.mode == RenameMode.LOWER:
        def make_lowercase_name(index: int, _obj: str) -> str:
            sequence_name = build_lowercase_name(
                index, config.alphabet_start, config.sequence_letters
            )
            name = f"{config.prefix}{config.base_name}{sequence_name}{config.suffix}"
            return apply_search_replace_to_name(name)

        renamed = _rename_objects(
            objects,
            make_lowercase_name,
        )

    elif config.mode == RenameMode.NUMBER:
        def make_number_name(index: int, _obj: str) -> str:
            sequence_name = build_number_name(
                index, config.start_number, config.padding
            )
            name = f"{config.prefix}{config.base_name}{sequence_name}{config.suffix}"
            return apply_search_replace_to_name(name)

        renamed = _rename_objects(
            objects,
            make_number_name,
        )

    refresh_preview()
    return renamed


def add_prefix() -> list[str]:
    config = read_ui_config()
    objects = get_objects_for_category(config.category)
    if not config.prefix:
        return []

    renamed = _rename_objects(
        objects, lambda _index, obj: f"{config.prefix}{get_short_name(obj)}"
    )
    refresh_preview()
    return renamed


def add_suffix() -> list[str]:
    config = read_ui_config()
    objects = get_objects_for_category(config.category)
    if not config.suffix:
        return []

    renamed = _rename_objects(
        objects, lambda _index, obj: f"{get_short_name(obj)}{config.suffix}"
    )
    refresh_preview()
    return renamed


def apply_search_replace(
    objects: Iterable[str], search_text: str, replace_text: str
) -> list[str]:
    if not search_text:
        return []

    def replace_in_name(_index: int, obj: str) -> str:
        return get_short_name(obj).replace(search_text, replace_text)

    matching_objects = [
        obj for obj in objects if search_text in get_short_name(obj)
    ]
    return _rename_objects(matching_objects, replace_in_name)


def replace_name() -> list[str]:
    config = read_ui_config()
    objects = get_objects_for_category(config.category)
    if not objects:
        cmds.warning("No objects matched the selected category.")
        return []

    if config.refer:
        if not config.search_text:
            cmds.warning("Enter text to search for before using Refer.")
            return []
        if len(objects) < 2:
            cmds.warning("Only applicable when two objects are selected.")
            return []

        first_name = get_short_name(objects[0])
        if config.search_text not in first_name:
            cmds.warning(
                "Searched text not found in first selection; nothing to refer."
            )
            return []

        referred_name = first_name.replace(config.search_text, config.replace_text)
        try:
            result = cmds.rename(objects[1], referred_name)
            cmds.select(objects[0], result)
            refresh_preview()
            return [result]
        except RuntimeError as error:
            cmds.warning(f"Could not apply Refer rename: {error}")
            return []

    renamed = apply_search_replace(objects, config.search_text, config.replace_text)
    refresh_preview()
    return renamed


def hierarchy_depth(full_name: str) -> int:
    return len([part for part in full_name.split("|") if part])


def deepest_first(objects: Sequence[str]) -> list[str]:
    unique = list(dict.fromkeys(objects))
    return sorted(unique, key=hierarchy_depth, reverse=True)
