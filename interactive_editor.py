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
        if make or model:
            return f"{obj_id} - {make} {model}".strip()
        return obj_id

    if obj_type == "lighting":
        make = str(obj.get("Make", "")).strip()
        fixture_type = str(obj.get("Type", "")).strip()
        if make or fixture_type:
            return f"{obj_id} - {make} {fixture_type}".strip()
        return obj_id

    return obj_id


def _get_selected_object():
    obj_type = st.session_state.editor_selected_type
    items = _get_object_list(obj_type)

    if not items:
        return None, None, None

    idx = int(st.session_state.editor_selected_index)
    if idx < 0:
        idx = 0
    if idx >= len(items):
        idx = len(items) - 1
        st.session_state.editor_selected_index = idx

    return obj_type, idx, items[idx]


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

    st.session_state.editor_coord_x_input = float(new_x)
    st.session_state.editor_coord_y_input = float(new_y)

    st.session_state.editor_status_msg = (
        f"Moved {obj_type} {obj.get('id', idx)} to "
        f"X={new_x:.2f} ft, Y={new_y:.2f} ft."
    )


def apply_editor_nudge(dx, dy):
    result = _get_selected_object()
    if result == (None, None, None):
        st.session_state.editor_status_msg = "No object selected."
        return

    _, _, obj = result
    cur_x = float(obj.get("x", 0.0))
    cur_y = float(obj.get("y", 0.0))
    _set_selected_xy(cur_x + dx, cur_y + dy)


def apply_editor_coordinate_update():
    try:
        new_x = float(st.session_state.editor_coord_x_input)
        new_y = float(st.session_state.editor_coord_y_input)
        _set_selected_xy(new_x, new_y)
    except Exception:
        st.session_state.editor_status_msg = "Invalid coordinate input."


def sync_selected_object_inputs():
    result = _get_selected_object()
    if result == (None, None, None):
        return

    _, _, obj = result
    st.session_state.editor_coord_x_input = float(obj.get("x", 0.0))
    st.session_state.editor_coord_y_input = float(obj.get("y", 0.0))


def _object_center(obj_type, obj):
    if obj_type in ["machine", "lighting"]:
        return float(obj.get("x", 0.0)), float(obj.get("y", 0.0))
    return 0.0, 0.0


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

    st.session_state.editor_selected_type = obj_type
    st.session_state.editor_selected_index = best_idx
    sync_selected_object_inputs()

    sel_obj = items[best_idx]
    st.session_state.editor_status_msg = (
        f"Selected nearest {obj_type}: "
        f"{sel_obj.get('id', best_idx)} "
        f"at distance {best_dist:.2f} ft."
    )


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

    st.session_state.editor_pick_x_input = pick_x
    st.session_state.editor_pick_y_input = pick_y
    st.session_state.editor_last_pick_x = pick_x
    st.session_state.editor_last_pick_y = pick_y

    obj_type = st.session_state.editor_selected_type
    _select_nearest_object(obj_type, pick_x, pick_y)


def render_interactive_editor_controls():
    st.subheader("Interactive 2D Layout Editor Controls")

    ctrl_col1, ctrl_col2 = st.columns([1, 1])

    with ctrl_col1:
        st.checkbox(
            "Enable Editor",
            key="editor_enabled",
        )

        st.selectbox(
            "Object Type",
            options=["machine", "lighting"],
            key="editor_selected_type",
            on_change=sync_selected_object_inputs,
        )

        items = _get_object_list(st.session_state.editor_selected_type)
        if items:
            labels = [
                _get_object_label(st.session_state.editor_selected_type, obj, idx)
                for idx, obj in enumerate(items)
            ]

            current_idx = int(st.session_state.editor_selected_index)
            if current_idx >= len(labels):
                current_idx = 0
                st.session_state.editor_selected_index = 0

            selected_label = st.selectbox(
                "Selected Object",
                options=labels,
                index=current_idx,
                key="editor_selected_label_select",
            )
            st.session_state.editor_selected_index = labels.index(selected_label)
            sync_selected_object_inputs()
        else:
            st.info("No objects available for the selected type.")

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
        st.markdown("**Direct Coordinate Edit**")

        st.number_input(
            "Selected X (ft)",
            step=0.5,
            key="editor_coord_x_input",
        )
        st.number_input(
            "Selected Y (ft)",
            step=0.5,
            key="editor_coord_y_input",
        )

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
        st.number_input(
            "Pick X (ft)",
            step=0.5,
            key="editor_pick_x_input",
        )
        st.number_input(
            "Pick Y (ft)",
            step=0.5,
            key="editor_pick_y_input",
        )

        if st.button("Select Nearest Object", use_container_width=True):
            apply_pick_selection()

    status_msg = str(st.session_state.get("editor_status_msg", "")).strip()
    if status_msg:
        st.info(status_msg)

    result = _get_selected_object()
    if result != (None, None, None):
        obj_type, idx, obj = result
        with st.expander("Selected Object Details", expanded=True):
            st.write(f"**Type:** {obj_type}")
            st.write(f"**ID:** {obj.get('id', idx)}")
            st.write(f"**X:** {float(obj.get('x', 0.0)):.2f} ft")
            st.write(f"**Y:** {float(obj.get('y', 0.0)):.2f} ft")

            if obj_type == "machine":
                st.write(f"**Make:** {obj.get('Make', '')}")
                st.write(f"**Model:** {obj.get('Model', '')}")
                st.write(f"**Width:** {float(obj.get('Width', 0.0)):.2f} ft")
                st.write(f"**Height:** {float(obj.get('Height', 0.0)):.2f} ft")
                st.write(f"**Standoff:** {float(obj.get('Standoff', 0.0)):.2f} ft")

            elif obj_type == "lighting":
                st.write(f"**Make:** {obj.get('Make', '')}")
                st.write(f"**Type:** {obj.get('Type', '')}")
                st.write(f"**Wattage:** {obj.get('Wattage', '')}")
                st.write(f"**Lux Target:** {obj.get('LuxTarget', '')}")


def draw_interactive_editor_figure():
    floor_w = float(st.session_state.floor_w)
    floor_h = float(st.session_state.floor_h)

    fig, ax = plt.subplots(figsize=(12, 6.5))
    fig.patch.set_facecolor("#0B1E2D")
    ax.set_facecolor("#0B1E2D")

    # Floor boundary
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

    # Grid
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
            label = m.get("id", f"M-{idx+1:03d}")
            ax.text(
                mx,
                my,
                label,
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
            label = l.get("id", f"L-{idx+1:03d}")
            ax.text(
                lx + 1.0,
                ly + 1.0,
                label,
                color="gold" if not is_selected else "#00E5FF",
                fontsize=8,
                weight="bold",
                zorder=6,
            )

    # Pick marker
    if (
        "editor_last_pick_x" in st.session_state
        and "editor_last_pick_y" in st.session_state
    ):
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


def render_interactive_editor():
    render_interactive_editor_controls()

    fig = draw_interactive_editor_figure()
    st.pyplot(fig, use_container_width=True)
