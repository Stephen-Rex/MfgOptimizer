# ui_components/project_info.py
import streamlit as st


def render_project_info_tab():
  st.subheader("📋 Blueprint Title Block Parameters")
  st.markdown(
      "Edit the metadata displayed inside the ASME Y14.1 Title Block on the"
      " blueprint drawing."
  )

  p_col1, p_col2 = st.columns(2)
  with p_col1:
    st.text_input("Designer / Company Name", key="designer_name")
    st.text_input("Drawing Title", key="dwg_title")
  with p_col2:
    st.text_input("Drawing Number (DWG NO)", key="dwg_num")
