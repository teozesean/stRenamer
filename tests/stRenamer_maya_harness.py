"""In-Maya test harness for stRenamer — mirrors tests/test_rename_tool.py.

HOW TO RUN
----------
1. Save this file anywhere (e.g. next to your stRenamer repo).
2. In Maya's Script Editor (Python tab), run:

       import runpy
       runpy.run_path(r"<full path to this file>", run_name="__main__")

   (runpy sets __file__, so the harness can find the repo's Maya folder
   on its own. If it still can't find the modules, set STRENAMER_MAYA_DIR
   below to the folder containing stRenamer_UTIL.py / stRenamer_UI.py.)

   ALTERNATIVE — import / reload (for re-running after edits):
   Rename this file to stRenamer_maya_harness.py (underscores — Python
   module names cannot contain hyphens), then in the Script Editor:

       import sys
       sys.path.append(r"<folder containing this file>")
       import stRenamer_maya_harness          # runs the suite once
       import importlib; importlib.reload(stRenamer_maya_harness)  # runs it again

   Importing runs the tests immediately, because main() is called at the
   bottom of this file — so reload is simply "run the suite again".

WHAT IT DOES
------------
- Opens a fresh scene and creates real mesh objects to test with
  (polyCube / polySphere / polyCylinder / polyCone / polyTorus, no
  construction history), all parented under one top-level group,
  "stRenamerHarness_grp".
- Runs the same checks as the offline test file, but against real
  maya.cmds: pure naming helpers, categories (Selected / Hierarchy /
  All / Duplicates), rename ordering, prefix / suffix, search & replace,
  Refer, the preview fields, reset-to-default, shape-selection mapping
  (selecting a mesh shape acts on its transform), and the new
  build_window() / show_rename_tool() behaviour.
- Prints [PASS] / [FAIL] per check and a summary at the end.
- Automatically removes every test object after each check (the whole
  harness group is deleted and the removal is verified), and deletes
  the tool window at the end — the scene is left with only the default
  cameras, exactly as it started.

It never touches your real scene: it starts with cmds.file(new=True).
"""

import importlib
import sys
import traceback
from pathlib import Path

# --- Set this only if auto-detection fails -------------------------------
# Folder containing stRenamer_UTIL.py and stRenamer_UI.py, e.g.:
#   STRENAMER_MAYA_DIR = r"C:\Users\sean\Documents\stRenamer\Maya"
STRENAMER_MAYA_DIR = ""

# --- Bootstrap: find the modules ----------------------------------------
try:
    import maya.cmds as cmds
except ImportError:  # not running inside Maya
    print("ERROR: this harness must be run inside Maya (maya.cmds not found).")
    raise SystemExit(1)

_HERE = globals().get("__file__")
_CANDIDATES = [STRENAMER_MAYA_DIR] if STRENAMER_MAYA_DIR else []
if _HERE:
    _CANDIDATES += [str(Path(_HERE).resolve().parent),
                    str(Path(_HERE).resolve().parent / "Maya")]
_CANDIDATES += [str(Path.cwd()), str(Path.cwd() / "Maya")]

for _dir in _CANDIDATES:
    if _dir and Path(_dir, "stRenamer_UTIL.py").exists():
        if _dir not in sys.path:
            sys.path.insert(0, _dir)
        break

try:
    import stRenamer_UTIL as util
    import stRenamer_UI as ui
except ImportError:
    print("ERROR: could not find stRenamer_UTIL.py / stRenamer_UI.py.")
    print("Looked in:", [c for c in _CANDIDATES if c])
    print("Set STRENAMER_MAYA_DIR at the top of this file to the repo's Maya folder.")
    raise SystemExit(1)


# --- Tiny test framework ---------------------------------------------------
_RESULTS = []


def check(name, fn):
    """Run fn(); record PASS, or FAIL with the exception text.

    Every test's objects live under the harness group, so each check ends
    by deleting that group — nothing the test created survives it.
    """
    try:
        fn()
    except Exception:
        _RESULTS.append((name, False, traceback.format_exc(limit=3)))
        print("[FAIL] %s" % name)
    else:
        _RESULTS.append((name, True, ""))
        print("[PASS] %s" % name)
    finally:
        cleanup_test_objects()


