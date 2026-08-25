# interactive_editor.py
import math
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import streamlit as st
from streamlit_plotly_events import plotly_events
from interactive_canvas import build_interactive_canvas_figure, apply_canvas_pick


def _snap_value(value, snap_ft, enabled=True):
    if not enabled:
        return float(value)
    snap_ft = max(float(snap_ft), 0.01)
    return round(float(value) / snap_ft) * snap_ft


def _clamp_to_floor(x, y, floor_w, floor_h):
    x = max(0.0, min(float(floor_w), float(x)))
    y = max(0.0, min(float(floor_h), float(y)))
    return x, y

def _clamp_conduit_to_floor(x_vals, y_vals, floor_w, floor_h):
    if not x_vals or not y_vals or len(x_vals) != len(y_vals):
        return x_vals, y_vals

    min_x = min(float(x) for x in x_vals)
    max_x = max(float(x) for x in x_vals)
    min_y = min(float(y) for y in y_vals)
    max_y = max(float(y) for y in y_vals)

    shift_x = 0.0
    shift_y = 0.0

    if min_x < 0.0:
        shift_x = -min_x
    elif max_x > floor_w:
        shift_x = floor_w - max_x

    if min_y < 0.0:
        shift_y = -min_y
    elif max_y > floor_h:
        shift_y = floor_h - max_y

    new_x = [float(x) + shift_x for x in x_vals]
    new_y = [float(y) + shift_y for y in y_vals]
    return new_x, new_y


def _clamp_crane_box(ll_x, ll_y, ur_x, ur_y, floor_w, floor_h):
    ll_x = float(ll_x)
    ll_y = float(ll_y)
    ur_x = float(ur_x)
    ur_y = float(ur_y)
    floor_w = float(floor_w)
    floor_h = float(floor_h)

    width = max(0.1, ur_x - ll_x)
    height = max(0.1, ur_y - ll_y)

    ll_x = max(0.0, min(ll_x, floor_w - width))
    ll_y = max(0.0, min(ll_y, floor_h - height))
    ur_x = ll_x + width
    ur_y = ll_y + height

    return ll_x, ll_y, ur_x, ur_y


def _get_object_list(obj_type):
    if obj_type == "machine":
        return st.session_state.placed_machines
    if obj_type == "lighting":
        return st.session_state.placed_lighting
    if obj_type == "conduit":
        return st.session_state.placed_conduits
    if obj_type == "crane":
        return st.session_state.placed_cranes
    if obj_type == "workflow":
        return [{"id": "WF-001"}] if len(st.session_state.path_points) > 0 else []
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

    if obj_type == "conduit":
        label = str(obj.get("label", "")).strip()
        points = len(obj.get("x", []))
        suffix = f"{label} ({points} pts)".strip()
        return f"{obj_id} - {suffix}" if suffix else obj_id

    if obj_type == "crane":
        make = str(obj.get("make", "")).strip()
        model = str(obj.get("model", "")).strip()
        suffix = f"{make} {model}".strip()
        return f"{obj_id} - {suffix}" if suffix else obj_id

    if obj_type == "workflow":
        return "WF-001 - Workflow Path"

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


def _object_center(obj_type, obj):
    if obj_type in ["machine", "lighting"]:
        return float(obj.get("x", 0.0)), float(obj.get("y", 0.0))

    if obj_type == "conduit":
        xs = [float(v) for v in obj.get("x", [])]
        ys = [float(v) for v in obj.get("y", [])]
        if xs and ys and len(xs) == len(ys):
            return sum(xs) / len(xs), sum(ys) / len(ys)
        return 0.0, 0.0

    if obj_type == "crane":
        ll_x = float(obj.get("ll_x", 0.0))
        ll_y = float(obj.get("ll_y", 0.0))
        ur_x = float(obj.get("ur_x", 0.0))
        ur_y = float(obj.get("ur_y", 0.0))
        return (ll_x + ur_x) / 2.0, (ll_y + ur_y) / 2.0

    if obj_type == "workflow":
        _normalize_workflow_df()
        df = _workflow_df()
        if len(df) > 0:
            xs = [float(v) for v in df["X Coordinate"].tolist()]
            ys = [float(v) for v in df["Y Coordinate"].tolist()]
            return sum(xs) / len(xs), sum(ys) / len(ys)
        return 0.0, 0.0

    return 0.0, 0.0

def prime_drag_drop_from_selection():
    result = _get_selected_object()
    if result == (None, None, None):
        return

    obj_type, idx, obj = result

    if obj_type in ["machine", "lighting"]:
        cx = float(obj.get("x", 0.0))
        cy = float(obj.get("y", 0.0))
    elif obj_type == "conduit":
        if st.session_state.get("editor_drag_mode", "object") == "conduit_vertex":
            vx = obj.get("x", [])
            vy = obj.get("y", [])
            if vx and vy and len(vx) == len(vy):
                vidx = _get_safe_selected_vertex_index()
                cx = float(vx[vidx])
                cy = float(vy[vidx])
            else:
                cx, cy = _object_center(obj_type, obj)
        else:
            cx, cy = _object_center(obj_type, obj)
    elif obj_type == "workflow":
        _normalize_workflow_df()
        wdf = st.session_state.path_points
        widx = _get_safe_workflow_point_index()
        cx = float(wdf.iloc[widx]["X Coordinate"])
        cy = float(wdf.iloc[widx]["Y Coordinate"])
    elif obj_type == "crane":
        cx = (float(obj.get("ll_x", 0.0)) + float(obj.get("ur_x", 0.0))) / 2.0
        cy = (float(obj.get("ll_y", 0.0)) + float(obj.get("ur_y", 0.0))) / 2.0
    else:
        return

    st.session_state.editor_drag_drop_x_ft = cx
    st.session_state.editor_drag_drop_y_ft = cy


def _get_safe_selected_vertex_index():
    result = _get_selected_object()
    if result == (None, None, None):
        return 0

    obj_type, _, obj = result
    if obj_type != "conduit":
        return 0

    point_count = len(obj.get("x", []))
    if point_count <= 0:
        return 0

    idx = int(st.session_state.get("editor_selected_vertex_index", 0))
    idx = max(0, min(idx, point_count - 1))
    return idx


def _apply_pending_vertex_selection_if_any():
    pending_idx = st.session_state.get("editor_pending_vertex_index", None)
    if pending_idx is not None:
        st.session_state["editor_selected_vertex_index"] = int(pending_idx)
        st.session_state["editor_pending_vertex_index"] = None


def _workflow_df():
    return st.session_state.path_points.copy()


def _workflow_point_count():
    df = _workflow_df()
    return len(df)


def _normalize_workflow_df():
    df = _workflow_df()

    expected_cols = [
        "Point",
        "X Coordinate",
        "Y Coordinate",
        "Safety Standoff (ft)",
        "Movement Speed",
    ]

    for col in expected_cols:
        if col not in df.columns:
            if col == "Point":
                df[col] = list(range(1, len(df) + 1))
            elif col == "Safety Standoff (ft)":
                df[col] = 5.0
            elif col == "Movement Speed":
                df[col] = 5.0
            else:
                df[col] = 0.0

    df = df[expected_cols].copy()
    df["Point"] = list(range(1, len(df) + 1))
    st.session_state.path_points = df


def _get_safe_workflow_point_index():
    _normalize_workflow_df()
    point_count = _workflow_point_count()
    if point_count <= 0:
        return 0

    idx = int(st.session_state.get("editor_workflow_selected_point_index", 0))
    idx = max(0, min(idx, point_count - 1))
    return idx


def _apply_pending_workflow_point_selection_if_any():
    pending_idx = st.session_state.get("editor_pending_workflow_point_index", None)
    if pending_idx is not None:
        st.session_state["editor_workflow_selected_point_index"] = int(pending_idx)
        st.session_state["editor_pending_workflow_point_index"] = None


