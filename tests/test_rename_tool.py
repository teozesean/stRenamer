"""Offline stress tests for the Maya Rename Tool UI and utility modules."""

from __future__ import annotations

import importlib
import sys
import types
import unittest
from pathlib import Path


class MockCmds(types.ModuleType):
    """Small Maya cmds stand-in for local UI and utility stress tests."""

    def __init__(self) -> None:
        super().__init__("maya.cmds")
        self.selection = ["|geo_01"]
        self.nodes = {
            "|geo_01": "transform",
            "|geo_01|geo_02": "transform",
            "|geo_01|geo_02|geo_03": "transform",
            "|geo_01|geo_02|geo_03|geo_04": "transform",
            "|geo_01|geo_02|geo_03|geo_04|geo_05": "transform",
            "|persp": "transform",
            "|top": "transform",
            "|front": "transform",
            "|side": "transform",
            "|pCube1": "transform",
            "|pCube1|pCubeShape1": "mesh",
        }
        self.parents = {
            "|pCube1|pCubeShape1": ["|pCube1"],
        }
        self.children = {
            "|geo_01": ["|geo_01|geo_02"],
            "|geo_01|geo_02": ["|geo_01|geo_02|geo_03"],
            "|geo_01|geo_02|geo_03": ["|geo_01|geo_02|geo_03|geo_04"],
            "|geo_01|geo_02|geo_03|geo_04": ["|geo_01|geo_02|geo_03|geo_04|geo_05"],
            "|pCube1": ["|pCube1|pCubeShape1"],
        }
        self.ui = {
            "Variable_BtnGrp": {"select": 1},
            "categoryCommand": {"select": 1},
            "Variable_tfGrp": {"text": ""},
            "Prefix_tf00": {"text": ""},
            "Suffix_tf00": {"text": ""},
            "Search_tf00": {"text": ""},
            "Replace_tf00": {"text": ""},
            "padding_tf": {"value1": 1, "value2": 2},
            "uppercase_checkbox00": {"value": True},
            "lowercase_checkbox00": {"value": True},
            "alphabet_start": {"value": "A"},
            "upper_optMenuGrp": {"value": "A"},
            "lower_optMenuGrp": {"value": "a"},
            "refer_checkbox00": {"value": False},
            "Current_Name_Result": {"text": ""},
            "New_Name_Result": {"text": ""},
        }
        self.renames: list[tuple[str, str]] = []
        self.warnings: list[str] = []
        self.fail_renames: set[str] = set()
        self.control_parents: dict[str, str] = {}

    def ls(self, **kwargs):
        if kwargs.get("allDagObjects"):
            raise TypeError("Invalid flag 'allDagObjects'")
        if kwargs.get("selection"):
            return list(self.selection)
        if kwargs.get("type") == "transform":
            return [n for n, kind in self.nodes.items() if kind == "transform"]
        return list(self.nodes)

    def nodeType(self, obj):
        return self.nodes.get(obj)

    def listRelatives(self, obj, **kwargs):
        if kwargs.get("parent"):
            return list(self.parents.get(obj, []))
        if kwargs.get("children"):
            children = list(self.children.get(obj, []))
            if kwargs.get("type"):
                children = [
                    child for child in children
                    if self.nodes.get(child) == kwargs["type"]
                ]
            return children
        if kwargs.get("allDescendents"):
            return list(self.children.get(obj, []))
        return []

    def rename(self, obj, new_name):
        if obj in self.fail_renames:
            raise RuntimeError("Simulated Maya rename failure")
        kind = self.nodes.get(obj)
        if kind not in ("transform",):
            raise RuntimeError("No valid object to rename was specified")

        self.renames.append((obj, new_name))
        prefix = obj.rpartition("|")[0]
        new_full_name = f"{prefix}|{new_name}" if prefix else f"|{new_name}"

        old_descendants = [
            name for name in list(self.nodes)
            if name.startswith(f"{obj}|")
        ]
        self.nodes[new_full_name] = self.nodes.pop(obj)

        for old_name in old_descendants:
            suffix = old_name[len(obj):]
            new_descendant = f"{new_full_name}{suffix}"
            self.nodes[new_descendant] = self.nodes.pop(old_name)

        return new_full_name

    def radioButtonGrp(self, name, **kwargs):
        state = self.ui.setdefault(name, {})
        if kwargs.get("query"):
            return state.get("select", kwargs.get("select", 1))
        if "select" in kwargs:
            state["select"] = kwargs["select"]
        return name

    def textFieldGrp(self, name, **kwargs):
        state = self.ui.setdefault(name, {})
        if kwargs.get("query"):
            return state.get("text", "")
        if "text" in kwargs:
            state["text"] = kwargs["text"]
        return name

    def textField(self, name, **kwargs):
        state = self.ui.setdefault(name, {})
        if kwargs.get("query"):
            return state.get("text", "")
        if "text" in kwargs:
            state["text"] = kwargs["text"]
        return name

    def intFieldGrp(self, name, **kwargs):
        state = self.ui.setdefault(name, {})
        if kwargs.get("query"):
            if kwargs.get("value1"):
                return state.get("value1", 1)
            if kwargs.get("value2"):
                return state.get("value2", 2)
        if "value1" in kwargs:
            state["value1"] = kwargs["value1"]
        if "value2" in kwargs:
            state["value2"] = kwargs["value2"]
        return name

    def optionMenuGrp(self, name, **kwargs):
        state = self.ui.setdefault(name, {})
        if kwargs.get("query"):
            return state.get("value", "A" if "upper" in name else "a")
        if "value" in kwargs:
            state["value"] = kwargs["value"]
        if kwargs.get("edit") and "select" in kwargs:
            state["value"] = "A" if "upper" in name else "a"
        return name

    def checkBox(self, name, **kwargs):
        state = self.ui.setdefault(name, {})
        parent = kwargs.get("parent", kwargs.get("p"))
        if parent:
            self.control_parents[name] = parent
        if kwargs.get("query"):
            return state.get("value", True)
        if "value" in kwargs:
            state["value"] = kwargs["value"]
        return name

    def warning(self, message):
        self.warnings.append(str(message))

    def select(self, *args, **kwargs):
        if args:
            self.selection = list(args[0]) if isinstance(args[0], (list, tuple)) else [args[0]]

    def __getattr__(self, name):
        def unknown(*args, **kwargs):
            return name
        return unknown

    def reset_scene(self) -> None:
        self.selection = ["|geo_01"]
        self.nodes = {
            "|geo_01": "transform",
            "|geo_01|geo_02": "transform",
            "|geo_01|geo_02|geo_03": "transform",
            "|geo_01|geo_02|geo_03|geo_04": "transform",
            "|geo_01|geo_02|geo_03|geo_04|geo_05": "transform",
            "|persp": "transform",
            "|top": "transform",
            "|front": "transform",
            "|side": "transform",
            "|pCube1": "transform",
            "|pCube1|pCubeShape1": "mesh",
        }
        self.parents = {
            "|pCube1|pCubeShape1": ["|pCube1"],
        }
        self.children = {
            "|geo_01": ["|geo_01|geo_02"],
            "|geo_01|geo_02": ["|geo_01|geo_02|geo_03"],
            "|geo_01|geo_02|geo_03": ["|geo_01|geo_02|geo_03|geo_04"],
            "|geo_01|geo_02|geo_03|geo_04": ["|geo_01|geo_02|geo_03|geo_04|geo_05"],
            "|pCube1": ["|pCube1|pCubeShape1"],
        }
        self.renames.clear()
        self.warnings.clear()
        self.fail_renames.clear()
        self.control_parents.clear()


