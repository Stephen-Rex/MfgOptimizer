# ui_components/workflow.py
import pandas as pd
import streamlit as st


def render_workflow_tab():
  st.header("🔄 Machine Part Flow Configuration")
  st.markdown(
      "Specify how parts will flow from source to destination machines for"
      " backend analysis."
  )

  with st.container():
    f_col1, f_col2 = st.columns(2)
    with f_col1:
      source_id = st.text_input(
          "Source Machine ID", placeholder="e.g., M-100", key="src_flow_tab"
      )
    with f_col2:
      dest_id = st.text_input(
          "Destination Machine ID", placeholder="e.g., M-200", key="dst_flow_tab"
      )

    if st.button("Add Machine Flow", type="primary", key="add_flow_btn"):
      if source_id and dest_id:
        st.session_state.machine_flows.append(
            {"Source": source_id, "Destination": dest_id}
        )
        st.success(
            f"✅ Route successfully defined: **{source_id}** ➔ **{dest_id}**"
        )
      else:
        st.warning("Please provide both Source and Destination Machine IDs.")

  if len(st.session_state.machine_flows) > 0:
    st.subheader("Active Defined Machine Flow Routes")
    st.dataframe(
        pd.DataFrame(st.session_state.machine_flows), use_container_width=True
    )

  st.divider()

  st.header("GM Workflow Path Definition")
  st.markdown(
      "Input and edit the sequential X/Y coordinate points that define the"
      " workflow path. Parts will travel sequentially from the first to the"
      " last point."
  )

  with st.form("path_point_form_tab"):
    st.subheader("Add Point to Workflow Path")
    col_x, col_y, col_standoff, col_speed = st.columns(4)

    with col_x:
      x_val = st.number_input("X Coordinate", value=0.0, format="%.2f")
    with col_y:
      y_val = st.number_input("Y Coordinate", value=0.0, format="%.2f")
    with col_standoff:
      standoff_val = st.number_input(
          "Safety Standoff (ft)", min_value=0.0, value=2.0, format="%.2f"
      )
    with col_speed:
      speed_val = st.number_input(
          "Part Movement Speed", min_value=0.0, value=5.0, format="%.2f"
      )

    submit_point = st.form_submit_button("Add Point")

    if submit_point:
      new_point_idx = len(st.session_state.path_points) + 1
      new_row = pd.DataFrame({
          "Point": [new_point_idx],
          "X Coordinate": [x_val],
          "Y Coordinate": [y_val],
          "Safety Standoff (ft)": [standoff_val],
          "Movement Speed": [speed_val],
      })
      st.session_state.path_points = pd.concat(
          [st.session_state.path_points, new_row], ignore_index=True
      )
      st.success("Point added to the path!")

  st.subheader("Edit/Review Path Points")
  st.markdown(
      "Use the table below to review or directly modify path parameters. You"
      " can also delete rows or add rows directly via the grid."
  )

  edited_path_df = st.data_editor(
      st.session_state.path_points,
      num_rows="dynamic",
      use_container_width=True,
      hide_index=True,
      key="data_editor_path_tab",
  )

  st.session_state.path_points = edited_path_df
  st.divider()

  if st.button(
      "💾 Save & Send to Optimization Engine",
      type="primary",
      key="save_c_engine_btn",
  ):
    st.info(
        "Configuration data and workflow paths are ready and serialized for"
        " execution."
    )