def _prime_workflow_inputs_from_selection():
    _normalize_workflow_df()
    df = _workflow_df()

    if len(df) == 0:
        st.session_state["editor_workflow_x_input"] = 0.0
        st.session_state["editor_workflow_y_input"] = 0.0
        st.session_state["editor_workflow_standoff_input"] = 0.0
        st.session_state["editor_workflow_speed_input"] = 0.0
        return

    idx = _get_safe_workflow_point_index()

    st.session_state["editor_workflow_x_input"] = float(df.iloc[idx]["X Coordinate"])
    st.session_state["editor_workflow_y_input"] = float(df.iloc[idx]["Y Coordinate"])
    st.session_state["editor_workflow_standoff_input"] = float(
        df.iloc[idx]["Safety Standoff (ft)"]
    )
    st.session_state["editor_workflow_speed_input"] = float(
        df.iloc[idx]["Movement Speed"]
    )


def _prime_editor_inputs_from_selection():
    result = _get_selected_object()
    if result == (None, None, None):
        st.session_state["editor_coord_x_input"] = 0.0
        st.session_state["editor_coord_y_input"] = 0.0
        st.session_state["editor_box_ll_x_input"] = 0.0
        st.session_state["editor_box_ll_y_input"] = 0.0
        st.session_state["editor_box_ur_x_input"] = 0.0
        st.session_state["editor_box_ur_y_input"] = 0.0
        st.session_state["editor_vertex_x_input"] = 0.0
        st.session_state["editor_vertex_y_input"] = 0.0
        return

    obj_type, _, obj = result

    cx, cy = _object_center(obj_type, obj)
    st.session_state["editor_coord_x_input"] = float(cx)
    st.session_state["editor_coord_y_input"] = float(cy)

    if obj_type == "crane":
        st.session_state["editor_box_ll_x_input"] = float(obj.get("ll_x", 0.0))
        st.session_state["editor_box_ll_y_input"] = float(obj.get("ll_y", 0.0))
        st.session_state["editor_box_ur_x_input"] = float(obj.get("ur_x", 0.0))
        st.session_state["editor_box_ur_y_input"] = float(obj.get("ur_y", 0.0))

    if obj_type == "conduit":
        vx = obj.get("x", [])
        vy = obj.get("y", [])
        if vx and vy and len(vx) == len(vy):
            vidx = _get_safe_selected_vertex_index()
            st.session_state["editor_vertex_x_input"] = float(vx[vidx])
            st.session_state["editor_vertex_y_input"] = float(vy[vidx])
        else:
            st.session_state["editor_vertex_x_input"] = 0.0
            st.session_state["editor_vertex_y_input"] = 0.0

    if obj_type == "workflow":
        _prime_workflow_inputs_from_selection()


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

    if obj_type in ["machine", "lighting"]:
        new_x, new_y = _clamp_to_floor(new_x, new_y, floor_w, floor_h)
        obj["x"] = new_x
        obj["y"] = new_y
        st.session_state.editor_status_msg = (
            f"Moved {obj_type} {obj.get('id', idx)} to "
            f"X={new_x:.2f} ft, Y={new_y:.2f} ft."
        )
        return

    if obj_type == "conduit":
        old_cx, old_cy = _object_center(obj_type, obj)
        dx = new_x - old_cx
        dy = new_y - old_cy

        x_vals = [float(v) + dx for v in obj.get("x", [])]
        y_vals = [float(v) + dy for v in obj.get("y", [])]

        if st.session_state.editor_snap_enabled:
            x_vals = [_snap_value(v, st.session_state.editor_snap_ft, True) for v in x_vals]
            y_vals = [_snap_value(v, st.session_state.editor_snap_ft, True) for v in y_vals]

        x_vals, y_vals = _clamp_conduit_to_floor(x_vals, y_vals, floor_w, floor_h)
        obj["x"] = x_vals
        obj["y"] = y_vals

        new_cx, new_cy = _object_center(obj_type, obj)
        st.session_state.editor_status_msg = (
            f"Moved conduit {obj.get('id', idx)} to "
            f"center X={new_cx:.2f} ft, Y={new_cy:.2f} ft."
        )
        return

    if obj_type == "crane":
        ll_x = float(obj.get("ll_x", 0.0))
        ll_y = float(obj.get("ll_y", 0.0))
        ur_x = float(obj.get("ur_x", 0.0))
        ur_y = float(obj.get("ur_y", 0.0))

        old_cx = (ll_x + ur_x) / 2.0
        old_cy = (ll_y + ur_y) / 2.0
        dx = new_x - old_cx
        dy = new_y - old_cy

        ll_x += dx
        ll_y += dy
        ur_x += dx
        ur_y += dy

        if st.session_state.editor_snap_enabled:
            ll_x = _snap_value(ll_x, st.session_state.editor_snap_ft, True)
            ll_y = _snap_value(ll_y, st.session_state.editor_snap_ft, True)
            ur_x = _snap_value(ur_x, st.session_state.editor_snap_ft, True)
            ur_y = _snap_value(ur_y, st.session_state.editor_snap_ft, True)

        ll_x, ll_y, ur_x, ur_y = _clamp_crane_box(
            ll_x, ll_y, ur_x, ur_y, floor_w, floor_h
        )

        obj["ll_x"] = ll_x
        obj["ll_y"] = ll_y
        obj["ur_x"] = ur_x
        obj["ur_y"] = ur_y

        st.session_state.editor_status_msg = (
            f"Moved crane {obj.get('id', idx)} to "
            f"center X={(ll_x + ur_x)/2.0:.2f} ft, Y={(ll_y + ur_y)/2.0:.2f} ft."
        )
        return


def _set_selected_crane_box(ll_x, ll_y, ur_x, ur_y):
    result = _get_selected_object()
    if result == (None, None, None):
        st.session_state.editor_status_msg = "No object selected."
        return

    obj_type, idx, obj = result
    if obj_type != "crane":
        st.session_state.editor_status_msg = "Bounding box edit applies to cranes only."
        return

    floor_w = float(st.session_state.floor_w)
    floor_h = float(st.session_state.floor_h)

    ll_x = float(ll_x)
    ll_y = float(ll_y)
    ur_x = float(ur_x)
    ur_y = float(ur_y)

    if ur_x <= ll_x or ur_y <= ll_y:
        st.session_state.editor_status_msg = (
            "Invalid crane box: upper-right must be greater than lower-left."
        )
        return

    if st.session_state.editor_snap_enabled:
        ll_x = _snap_value(ll_x, st.session_state.editor_snap_ft, True)
        ll_y = _snap_value(ll_y, st.session_state.editor_snap_ft, True)
        ur_x = _snap_value(ur_x, st.session_state.editor_snap_ft, True)
        ur_y = _snap_value(ur_y, st.session_state.editor_snap_ft, True)

    ll_x, ll_y, ur_x, ur_y = _clamp_crane_box(ll_x, ll_y, ur_x, ur_y, floor_w, floor_h)

    obj["ll_x"] = ll_x
    obj["ll_y"] = ll_y
    obj["ur_x"] = ur_x
    obj["ur_y"] = ur_y

    st.session_state.editor_status_msg = (
        f"Updated crane {obj.get('id', idx)} bounding box."
    )


def _set_selected_conduit_vertex(new_x, new_y):
    result = _get_selected_object()
    if result == (None, None, None):
        st.session_state.editor_status_msg = "No conduit selected."
        return

    obj_type, idx, obj = result
    if obj_type != "conduit":
        st.session_state.editor_status_msg = "Vertex editing applies to conduits only."
        return

    x_vals = [float(v) for v in obj.get("x", [])]
    y_vals = [float(v) for v in obj.get("y", [])]

    if len(x_vals) < 2 or len(x_vals) != len(y_vals):
        st.session_state.editor_status_msg = "Selected conduit has invalid point data."
        return

    vidx = _get_safe_selected_vertex_index()

    floor_w = float(st.session_state.floor_w)
    floor_h = float(st.session_state.floor_h)

    new_x = float(new_x)
    new_y = float(new_y)

    if st.session_state.editor_snap_enabled:
        new_x = _snap_value(new_x, st.session_state.editor_snap_ft, True)
        new_y = _snap_value(new_y, st.session_state.editor_snap_ft, True)

    new_x, new_y = _clamp_to_floor(new_x, new_y, floor_w, floor_h)

    x_vals[vidx] = new_x
    y_vals[vidx] = new_y

    obj["x"] = x_vals
    obj["y"] = y_vals

    st.session_state.editor_status_msg = (
        f"Updated conduit vertex P{vidx+1} for {obj.get('id', idx)} "
        f"to X={new_x:.2f} ft, Y={new_y:.2f} ft."
    )