ROOT = Path(__file__).resolve().parents[1]
MAYA_SOURCE = ROOT / "Maya"

maya = types.ModuleType("maya")
cmds = MockCmds()
maya.cmds = cmds
sys.modules["maya"] = maya
sys.modules["maya.cmds"] = cmds
sys.path.insert(0, str(MAYA_SOURCE))


class NamingTests(unittest.TestCase):
    def setUp(self):
        sys.modules.pop("stRenamer_UTIL", None)
        self.util = importlib.import_module("stRenamer_UTIL")

    def test_uppercase_sequence_across_rollover(self):
        expected = ["A", "Z", "AA", "AB", "AZ", "BA"]
        actual = [self.util.build_uppercase_name(i) for i in range(26)]
        self.assertEqual(actual[0], expected[0])
        self.assertEqual(actual[25], expected[1])
        self.assertEqual(self.util.build_uppercase_name(26), expected[2])
        self.assertEqual(self.util.build_uppercase_name(27), expected[3])
        self.assertEqual(self.util.build_uppercase_name(51), expected[4])
        self.assertEqual(self.util.build_uppercase_name(52), expected[5])

    def test_lowercase_sequence_across_rollover(self):
        self.assertEqual(self.util.build_lowercase_name(0), "a")
        self.assertEqual(self.util.build_lowercase_name(25), "z")
        self.assertEqual(self.util.build_lowercase_name(26), "aa")

    def test_sequence_disabled_returns_selected_start(self):
        self.assertEqual(self.util.build_uppercase_name(99, "D", False), "D")
        self.assertEqual(self.util.build_lowercase_name(99, "c", False), "c")

    def test_number_padding_and_negative_start(self):
        self.assertEqual(self.util.build_number_name(0, 1, 3), "001")
        self.assertEqual(self.util.build_number_name(4, 10, 2), "14")

    def test_short_name_strips_full_hierarchy(self):
        self.assertEqual(self.util.get_short_name("|geo_01|geo_02|geo_03|geo_05"), "geo_05")

    def test_excel_letters_rejects_empty_alphabet(self):
        with self.assertRaisesRegex(ValueError, "Alphabet cannot be empty"):
            self.util.excel_letters(0, "")


