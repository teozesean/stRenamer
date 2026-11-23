# Maya Rename Tool

A Maya rename utility with a small UI and a separate module for scene and naming operations.

## Files

- [`Maya/stRenamer_UI.py`](Maya/stRenamer_UI.py) builds the window and connects UI events to the utility functions.
- [`Maya/stRenamer_UTIL.py`](Maya/stRenamer_UTIL.py) reads settings, finds target transforms, generates names, and renames scene nodes.

Keep the UI and utility files in the same Maya scripts folder because the UI imports `stRenamer_UTIL` by module name.

## Launch in Maya

Copy both Maya files into a scripts folder, then run:

```python
import importlib
import stRenamer_UTIL as rename_util
import stRenamer_UI as rename_ui

importlib.reload(rename_util)
importlib.reload(rename_ui)
rename_ui.show_rename_tool()
```

Importing or reloading the UI module no longer builds the window. `show_rename_tool()` builds it the first time (via `build_window()`) and shows the existing window on later calls, refreshing its preview either way.

## Hierarchy order

The Hierarchy category walks selected transform roots and their transform children in parent-first order. Sequence numbers follow that order, while Maya rename calls run child-first so renaming a parent does not invalidate the stored full paths of its descendants.

The All category reads transform nodes directly, excludes Maya's default cameras (`|front`, `|persp`, `|side`, and `|top`), and does not change the current selection.

## Review notes

See the [code review guide](Archive/Markdown/RenameTool_Code_Review.md) for the changes, remaining limitations, and examples of the structural and PEP 8 improvements.
