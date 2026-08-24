# interactive_editor.py
import matplotlib.pyplot as plt
import numpy as np
import streamlit as st


def _snap_value(val, snap_ft, snap_enabled=True):
    if not snap_enabled or snap_ft <= 0:
        return float(val)
    return round(float(val) / float(snap_ft)) * float(snap_ft)


def _clamp_to_floor(x, y):
    x = min(max(float(x), 0.0), float(st.session_state.floor_w))
    y = min(max(float(y), 0.0), float(st.session_state.floor_h))
    return x, y


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


def _get_object_label(obj_type, idx, obj):
    if obj_type == "machine":
        return f"M{idx+1}: {obj.get('Make', '')} {obj.get('Model', '')}"
    if obj_type == "lighting":
        return f"L{idx+1}: {obj.get('Make', '')} {obj.get('Brand', '')}"
    if obj_type == "conduit":
        return f"CND{idx+1}: {obj.get('label', 'Run')}"
    if obj_type == "crane":
        return f"CR{idx+1}: {obj.get('make', '')} {obj.get('model', '')}"
    return f"{obj_type} {idx+1}"


def _get_selected_object():
    obj_type = st.session_state.editor_selected_type
    idx = int(st.session_state.editor_selected_index)
    objs = _get_object_list(obj_type)

    if not objs:
        return obj_type, idx, None, objs
    if idx < 0 or idx >= len(objs):
        return obj_type, idx, None, objs

    return obj_type, idx, objs[idx], objs


def _set_selected_xy(x, y):
    obj_type, idx, obj, objs = _get_selected_object()
    if obj is None:
        st.session_state.editor_status_msg = "No selected object available."
        return

    if obj_type not in ["machine", "lighting"]:
        st.session_state.editor_status_msg = (
            "Direct coordinate editing is currently enabled for machines and lighting only."
        )
        return

    snap_enabled = bool(st.session_state.editor_snap_enabled)
    snap_ft = float(st.session_state.editor_snap_ft)

    x = _snap_value(x, snap_ft, snap_enabled)
    y = _snap_value(y, snap_ft, snap_enabled)
    x, y = _clamp_to_floor(x, y)

    obj["x"] = x
    obj["y"] = y

    if obj_type == "machine":
        st.session_state.editor_status_msg = (
            f"Updated machine M{idx+1} to ({x:.1f}, {y:.1f}) ft."
        )
    else:
        st.session_state.editor_status_msg = (
            f"Updated lighting L{idx+1} to ({x:.1f}, {y:.1f}) ft."
        )


def apply_editor_nudge(dx, dy):
    obj_type, idx, obj, objs = _get_selected_object()
    if obj is None:
        st.session_state.editor_status_msg = "No objects available for editing."
        return

    if obj_type not in ["machine", "lighting"]:
        st.session_state.editor_status_msg = (
            "Phase 2A nudge controls currently support machines and lighting only."
        )
        return

    new_x = float(obj["x"]) + float(dx)
    new_y = float(obj["y"]) + float(dy)
    _set_selected_xy(new_x, new_y)

    st.session_state.editor_clear_pending_move = True
    st.session_state.editor_clear_coord_inputs = True


def apply_editor_coordinate_update():
    x = float(st.session_state.get("editor_coord_x_input", 0.0))
    y = float(st.session_state.get("editor_coord_y_input", 0.0))
    _set_selected_xy(x, y)
    st.session_state.editor_clear_coord_inputs = True


def sync_selected_object_inputs():
    obj_type, idx, obj, objs = _get_selected_object()
    if obj is None:
        return

    if obj_type in ["machine", "lighting"]:
        st.session_state["editor_coord_x_input"] = float(obj.get("x", 0.0))
        st.session_state["editor_coord_y_input"] = float(obj.get("y", 0.0))