def _add_conduit_vertex_after_selected():
    result = _get_selected_object()
    if result == (None, None, None):
        st.session_state.editor_status_msg = "No conduit selected."
        return

    obj_type, idx, obj = result
    if obj_type != "conduit":
        st.session_state.editor_status_msg = "Vertex editing applies to conduits only."
        return

    x_vals = [float(v) for v in obj.get("x", [])]
    y_vals = [float(v) for v in obj.get("y", [])]

    if len(x_vals) < 2 or len(x_vals) != len(y_vals):
        st.session_state.editor_status_msg = "Selected conduit has invalid point data."
        return

    vidx = _get_safe_selected_vertex_index()

    if vidx < len(x_vals) - 1:
        new_x = (x_vals[vidx] + x_vals[vidx + 1]) / 2.0
        new_y = (y_vals[vidx] + y_vals[vidx + 1]) / 2.0
        insert_at = vidx + 1
    else:
        if len(x_vals) >= 2:
            dx = x_vals[-1] - x_vals[-2]
            dy = y_vals[-1] - y_vals[-2]
        else:
            dx = 5.0
            dy = 0.0
        new_x = x_vals[-1] + dx * 0.5
        new_y = y_vals[-1] + dy * 0.5
        insert_at = len(x_vals)

    floor_w = float(st.session_state.floor_w)
    floor_h = float(st.session_state.floor_h)

    if st.session_state.editor_snap_enabled:
        new_x = _snap_value(new_x, st.session_state.editor_snap_ft, True)
        new_y = _snap_value(new_y, st.session_state.editor_snap_ft, True)

    new_x, new_y = _clamp_to_floor(new_x, new_y, floor_w, floor_h)

    x_vals.insert(insert_at, new_x)
    y_vals.insert(insert_at, new_y)

    obj["x"] = x_vals
    obj["y"] = y_vals
    st.session_state.editor_pending_vertex_index = insert_at

    st.session_state.editor_status_msg = (
        f"Inserted conduit vertex P{insert_at+1} for {obj.get('id', idx)}."
    )


def _delete_selected_conduit_vertex():
    result = _get_selected_object()
    if result == (None, None, None):
        st.session_state.editor_status_msg = "No conduit selected."
        return

    obj_type, idx, obj = result
    if obj_type != "conduit":
        st.session_state.editor_status_msg = "Vertex editing applies to conduits only."
        return

    x_vals = [float(v) for v in obj.get("x", [])]
    y_vals = [float(v) for v in obj.get("y", [])]

    if len(x_vals) <= 2 or len(x_vals) != len(y_vals):
        st.session_state.editor_status_msg = (
            "Cannot delete vertex: a conduit must retain at least two points."
        )
        return

    vidx = _get_safe_selected_vertex_index()

    x_vals.pop(vidx)
    y_vals.pop(vidx)

    obj["x"] = x_vals
    obj["y"] = y_vals

    st.session_state.editor_pending_vertex_index = max(
        0, min(vidx, len(x_vals) - 1)
    )
    st.session_state.editor_status_msg = (
        f"Deleted conduit vertex P{vidx+1} for {obj.get('id', idx)}."
    )


def apply_editor_coordinate_update():
    try:
        new_x = float(st.session_state.editor_coord_x_input)
        new_y = float(st.session_state.editor_coord_y_input)
    except Exception:
        st.session_state.editor_status_msg = "Invalid coordinate input."
        return

    _set_selected_xy(new_x, new_y)
    st.session_state.editor_prime_inputs = True
    st.rerun()


def apply_editor_nudge(dx, dy):
    result = _get_selected_object()
    if result == (None, None, None):
        st.session_state.editor_status_msg = "No object selected."
        return

    obj_type, _, obj = result

    if obj_type == "workflow":
        apply_workflow_point_nudge(dx, dy)
        return

    cur_x, cur_y = _object_center(obj_type, obj)
    _set_selected_xy(cur_x + dx, cur_y + dy)
    st.session_state.editor_prime_inputs = True
    st.rerun()


def apply_crane_box_update():
    try:
        ll_x = float(st.session_state.editor_box_ll_x_input)
        ll_y = float(st.session_state.editor_box_ll_y_input)
        ur_x = float(st.session_state.editor_box_ur_x_input)
        ur_y = float(st.session_state.editor_box_ur_y_input)
    except Exception:
        st.session_state.editor_status_msg = "Invalid crane box input."
        return

    _set_selected_crane_box(ll_x, ll_y, ur_x, ur_y)
    st.session_state.editor_prime_inputs = True
    st.rerun()


def apply_conduit_vertex_update():
    try:
        vx = float(st.session_state.editor_vertex_x_input)
        vy = float(st.session_state.editor_vertex_y_input)
    except Exception:
        st.session_state.editor_status_msg = "Invalid conduit vertex input."
        return

    _set_selected_conduit_vertex(vx, vy)
    st.session_state.editor_prime_inputs = True
    st.rerun()


def apply_conduit_vertex_nudge(dx, dy):
    result = _get_selected_object()
    if result == (None, None, None):
        st.session_state.editor_status_msg = "No conduit selected."
        return

    obj_type, _, obj = result
    if obj_type != "conduit":
        st.session_state.editor_status_msg = "Vertex nudge applies to conduits only."
        return

    vidx = _get_safe_selected_vertex_index()
    x_vals = obj.get("x", [])
    y_vals = obj.get("y", [])
    if len(x_vals) <= vidx or len(y_vals) <= vidx:
        st.session_state.editor_status_msg = "Invalid conduit vertex selection."
        return

    vx = float(x_vals[vidx]) + dx
    vy = float(y_vals[vidx]) + dy
    _set_selected_conduit_vertex(vx, vy)
    st.session_state.editor_prime_inputs = True
    st.rerun()


def apply_add_conduit_vertex():
    _add_conduit_vertex_after_selected()
    st.session_state.editor_prime_inputs = True
    st.rerun()


def apply_delete_conduit_vertex():
    _delete_selected_conduit_vertex()
    st.session_state.editor_prime_inputs = True
    st.rerun()


def apply_workflow_point_update():
    _normalize_workflow_df()
    df = _workflow_df()

    if len(df) == 0:
        st.session_state.editor_status_msg = "No workflow points available."
        return

    try:
        x_val = float(st.session_state.editor_workflow_x_input)
        y_val = float(st.session_state.editor_workflow_y_input)
        standoff_val = float(st.session_state.editor_workflow_standoff_input)
        speed_val = float(st.session_state.editor_workflow_speed_input)
    except Exception:
        st.session_state.editor_status_msg = "Invalid workflow point input."
        return

    floor_w = float(st.session_state.floor_w)
    floor_h = float(st.session_state.floor_h)

    if st.session_state.editor_snap_enabled:
        x_val = _snap_value(x_val, st.session_state.editor_snap_ft, True)
        y_val = _snap_value(y_val, st.session_state.editor_snap_ft, True)

    x_val, y_val = _clamp_to_floor(x_val, y_val, floor_w, floor_h)
    standoff_val = max(0.0, standoff_val)
    speed_val = max(0.0, speed_val)

    idx = _get_safe_workflow_point_index()

    df.at[idx, "X Coordinate"] = x_val
    df.at[idx, "Y Coordinate"] = y_val
    df.at[idx, "Safety Standoff (ft)"] = standoff_val
    df.at[idx, "Movement Speed"] = speed_val
    df["Point"] = list(range(1, len(df) + 1))

    st.session_state.path_points = df
    st.session_state.editor_status_msg = (
        f"Updated workflow point W{idx+1} to "
        f"X={x_val:.2f} ft, Y={y_val:.2f} ft."
    )
    st.session_state.editor_prime_inputs = True
    st.rerun()


