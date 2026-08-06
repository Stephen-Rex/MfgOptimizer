# ui_components/crane.py
import streamlit as st
from state_manager import on_crane_select_change


def render_crane_tab(crane_lib):
  crane_col1, crane_col2 = st.columns(2)

  with crane_col1:
    st.subheader("🏗️ Add Overhead Crane Coverage Area")
    st.markdown(
        "Select a crane model from the default library to auto-populate"
        " specifications, then define the 2 corner points (Lower Left & Upper"
        " Right) for the coverage area."
    )

    crane_lib_options = [
        f"{c['Make']} {c['Model']} ({c['MaxLiftWeight']} T Max Weight)"
        for c in crane_lib
    ]
    st.selectbox(
        "Choose Crane Model from Library",
        range(len(crane_lib_options)),
        format_func=lambda x: crane_lib_options[x],
        key="crane_lib_select_add",
        on_change=lambda: on_crane_select_change(crane_lib),
    )

    crane_make = st.text_input("Crane Make", key="crane_make_add")
    crane_model = st.text_input("Crane Model", key="crane_model_add")

    specs_col1, specs_col2, specs_col3 = st.columns(3)
    with specs_col1:
      crane_lift_wt = st.number_input(
          "Max Lift Weight (tons)",
          min_value=0.5,
          max_value=200.0,
          step=0.5,
          key="crane_wt_add",
      )
    with specs_col2:
      crane_lift_sp = st.number_input(
          "Max Lift Speed (ft/min)",
          min_value=1.0,
          max_value=200.0,
          step=1.0,
          key="crane_lsp_add",
      )
    with specs_col3:
      crane_trans_sp = st.number_input(
          "Max Transversal Speed (ft/min)",
          min_value=1.0,
          max_value=500.0,
          step=5.0,
          key="crane_tsp_add",
      )

    st.markdown("##### 📍 Define Rectangular Coverage Corner Points (ft)")
    ll_col1, ll_col2 = st.columns(2)
    with ll_col1:
      ll_x_val = st.number_input(
          "Lower Left X (ft)", value=20.0, key="crane_ll_x_add"
      )
    with ll_col2:
      ll_y_val = st.number_input(
          "Lower Left Y (ft)", value=20.0, key="crane_ll_y_add"
      )

    ur_col1, ur_col2 = st.columns(2)
    with ur_col1:
      ur_x_val = st.number_input(
          "Upper Right X (ft)", value=180.0, key="crane_ur_x_add"
      )
    with ur_col2:
      ur_y_val = st.number_input(
          "Upper Right Y (ft)", value=80.0, key="crane_ur_y_add"
      )

    if st.button("Add Crane Coverage to Floor", type="primary"):
      new_crane = {
          "make": crane_make,
          "model": crane_model,
          "max_lift_weight": crane_lift_wt,
          "max_lift_speed": crane_lift_sp,
          "max_transversal_speed": crane_trans_sp,
          "ll_x": ll_x_val,
          "ll_y": ll_y_val,
          "ur_x": ur_x_val,
          "ur_y": ur_y_val,
      }
      st.session_state.placed_cranes.append(new_crane)
      st.success(
          f"Added Crane C{len(st.session_state.placed_cranes)} ({crane_make}"
          f" {crane_model}) coverage area!"
      )
      st.rerun() if hasattr(st, "rerun") else st.experimental_rerun()

  with crane_col2:
    st.subheader("🛠️ Edit or Delete Placed Cranes")
    if len(st.session_state.placed_cranes) > 0:
      crane_opts = [
          f"C{i+1}: {c.get('make', 'Crane')} {c.get('model', '')}"
          f" ({c.get('max_lift_weight', 0)} T)"
          for i, c in enumerate(st.session_state.placed_cranes)
      ]
      selected_crane_idx = st.selectbox(
          "Select Crane to Modify",
          range(len(crane_opts)),
          format_func=lambda x: crane_opts[x],
          key="edit_crane_select",
      )

      c_edit = st.session_state.placed_cranes[selected_crane_idx]

      e_make = st.text_input(
          "Edit Make",
          c_edit.get("make", ""),
          key=f"e_cr_make_{selected_crane_idx}",
      )
      e_model = st.text_input(
          "Edit Model",
          c_edit.get("model", ""),
          key=f"e_cr_model_{selected_crane_idx}",
      )

      e_col1, e_col2, e_col3 = st.columns(3)
      with e_col1:
        e_wt = st.number_input(
            "Max Weight (T)",
            value=float(c_edit.get("max_lift_weight", 10.0)),
            key=f"e_cr_wt_{selected_crane_idx}",
        )
      with e_col2:
        e_lsp = st.number_input(
            "Lift Speed (ft/min)",
            value=float(c_edit.get("max_lift_speed", 25.0)),
            key=f"e_cr_lsp_{selected_crane_idx}",
        )
      with e_col3:
        e_tsp = st.number_input(
            "Transversal Speed",
            value=float(c_edit.get("max_transversal_speed", 120.0)),
            key=f"e_cr_tsp_{selected_crane_idx}",
        )

      st.markdown("##### 📍 Edit Corner Coordinates (ft)")
      ell_col1, ell_col2 = st.columns(2)
      with ell_col1:
        e_ll_x = st.number_input(
            "Lower Left X (ft)",
            value=float(c_edit.get("ll_x", c_edit.get("x1", 20.0))),
            key=f"e_cr_ll_x_{selected_crane_idx}",
        )
      with ell_col2:
        e_ll_y = st.number_input(
            "Lower Left Y (ft)",
            value=float(c_edit.get("ll_y", c_edit.get("y1", 20.0))),
            key=f"e_cr_ll_y_{selected_crane_idx}",
        )

      eur_col1, eur_col2 = st.columns(2)
      with eur_col1:
        e_ur_x = st.number_input(
            "Upper Right X (ft)",
            value=float(c_edit.get("ur_x", c_edit.get("x3", 180.0))),
            key=f"e_cr_ur_x_{selected_crane_idx}",
        )
      with eur_col2:
        e_ur_y = st.number_input(
            "Upper Right Y (ft)",
            value=float(c_edit.get("ur_y", c_edit.get("y3", 80.0))),
            key=f"e_cr_ur_y_{selected_crane_idx}",
        )

      c_btn_c1, c_btn_c2 = st.columns(2)
      with c_btn_c1:
        if st.button(
            "Update Crane Data", key=f"up_cr_btn_{selected_crane_idx}"
        ):
          st.session_state.placed_cranes[selected_crane_idx] = {
              "make": e_make,
              "model": e_model,
              "max_lift_weight": e_wt,
              "max_lift_speed": e_lsp,
              "max_transversal_speed": e_tsp,
              "ll_x": e_ll_x,
              "ll_y": e_ll_y,
              "ur_x": e_ur_x,
              "ur_y": e_ur_y,
          }
          st.success(f"Updated Crane C{selected_crane_idx+1} configuration!")
          st.rerun() if hasattr(st, "rerun") else st.experimental_rerun()
      with c_btn_c2:
        if st.button("Delete Crane", key=f"del_cr_btn_{selected_crane_idx}"):
          removed_crane = st.session_state.placed_cranes.pop(
              selected_crane_idx
          )
          st.warning(
              f"Removed Crane C{selected_crane_idx+1}"
              f" ({removed_crane.get('make', '')}"
              f" {removed_crane.get('model', '')})."
          )
          st.rerun() if hasattr(st, "rerun") else st.experimental_rerun()
    else:
      st.info("No overhead cranes currently placed.")
