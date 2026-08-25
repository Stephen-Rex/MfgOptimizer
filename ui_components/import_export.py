# ui_components/import_export.py
import json
import streamlit as st
from state_manager import (
    parse_coords,
    on_crane_select_change,
    apply_imported_layout,
    generate_next_id,
    validate_machine_record,
    validate_polyline,
    validate_bbox,
    polyline_length,
)

def render_import_export_tab():
    st.header("💾 Import & Export Factory Layout Designs")
    st.markdown(
        "Save your current project configuration as a JSON-formatted project file "
        "or import a previously saved layout."
    )

    io_col1, io_col2 = st.columns(2)

    with io_col1:
        st.subheader("📤 Export Current Project Layout")
        st.markdown(
            "Download the current factory layout configuration as a JSON project file."
        )

        export_data = {
            "schema_version": "1.2",
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
            "show_locator_dims": st.session_state.show_locator_dims,
            "editor_enabled": st.session_state.editor_enabled,
            "editor_selected_type": st.session_state.editor_selected_type,
            "editor_selected_index": st.session_state.editor_selected_index,
            "editor_snap_enabled": st.session_state.editor_snap_enabled,
            "editor_snap_ft": st.session_state.editor_snap_ft,
            "editor_show_grid": st.session_state.editor_show_grid,
            "editor_show_labels": st.session_state.editor_show_labels,
            "workflow_dim_visible": st.session_state.workflow_dim_visible,
            "workflow_dim_label_x_offset_ft": st.session_state.workflow_dim_label_x_offset_ft,
            "workflow_dim_label_y_offset_ft": st.session_state.workflow_dim_label_y_offset_ft,
            "workflow_dim_show_length": st.session_state.workflow_dim_show_length,
            "workflow_dim_show_metadata": st.session_state.workflow_dim_show_metadata,
        }

        export_str = json.dumps(export_data, indent=2)

        st.download_button(
            label="⬇️ Download Project File (.json)",
            data=export_str,
            file_name=f"factory_layout_{st.session_state.dwg_num.replace(' ', '_')}.json",
            mime="application/json",
            type="primary",
        )

        with st.expander("Preview Export File Content"):
            st.code(export_str, language="json")

    with io_col2:
        st.subheader("📥 Import Saved Project Layout")
        st.markdown(
            "Upload a project file (`.json` or legacy `.txt`) to restore a saved layout."
        )

        uploaded_file = st.file_uploader(
            "Choose a layout file (.json or .txt)",
            type=["json", "txt"],
            key="uploaded_layout_file",
        )

        if uploaded_file is not None:
            st.button(
                "Apply Imported Layout to Floor",
                type="primary",
                on_click=apply_imported_layout,
            )

        if "import_status" in st.session_state:
            status_type, msg = st.session_state["import_status"]
            if status_type == "success":
                st.success(msg)
            elif status_type == "error":
                st.error(msg)