def apply_workflow_point_nudge(dx, dy):
    _normalize_workflow_df()
    df = _workflow_df()

    if len(df) == 0:
        st.session_state.editor_status_msg = "No workflow points available."
        return

    idx = _get_safe_workflow_point_index()

    cur_x = float(df.iloc[idx]["X Coordinate"])
    cur_y = float(df.iloc[idx]["Y Coordinate"])
    cur_s = float(df.iloc[idx]["Safety Standoff (ft)"])
    cur_v = float(df.iloc[idx]["Movement Speed"])

    new_x = cur_x + float(dx)
    new_y = cur_y + float(dy)

    floor_w = float(st.session_state.floor_w)
    floor_h = float(st.session_state.floor_h)

    if st.session_state.editor_snap_enabled:
        new_x = _snap_value(new_x, st.session_state.editor_snap_ft, True)
        new_y = _snap_value(new_y, st.session_state.editor_snap_ft, True)

    new_x, new_y = _clamp_to_floor(new_x, new_y, floor_w, floor_h)

    df.at[idx, "X Coordinate"] = new_x
    df.at[idx, "Y Coordinate"] = new_y
    df.at[idx, "Safety Standoff (ft)"] = max(0.0, cur_s)
    df.at[idx, "Movement Speed"] = max(0.0, cur_v)
    df["Point"] = list(range(1, len(df) + 1))

    st.session_state.path_points = df
    st.session_state.editor_status_msg = (
        f"Nudged workflow point W{idx+1} to "
        f"X={new_x:.2f} ft, Y={new_y:.2f} ft."
    )
    st.session_state.editor_prime_inputs = True
    st.rerun()


def apply_add_workflow_point():
    _normalize_workflow_df()
    df = _workflow_df()

    if len(df) == 0:
        new_row = {
            "Point": 1,
            "X Coordinate": 0.0,
            "Y Coordinate": 0.0,
            "Safety Standoff (ft)": 5.0,
            "Movement Speed": 5.0,
        }
        df = pd.DataFrame([new_row])
        st.session_state.path_points = df
        st.session_state.editor_pending_workflow_point_index = 0
        st.session_state.editor_status_msg = "Added first workflow point W1."
        st.session_state.editor_prime_inputs = True
        st.rerun()
        return

    idx = _get_safe_workflow_point_index()

    x1 = float(df.iloc[idx]["X Coordinate"])
    y1 = float(df.iloc[idx]["Y Coordinate"])
    s1 = float(df.iloc[idx]["Safety Standoff (ft)"])
    v1 = float(df.iloc[idx]["Movement Speed"])

    if idx < len(df) - 1:
        x2 = float(df.iloc[idx + 1]["X Coordinate"])
        y2 = float(df.iloc[idx + 1]["Y Coordinate"])
        s2 = float(df.iloc[idx + 1]["Safety Standoff (ft)"])
        v2 = float(df.iloc[idx + 1]["Movement Speed"])

        new_x = (x1 + x2) / 2.0
        new_y = (y1 + y2) / 2.0
        new_s = (s1 + s2) / 2.0
        new_v = (v1 + v2) / 2.0
        insert_at = idx + 1
    else:
        if len(df) >= 2:
            px = float(df.iloc[idx - 1]["X Coordinate"])
            py = float(df.iloc[idx - 1]["Y Coordinate"])
            dx = x1 - px
            dy = y1 - py
        else:
            dx = 10.0
            dy = 0.0

        new_x = x1 + dx * 0.5
        new_y = y1 + dy * 0.5
        new_s = s1
        new_v = v1
        insert_at = len(df)

    floor_w = float(st.session_state.floor_w)
    floor_h = float(st.session_state.floor_h)

    if st.session_state.editor_snap_enabled:
        new_x = _snap_value(new_x, st.session_state.editor_snap_ft, True)
        new_y = _snap_value(new_y, st.session_state.editor_snap_ft, True)

    new_x, new_y = _clamp_to_floor(new_x, new_y, floor_w, floor_h)

    top = df.iloc[:insert_at].copy()
    bottom = df.iloc[insert_at:].copy()

    new_row = pd.DataFrame([{
        "Point": 0,
        "X Coordinate": new_x,
        "Y Coordinate": new_y,
        "Safety Standoff (ft)": max(0.0, new_s),
        "Movement Speed": max(0.0, new_v),
    }])

    df = pd.concat([top, new_row, bottom], ignore_index=True)
    df["Point"] = list(range(1, len(df) + 1))

    st.session_state.path_points = df
    st.session_state.editor_pending_workflow_point_index = insert_at
    st.session_state.editor_status_msg = f"Inserted workflow point W{insert_at+1}."
    st.session_state.editor_prime_inputs = True
    st.rerun()


def apply_delete_workflow_point():
    _normalize_workflow_df()
    df = _workflow_df()

    if len(df) <= 2:
        st.session_state.editor_status_msg = (
            "Cannot delete workflow point: path must retain at least two points."
        )
        return

    idx = _get_safe_workflow_point_index()
    df = df.drop(df.index[idx]).reset_index(drop=True)
    df["Point"] = list(range(1, len(df) + 1))

    st.session_state.path_points = df
    st.session_state.editor_pending_workflow_point_index = max(
        0, min(idx, len(df) - 1)
    )
    st.session_state.editor_status_msg = f"Deleted workflow point W{idx+1}."
    st.session_state.editor_prime_inputs = True
    st.rerun()


def _select_nearest_object(obj_type, pick_x, pick_y):
    items = _get_object_list(obj_type)
    if not items:
        st.session_state.editor_status_msg = f"No {obj_type} objects available."
        return

    best_idx = None
    best_dist = None

    for idx, obj in enumerate(items):
        ox, oy = _object_center(obj_type, obj)
        d = math.sqrt((ox - pick_x) ** 2 + (oy - pick_y) ** 2)
        if best_dist is None or d < best_dist:
            best_dist = d
            best_idx = idx

    if best_idx is None:
        st.session_state.editor_status_msg = f"Could not select a {obj_type}."
        return

    st.session_state.editor_selected_index = best_idx
    st.session_state.editor_selected_vertex_index = 0
    st.session_state.editor_workflow_selected_point_index = 0
    sel_obj = items[best_idx]
    st.session_state.editor_status_msg = (
        f"Selected nearest {obj_type}: "
        f"{sel_obj.get('id', best_idx)} at distance {best_dist:.2f} ft."
    )
    st.session_state.editor_prime_inputs = True


def apply_pick_selection():
    try:
        pick_x = float(st.session_state.editor_pick_x_input)
        pick_y = float(st.session_state.editor_pick_y_input)
    except Exception:
        st.session_state.editor_status_msg = "Invalid pick coordinate input."
        return

    floor_w = float(st.session_state.floor_w)
    floor_h = float(st.session_state.floor_h)
    pick_x, pick_y = _clamp_to_floor(pick_x, pick_y, floor_w, floor_h)

    st.session_state.editor_last_pick_x = pick_x
    st.session_state.editor_last_pick_y = pick_y

    obj_type = st.session_state.editor_selected_type
    _select_nearest_object(obj_type, pick_x, pick_y)
    st.rerun()


def _on_object_type_change():
    st.session_state.editor_selected_index = 0
    st.session_state.editor_selected_vertex_index = 0
    st.session_state.editor_workflow_selected_point_index = 0
    st.session_state.editor_prime_inputs = True


def _on_selected_object_change():
    labels = st.session_state.get("editor_object_labels", [])
    selected_label = st.session_state.get("editor_selected_label_select", "")

    if selected_label in labels:
        st.session_state.editor_selected_index = labels.index(selected_label)
        st.session_state.editor_selected_vertex_index = 0
        st.session_state.editor_workflow_selected_point_index = 0
        st.session_state.editor_prime_inputs = True


def _on_selected_vertex_change():
    st.session_state.editor_prime_inputs = True


