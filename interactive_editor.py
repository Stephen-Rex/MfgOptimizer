# interactive_editor.py
import math
import matplotlib.pyplot as plt
import numpy as np
import streamlit as st


def _snap_value(val, snap_ft, snap_enabled=True):
  if not snap_enabled or snap_ft <= 0:
    return float(val)
  return round(float(val) / float(snap_ft)) * float(snap_ft)


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


def apply_editor_nudge():
  obj_type = st.session_state.editor_selected_type
  idx = int(st.session_state.editor_selected_index)
  dx = float(st.session_state.editor_pending_dx_ft)
  dy = float(st.session_state.editor_pending_dy_ft)

  snap_enabled = bool(st.session_state.editor_snap_enabled)
  snap_ft = float(st.session_state.editor_snap_ft)

  objs = _get_object_list(obj_type)
  if not objs:
    st.session_state.editor_status_msg = "No objects available for editing."
    return

  if idx < 0 or idx >= len(objs):
    st.session_state.editor_status_msg = "Selected object index is out of range."
    return

  obj = objs[idx]

  if obj_type == "machine":
    new_x = _snap_value(float(obj["x"]) + dx, snap_ft, snap_enabled)
    new_y = _snap_value(float(obj["y"]) + dy, snap_ft, snap_enabled)
    new_x = min(max(new_x, 0.0), float(st.session_state.floor_w))
    new_y = min(max(new_y, 0.0), float(st.session_state.floor_h))
    obj["x"] = new_x
    obj["y"] = new_y
    st.session_state.editor_status_msg = (
        f"Moved machine M{idx+1} to ({new_x:.1f}, {new_y:.1f}) ft."
    )

  elif obj_type == "lighting":
    new_x = _snap_value(float(obj["x"]) + dx, snap_ft, snap_enabled)
    new_y = _snap_value(float(obj["y"]) + dy, snap_ft, snap_enabled)
    new_x = min(max(new_x, 0.0), float(st.session_state.floor_w))
    new_y = min(max(new_y, 0.0), float(st.session_state.floor_h))
    obj["x"] = new_x
    obj["y"] = new_y
    st.session_state.editor_status_msg = (
        f"Moved lighting L{idx+1} to ({new_x:.1f}, {new_y:.1f}) ft."
    )

  elif obj_type == "conduit":
    new_x = []
    new_y = []
    for x_val, y_val in zip(obj.get("x", []), obj.get("y", [])):
      nx = _snap_value(float(x_val) + dx, snap_ft, snap_enabled)
      ny = _snap_value(float(y_val) + dy, snap_ft, snap_enabled)
      nx = min(max(nx, 0.0), float(st.session_state.floor_w))
      ny = min(max(ny, 0.0), float(st.session_state.floor_h))
      new_x.append(nx)
      new_y.append(ny)
    obj["x"] = new_x
    obj["y"] = new_y
    st.session_state.editor_status_msg = (
        f"Shifted conduit CND{idx+1} by ({dx:.1f}, {dy:.1f}) ft."
    )

  elif obj_type == "crane":
    if all(k in obj for k in ["ll_x", "ll_y", "ur_x", "ur_y"]):
      ll_x = _snap_value(float(obj["ll_x"]) + dx, snap_ft, snap_enabled)
      ll_y = _snap_value(float(obj["ll_y"]) + dy, snap_ft, snap_enabled)
      ur_x = _snap_value(float(obj["ur_x"]) + dx, snap_ft, snap_enabled)
      ur_y = _snap_value(float(obj["ur_y"]) + dy, snap_ft, snap_enabled)

      ll_x = min(max(ll_x, 0.0), float(st.session_state.floor_w))
      ur_x = min(max(ur_x, 0.0), float(st.session_state.floor_w))
      ll_y = min(max(ll_y, 0.0), float(st.session_state.floor_h))
      ur_y = min(max(ur_y, 0.0), float(st.session_state.floor_h))

      obj["ll_x"] = min(ll_x, ur_x)
      obj["ur_x"] = max(ll_x, ur_x)
      obj["ll_y"] = min(ll_y, ur_y)
      obj["ur_y"] = max(ll_y, ur_y)

      st.session_state.editor_status_msg = (
          f"Shifted crane CR{idx+1} by ({dx:.1f}, {dy:.1f}) ft."
      )
    else:
      st.session_state.editor_status_msg = (
          "Crane editor currently supports ll_x/ll_y/ur_x/ur_y records only."
      )
  else:
    st.session_state.editor_status_msg = "Unsupported object type."

  st.session_state.editor_pending_dx_ft = 0.0
  st.session_state.editor_pending_dy_ft = 0.0


