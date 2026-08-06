# ui_components/import_export.py
import json
import streamlit as st
from state_manager import apply_imported_layout


def render_import_export_tab():
  st.header("💾 Import & Export Factory Layout Designs")
  st.markdown(
      "Save your current project configuration as a formatted text file (JSON"
      " format) or import a previously saved design file."
  )

  io_col1, io_col2 = st.columns(2)

  with io_col1:
    st.subheader("📤 Export Current Project Layout")
    st.markdown(
        "Click the button below to download your complete factory floor"
        " configuration file."
    )

    export_data = {
        "designer_name": st.session_state.designer_name,
        "dwg_title": st.session_state.dwg_title,
        "dwg_num": st.session_state.dwg_num,
        "sheet_size": st.session_state.sheet_size,
        "floor_w": st.session_state.floor_w,
        "floor_h": st.session_state.floor_h,
        "path_width_ft": st.session_state.path_width_ft,
        "show_machines": st.session_state.show_machines,
        "show_lighting": st.session_state.show_lighting,
        "show_cranes": st.session_state.show_cranes,
        "show_workflow": st.session_state.show_workflow,
        "show_electrical": st.session_state.show_electrical,
        "show_safety": st.session_state.show_safety,
        "show_contour": st.session_state.show_contour,
        "show_decibel": st.session_state.show_decibel,
        "placed_machines": st.session_state.placed_machines,
        "placed_lighting": st.session_state.placed_lighting,
        "placed_conduits": st.session_state.placed_conduits,
        "placed_cranes": st.session_state.placed_cranes,
        "machine_flows": st.session_state.machine_flows,
        "path_points": st.session_state.path_points.to_dict(orient="records"),
    }

    export_str = json.dumps(export_data, indent=2)

    st.download_button(
        label="⬇️ Download Project File (.txt)",
        data=export_str,
        file_name=(
            "factory_layout_"
            f"{st.session_state.dwg_num.replace(' ', '_')}.txt"
        ),
        mime="text/plain",
        type="primary",
    )

    with st.expander("Preview Formatted Export File Content"):
      st.code(export_str, language="json")

  with io_col2:
    st.subheader("📥 Import Saved Project Layout")
    st.markdown(
        "Upload a formatted project text file (`.txt`) to restore a saved"
        " layout."
    )

    uploaded_file = st.file_uploader(
        "Choose a layout text file",
        type=["txt", "json"],
        key="uploaded_layout_file",
    )

    if uploaded_file is not None:
      st.button(
          "🔄 Apply Imported Layout to Floor",
          type="primary",
          on_click=apply_imported_layout,
      )

    if "import_status" in st.session_state:
      status_type, msg = st.session_state["import_status"]
      if status_type == "success":
        st.success(msg)
      elif status_type == "error":
        st.error(msg)