def draw_interactive_editor_figure():
    floor_w = float(st.session_state.floor_w)
    floor_h = float(st.session_state.floor_h)

    fig, ax = plt.subplots(figsize=(12, 6.5))
    fig.patch.set_facecolor("#0B1E2D")
    ax.set_facecolor("#0B1E2D")

    floor_rect = patches.Rectangle(
        (0, 0),
        floor_w,
        floor_h,
        fill=False,
        edgecolor="#39FF14",
        linewidth=2.0,
        zorder=2,
    )
    ax.add_patch(floor_rect)

    if st.session_state.editor_show_grid:
        grid_step = float(st.session_state.editor_snap_ft)
        if grid_step <= 0:
            grid_step = 1.0

        x = 0.0
        while x <= floor_w:
            ax.plot([x, x], [0, floor_h], color="#1F3B4D", lw=0.7, zorder=1)
            x += grid_step

        y = 0.0
        while y <= floor_h:
            ax.plot([0, floor_w], [y, y], color="#1F3B4D", lw=0.7, zorder=1)
            y += grid_step

    selected_type = st.session_state.editor_selected_type
    selected_index = int(st.session_state.editor_selected_index)
    selected_vertex_index = _get_safe_selected_vertex_index()

    # Conduits
    for idx, cond in enumerate(st.session_state.placed_conduits):
        xs = [float(v) for v in cond.get("x", [])]
        ys = [float(v) for v in cond.get("y", [])]
        if len(xs) >= 2 and len(xs) == len(ys):
            is_selected = selected_type == "conduit" and idx == selected_index
            ax.plot(
                xs,
                ys,
                color="#FFA500" if not is_selected else "#00E5FF",
                lw=2.0 if not is_selected else 3.0,
                zorder=3,
            )

            for p_idx, (px, py) in enumerate(zip(xs, ys)):
                is_sel_vertex = is_selected and p_idx == selected_vertex_index
                ax.scatter(
                    [px],
                    [py],
                    color="#FFD700" if not is_sel_vertex else "#FF00FF",
                    s=20 if not is_sel_vertex else 70,
                    zorder=4,
                    edgecolors="black",
                )
                if st.session_state.editor_show_labels:
                    ax.text(
                        px,
                        py + 1.0,
                        f"P{p_idx+1}",
                        color="white",
                        fontsize=7,
                        ha="center",
                        zorder=5,
                    )

            if st.session_state.editor_show_labels:
                cx, cy = _object_center("conduit", cond)
                ax.text(
                    cx,
                    cy,
                    cond.get("id", f"C-{idx+1:03d}"),
                    color="white",
                    fontsize=8,
                    weight="bold",
                    ha="center",
                    va="bottom",
                    zorder=5,
                )

    # Workflow path
    if "path_points" in st.session_state and len(st.session_state.path_points) >= 2:
        _normalize_workflow_df()
        wdf = _workflow_df()

        wx = [float(v) for v in wdf["X Coordinate"].tolist()]
        wy = [float(v) for v in wdf["Y Coordinate"].tolist()]

        ax.plot(
            wx,
            wy,
            color="#808080",
            lw=3.0,
            zorder=3,
        )

        selected_w_idx = _get_safe_workflow_point_index()

        for p_idx, (px, py) in enumerate(zip(wx, wy)):
            is_sel = (
                st.session_state.editor_selected_type == "workflow"
                and p_idx == selected_w_idx
            )
            ax.scatter(
                [px],
                [py],
                color="#FFD700" if not is_sel else "#FF00FF",
                s=25 if not is_sel else 75,
                zorder=4,
                edgecolors="black",
            )
            if st.session_state.editor_show_labels:
                ax.text(
                    px,
                    py + 1.0,
                    f"W{p_idx+1}",
                    color="white",
                    fontsize=7,
                    ha="center",
                    zorder=5,
                )

    # Cranes
    for idx, cr in enumerate(st.session_state.placed_cranes):
        ll_x = float(cr.get("ll_x", 0.0))
        ll_y = float(cr.get("ll_y", 0.0))
        ur_x = float(cr.get("ur_x", 0.0))
        ur_y = float(cr.get("ur_y", 0.0))

        is_selected = selected_type == "crane" and idx == selected_index

        rect = patches.Rectangle(
            (ll_x, ll_y),
            ur_x - ll_x,
            ur_y - ll_y,
            fill=True,
            facecolor="#A0A0A0",
            alpha=0.25 if not is_selected else 0.35,
            edgecolor="#D3D3D3" if not is_selected else "#FFD700",
            linewidth=1.5 if not is_selected else 2.5,
            linestyle="--",
            zorder=2,
        )
        ax.add_patch(rect)

        if st.session_state.editor_show_labels:
            cx, cy = _object_center("crane", cr)
            ax.text(
                cx,
                cy,
                cr.get("id", f"CR-{idx+1:03d}"),
                color="white",
                fontsize=8,
                weight="bold",
                ha="center",
                va="center",
                zorder=5,
            )

    # Machines
    for idx, m in enumerate(st.session_state.placed_machines):
        mx = float(m.get("x", 0.0))
        my = float(m.get("y", 0.0))
        mw = float(m.get("Width", 0.0))
        mh = float(m.get("Height", 0.0))
        so = float(m.get("Standoff", 0.0))

        is_selected = selected_type == "machine" and idx == selected_index

        rect = patches.Rectangle(
            (mx - mw / 2.0, my - mh / 2.0),
            mw,
            mh,
            facecolor="#87CEEB" if not is_selected else "#00E5FF",
            edgecolor="white" if not is_selected else "#FFD700",
            linewidth=1.5 if not is_selected else 2.5,
            alpha=0.9,
            zorder=4,
        )
        ax.add_patch(rect)

        standoff_circle = patches.Circle(
            (mx, my),
            radius=max(mw, mh) / 2.0 + so,
            fill=False,
            edgecolor="#FF6666" if not is_selected else "#FFD700",
            linestyle=":",
            linewidth=1.0 if not is_selected else 1.8,
            zorder=3,
        )
        ax.add_patch(standoff_circle)

        if st.session_state.editor_show_labels:
            ax.text(
                mx,
                my,
                m.get("id", f"M-{idx+1:03d}"),
                ha="center",
                va="center",
                color="white",
                fontsize=8,
                weight="bold",
                zorder=5,
            )

    # Lighting
    for idx, l in enumerate(st.session_state.placed_lighting):
        lx = float(l.get("x", 0.0))
        ly = float(l.get("y", 0.0))
        is_selected = selected_type == "lighting" and idx == selected_index

        ax.plot(
            lx,
            ly,
            marker="o",
            markersize=10 if not is_selected else 13,
            color="gold" if not is_selected else "#00E5FF",
            markeredgecolor="black" if not is_selected else "#FFD700",
            markeredgewidth=1.0 if not is_selected else 1.8,
            zorder=5,
        )

        if st.session_state.editor_show_labels:
            ax.text(
                lx + 1.0,
                ly + 1.0,
                l.get("id", f"L-{idx+1:03d}"),
                color="gold" if not is_selected else "#00E5FF",
                fontsize=8,
                weight="bold",
                zorder=6,
            )

    if "editor_last_pick_x" in st.session_state and "editor_last_pick_y" in st.session_state:
        px = float(st.session_state.editor_last_pick_x)
        py = float(st.session_state.editor_last_pick_y)
        ax.plot(
            px,
            py,
            marker="x",
            markersize=12,
            color="#FF00FF",
            markeredgewidth=2.0,
            zorder=7,
        )
        ax.text(
            px + 1.0,
            py + 1.0,
            "Pick",
            color="#FF00FF",
            fontsize=8,
            weight="bold",
            zorder=7,
        )

    ax.set_xlim(0, floor_w)
    ax.set_ylim(0, floor_h)
    ax.set_aspect("equal")
    ax.set_xlabel("X (ft)", color="white")
    ax.set_ylabel("Y (ft)", color="white")
    ax.tick_params(colors="white")

    for spine in ax.spines.values():
        spine.set_color("white")

    ax.set_title("Interactive 2D Layout Editor", color="white", fontsize=14)
    return fig