class MayaUtilityTests(unittest.TestCase):
    def setUp(self):
        sys.modules.pop("stRenamer_UTIL", None)
        self.util = importlib.import_module("stRenamer_UTIL")
        cmds.reset_scene()

        cmds.ui["Variable_BtnGrp"]["select"] = 1
        cmds.ui["categoryCommand"]["select"] = 1
        cmds.ui["Variable_tfGrp"]["text"] = ""
        cmds.ui["Prefix_tf00"]["text"] = ""
        cmds.ui["Suffix_tf00"]["text"] = ""
        cmds.ui["Search_tf00"]["text"] = ""
        cmds.ui["Replace_tf00"]["text"] = ""
        cmds.ui["padding_tf"]["value1"] = 1
        cmds.ui["padding_tf"]["value2"] = 2
        cmds.ui["uppercase_checkbox00"]["value"] = True
        cmds.ui["lowercase_checkbox00"]["value"] = True
        cmds.ui["upper_optMenuGrp"]["value"] = "A"
        cmds.ui["lower_optMenuGrp"]["value"] = "a"
        cmds.ui["refer_checkbox00"]["value"] = False

    def test_shape_selection_maps_to_parent_transform(self):
        cmds.selection = ["|pCube1|pCubeShape1"]
        targets = self.util.get_selected_objects()
        self.assertEqual(targets, ["|pCube1"])

    def test_hierarchy_category_excludes_shapes(self):
        targets = self.util.get_objects_for_category(2)
        self.assertEqual(
            targets,
            [
                "|geo_01",
                "|geo_01|geo_02",
                "|geo_01|geo_02|geo_03",
                "|geo_01|geo_02|geo_03|geo_04",
                "|geo_01|geo_02|geo_03|geo_04|geo_05",
            ],
        )
        self.assertNotIn("|pCube1|pCubeShape1", targets)

    def test_hierarchy_parent_child_selection_deduplicates_and_preserves_order(self):
        cmds.selection = ["|geo_01|geo_02", "|geo_01"]
        targets = self.util.get_objects_for_category(2)

        self.assertEqual(
            targets,
            [
                "|geo_01|geo_02",
                "|geo_01|geo_02|geo_03",
                "|geo_01|geo_02|geo_03|geo_04",
                "|geo_01|geo_02|geo_03|geo_04|geo_05",
                "|geo_01",
            ],
        )
        self.assertEqual(len(targets), len(set(targets)))

    def test_all_category_excludes_shapes(self):
        targets = self.util.get_objects_for_category(3)
        self.assertTrue(targets)
        self.assertTrue(all(cmds.nodeType(obj) == "transform" for obj in targets))
        self.assertNotIn("|pCube1|pCubeShape1", targets)

    def test_number_rename_stays_transform_only(self):
        cmds.ui["Variable_BtnGrp"]["select"] = 4
        cmds.ui["padding_tf"]["value1"] = 10
        cmds.ui["padding_tf"]["value2"] = 3
        cmds.selection = [
            "|geo_01",
            "|geo_01|geo_02|geo_03|geo_04|geo_05",
        ]
        result = self.util.rename_selected()
        self.assertEqual(cmds.renames, [
            ("|geo_01|geo_02|geo_03|geo_04|geo_05", "011"),
            ("|geo_01", "010"),
        ])
        self.assertEqual(len(result), 2)

    def test_zero_start_number_is_preserved_in_ui_config(self):
        cmds.ui["padding_tf"]["value1"] = 0

        config = self.util.read_ui_config()

        self.assertEqual(config.start_number, 0)

    def test_uppercase_rename_uses_generated_names(self):
        cmds.ui["Variable_BtnGrp"]["select"] = 2
        cmds.selection = ["|geo_01", "|geo_01|geo_02"]
        self.util.rename_selected()
        self.assertEqual(cmds.renames, [
            ("|geo_01|geo_02", "B"),
            ("|geo_01", "A"),
        ])

    def test_search_replace_callback_handles_empty_search(self):
        cmds.ui["Search_tf00"]["text"] = ""
        cmds.ui["categoryCommand"]["select"] = 1
        result = self.util.replace_name()
        self.assertEqual(result, [])

    def test_refer_requires_two_objects(self):
        cmds.selection = ["|geo_01"]
        cmds.ui["refer_checkbox00"]["value"] = True
        cmds.ui["Search_tf00"]["text"] = "geo"
        cmds.ui["Replace_tf00"]["text"] = "test"
        result = self.util.replace_name()
        self.assertEqual(result, [])
        self.assertTrue(cmds.warnings)

    def test_repeated_number_sequences_are_consistent(self):
        for padding in range(1, 7):
            for start in range(-20, 21):
                for index in range(100):
                    name = self.util.build_number_name(index, start, padding)
                    self.assertRegex(name, r"^-?[0-9]+$")

    def test_reset_restores_every_ui_setting(self):
        cmds.ui["categoryCommand"]["select"] = 3
        cmds.ui["Variable_BtnGrp"]["select"] = 4
        cmds.ui["Variable_tfGrp"]["text"] = "Changed"
        cmds.ui["Prefix_tf00"]["text"] = "Pre"
        cmds.ui["Suffix_tf00"]["text"] = "Suf"
        cmds.ui["Search_tf00"]["text"] = "Old"
        cmds.ui["Replace_tf00"]["text"] = "New"
        cmds.ui["padding_tf"]["value1"] = 99
        cmds.ui["padding_tf"]["value2"] = 8
        cmds.ui["refer_checkbox00"]["value"] = True

        self.util.reset_to_default()

        self.assertEqual(cmds.ui["categoryCommand"]["select"], 1)
        self.assertEqual(cmds.ui["Variable_BtnGrp"]["select"], 1)
        self.assertEqual(cmds.ui["Variable_tfGrp"]["text"], "")
        self.assertEqual(cmds.ui["Prefix_tf00"]["text"], "")
        self.assertEqual(cmds.ui["Suffix_tf00"]["text"], "")
        self.assertEqual(cmds.ui["Search_tf00"]["text"], "")
        self.assertEqual(cmds.ui["Replace_tf00"]["text"], "")
        self.assertEqual(cmds.ui["padding_tf"]["value1"], 1)
        self.assertEqual(cmds.ui["padding_tf"]["value2"], 2)
        self.assertFalse(cmds.ui["refer_checkbox00"]["value"])

    def test_hierarchy_targets_are_renamed_deepest_first(self):
        objects = [
            "|geo_01",
            "|geo_01|geo_02",
            "|geo_01|geo_02|geo_03",
            "|geo_01|geo_02|geo_03|geo_04",
            "|geo_01|geo_02|geo_03|geo_04|geo_05",
        ]
        ordered = self.util.deepest_first(objects)
        self.assertEqual(
            ordered,
            [
                "|geo_01|geo_02|geo_03|geo_04|geo_05",
                "|geo_01|geo_02|geo_03|geo_04",
                "|geo_01|geo_02|geo_03",
                "|geo_01|geo_02",
                "|geo_01",
            ],
        )

        cmds.selection = objects
        cmds.ui["Variable_BtnGrp"]["select"] = 4
        cmds.ui["padding_tf"]["value1"] = 1
        cmds.ui["padding_tf"]["value2"] = 2
        self.util.rename_selected()

        self.assertEqual(cmds.renames[0][0], ordered[0])
        self.assertEqual(cmds.renames[-1][0], ordered[-1])
        self.assertEqual(
            [name for _obj, name in cmds.renames],
            ["05", "04", "03", "02", "01"],
        )

    def test_rename_continues_after_one_node_fails(self):
        cmds.selection = ["|geo_01", "|pCube1"]
        cmds.fail_renames.add("|pCube1")
        cmds.ui["Variable_BtnGrp"]["select"] = 4
        cmds.ui["padding_tf"]["value1"] = 1
        cmds.ui["padding_tf"]["value2"] = 3

        result = self.util.rename_selected()

        self.assertEqual(result, ["|001"])
        self.assertEqual(cmds.renames, [("|geo_01", "001")])
        self.assertTrue(any("|pCube1" in warning for warning in cmds.warnings))

    def test_each_rename_mode_applies_prefix_suffix_and_search(self):
        expected_names = {
            1: ["P_part_S", "P_part_1_S"],
            2: ["P_partA_S", "P_partB_S"],
            3: ["P_parta_S", "P_partb_S"],
            4: ["P_part01_S", "P_part02_S"],
        }

        for mode, expected in expected_names.items():
            with self.subTest(mode=mode):
                cmds.reset_scene()
                cmds.selection = ["|pCube1", "|persp"]
                cmds.ui["categoryCommand"]["select"] = 1
                cmds.ui["Variable_BtnGrp"]["select"] = mode
                cmds.ui["Variable_tfGrp"]["text"] = "item"
                cmds.ui["Prefix_tf00"]["text"] = "P_"
                cmds.ui["Suffix_tf00"]["text"] = "_S"
                cmds.ui["Search_tf00"]["text"] = "item"
                cmds.ui["Replace_tf00"]["text"] = "part"
                cmds.ui["padding_tf"]["value1"] = 1
                cmds.ui["padding_tf"]["value2"] = 2

                self.util.rename_selected()

                self.assertEqual(
                    [new_name for _obj, new_name in cmds.renames], expected
                )

    def test_uppercase_rollover_through_702_items(self):
        generated = [self.util.build_uppercase_name(index) for index in range(702)]
        self.assertEqual(generated[25], "Z")
        self.assertEqual(generated[26], "AA")
        self.assertEqual(generated[27], "AB")
        self.assertEqual(generated[51], "AZ")
        self.assertEqual(generated[52], "BA")
        self.assertEqual(generated[701], "ZZ")

    def test_lowercase_rollover_through_702_items(self):
        generated = [self.util.build_lowercase_name(index) for index in range(702)]
        self.assertEqual(generated[25], "z")
        self.assertEqual(generated[26], "aa")
        self.assertEqual(generated[27], "ab")
        self.assertEqual(generated[51], "az")
        self.assertEqual(generated[52], "ba")
        self.assertEqual(generated[701], "zz")

    def test_custom_alphabet_starts_roll_over_safely(self):
        for start in "ABCDEFGHIJKLMNOPQRSTUVWXYZA":
            values = [self.util.build_uppercase_name(index, start) for index in range(702)]
            self.assertEqual(len(values), 702)
            self.assertTrue(all(values))

        for start in "abcdefghijklmnopqrstuvwxyz":
            values = [self.util.build_lowercase_name(index, start) for index in range(702)]
            self.assertEqual(len(values), 702)
            self.assertTrue(all(values))

    def test_702_rename_sequences_produce_unique_names(self):
        uppercase = [self.util.build_uppercase_name(index) for index in range(702)]
        lowercase = [self.util.build_lowercase_name(index) for index in range(702)]
        numbers = [self.util.build_number_name(index, 1, 4) for index in range(702)]

        self.assertEqual(len(set(uppercase)), 702)
        self.assertEqual(len(set(lowercase)), 702)
        self.assertEqual(len(set(numbers)), 702)
        self.assertEqual(uppercase[-1], "ZZ")
        self.assertEqual(lowercase[-1], "zz")
        self.assertEqual(numbers[-1], "0702")

    def test_empty_base_name_keeps_current_name_with_prefix_suffix(self):
        cmds.selection = ["|pCube1"]
        cmds.ui["Prefix_tf00"]["text"] = "pre_"
        cmds.ui["Suffix_tf00"]["text"] = "_suf"

        self.util.rename_selected()

        self.assertEqual(cmds.renames, [("|pCube1", "pre_pCube1_suf")])

    def test_deepest_first_multiple_hierarchy_levels(self):
        objects = [
            "|World|Root",
            "|World|Root|Group",
            "|World|Root|Group|Cube",
            "|World|Root|Group|Cube|Shape",
        ]
        ordered = self.util.deepest_first(objects)
        self.assertEqual(ordered, list(reversed(objects)))

    def test_duplicate_names_in_all_category_are_still_transform_only(self):
        duplicate_transforms = [
            "|geo_01",
            "|geo_01|geo_02",
            "|geo_01|geo_02|geo_03",
            "|pCube1",
        ]
        for obj in duplicate_transforms:
            self.assertEqual(cmds.nodeType(obj), "transform")

        targets = self.util.get_objects_for_category(3)
        self.assertTrue(all(cmds.nodeType(obj) == "transform" for obj in targets))

    def test_geo_multi_level_hierarchy_deepest_first(self):
        objects = [
            "|geo_01",
            "|geo_01|geo_02",
            "|geo_01|geo_02|geo_03",
            "|geo_01|geo_02|geo_03|geo_04",
            "|geo_01|geo_02|geo_03|geo_04|geo_05",
        ]

        ordered = self.util.deepest_first(objects)
        self.assertEqual(
            ordered,
            [
                "|geo_01|geo_02|geo_03|geo_04|geo_05",
                "|geo_01|geo_02|geo_03|geo_04",
                "|geo_01|geo_02|geo_03",
                "|geo_01|geo_02",
                "|geo_01",
            ],
        )

    def test_mixed_hierarchy_numbers_parent_first_and_renames_child_first(self):
        objects = [
            "|pCube1",
            "|pCube1|test_01",
            "|pCube1|test_01|test_02",
            "|pCube1|test_01|test_02|geo_04",
            "|pCube1|test_01|test_02|geo_04|geo_05",
        ]

        cmds.nodes.update({obj: "transform" for obj in objects})
        cmds.children.update(
            {
                "|pCube1": ["|pCube1|test_01"],
                "|pCube1|test_01": ["|pCube1|test_01|test_02"],
                "|pCube1|test_01|test_02": [
                    "|pCube1|test_01|test_02|geo_04"
                ],
                "|pCube1|test_01|test_02|geo_04": [
                    "|pCube1|test_01|test_02|geo_04|geo_05"
                ],
            }
        )

        cmds.selection = ["|pCube1"]
        cmds.ui["categoryCommand"]["select"] = 2
        cmds.ui["Variable_BtnGrp"]["select"] = 2
        cmds.ui["Variable_tfGrp"]["text"] = "geo_"
        cmds.ui["upper_optMenuGrp"]["value"] = "A"
        cmds.ui["uppercase_checkbox00"]["value"] = True

        targets = self.util.get_objects_for_category(2)
        self.assertEqual(targets, objects)

        self.util.rename_selected()

        self.assertEqual(
            cmds.renames,
            [
                ("|pCube1|test_01|test_02|geo_04|geo_05", "geo_E"),
                ("|pCube1|test_01|test_02|geo_04", "geo_D"),
                ("|pCube1|test_01|test_02", "geo_C"),
                ("|pCube1|test_01", "geo_B"),
                ("|pCube1", "geo_A"),
            ],
        )

    def test_all_category_does_not_change_selection(self):
        original_selection = ["|pCube1"]
        cmds.selection = list(original_selection)

        self.util.get_objects_for_category(3)

        self.assertEqual(cmds.selection, original_selection)