def render_interactive_editor_controls():
    if st.session_state.get("editor_clear_pending_move", False):
        st.session_state["editor_pending_dx_ft_input"] = 0.0
        st.session_state["editor_pending_dy_ft_input"] = 0.0
        st.session_state["editor_clear_pending_move"] = False

    st.subheader("Interactive 2D Editor Controls")
    st.markdown(
        "Phase 2A editor supports precise interactive editing for machines and "
        "lighting using selection, direct coordinate editing, and nudge controls."
    )

    top1, top2, top3, top4 = st.columns(4)

    with top1:
        st.selectbox(
            "Object Type",
            ["machine", "lighting"],
            key="editor_selected_type",
        )

    objs = _get_object_list(st.session_state.editor_selected_type)
    obj_options = list(range(len(objs))) if objs else [0]

    with top2:
        selected_idx_before = st.session_state.get("editor_selected_index", 0)
        st.selectbox(
            "Selected Object",
            obj_options,
            format_func=lambda i: (
                _get_object_label(
                    st.session_state.editor_selected_type, i, objs[i]
                )
                if objs and i < len(objs)
                else "No objects available"
            ),
            key="editor_selected_index",
        )

    with top3:
        st.checkbox("Enable Grid Snap", key="editor_snap_enabled")
        st.number_input(
            "Snap Increment (ft)",
            min_value=0.1,
            max_value=20.0,
            step=0.1,
            key="editor_snap_ft",
        )

    with top4:
        st.checkbox("Show Editor Grid", key="editor_show_grid")
        st.checkbox("Show Editor Labels", key="editor_show_labels")

    selected_idx_after = st.session_state.get("editor_selected_index", 0)
    if selected_idx_after != selected_idx_before or st.session_state.get(
        "editor_clear_coord_inputs", False
    ):
        sync_selected_object_inputs()
        st.session_state["editor_clear_coord_inputs"] = False

    obj_type, idx, obj, objs = _get_selected_object()

    st.markdown("### Selected Object Position")

    pos1, pos2, pos3 = st.columns([1, 1, 1])

    with pos1:
        st.number_input(
            "Selected X (ft)",
            min_value=0.0,
            max_value=float(st.session_state.floor_w),
            step=0.5,
            key="editor_coord_x_input",
        )

    with pos2:
        st.number_input(
            "Selected Y (ft)",
            min_value=0.0,
            max_value=float(st.session_state.floor_h),
            step=0.5,
            key="editor_coord_y_input",
        )

    with pos3:
        st.write("")
        st.write("")
        if st.button(
            "Apply Coordinates",
            type="primary",
            key="editor_apply_coord_btn",
        ):
            apply_editor_coordinate_update()
            st.rerun() if hasattr(st, "rerun") else st.experimental_rerun()

    st.markdown("### Nudge Controls")

    step_col1, step_col2 = st.columns([1, 3])
    with step_col1:
        st.number_input(
            "Nudge Step (ft)",
            min_value=0.1,
            max_value=25.0,
            step=0.1,
            key="editor_move_step_ft",
        )

    step_ft = float(st.session_state.editor_move_step_ft)

    nrow1 = st.columns([1, 1, 1])
    with nrow1[1]:
        if st.button("⬆️ Up", key="editor_nudge_up_btn"):
            apply_editor_nudge(0.0, step_ft)
            st.rerun() if hasattr(st, "rerun") else st.experimental_rerun()

    nrow2 = st.columns([1, 1, 1])
    with nrow2[0]:
        if st.button("⬅️ Left", key="editor_nudge_left_btn"):
            apply_editor_nudge(-step_ft, 0.0)
            st.rerun() if hasattr(st, "rerun") else st.experimental_rerun()
    with nrow2[1]:
        if st.button("⏺ Center Sync", key="editor_sync_btn"):
            sync_selected_object_inputs()
            st.session_state.editor_status_msg = "Coordinate inputs synced to selected object."
            st.rerun() if hasattr(st, "rerun") else st.experimental_rerun()
    with nrow2[2]:
        if st.button("➡️ Right", key="editor_nudge_right_btn"):
            apply_editor_nudge(step_ft, 0.0)
            st.rerun() if hasattr(st, "rerun") else st.experimental_rerun()

    nrow3 = st.columns([1, 1, 1])
    with nrow3[1]:
        if st.button("⬇️ Down", key="editor_nudge_down_btn"):
            apply_editor_nudge(0.0, -step_ft)
            st.rerun() if hasattr(st, "rerun") else st.experimental_rerun()

    if obj_type == "machine" and obj is not None:
        st.markdown("### Selected Machine Info")
        st.write(f"**Make/Model:** {obj.get('Make', '')} {obj.get('Model', '')}")
        st.write(
            f"**Footprint:** {float(obj.get('Width', 0.0)):.1f} ft x "
            f"{float(obj.get('Height', 0.0)):.1f} ft"
        )
        st.write(f"**Standoff:** {float(obj.get('Standoff', 0.0)):.1f} ft")

    elif obj_type == "lighting" and obj is not None:
        st.markdown("### Selected Lighting Info")
        st.write(f"**Fixture:** {obj.get('Make', '')} {obj.get('Brand', '')}")
        st.write(f"**Type:** {obj.get('Type', '')}")
        st.write(f"**Wattage:** {float(obj.get('Wattage', 0.0)):.1f} W")

    if st.session_state.get("editor_status_msg"):
        st.info(st.session_state.editor_status_msg)