def render_interactive_editor_controls():
    st.subheader("Interactive 2D Layout Editor Controls")

    ctrl_col1, ctrl_col2 = st.columns([1, 1])

    st.markdown("### Phase 3 Canvas Selection")

    p3c1, p3c2, p3c3 = st.columns(3)

    with p3c1:
        st.selectbox(
            "Canvas Mode",
            options=["select", "move", "dim"],
            key="editor_canvas_mode",
        )

    with p3c2:
        st.checkbox("Enable Drag Mode", key="editor_drag_enabled")

    with p3c3:
        st.write("")
        st.write("")
        st.caption(
            "Phase 3A enables interactive canvas selection. "
            "Continuous drag will be layered in next."
        )

    pick_col1, pick_col2, pick_col3 = st.columns([1, 1, 1])

    with pick_col1:
        st.number_input(
            "Canvas Pick X (ft)",
            min_value=0.0,
            max_value=float(st.session_state.floor_w),
            step=0.1,
            key="editor_click_x_ft",
        )

    with pick_col2:
        st.number_input(
            "Canvas Pick Y (ft)",
            min_value=0.0,
            max_value=float(st.session_state.floor_h),
            step=0.1,
            key="editor_click_y_ft",
        )

    with pick_col3:
        st.write("")
        st.write("")
        if st.button("Select Nearest From Canvas Pick", key="editor_canvas_pick_btn"):
            apply_canvas_pick(
                st.session_state.editor_click_x_ft,
                st.session_state.editor_click_y_ft,
            )
            st.rerun()

    phase3_msg = st.session_state.get("editor_phase3_status", "")
    if phase3_msg:
        st.info(phase3_msg)    
    
    #####
    with ctrl_col1:
        st.checkbox("Enable Editor", key="editor_enabled")

        st.selectbox(
            "Object Type",
            options=["machine", "lighting", "conduit", "crane", "workflow"],
            key="editor_selected_type",
            on_change=_on_object_type_change,
        )

        items = _get_object_list(st.session_state.editor_selected_type)

        if items:
            labels = [
                _get_object_label(st.session_state.editor_selected_type, obj, idx)
                for idx, obj in enumerate(items)
            ]
            st.session_state.editor_object_labels = labels

            _normalize_selected_index()
            current_idx = int(st.session_state.editor_selected_index)

            st.selectbox(
                "Selected Object",
                options=labels,
                index=current_idx,
                key="editor_selected_label_select",
                on_change=_on_selected_object_change,
            )
        else:
            st.info("No objects available for the selected type.")

        if st.session_state.editor_selected_type == "conduit":
            result = _get_selected_object()
            if result != (None, None, None):
                _, _, cond = result
                point_count = len(cond.get("x", []))
                if point_count > 0:
                    vertex_options = list(range(point_count))
                    st.selectbox(
                        "Selected Conduit Vertex",
                        options=vertex_options,
                        index=_get_safe_selected_vertex_index(),
                        format_func=lambda i: f"P{i+1}",
                        key="editor_selected_vertex_index",
                        on_change=_on_selected_vertex_change,
                    )

        if st.session_state.editor_selected_type == "workflow":
            _normalize_workflow_df()
            point_count = _workflow_point_count()

            if point_count > 0:
                workflow_options = list(range(point_count))
                st.selectbox(
                    "Selected Workflow Point",
                    options=workflow_options,
                    index=_get_safe_workflow_point_index(),
                    format_func=lambda i: f"W{i+1}",
                    key="editor_workflow_selected_point_index",
                    on_change=lambda: st.session_state.update(
                        {"editor_prime_inputs": True}
                    ),
                )
            else:
                st.info("No workflow points available.")

        st.checkbox("Snap to Grid", key="editor_snap_enabled")
        st.number_input(
            "Snap/Grid Increment (ft)",
            min_value=0.1,
            step=0.1,
            key="editor_snap_ft",
        )
        st.checkbox("Show Grid", key="editor_show_grid")
        st.checkbox("Show Labels", key="editor_show_labels")

    st.markdown("### Phase 3B Drag / Drop Placement")

    d1, d2, d3 = st.columns(3)

    with d1:
        drag_mode_options = ["object"]
        if st.session_state.editor_selected_type == "conduit":
            drag_mode_options = ["object", "conduit_vertex"]
        elif st.session_state.editor_selected_type == "workflow":
            drag_mode_options = ["workflow_point"]
        elif st.session_state.editor_selected_type == "crane":
            drag_mode_options = ["object"]

        current_drag_mode = st.session_state.get("editor_drag_mode", drag_mode_options[0])
        if current_drag_mode not in drag_mode_options:
            current_drag_mode = drag_mode_options[0]

        st.selectbox(
            "Drag Target",
            options=drag_mode_options,
            index=drag_mode_options.index(current_drag_mode),
            key="editor_drag_mode",
        )

    with d2:
        st.number_input(
            "Drop X (ft)",
            min_value=0.0,
            max_value=float(st.session_state.floor_w),
            step=0.1,
            key="editor_drag_drop_x_ft",
        )

    with d3:
        st.number_input(
            "Drop Y (ft)",
            min_value=0.0,
            max_value=float(st.session_state.floor_h),
            step=0.1,
            key="editor_drag_drop_y_ft",
        )

    dd1, dd2, dd3 = st.columns(3)

    with dd1:
        if st.button("Arm Drag", use_container_width=True):
            arm_editor_drag()

    with dd2:
        if st.button("Apply Drop", use_container_width=True):
            apply_drag_drop()
            st.rerun()

    with dd3:
        if st.button("Cancel Drag", use_container_width=True):
            cancel_editor_drag()

    if st.session_state.get("editor_drag_armed", False):
        st.warning("Drag is armed. Next drop will move the selected target.")    





    
    with ctrl_col2:
        st.markdown("**Direct Coordinate Edit / Center Move**")
        st.number_input("Selected X / Center X (ft)", step=0.5, key="editor_coord_x_input")
        st.number_input("Selected Y / Center Y (ft)", step=0.5, key="editor_coord_y_input")

        if st.button("Apply Coordinates", use_container_width=True):
            apply_editor_coordinate_update()

        st.markdown("**Nudge Selected Object**")
        st.number_input(
            "Nudge Step (ft)",
            min_value=0.1,
            step=0.1,
            key="editor_move_step_ft",
        )

        n1, n2, n3 = st.columns(3)
        with n2:
            if st.button("⬆ Up", use_container_width=True):
                apply_editor_nudge(0.0, float(st.session_state.editor_move_step_ft))
        with n1:
            if st.button("⬅ Left", use_container_width=True):
                apply_editor_nudge(-float(st.session_state.editor_move_step_ft), 0.0)
        with n2:
            if st.button("⬇ Down", use_container_width=True):
                apply_editor_nudge(0.0, -float(st.session_state.editor_move_step_ft))
        with n3:
            if st.button("➡ Right", use_container_width=True):
                apply_editor_nudge(float(st.session_state.editor_move_step_ft), 0.0)

        st.markdown("**Pick Nearest Object by Floor Coordinate**")
        st.number_input("Pick X (ft)", step=0.5, key="editor_pick_x_input")
        st.number_input("Pick Y (ft)", step=0.5, key="editor_pick_y_input")

        if st.button("Select Nearest Object", use_container_width=True):
            apply_pick_selection()

        if st.session_state.editor_selected_type == "crane":
            st.markdown("**Crane Bounding Box Edit**")
            st.number_input("Lower Left X (ft)", step=0.5, key="editor_box_ll_x_input")
            st.number_input("Lower Left Y (ft)", step=0.5, key="editor_box_ll_y_input")
            st.number_input("Upper Right X (ft)", step=0.5, key="editor_box_ur_x_input")
            st.number_input("Upper Right Y (ft)", step=0.5, key="editor_box_ur_y_input")

            if st.button("Apply Crane Box", use_container_width=True):
                apply_crane_box_update()

        if st.session_state.editor_selected_type == "conduit":
            st.markdown("**Conduit Vertex Edit**")
            st.number_input("Vertex X (ft)", step=0.5, key="editor_vertex_x_input")
            st.number_input("Vertex Y (ft)", step=0.5, key="editor_vertex_y_input")

            if st.button("Apply Vertex Coordinates", use_container_width=True):
                apply_conduit_vertex_update()

            st.markdown("**Nudge Selected Vertex**")
            v1, v2, v3 = st.columns(3)
            with v2:
                if st.button("⬆ Vertex Up", use_container_width=True):
                    apply_conduit_vertex_nudge(0.0, float(st.session_state.editor_move_step_ft))
            with v1:
                if st.button("⬅ Vertex Left", use_container_width=True):
                    apply_conduit_vertex_nudge(-float(st.session_state.editor_move_step_ft), 0.0)
            with v2:
                if st.button("⬇ Vertex Down", use_container_width=True):
                    apply_conduit_vertex_nudge(0.0, -float(st.session_state.editor_move_step_ft))
            with v3:
                if st.button("➡ Vertex Right", use_container_width=True):
                    apply_conduit_vertex_nudge(float(st.session_state.editor_move_step_ft), 0.0)

            a1, a2 = st.columns(2)
            with a1:
                if st.button("Add Vertex After Selected", use_container_width=True):
                    apply_add_conduit_vertex()
            with a2:
                if st.button("Delete Selected Vertex", use_container_width=True):
                    apply_delete_conduit_vertex()

        if st.session_state.editor_selected_type == "workflow":
            st.markdown("**Workflow Point Edit**")
            st.number_input("Workflow X (ft)", step=0.5, key="editor_workflow_x_input")
            st.number_input("Workflow Y (ft)", step=0.5, key="editor_workflow_y_input")
            st.number_input(
                "Workflow Safety Standoff (ft)",
                min_value=0.0,
                step=0.5,
                key="editor_workflow_standoff_input",
            )
            st.number_input(
                "Workflow Movement Speed",
                min_value=0.0,
                step=0.5,
                key="editor_workflow_speed_input",
            )

            if st.button("Apply Workflow Point", use_container_width=True):
                apply_workflow_point_update()

            wf_a1, wf_a2 = st.columns(2)
            with wf_a1:
                if st.button("Add Workflow Point After Selected", use_container_width=True):
                    apply_add_workflow_point()
            with wf_a2:
                if st.button("Delete Selected Workflow Point", use_container_width=True):
                    apply_delete_workflow_point()

    status_msg = str(st.session_state.get("editor_status_msg", "")).strip()
    if status_msg:
        st.info(status_msg)

    result = _get_selected_object()
    if result != (None, None, None):
        obj_type, idx, obj = result
        with st.expander("Selected Object Details", expanded=True):
            st.write(f"**Type:** {obj_type}")
            st.write(f"**ID:** {obj.get('id', idx)}")

            cx, cy = _object_center(obj_type, obj)
            st.write(f"**Center X:** {cx:.2f} ft")
            st.write(f"**Center Y:** {cy:.2f} ft")

            if obj_type == "crane":
                st.write(
                    f"**LL:** ({float(obj.get('ll_x', 0.0)):.2f}, "
                    f"{float(obj.get('ll_y', 0.0)):.2f})"
                )
                st.write(
                    f"**UR:** ({float(obj.get('ur_x', 0.0)):.2f}, "
                    f"{float(obj.get('ur_y', 0.0)):.2f})"
                )

            if obj_type == "conduit":
                st.write(f"**Points:** {len(obj.get('x', []))}")
                vidx = _get_safe_selected_vertex_index()
                if len(obj.get("x", [])) > vidx:
                    st.write(
                        f"**Selected Vertex:** P{vidx+1} "
                        f"({float(obj['x'][vidx]):.2f}, {float(obj['y'][vidx]):.2f})"
                    )

            if obj_type == "workflow":
                _normalize_workflow_df()
                wdf = _workflow_df()
                if len(wdf) > 0:
                    widx = _get_safe_workflow_point_index()
                    st.write(f"**Points:** {len(wdf)}")
                    st.write(
                        f"**Selected Point:** W{widx+1} "
                        f"({float(wdf.iloc[widx]['X Coordinate']):.2f}, "
                        f"{float(wdf.iloc[widx]['Y Coordinate']):.2f})"
                    )
                    st.write(
                        f"**Standoff:** "
                        f"{float(wdf.iloc[widx]['Safety Standoff (ft)']):.2f} ft"
                    )
                    st.write(
                        f"**Movement Speed:** "
                        f"{float(wdf.iloc[widx]['Movement Speed']):.2f}"
                    )

