# interactive_editor.py
import math
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import streamlit as st


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

    return 0.0, 0.0


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

    # Defer widget-key update until next rerun
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

def _apply_pending_vertex_selection_if_any():
    pending_idx = st.session_state.get("editor_pending_vertex_index", None)
    if pending_idx is not None:
        st.session_state["editor_selected_vertex_index"] = int(pending_idx)
        st.session_state["editor_pending_vertex_index"] = None

def apply_delete_conduit_vertex():
    _delete_selected_conduit_vertex()
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
    st.session_state.editor_prime_inputs = True


def _on_selected_object_change():
    labels = st.session_state.get("editor_object_labels", [])
    selected_label = st.session_state.get("editor_selected_label_select", "")

    if selected_label in labels:
        st.session_state.editor_selected_index = labels.index(selected_label)
        st.session_state.editor_selected_vertex_index = 0
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
    selected_vertex_index = int(st.session_state.get("editor_selected_vertex_index", 0))

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

    with ctrl_col1:
        st.checkbox("Enable Editor", key="editor_enabled")

        st.selectbox(
            "Object Type",
            options=["machine", "lighting", "conduit", "crane"],
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
                    safe_vidx = _get_safe_selected_vertex_index()
                    vertex_options = list(range(point_count))
                    st.selectbox(
                        "Selected Conduit Vertex",
                        options=vertex_options,
                        index=safe_vidx,
                        format_func=lambda i: f"P{i+1}",
                        key="editor_selected_vertex_index",
                        on_change=_on_selected_vertex_change,
                    )

        st.checkbox("Snap to Grid", key="editor_snap_enabled")
        st.number_input(
            "Snap/Grid Increment (ft)",
            min_value=0.1,
            step=0.1,
            key="editor_snap_ft",
        )
        st.checkbox("Show Grid", key="editor_show_grid")
        st.checkbox("Show Labels", key="editor_show_labels")

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
                vidx = int(st.session_state.get("editor_selected_vertex_index", 0))
                if len(obj.get("x", [])) > vidx:
                    st.write(
                        f"**Selected Vertex:** P{vidx+1} "
                        f"({float(obj['x'][vidx]):.2f}, {float(obj['y'][vidx]):.2f})"
                    )


def render_interactive_editor():
    _apply_pending_vertex_selection_if_any()

    if st.session_state.get("editor_prime_inputs", True):
        _prime_editor_inputs_from_selection()
        st.session_state.editor_prime_inputs = False

    render_interactive_editor_controls()
    fig = draw_interactive_editor_figure()
    st.pyplot(fig, use_container_width=True)
