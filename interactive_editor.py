# interactive_editor.py
import math
import streamlit as st
import matplotlib.pyplot as plt
import matplotlib.patches as patches


def _snap_value(value, snap_ft, enabled=True):
    if not enabled:
        return float(value)
    snap_ft = max(float(snap_ft), 0.01)
    return round(float(value) / snap_ft) * snap_ft


def _clamp_to_floor(x, y, floor_w, floor_h):
    x = max(0.0, min(float(floor_w), float(x)))
    y = max(0.0, min(float(floor_h), float(y)))
    return x, y


def _get_object_list(obj_type):
    if obj_type == "machine":
        return st.session_state.placed_machines
    if obj_type == "lighting":
        return st.session_state.placed_lighting
    return []


def _get_object_label(obj_type, obj, idx):
    obj_id = obj.get("id", f"{obj_type[:1].upper()}-{idx+1:03d}")

    if obj_type == "machine":
        make = str(obj.get("Make", "")).strip()
        model = str(obj.get("Model", "")).strip()
        suffix = f"{make} {model}".strip()
        return f"{obj_id} - {suffix}" if suffix else obj_id

    if obj_type == "lighting":
        make = str(obj.get("Make", "")).strip()
        fixture_type = str(obj.get("Type", "")).strip()
        suffix = f"{make} {fixture_type}".strip()
        return f"{obj_id} - {suffix}" if suffix else obj_id

    return obj_id


def _normalize_selected_index():
    obj_type = st.session_state.editor_selected_type
    items = _get_object_list(obj_type)

    if not items:
        st.session_state.editor_selected_index = 0
        return

    idx = int(st.session_state.get("editor_selected_index", 0))
    idx = max(0, min(idx, len(items) - 1))
    st.session_state.editor_selected_index = idx


def _get_selected_object():
    obj_type = st.session_state.editor_selected_type
    items = _get_object_list(obj_type)

    if not items:
        return None, None, None

    _normalize_selected_index()
    idx = int(st.session_state.editor_selected_index)
    return obj_type, idx, items[idx]


def _prime_editor_inputs_from_selection():
    """
    Safe pre-widget sync:
    populate widget-backed values only before widgets are instantiated.
    """
    result = _get_selected_object()
    if result == (None, None, None):
        st.session_state["editor_coord_x_input"] = 0.0
        st.session_state["editor_coord_y_input"] = 0.0
        return

    _, _, obj = result
    st.session_state["editor_coord_x_input"] = float(obj.get("x", 0.0))
    st.session_state["editor_coord_y_input"] = float(obj.get("y", 0.0))


def _set_selected_xy(new_x, new_y):
    result = _get_selected_object()
    if result == (None, None, None):
        st.session_state.editor_status_msg = "No object selected."
        return

    obj_type, idx, obj = result
    floor_w = float(st.session_state.floor_w)
    floor_h = float(st.session_state.floor_h)

    new_x = float(new_x)
    new_y = float(new_y)

    if st.session_state.editor_snap_enabled:
        new_x = _snap_value(new_x, st.session_state.editor_snap_ft, True)
        new_y = _snap_value(new_y, st.session_state.editor_snap_ft, True)

    new_x, new_y = _clamp_to_floor(new_x, new_y, floor_w, floor_h)

    obj["x"] = new_x
    obj["y"] = new_y

    st.session_state.editor_status_msg = (
        f"Moved {obj_type} {obj.get('id', idx)} to "
        f"X={new_x:.2f} ft, Y={new_y:.2f} ft."
    )


def apply_editor_coordinate_update():
    try:
        new_x = float(st.session_state.editor_coord_x_input)
        new_y = float(st.session_state.editor_coord_y_input)
    except Exception:
        st.session_state.editor_status_msg = "Invalid coordinate input."
        return

    _set_selected_xy(new_x, new_y)


def apply_editor_nudge(dx, dy):
    result = _get_selected_object()
    if result == (None, None, None):
        st.session_state.editor_status_msg = "No object selected."
        return

    _, _, obj = result
    cur_x = float(obj.get("x", 0.0))
  
