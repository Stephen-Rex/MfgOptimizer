# ui_components/plots.py
import streamlit as st


def render_plots_tab():
  st.subheader("📊 Blueprint Layer Visibility & Contour Underlays")
  st.markdown("Toggle component layers and analysis underlay visualizations.")

  st.markdown("##### 🧩 Component Layer Visibility Toggles")
  lyr_col1, lyr_col2, lyr_col3, lyr_col4, lyr_col5, lyr_col6 = st.columns(6)
  with lyr_col1:
    st.checkbox("Show Machinery Layer", key="show_machines")
  with lyr_col2:
    st.checkbox("Show Lighting Layer", key="show_lighting")
  with lyr_col3:
    st.checkbox("Show Crane Layer", key="show_cranes")
  with lyr_col4:
    st.checkbox("Show Workflow Layer", key="show_workflow")
  with lyr_col5:
    st.checkbox("Show Electrical Layer", key="show_electrical")
  with lyr_col6:
    st.checkbox("Show Machine Coordinates", key="show_locator_dims")

  st.markdown("##### 🎚 Analysis Plot Underlays")
  plt_col1, plt_col2, plt_col3 = st.columns(3)
  with plt_col1:
    st.checkbox("Show Safety Heatmap underlay", key="show_safety")
  with plt_col2:
    st.checkbox("Show Part Volume Contour plots", key="show_contour")
  with plt_col3:
    st.checkbox(
        "Show Machine Decibel Contour plot (Inverse Square Law)",
        key="show_decibel",
    )