def draw_interactive_editor_figure():
    floor_w = float(st.session_state.floor_w)
    floor_h = float(st.session_state.floor_h)

    fig, ax = plt.subplots(figsize=(10, 6.5))
    fig.patch.set_facecolor("#0B1E2D")
    ax.set_facecolor("#0B1E2D")

    # Floor boundary
    ax.plot(
        [0, floor_w, floor_w, 0, 0],
        [0, 0, floor_h, floor_h, 0],
        color="#39FF14",
        lw=2,
        zorder=1,
    )

    if st.session_state.editor_show_grid:
        for xg in np.arange(0, floor_w + 0.001, 10.0):
            ax.plot([xg, xg], [0, floor_h], color="#444444", lw=0.5, linestyle=":")
        for yg in np.arange(0, floor_h + 0.001, 10.0):
            ax.plot([0, floor_w], [yg, yg], color="#444444", lw=0.5, linestyle=":")

    selected_type = st.session_state.editor_selected_type
    selected_idx = int(st.session_state.editor_selected_index)

    # Machines
    for idx, m in enumerate(st.session_state.placed_machines):
        x = float(m["x"])
        y = float(m["y"])
        w = float(m.get("Width", 10.0))
        h = float(m.get("Height", 8.0))
        is_selected = selected_type == "machine" and idx == selected_idx

        rect = plt.Rectangle(
            (x - w / 2.0, y - h / 2.0),
            w,
            h,
            fill=True,
            color="#00A8E8" if not is_selected else "#FF6B6B",
            alpha=0.75,
            edgecolor="white",
            lw=2 if is_selected else 1,
            zorder=3,
        )
        ax.add_patch(rect)

        if st.session_state.editor_show_labels:
            ax.text(
                x,
                y,
                f"M{idx+1}",
                color="white",
                fontsize=8,
                ha="center",
                va="center",
                zorder=4,
            )

    # Lighting
    for idx, l in enumerate(st.session_state.placed_lighting):
        x = float(l["x"])
        y = float(l["y"])
        is_selected = selected_type == "lighting" and idx == selected_idx

        ax.scatter(
            [x],
            [y],
            s=120 if is_selected else 70,
            c="#FFD700" if not is_selected else "#FF8C00",
            edgecolors="black",
            zorder=4,
        )

        if st.session_state.editor_show_labels:
            ax.text(
                x + 1.0,
                y + 1.0,
                f"L{idx+1}",
                color="#FFD700",
                fontsize=8,
                zorder=5,
            )

    ax.set_xlim(-5, floor_w + 5)
    ax.set_ylim(-5, floor_h + 5)
    ax.set_aspect("equal")
    ax.set_xlabel("X (ft)", color="white")
    ax.set_ylabel("Y (ft)", color="white")
    ax.tick_params(colors="white")

    for spine in ax.spines.values():
        spine.set_color("white")

    ax.set_title("Interactive 2D Editor - Phase 2A", color="white")
    return fig


def render_interactive_editor():
    render_interactive_editor_controls()
    fig = draw_interactive_editor_figure()
    st.pyplot(fig, use_container_width=True)
    st.caption(
        "Phase 2A note: this editor now supports improved interactive editing "
        "for machines and lighting using direct coordinate edits and nudge "
        "controls. True pointer drag/drop requires a custom interactive canvas layer."
    )
