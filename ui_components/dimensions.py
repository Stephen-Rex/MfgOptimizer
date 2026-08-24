# ui_components/dimensions.py
import streamlit as st


def render_dimensions_tab():
  st.subheader("📐 Factory Floor & ASME Drawing Sheet Configuration")
  dim_col1, dim_col2 = st.columns(2)
  with dim_col1:
    st.selectbox(
        "Select ASME Sheet Boundary Size", ["A", "B", "C", "D"], key="sheet_size"
    )
    st.number_input(
        "Factory Floor Width (feet)",
        min_value=10.0,
        max_value=1000.0,
        step=10.0,
        key="floor_w",
    )
  with dim_col2:
    st.number_input(
        "Factory Floor Height (feet)",
        min_value=10.0,
        max_value=1000.0,
        step=10.0,
        key="floor_h",
    )
    st.number_input(
        "Workflow Path Width (feet)",
        min_value=0.5,
        max_value=10.0,
        step=0.5,
        key="path_width_ft",
    )
