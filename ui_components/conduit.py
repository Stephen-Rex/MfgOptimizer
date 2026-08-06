# ui_components/conduit.py
import streamlit as st
from state_manager import parse_coords


def render_conduit_tab():
  c_col1, c_col2 = st.columns(2)
  with c_col1:
    st.subheader("🔌 Route Conduit Run (Polyline)")
    cx_lbl = st.text_input(
        "Conduit Run Label", "Sub-Station Hookup", key="cx_lbl_tab"
    )
    cx_x_str = st.text_input(
        "X Coordinates (comma separated)", "40.0, 120.0", key="cx_x_tab"
    )
    cx_y_str = st.text_input(
        "Y Coordinates (comma separated)", "80.0, 35.0", key="cx_y_tab"
    )
    cx_depth = st.number_input(
        "Trench Burial Depth (inches)",
        min_value=12,
        max_value=60,
        value=36,
        key="cx_depth_tab",
    )
    cx_tape = st.checkbox(
        "Contains Orange 4 mil Warning Tape", value=True, key="cx_tape_tab"
    )

    if st.button("Route Conduit Path", type="primary"):
      parsed_x = parse_coords(cx_x_str)
      parsed_y = parse_coords(cx_y_str)

      if (
          parsed_x is None
          or parsed_y is None
          or len(parsed_x) != len(parsed_y)
      ):
        st.error(
            "Error: Coordinates must be valid numeric values, and X and Y must"
            " contain matching point counts."
        )
      else:
        st.session_state.placed_conduits.append({
            "label": cx_lbl,
            "x": parsed_x,
            "y": parsed_y,
            "depth_in": cx_depth,
            "warning_tape": cx_tape,
        })
        st.success(f"Successfully routed conduit '{cx_lbl}'!")
        st.rerun() if hasattr(st, "rerun") else st.experimental_rerun()

  with c_col2:
    if len(st.session_state.placed_conduits) > 0:
      st.subheader("🛠️ Modify or Delete Placed Conduits")
      conduit_options = [
          f"{i+1}: {c['label']} ({len(c['x'])} points)"
          for i, c in enumerate(st.session_state.placed_conduits)
      ]
      selected_cond_idx = st.selectbox(
          "Select Conduit to Edit",
          range(len(conduit_options)),
          format_func=lambda x: conduit_options[x],
      )

      cond = st.session_state.placed_conduits[selected_cond_idx]
      edit_cx_lbl = st.text_input(
          "Edit Conduit Label", cond["label"], key=f"lbl_tab_{selected_cond_idx}"
      )
      edit_cx_x_str = st.text_input(
          "Edit X Coordinates",
          ", ".join(map(str, cond["x"])),
          key=f"cx_tab_{selected_cond_idx}",
      )
      edit_cx_y_str = st.text_input(
          "Edit Y Coordinates",
          ", ".join(map(str, cond["y"])),
          key=f"cy_tab_{selected_cond_idx}",
      )
      edit_cx_depth = st.number_input(
          "Edit Burial Depth (inches)",
          min_value=12,
          max_value=60,
          value=int(cond["depth_in"]),
          key=f"dp_tab_{selected_cond_idx}",
      )
      edit_cx_tape = st.checkbox(
          "Edit Warning Tape Status",
          value=cond["warning_tape"],
          key=f"tp_tab_{selected_cond_idx}",
      )

      c_btn_col1, c_btn_col2 = st.columns(2)
      with c_btn_col1:
        if st.button(
            "Update Conduit Run", key=f"up_c_tab_{selected_cond_idx}"
        ):
          up_x = parse_coords(edit_cx_x_str)
          up_y = parse_coords(edit_cx_y_str)
          if up_x is None or up_y is None or len(up_x) != len(up_y):
            st.error("Error: Coordinates must be valid numeric pairs.")
          else:
            st.session_state.placed_conduits[selected_cond_idx] = {
                "label": edit_cx_lbl,
                "x": up_x,
                "y": up_y,
                "depth_in": edit_cx_depth,
                "warning_tape": edit_cx_tape,
            }
            st.success("Conduit run updated successfully!")
            st.rerun() if hasattr(st, "rerun") else st.experimental_rerun()
      with c_btn_col2:
        if st.button(
            "Delete Conduit Run", key=f"del_c_tab_{selected_cond_idx}"
        ):
          removed_c = st.session_state.placed_conduits.pop(selected_cond_idx)
          st.warning(f"Removed conduit run '{removed_c['label']}'.")
          st.rerun() if hasattr(st, "rerun") else st.experimental_rerun()
    else:
      st.info("No conduits currently routed.")
