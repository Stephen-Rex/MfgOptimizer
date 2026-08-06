# ui_components/lighting.py
import streamlit as st


def render_lighting_tab(lighting_lib):
  l_col1, l_col2 = st.columns(2)
  with l_col1:
    st.subheader("💡 Place Light from Library")
    light_options = [
        f"{l['Make']} {l['Brand']} ({l['Type']})" for l in lighting_lib
    ]
    selected_l_idx = st.selectbox(
        "Choose Lighting Fixture",
        range(len(light_options)),
        format_func=lambda x: light_options[x],
        key="l_sel_tab",
    )
    lx_coord = st.number_input(
        "Placement X (ft)",
        min_value=0.0,
        max_value=float(st.session_state.floor_w),
        value=50.0,
        key="lx_tab",
    )
    ly_coord = st.number_input(
        "Placement Y (ft)",
        min_value=0.0,
        max_value=float(st.session_state.floor_h),
        value=80.0,
        key="ly_tab",
    )

    if st.button("Drop Light onto Floor", type="primary"):
      spec_l = lighting_lib[selected_l_idx].copy()
      spec_l["x"] = lx_coord
      spec_l["y"] = ly_coord
      st.session_state.placed_lighting.append(spec_l)
      st.success(f"Placed Lighting Fixture at ({lx_coord}, {ly_coord})!")
      st.rerun() if hasattr(st, "rerun") else st.experimental_rerun()

  with l_col2:
    if len(st.session_state.placed_lighting) > 0:
      st.subheader("🛠️ Modify or Delete Placed Lighting")
      placed_l_opts = [
          f"L{i+1}: {li['Make']} {li['Brand']} at ({li['x']:.1f} ft,"
          f" {li['y']:.1f} ft)"
          for i, li in enumerate(st.session_state.placed_lighting)
      ]
      selected_placed_l_idx = st.selectbox(
          "Select Light on Floor to Edit",
          range(len(placed_l_opts)),
          format_func=lambda x: placed_l_opts[x],
      )
      active_light = st.session_state.placed_lighting[selected_placed_l_idx]
      edit_lx = st.number_input(
          "Adjust Light Coordinate X (ft)",
          min_value=0.0,
          max_value=float(st.session_state.floor_w),
          value=float(active_light["x"]),
          key=f"elx_tab_{selected_placed_l_idx}",
      )
      edit_ly = st.number_input(
          "Adjust Light Coordinate Y (ft)",
          min_value=0.0,
          max_value=float(st.session_state.floor_h),
          value=float(active_light["y"]),
          key=f"ely_tab_{selected_placed_l_idx}",
      )

      l_btn_col1, l_btn_col2 = st.columns(2)
      with l_btn_col1:
        if st.button(
            "Update Light Position", key=f"up_l_tab_{selected_placed_l_idx}"
        ):
          st.session_state.placed_lighting[selected_placed_l_idx]["x"] = edit_lx
          st.session_state.placed_lighting[selected_placed_l_idx]["y"] = edit_ly
          st.success(f"Lighting L{selected_placed_l_idx+1} position updated!")
          st.rerun() if hasattr(st, "rerun") else st.experimental_rerun()
      with l_btn_col2:
        if st.button(
            "Delete Light Fixture", key=f"del_l_tab_{selected_placed_l_idx}"
        ):
          removed_light = st.session_state.placed_lighting.pop(
              selected_placed_l_idx
          )
          st.warning(
              f"Removed L{selected_placed_l_idx+1} ({removed_light['Make']}"
              f" {removed_light['Brand']})."
          )
          st.rerun() if hasattr(st, "rerun") else st.experimental_rerun()
    else:
      st.info("No lighting fixtures currently placed.")