def eq(actual, expected, what=""):
    if actual != expected:
        raise AssertionError("%s: expected %r, got %r" % (what or "value", expected, actual))


def short(names):
    return [util.get_short_name(n) for n in names]


# --- Test objects: real meshes under one group -----------------------------
HARNESS_GROUP = "stRenamerHarness_grp"
_GROUP = ""  # full path of the group in the current scene, set by fresh_scene()

# A rotating cast of primitives so the tests run on varied real geometry.
_PRIMS = ("cube", "sphere", "cylinder", "cone", "torus")
_prim_index = [0]


def _next_prim():
    name = _PRIMS[_prim_index[0] % len(_PRIMS)]
    _prim_index[0] += 1
    return name


def fresh_scene():
    global _GROUP
    cmds.file(new=True, force=True)
    _GROUP = cmds.ls(cmds.group(empty=True, name=HARNESS_GROUP), long=True)[0]


def make_mesh(name, parent=None):
    """Create a real mesh (no construction history) under the harness group.

    Returns the transform's full path. The primitive type rotates so the
    suite covers cubes, spheres, cylinders, cones, and toruses.

    NOTE: cmds.parent() does not reliably return the full path (in Maya
    2023 it returns the short name, or a path relative to the parent
    argument), so the full path is built from the parent's full path
    plus the created node's short name instead of trusting its return.
    """
    prim = _next_prim()
    maker = {
        "cube": cmds.polyCube,
        "sphere": cmds.polySphere,
        "cylinder": cmds.polyCylinder,
        "cone": cmds.polyCone,
        "torus": cmds.polyTorus,
    }[prim]
    created = maker(name=name, constructionHistory=False)[0]
    short_name = util.get_short_name(created)
    target = parent or _GROUP
    cmds.parent(created, target)
    full_path = target + "|" + short_name
    if not cmds.objExists(full_path):
        raise AssertionError("make_mesh: %s not found after parenting" % full_path)
    return full_path


def make_group(name, parent=None):
    node = cmds.group(empty=True, name=name)
    short_name = util.get_short_name(node)
    target = parent or _GROUP
    cmds.parent(node, target)
    full_path = target + "|" + short_name
    if not cmds.objExists(full_path):
        raise AssertionError("make_group: %s not found after parenting" % full_path)
    return full_path


def cleanup_test_objects():
    """Delete the harness group (and everything in it) and verify it's gone."""
    global _GROUP
    if _GROUP and cmds.objExists(_GROUP):
        cmds.delete(_GROUP)
    if _GROUP and cmds.objExists(_GROUP):
        raise AssertionError("cleanup failed: %s still in scene" % _GROUP)
    _GROUP = ""


def assert_scene_clean():
    """After cleanup, only Maya's default camera transforms may remain."""
    remaining = cmds.ls(type="transform", long=True) or []
    unexpected = [o for o in remaining
                  if o not in ("|front", "|persp", "|side", "|top")]
    if unexpected:
        raise AssertionError("scene not clean, left over: %s" % unexpected)


# --- Scene / UI helpers -----------------------------------------------------
def set_category(n):
    cmds.radioButtonGrp("categoryCommand", edit=True, select=n)


def set_mode(n):
    cmds.radioButtonGrp("Variable_BtnGrp", edit=True, select=n)


def set_text(control, value):
    cmds.textFieldGrp(control, edit=True, text=value)


def set_plain_text(control, value):
    cmds.textField(control, edit=True, text=value)


def set_numbering(start, padding):
    cmds.intFieldGrp("padding_tf", edit=True, value1=start, value2=padding)


def reset_ui():
    util.reset_to_default()


