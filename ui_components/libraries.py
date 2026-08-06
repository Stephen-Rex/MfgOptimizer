# ui_components/libraries.py
import pandas as pd
import streamlit as st


def render_libraries_tab(machinery_lib, lighting_lib, crane_lib):
  st.header("📚 Default Machinery, Lighting & Crane Libraries")
  st.markdown(
      "Reference specification tables loaded from default library"
      " configurations."
  )

  df_machinery = pd.DataFrame(machinery_lib)
  df_lighting = pd.DataFrame(lighting_lib)
  df_cranes = pd.DataFrame(crane_lib)

  lib_col1, lib_col2, lib_col3 = st.columns(3)

  with lib_col1:
    st.subheader("🤖 Default Machinery Library")
    st.dataframe(df_machinery, use_container_width=True)

  with lib_col2:
    st.subheader("💡 Default Lighting Library")
    st.dataframe(df_lighting, use_container_width=True)

  with lib_col3:
    st.subheader("🏗️ Default Overhead Crane Library")
    st.dataframe(df_cranes, use_container_width=True)