def _apply_pending_canvas_selection_if_any():
    pending_type = st.session_state.get("editor_pending_selected_type", None)
    pending_index = st.session_state.get("editor_pending_selected_index", None)
    pending_vertex = st.session_state.get("editor_pending_selected_vertex_index", None)
    pending_workflow_point = st.session_state.get("editor_pending_workflow_selected_point_index", None)
    pending_status = st.session_state.get("editor_pending_phase3_status", None)

    if pending_type is None and pending_index is None:
        return

    if pending_type is not None:
        st.session_state.editor_phase3_status = (
            f"Pending selected type was {pending_type}, but assignment was skipped for debug."
        )

    if pending_index is not None:
        st.session_state.editor_selected_index = int(pending_index)

    if pending_vertex is not None:
        st.session_state.editor_selected_vertex_index = int(pending_vertex)

    if pending_workflow_point is not None:
        st.session_state.editor_workflow_selected_point_index = int(pending_workflow_point)

    if pending_status is not None:
        st.session_state.editor_phase3_status = str(pending_status)

    st.session_state.editor_prime_inputs = True

    st.session_state.editor_pending_selected_type = None
    st.session_state.editor_pending_selected_index = None
    st.session_state.editor_pending_selected_vertex_index = None
    st.session_state.editor_pending_workflow_selected_point_index = None
    st.session_state.editor_pending_phase3_status = None


def render_interactive_editor():
    _apply_pending_canvas_selection_if_any()
    _apply_pending_vertex_selection_if_any()
    _apply_pending_workflow_point_selection_if_any()

    if st.session_state.get("editor_prime_inputs", True):
        _prime_editor_inputs_from_selection()
        _prime_workflow_inputs_from_selection()
        st.session_state.editor_prime_inputs = False

    render_interactive_editor_controls()

    # Phase 3C: remove legacy Matplotlib editor surface from visible workflow
    fig = build_interactive_canvas_figure()
    selected_points = plotly_events(
        fig,
        click_event=True,
        hover_event=False,
        select_event=False,
        override_height=650,
        override_width="100%",
        key=f"interactive_canvas_events_{st.session_state.get('editor_canvas_refresh_token', 0)}",
    )

    if selected_points:
        _apply_canvas_click_selection(selected_points)
        if st.session_state.get("editor_drag_armed", False):
            _apply_canvas_click_to_drop(selected_points)
        st.rerun()

    st.caption(
        "Phase 3 canvas: click objects to select them directly. "
    )

    phase3_msg = st.session_state.get("editor_phase3_status", "")
    if phase3_msg:
        st.info(phase3_msg)  

def arm_editor_drag():
    st.session_state.editor_drag_armed = True
    st.session_state.editor_phase3_status = "Drag armed. Select a drop point to place the selected item."

def cancel_editor_drag():
    st.session_state.editor_drag_armed = False
    st.session_state.editor_phase3_status = "Drag cancelled."

def _set_selected_conduit_vertex_xy(new_x, new_y):
    result = _get_selected_object()
    if result == (None, None, None):
        st.session_state.editor_status_msg = "No conduit selected."
        return

    obj_type, idx, obj = result
    if obj_type != "conduit":
        st.session_state.editor_status_msg = "Selected object is not a conduit."
        return

    floor_w = float(st.session_state.floor_w)
    floor_h = float(st.session_state.floor_h)

    new_x = float(new_x)
    new_y = float(new_y)

    if st.session_state.editor_snap_enabled:
        new_x = _snap_value(new_x, st.session_state.editor_snap_ft, True)
        new_y = _snap_value(new_y, st.session_state.editor_snap_ft, True)

    new_x, new_y = _clamp_to_floor(new_x, new_y, floor_w, floor_h)

    vx = list(obj.get("x", []))
    vy = list(obj.get("y", []))

    if not vx or not vy or len(vx) != len(vy):
        st.session_state.editor_status_msg = "Selected conduit has invalid geometry."
        return

    vidx = _get_safe_selected_vertex_index()
    vx[vidx] = float(new_x)
    vy[vidx] = float(new_y)

    obj["x"] = vx
    obj["y"] = vy
    st.session_state.editor_status_msg = (
        f"Moved conduit vertex P{vidx+1} to X={new_x:.2f} ft, Y={new_y:.2f} ft."
    )
    st.session_state.editor_prime_inputs = True

def _set_selected_workflow_point_xy(new_x, new_y):
    _normalize_workflow_df()

    if "path_points" not in st.session_state or len(st.session_state.path_points) == 0:
        st.session_state.editor_status_msg = "No workflow path available."
        return

    floor_w = float(st.session_state.floor_w)
    floor_h = float(st.session_state.floor_h)

    new_x = float(new_x)
    new_y = float(new_y)

    if st.session_state.editor_snap_enabled:
        new_x = _snap_value(new_x, st.session_state.editor_snap_ft, True)
        new_y = _snap_value(new_y, st.session_state.editor_snap_ft, True)

    new_x, new_y = _clamp_to_floor(new_x, new_y, floor_w, floor_h)

    wdf = st.session_state.path_points.copy()
    widx = _get_safe_workflow_point_index()

    wdf.at[widx, "X Coordinate"] = float(new_x)
    wdf.at[widx, "Y Coordinate"] = float(new_y)

    st.session_state.path_points = wdf
    st.session_state.editor_status_msg = (
        f"Moved workflow point W{widx+1} to X={new_x:.2f} ft, Y={new_y:.2f} ft."
    )
    st.session_state.editor_prime_inputs = True