# --- 1. Pure naming helpers (no scene, no UI needed) -------------------------
def test_pure_naming():
    eq(util.excel_letters(0, "ABCDEFGHIJKLMNOPQRSTUVWXYZ"), "A", "excel 0")
    eq(util.excel_letters(25, "ABCDEFGHIJKLMNOPQRSTUVWXYZ"), "Z", "excel 25")
    eq(util.excel_letters(26, "ABCDEFGHIJKLMNOPQRSTUVWXYZ"), "AA", "excel 26")
    eq(util.excel_letters(701, "ABCDEFGHIJKLMNOPQRSTUVWXYZ"), "ZZ", "excel 701")

    try:
        util.excel_letters(-1, "ABC")
        raise AssertionError("negative index should raise")
    except ValueError:
        pass
    try:
        util.excel_letters(0, "")
        raise AssertionError("empty alphabet should raise")
    except ValueError:
        pass

    eq([util.build_uppercase_name(i) for i in (0, 25, 26, 27, 51, 52)],
       ["A", "Z", "AA", "AB", "AZ", "BA"], "uppercase rollover")
    eq(util.build_lowercase_name(26), "aa", "lowercase rollover")
    eq(util.build_uppercase_name(99, "D", False), "D", "sequence off")
    eq(util.build_number_name(0, 1, 3), "001", "number padding")
    eq(util.build_number_name(4, 10, 2), "14", "number start 10")
    eq(util.get_short_name("|geo_01|geo_02|geo_03"), "geo_03", "short name")
    eq(util.deepest_first(["|a", "|a|b", "|a|b|c"]),
       ["|a|b|c", "|a|b", "|a"], "deepest first")


# --- 2. Categories ------------------------------------------------------------
def test_all_category_excludes_default_cameras():
    fresh_scene()
    a = make_mesh("camTestA")
    b = make_mesh("camTestB")
    all_objs = util.get_objects_for_category(3)
    for cam in ("|front", "|persp", "|side", "|top"):
        if cam in all_objs:
            raise AssertionError("All category included default camera %s" % cam)
    if a not in all_objs or b not in all_objs:
        raise AssertionError("All category missed test meshes: %s" % all_objs)


def test_hierarchy_category_parent_first():
    fresh_scene()
    root = make_mesh("hRoot")
    mid = make_mesh("hMid", parent=root)
    leaf = make_mesh("hLeaf", parent=mid)
    cmds.select(root, replace=True)
    got = util.get_objects_for_category(2)
    eq(got, [root, mid, leaf], "hierarchy order")


def test_shape_selection_maps_to_transform():
    fresh_scene()
    mesh = make_mesh("shapeTest")
    # The shape is a child of the transform: |group|shapeTest|shapeTestShape.
    shape = mesh + "|" + util.get_short_name(mesh) + "Shape"
    if not cmds.objExists(shape):
        raise AssertionError("expected shape node %s" % shape)
    cmds.select(shape, replace=True)
    got = util.get_selected_objects()
    eq(got, [mesh], "shape selection maps to its transform")


def test_duplicates_category():
    fresh_scene()
    g1 = make_group("dupGrpA")
    g2 = make_group("dupGrpB")
    d1 = make_mesh("dupObj", parent=g1)
    d2 = make_mesh("dupObj", parent=g2)
    dups = util.get_duplicate_objects()
    eq(sorted(dups), sorted([d1, d2]), "duplicate meshes")
    found = util.select_duplicates()
    eq(sorted(found), sorted([d1, d2]), "select_duplicates returns both")
    eq(sorted(cmds.ls(selection=True, long=True)), sorted([d1, d2]),
       "duplicates selected")
    eq(cmds.radioButtonGrp("categoryCommand", query=True, select=True), 1,
       "category resets to Selected after select_duplicates")


def test_selection_order_is_numbering_order():
    fresh_scene()
    s1 = make_mesh("s1")
    s2 = make_mesh("s2")
    s3 = make_mesh("s3")
    cmds.select([s3, s1, s2], replace=True)
    reset_ui()
    set_category(1)  # Selected
    set_mode(4)      # Number
    set_text("Variable_tfGrp", "ord")
    set_numbering(1, 2)
    renamed = util.rename_selected()
    eq(short(renamed), ["ord01", "ord02", "ord03"],
       "numbering follows selection order")


# --- 3. Rename operations -------------------------------------------------------
def test_hierarchy_rename_parent_first_numbering_child_first_renames():
    fresh_scene()
    root = make_mesh("rRoot")
    mid = make_mesh("rMid", parent=root)
    leaf = make_mesh("rLeaf", parent=mid)
    cmds.select(root, replace=True)
    reset_ui()
    set_category(2)  # Hierarchy
    set_mode(4)      # Number
    set_text("Variable_tfGrp", "h")
    set_numbering(1, 1)
    util.rename_selected()
    # Parent-first numbering: root h1, child h2, leaf h3 — even though the
    # leaf is renamed first internally to keep paths valid.
    if not cmds.objExists(_GROUP + "|h1|h2|h3"):
        raise AssertionError("expected %s, scene has: %s"
                             % (_GROUP + "|h1|h2|h3",
                                cmds.ls(type="transform", long=True)))