def render_interactive_editor_controls():
  st.subheader("Interactive 2D Editor Controls")
  st.markdown(
      "Phase 1 editor: select an object class, choose an object, and move it"
      " using controlled offsets. This establishes the state model for later"
      " drag-and-drop support."
  )

  col1, col2, col3 = st.columns(3)

  with col1:
    st.selectbox(
        "Object Type",
        ["machine", "lighting", "conduit", "crane"],
        key="editor_selected_type",
    )

  objs = _get_object_list(st.session_state.editor_selected_type)
  obj_options = list(range(len(objs))) if objs else [0]

  with col2:
    st.selectbox(
        "Selected Object",
        obj_options,
        format_func=lambda i: (
            _get_object_label(
                st.session_state.editor_selected_type, i, objs[i]
            ) if objs and i < len(objs) else "No objects available"
        ),
        key="editor_selected_index",
    )

  with col3:
    st.checkbox("Enable Grid Snap", key="editor_snap_enabled")
    st.number_input(
        "Snap Increment (ft)",
        min_value=0.1,
        max_value=20.0,
        step=0.1,
        key="editor_snap_ft",
    )

  dcol1, dcol2, dcol3 = st.columns(3)
  with dcol1:
    st.checkbox("Show Editor Grid", key="editor_show_grid")
  with dcol2:
    st.checkbox("Show Editor Labels", key="editor_show_labels")
  with dcol3:
    st.checkbox("Editor Mode Enabled", key="editor_enabled")

  ncol1, ncol2, ncol3 = st.columns([1, 1, 1])
  with ncol1:
    st.number_input(
        "Move ΔX (ft)",
        min_value=-100.0,
        max_value=100.0,
        step=0.5,
        key="editor_pending_dx_ft",
    )
  with ncol2:
    st.number_input(
        "Move ΔY (ft)",
        min_value=-100.0,
        max_value=100.0,
        step=0.5,
        key="editor_pending_dy_ft",
    )
  with ncol3:
    st.write("")
    st.write("")
    if st.button("Apply Move", type="primary", key="editor_apply_move_btn"):
      apply_editor_nudge()
      st.rerun() if hasattr(st, "rerun") else st.experimental_rerun()

  if st.session_state.editor_status_msg:
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
    w = float(m["Width"])
    h = float(m["Height"])
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
        s=90 if is_selected else 60,
        c="#FFD700" if not is_selected else "#FF8C00",
        edgecolors="black",
        zorder=4,
    )
    if st.session_state.editor_show_labels:
      ax.text(x + 1.0, y + 1.0, f"L{idx+1}", color="#FFD700", fontsize=8)

  # Conduits
  for idx, c in enumerate(st.session_state.placed_conduits):
    xs = [float(v) for v in c.get("x", [])]
    ys = [float(v) for v in c.get("y", [])]
    if len(xs) >= 2:
      is_selected = selected_type == "conduit" and idx == selected_idx
      ax.plot(
          xs,
          ys,
          color="#FFA500" if not is_selected else "#FF4040",
          lw=2.5 if is_selected else 2.0,
          zorder=2,
      )
      ax.scatter(xs, ys, c="white", s=20, zorder=3)
      if st.session_state.editor_show_labels:
        ax.text(xs[0], ys[0] + 2.0, f"CND{idx+1}", color="#FFA500", fontsize=8)

  # Cranes
  for idx, cr in enumerate(st.session_state.placed_cranes):
    if all(k in cr for k in ["ll_x", "ll_y", "ur_x", "ur_y"]):
      x0 = float(cr["ll_x"])
      y0 = float(cr["ll_y"])
      x1 = float(cr["ur_x"])
      y1 = float(cr["ur_y"])
      is_selected = selected_type == "crane" and idx == selected_idx

      rect = plt.Rectangle(
          (min(x0, x1), min(y0, y1)),
          abs(x1 - x0),
          abs(y1 - y0),
          fill=True,
          color="#999999" if not is_selected else "#FF66CC",
          alpha=0.25,
          edgecolor="#DDDDDD",
          lw=2 if is_selected else 1.2,
          linestyle="--",
          zorder=2,
      )
      ax.add_patch(rect)

      if st.session_state.editor_show_labels:
        ax.text(
            (x0 + x1) / 2.0,
            (y0 + y1) / 2.0,
            f"CR{idx+1}",
            color="white",
            fontsize=8,
            ha="center",
            va="center",
            zorder=3,
        )

  ax.set_xlim(-5, floor_w + 5)
  ax.set_ylim(-5, floor_h + 5)
  ax.set_aspect("equal")
  ax.set_xlabel("X (ft)", color="white")
  ax.set_ylabel("Y (ft)", color="white")
  ax.tick_params(colors="white")
  for spine in ax.spines.values():
    spine.set_color("white")

  ax.set_title("Interactive 2D Editor - Phase 1", color="white")
  return fig


def render_interactive_editor():
  render_interactive_editor_controls()
  fig = draw_interactive_editor_figure()
  st.pyplot(fig, use_container_width=True)
  st.caption(
      "Phase 1 note: this editor currently uses selection + offset movement."
      " Direct pointer drag/drop is planned for the next phase."
  )
