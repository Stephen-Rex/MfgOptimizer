# ui_components/editor.py
import streamlit as st


def render_editor_tab():
  st.subheader("🛠 Interactive 2D Editor Settings")
  st.markdown(
      "Configure the Phase 1 interactive editor workspace. This panel"
      " controls editor behavior, not the formal ASME blueprint render."
  )

  e_col1, e_col2, e_col3 = st.columns(3)

  with e_col1:
    st.checkbox("Enable Interactive Editor", key="editor_enabled")
    st.checkbox("Show Editor Grid", key="editor_show_grid")

  with e_col2:
    st.checkbox("Enable Grid Snap", key="editor_snap_enabled")
    st.number_input(
        "Editor Snap Increment (ft)",
        min_value=0.1,
        max_value=20.0,
        step=0.1,
        key="editor_snap_ft",
    )

  with e_col3:
    st.checkbox("Show Editor Labels", key="editor_show_labels")
    st.selectbox(
        "Default Editor Object Type",
        ["machine", "lighting", "conduit", "crane"],
        key="editor_selected_type",
    )

  st.info(
      "Phase 1 editor supports controlled movement using object selection and"
      " offset application. Direct drag/drop will be added in the next phase."
  )
