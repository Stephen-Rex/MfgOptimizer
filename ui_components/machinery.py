# ui_components/machinery.py
import streamlit as st


def render_machinery_tab(machinery_lib):
  m_col1, m_col2 = st.columns(2)
  with m_col1:
    st.subheader("🤖 Place Machine from Library")
    machine_options = [
        f"{m['Make']} {m['Model']} ({m['Type']})" for m in machinery_lib
    ]
    selected_m_idx = st.selectbox(
        "Choose Machine",
        range(len(machine_options)),
        format_func=lambda x: machine_options[x],
    )
    mx_coord = st.number_input(
        "Target Placement X (ft)",
        min_value=0.0,
        max_value=float(st.session_state.floor_w),
        value=70.0,
        key="mx_tab",
    )
    my_coord = st.number_input(
        "Target Placement Y (ft)",
        min_value=0.0,
        max_value=float(st.session_state.floor_h),
        value=50.0,
        key="my_tab",
    )

    if st.button("Drop Machine onto Floor", type="primary"):
      spec = machinery_lib[selected_m_idx].copy()
      spec["x"] = mx_coord
      spec["y"] = my_coord
      st.session_state.placed_machines.append(spec)
      st.success(
          f"Placed {spec['Make']} {spec['Model']} at ({mx_coord}, {my_coord})!"
      )
      st.rerun() if hasattr(st, "rerun") else st.experimental_rerun()

  with m_col2:
    if len(st.session_state.placed_machines) > 0:
      st.subheader("🛠️ Modify or Delete Placed Machinery")
      placed_options = [
          f"M{i+1}: {m['Make']} {m['Model']} at ({m['x']:.1f} ft, {m['y']:.1f}"
          " ft)"
          for i, m in enumerate(st.session_state.placed_machines)
      ]
      selected_placed_idx = st.selectbox(
          "Select Machine on Floor to Edit",
          range(len(placed_options)),
          format_func=lambda x: placed_options[x],
      )

      mach = st.session_state.placed_machines[selected_placed_idx]
      edit_x = st.number_input(
          "Adjust Coordinate X (ft)",
          min_value=0.0,
          max_value=float(st.session_state.floor_w),
          value=float(mach["x"]),
          key=f"edit_x_tab_{selected_placed_idx}",
      )
      edit_y = st.number_input(
          "Adjust Coordinate Y (ft)",
          min_value=0.0,
          max_value=float(st.session_state.floor_h),
          value=float(mach["y"]),
          key=f"edit_y_tab_{selected_placed_idx}",
      )

      btn_col1, btn_col2 = st.columns(2)
      with btn_col1:
        if st.button(
            "Update Position", key=f"update_m_btn_{selected_placed_idx}"
        ):
          st.session_state.placed_machines[selected_placed_idx]["x"] = edit_x
          st.session_state.placed_machines[selected_placed_idx]["y"] = edit_y
          st.success(f"Machine M{selected_placed_idx+1} moved successfully!")
          st.rerun() if hasattr(st, "rerun") else st.experimental_rerun()
      with btn_col2:
        if st.button(
            "Delete Machine", key=f"delete_m_btn_{selected_placed_idx}"
        ):
          removed = st.session_state.placed_machines.pop(selected_placed_idx)
          st.warning(
              f"Removed M{selected_placed_idx+1} ({removed['Make']}"
              f" {removed['Model']}) from layout."
          )
          st.rerun() if hasattr(st, "rerun") else st.experimental_rerun()
    else:
      st.info("No machines currently placed on the layout.")
