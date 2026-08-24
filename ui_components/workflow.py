# ui_components/workflow.py
import pandas as pd
import streamlit as st


def render_workflow_tab():
    st.header("🔄 Machine Part Flow Configuration")
    st.markdown(
        "Specify part travel path, movement mode, and path parameters for workflow analysis."
    )

    mode_options = [
        "human",
        "autonomous_robot",
        "robotic_arm",
        "overhead_crane",
        "forklift",
    ]

    wf_col1, wf_col2 = st.columns(2)
    with wf_col1:
        selected_mode = st.selectbox(
            "Movement Mode",
            mode_options,
            key="workflow_mode_select",
        )
        #st.number_input(
        #    "Default Workflow Path Width (ft)",
        #    min_value=0.5,
        #    max_value=20.0,
        #    step=0.5,
        #    key="path_width_ft",
        #)
    st.markdown(
    f"**Current Workflow Path Width:** {st.session_state.path_width_ft} ft "
    "(edit in the Floor & Sheet Dimensions tab)"
    )

    with wf_col2:
        st.markdown(
            "Edit workflow waypoints directly in the table below. "
            "All points in the path will use the selected movement mode."
        )

    if "Movement Mode" not in st.session_state.path_points.columns:
        st.session_state.path_points["Movement Mode"] = selected_mode
    else:
        st.session_state.path_points["Movement Mode"] = selected_mode

    edited_df = st.data_editor(
        st.session_state.path_points,
        num_rows="dynamic",
        use_container_width=True,
        key="workflow_editor",
    )

    if st.button("Apply Workflow Edits", type="primary", key="apply_workflow_edits"):
        try:
            required_cols = [
                "X Coordinate",
                "Y Coordinate",
                "Safety Standoff (ft)",
                "Movement Speed",
                "Movement Mode",
            ]
            for col in required_cols:
                if col not in edited_df.columns:
                    st.error(f"Workflow table missing required column: {col}")
                    return

            edited_df["Movement Mode"] = selected_mode
            st.session_state.path_points = edited_df
            st.success("Workflow path configuration updated.")
            st.rerun() if hasattr(st, "rerun") else st.experimental_rerun()
        except Exception as e:
            st.error(f"Error updating workflow data: {e}")