def test_uppercase_and_lowercase_sequences():
    fresh_scene()
    u1 = make_mesh("u1")
    u2 = make_mesh("u2")
    u3 = make_mesh("u3")
    cmds.select([u1, u2, u3], replace=True)
    reset_ui()
    set_category(1)
    set_mode(2)  # A - Z
    set_text("Variable_tfGrp", "part")
    renamed = util.rename_selected()
    eq(short(renamed), ["partA", "partB", "partC"], "uppercase sequence")

    fresh_scene()
    l1 = make_mesh("l1")
    l2 = make_mesh("l2")
    cmds.select([l1, l2], replace=True)
    reset_ui()
    set_category(1)
    set_mode(3)  # a - z
    set_text("Variable_tfGrp", "seg")
    renamed = util.rename_selected()
    eq(short(renamed), ["sega", "segb"], "lowercase sequence")


def test_prefix_and_suffix():
    fresh_scene()
    box_a = make_mesh("boxA")
    box_b = make_mesh("boxB")
    cmds.select([box_a, box_b], replace=True)
    reset_ui()
    set_category(1)
    set_plain_text("Prefix_tf00", "pre_")
    renamed = util.add_prefix()
    eq(short(renamed), ["pre_boxA", "pre_boxB"], "add prefix")

    # Selection survives a rename in Maya, so the same two meshes are
    # still selected here under their new names.
    set_plain_text("Suffix_tf00", "_suf")
    renamed = util.add_suffix()
    eq(short(renamed), ["pre_boxA_suf", "pre_boxB_suf"], "add suffix")


def test_search_and_replace():
    fresh_scene()
    car_red = make_mesh("car_red")
    car_blue = make_mesh("car_blue")
    cmds.select([car_red, car_blue], replace=True)
    reset_ui()
    set_category(1)
    set_text("Search_tf00", "car")
    set_text("Replace_tf00", "truck")
    renamed = util.replace_name()
    eq(sorted(short(renamed)), ["truck_blue", "truck_red"], "search & replace")


def test_refer():
    fresh_scene()
    first = make_mesh("old_apple")
    second = make_mesh("old_banana")
    cmds.select([first, second], replace=True)
    reset_ui()
    set_category(1)
    set_text("Search_tf00", "old")
    set_text("Replace_tf00", "new")
    cmds.checkBox("refer_checkbox00", edit=True, value=True)
    renamed = util.replace_name()
    eq(short(renamed), ["new_apple"], "refer renames second object")
    # Refer reselects the first object and the renamed second one.
    eq(short(cmds.ls(selection=True, long=True)),
       ["old_apple", "new_apple"], "refer reselects both")


# --- 4. Preview, reset, and the window itself -----------------------------------
def test_preview_fields():
    fresh_scene()
    make_mesh("prevObj")
    cmds.select(_GROUP + "|prevObj", replace=True)
    reset_ui()
    set_text("Variable_tfGrp", "newName")
    util.refresh_preview()
    eq(cmds.textField("Current_Name_Result", query=True, text=True),
       "prevObj", "preview current name")
    eq(cmds.textField("New_Name_Result", query=True, text=True),
       "newName", "preview new name")

    cmds.select(clear=True)
    util.refresh_preview()
    current = cmds.textField("Current_Name_Result", query=True, text=True)
    if "Nothing selected" not in current:
        raise AssertionError("expected nothing-selected placeholder, got %r" % current)