def _set_selected_crane_center_xy(new_x, new_y):
    result = _get_selected_object()
    if result == (None, None, None):
        st.session_state.editor_status_msg = "No crane selected."
        return

    obj_type, idx, obj = result
    if obj_type != "crane":
        st.session_state.editor_status_msg = "Selected object is not a crane."
        return

    floor_w = float(st.session_state.floor_w)
    floor_h = float(st.session_state.floor_h)

    ll_x = float(obj.get("ll_x", 0.0))
    ll_y = float(obj.get("ll_y", 0.0))
    ur_x = float(obj.get("ur_x", 0.0))
    ur_y = float(obj.get("ur_y", 0.0))

    width = ur_x - ll_x
    height = ur_y - ll_y

    new_x = float(new_x)
    new_y = float(new_y)

    if st.session_state.editor_snap_enabled:
        new_x = _snap_value(new_x, st.session_state.editor_snap_ft, True)
        new_y = _snap_value(new_y, st.session_state.editor_snap_ft, True)

    new_ll_x = new_x - width / 2.0
    new_ll_y = new_y - height / 2.0

    new_ll_x = max(0.0, min(new_ll_x, floor_w - width))
    new_ll_y = max(0.0, min(new_ll_y, floor_h - height))

    obj["ll_x"] = new_ll_x
    obj["ll_y"] = new_ll_y
    obj["ur_x"] = new_ll_x + width
    obj["ur_y"] = new_ll_y + height

    st.session_state.editor_status_msg = (
        f"Moved crane to center X={new_x:.2f} ft, Y={new_y:.2f} ft."
    )
    st.session_state.editor_prime_inputs = True

def apply_drag_drop():
    if not st.session_state.get("editor_drag_armed", False):
        st.session_state.editor_phase3_status = "Drag is not armed."
        return

    drop_x = float(st.session_state.editor_drag_drop_x_ft)
    drop_y = float(st.session_state.editor_drag_drop_y_ft)

    obj_type = st.session_state.get("editor_selected_type", "machine")
    drag_mode = st.session_state.get("editor_drag_mode", "object")

    if obj_type in ["machine", "lighting"] and drag_mode == "object":
        _set_selected_xy(drop_x, drop_y)

    elif obj_type == "conduit":
        if drag_mode == "conduit_vertex":
            _set_selected_conduit_vertex_xy(drop_x, drop_y)
        else:
            _set_selected_xy(drop_x, drop_y)

    elif obj_type == "workflow":
        _set_selected_workflow_point_xy(drop_x, drop_y)

    elif obj_type == "crane":
        _set_selected_crane_center_xy(drop_x, drop_y)

    else:
        st.session_state.editor_status_msg = "Unsupported drag target."

    st.session_state.editor_drag_armed = False
    st.session_state.editor_phase3_status = "Drop applied."


def _apply_canvas_click_selection(point_data):
    if not point_data:
        return

    clicked = point_data[0]

    customdata = clicked.get("customdata", None)
    x_val = clicked.get("x", None)
    y_val = clicked.get("y", None)
    curve_number = clicked.get("curveNumber", None)

    if x_val is not None:
        st.session_state.editor_last_pick_x = float(x_val)
    if y_val is not None:
        st.session_state.editor_last_pick_y = float(y_val)

    entity_type = None
    obj_index = None
    sub_index = -1

    if customdata and len(customdata) >= 4:
        entity_type = str(customdata[0])
        obj_index = int(customdata[1])
        sub_index = int(customdata[3])

    elif curve_number is not None:
        trace_map = st.session_state.get("editor_trace_map", [])
        try:
            curve_idx = int(curve_number)
        except Exception:
            curve_idx = -1

        if 0 <= curve_idx < len(trace_map):
            trace_info = trace_map[curve_idx]
            entity_type = str(trace_info.get("entity_type", ""))
            obj_index = int(trace_info.get("obj_index", 0))
            sub_index = int(trace_info.get("sub_index", -1))

    if entity_type is None or obj_index is None:
        if x_val is not None and y_val is not None:
            apply_canvas_pick(float(x_val), float(y_val))
            st.session_state.editor_phase3_status = (
                f"Canvas metadata missing; fallback used at "
                f"X={float(x_val):.2f}, Y={float(y_val):.2f}. "
                f"Raw click: {clicked}"
            )
        else:
            st.session_state.editor_phase3_status = (
                f"Canvas click missing metadata and coordinates. Raw click: {clicked}"
            )
        return

    if entity_type == "pick_marker":
        st.session_state.editor_phase3_status = "Clicked pick marker."
        return

    pending_type = None
    pending_index = 0
    pending_vertex = 0
    pending_workflow_point = 0
    pending_status = ""

    if entity_type == "machine":
        pending_type = "machine"
        pending_index = obj_index
        pending_vertex = 0
        pending_workflow_point = 0
        pending_status = f"Canvas selected machine {obj_index}."

    elif entity_type == "lighting":
        pending_type = "lighting"
        pending_index = obj_index
        pending_vertex = 0
        pending_workflow_point = 0
        pending_status = f"Canvas selected lighting {obj_index}."

    elif entity_type == "conduit":
        pending_type = "conduit"
        pending_index = obj_index
        pending_vertex = 0
        pending_workflow_point = 0
        pending_status = f"Canvas selected conduit {obj_index}."

    elif entity_type == "conduit_vertex":
        pending_type = "conduit"
        pending_index = obj_index
        pending_vertex = sub_index
        pending_workflow_point = 0
        pending_status = f"Canvas selected conduit {obj_index} vertex {sub_index}."

    elif entity_type == "workflow":
        pending_type = "workflow"
        pending_index = 0
        pending_vertex = 0
        pending_workflow_point = max(sub_index, 0) if sub_index >= 0 else 0
        pending_status = "Canvas selected workflow."

    elif entity_type == "workflow_point":
        pending_type = "workflow"
        pending_index = 0
        pending_vertex = 0
        pending_workflow_point = sub_index
        pending_status = f"Canvas selected workflow point {sub_index}."

    elif entity_type == "crane":
        pending_type = "crane"
        pending_index = obj_index
        pending_vertex = 0
        pending_workflow_point = 0
        pending_status = f"Canvas selected crane {obj_index}."

    else:
        if x_val is not None and y_val is not None:
            apply_canvas_pick(float(x_val), float(y_val))
            st.session_state.editor_phase3_status = (
                f"Unknown trace entity '{entity_type}'; used nearest-object fallback "
                f"at X={float(x_val):.2f}, Y={float(y_val):.2f}."
            )
        else:
            st.session_state.editor_phase3_status = (
                f"Canvas click received unknown entity type: {entity_type}"
            )
        return

    st.session_state.editor_pending_selected_type = pending_type
    st.session_state.editor_pending_selected_index = pending_index
    st.session_state.editor_pending_selected_vertex_index = pending_vertex
    st.session_state.editor_pending_workflow_selected_point_index = pending_workflow_point
    st.session_state.editor_pending_phase3_status = pending_status
    st.session_state.editor_canvas_refresh_token += 1
    

def _apply_canvas_click_to_drop(point_data):
    if not point_data:
        return

    clicked = point_data[0]
    x_val = clicked.get("x", None)
    y_val = clicked.get("y", None)

    if x_val is None or y_val is None:
        return

    floor_w = float(st.session_state.floor_w)
    floor_h = float(st.session_state.floor_h)

    x_val, y_val = _clamp_to_floor(float(x_val), float(y_val), floor_w, floor_h)

    st.session_state.editor_drag_drop_x_ft = x_val
    st.session_state.editor_drag_drop_y_ft = y_val
    st.session_state.editor_last_pick_x = x_val
    st.session_state.editor_last_pick_y = y_val
    st.session_state.editor_phase3_status = (
        f"Drop target set to X={x_val:.2f} ft, Y={y_val:.2f} ft."
    )