class CallbackAndPreviewTests(unittest.TestCase):
    def setUp(self):
        sys.modules.pop("stRenamer_UTIL", None)
        sys.modules.pop("stRenamer_UI", None)
        cmds.reset_scene()

    def test_ui_imports_and_all_callbacks_accept_maya_arguments(self):
        ui = importlib.import_module("stRenamer_UI")
        ui.build_window()
        self.assertEqual(cmds.control_parents["refer_checkbox00"], "Search_row00")
        callback_names = [
            "reset_to_default",
            "refresh_current_name",
            "refresh_new_name",
            "duplicate_selection",
            "variable_visibility",
            "rename_selected",
            "add_prefix",
            "add_suffix",
            "replace_name",
        ]
        for name in callback_names:
            callback = getattr(ui, name)
            callback("maya-provided-value")

    def test_preview_updates_both_fields(self):
        util = importlib.import_module("stRenamer_UTIL")
        ui = importlib.import_module("stRenamer_UI")
        ui.build_window()
        ui.refresh_new_name()
        self.assertEqual(cmds.ui["Current_Name_Result"]["text"], "geo_01")
        self.assertEqual(cmds.ui["New_Name_Result"]["text"], "geo_01")

    def test_import_builds_no_window_until_shown(self):
        ui = importlib.import_module("stRenamer_UI")
        # Importing the module must not build the window any more.
        self.assertNotIn("refer_checkbox00", cmds.control_parents)
        ui.build_window()
        self.assertEqual(cmds.control_parents["refer_checkbox00"], "Search_row00")
        # Showing again reuses the existing window without error.
        ui.show_rename_tool()
        self.assertEqual(cmds.control_parents["refer_checkbox00"], "Search_row00")


if __name__ == "__main__":
    unittest.main(verbosity=2)