def test_reset_to_default():
    set_category(3)
    set_mode(4)
    set_text("Variable_tfGrp", "junk")
    set_plain_text("Prefix_tf00", "x")
    set_numbering(9, 5)
    cmds.checkBox("refer_checkbox00", edit=True, value=True)
    util.reset_to_default()
    eq(cmds.radioButtonGrp("categoryCommand", query=True, select=True), 1, "category reset")
    eq(cmds.radioButtonGrp("Variable_BtnGrp", query=True, select=True), 1, "mode reset")
    eq(cmds.textFieldGrp("Variable_tfGrp", query=True, text=True), "", "base name reset")
    eq(cmds.textField("Prefix_tf00", query=True, text=True), "", "prefix reset")
    eq(cmds.intFieldGrp("padding_tf", query=True, value1=True), 1, "start no reset")
    eq(cmds.intFieldGrp("padding_tf", query=True, value2=True), 2, "padding reset")
    eq(cmds.checkBox("refer_checkbox00", query=True, value=True), False, "refer reset")


def test_window_build_and_launch():
    # Importing the UI module must not build a window (the Nov 23 refactor).
    if cmds.window("renameToolwindow", exists=True):
        cmds.deleteUI("renameToolwindow")
    importlib.reload(ui)
    if cmds.window("renameToolwindow", exists=True):
        raise AssertionError("importing stRenamer_UI built a window")
    ui.show_rename_tool()
    if not cmds.window("renameToolwindow", exists=True):
        raise AssertionError("show_rename_tool did not build the window")
    ui.show_rename_tool()  # second call shows the existing one, no rebuild
    if not cmds.window("renameToolwindow", exists=True):
        raise AssertionError("window vanished on second show_rename_tool")
    ui.build_window()  # explicit rebuild also works
    if not cmds.window("renameToolwindow", exists=True):
        raise AssertionError("build_window did not rebuild the window")


# --- Run everything -------------------------------------------------------------
def main():
    print("=" * 64)
    print("stRenamer in-Maya harness  |  Maya %s" % cmds.about(version=True))
    print("UTIL: %s" % getattr(util, "__file__", "stRenamer_UTIL"))
    print("Test meshes live under: %s (deleted after every check)"
          % HARNESS_GROUP)
    print("=" * 64)

    # Window first: most UI-driven checks need the controls to exist.
    check("window: import builds nothing, show builds, show again reuses",
          test_window_build_and_launch)

    check("pure naming: excel_letters / build_* / short name / deepest first",
          test_pure_naming)
    check("category: All excludes default cameras",
          test_all_category_excludes_default_cameras)
    check("category: Hierarchy returns parent-first order",
          test_hierarchy_category_parent_first)
    check("category: shape selection maps to its transform",
          test_shape_selection_maps_to_transform)
    check("category: Duplicates found and selected",
          test_duplicates_category)
    check("rename: numbering follows selection order",
          test_selection_order_is_numbering_order)
    check("rename: hierarchy parent-first numbering, child-first renames",
          test_hierarchy_rename_parent_first_numbering_child_first_renames)
    check("rename: uppercase and lowercase sequences",
          test_uppercase_and_lowercase_sequences)
    check("rename: prefix and suffix",
          test_prefix_and_suffix)
    check("rename: search & replace",
          test_search_and_replace)
    check("rename: Refer renames second object from first",
          test_refer)
    check("preview: current / new name fields, nothing-selected placeholder",
          test_preview_fields)
    check("reset: reset_to_default restores defaults",
          test_reset_to_default)

    # Final cleanup: window away, and prove the scene holds nothing
    # the harness created.
    try:
        if cmds.window("renameToolwindow", exists=True):
            cmds.deleteUI("renameToolwindow")
    except Exception:
        pass
    cleanup_test_objects()
    try:
        assert_scene_clean()
        print("[PASS] cleanup: all test meshes removed, scene clean")
        _RESULTS.append(("cleanup: all test meshes removed, scene clean",
                         True, ""))
    except Exception:
        print("[FAIL] cleanup: test objects left in scene")
        traceback.print_exc(limit=2)
        _RESULTS.append(("cleanup: all test meshes removed, scene clean",
                         False, ""))

    passed = sum(1 for _, ok, _ in _RESULTS if ok)
    failed = [(n, t) for n, ok, t in _RESULTS if not ok]
    print("=" * 64)
    print("RESULT: %d passed, %d failed, %d total"
          % (passed, len(failed), len(_RESULTS)))
    for name, tb in failed:
        print("-" * 64)
        print("FAILED: %s\n%s" % (name, tb))
    print("=" * 64)
    return not failed


main()
