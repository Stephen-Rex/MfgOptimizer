# ui_components/conduit.py
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


def render_conduit_tab():
    c_col1, c_col2 = st.columns(2)

    with c_col1:
        st.subheader("🔌 Route Utility Run (Polyline)")
        cx_lbl = st.text_input(
            "Utility Run Label", "Sub-Station Hookup", key="cx_lbl_tab"
        )
        cx_type = st.selectbox(
            "Utility Type",
            ["electrical", "water", "drainage", "network", "hvac"],
            key="cx_type_tab",
        )
        cx_x_str = st.text_input(
            "X Coordinates (comma separated)", "40.0, 120.0", key="cx_x_tab"
        )
        cx_y_str = st.text_input(
            "Y Coordinates (comma separated)", "80.0, 35.0", key="cx_y_tab"
        )
        cx_depth = st.number_input(
            "Trench Burial Depth (inches)",
            min_value=12,
            max_value=60,
            value=36,
            key="cx_depth_tab",
        )
        cx_tape = st.checkbox(
            "Warning Tape Installed", value=True, key="cx_tape_tab"
        )

        if st.button("Add Utility Run", type="primary", key="add_conduit_btn"):
            parsed_x = parse_coords(cx_x_str)
            parsed_y = parse_coords(cx_y_str)

            if parsed_x is None or parsed_y is None or len(parsed_x) != len(parsed_y):
                st.error("Coordinates must be valid numeric X/Y pairs.")
            else:
                st.session_state.placed_conduits.append({
                    "label": cx_lbl,
                    "utility_type": cx_type,
                    "x": parsed_x,
                    "y": parsed_y,
                    "depth_in": cx_depth,
                    "warning_tape": cx_tape,
                })
                st.success(f"Successfully routed utility '{cx_lbl}' ({cx_type}).")
                st.rerun() if hasattr(st, "rerun") else st.experimental_rerun()

    with c_col2:
        if len(st.session_state.placed_conduits) > 0:
            st.subheader("🛠 Modify or Delete Utility Runs")
            conduit_options = [
                f"{i+1}: {c['label']} ({c.get('utility_type', 'electrical')})"
                for i, c in enumerate(st.session_state.placed_conduits)
            ]
            selected_cond_idx = st.selectbox(
                "Select Utility Run to Edit",
                range(len(conduit_options)),
                format_func=lambda x: conduit_options[x],
                key="edit_conduit_select",
            )

            cond = st.session_state.placed_conduits[selected_cond_idx]
            edit_cx_lbl = st.text_input(
                "Edit Utility Label",
                cond["label"],
                key=f"lbl_tab_{selected_cond_idx}",
            )
            edit_cx_type = st.selectbox(
                "Edit Utility Type",
                ["electrical", "water", "drainage", "network", "hvac"],
                index=["electrical", "water", "drainage", "network", "hvac"].index(
                    cond.get("utility_type", "electrical")
                ),
                key=f"type_tab_{selected_cond_idx}",
            )
            edit_cx_x_str = st.text_input(
                "Edit X Coordinates",
                ", ".join(map(str, cond["x"])),
                key=f"cx_tab_{selected_cond_idx}",
            )
            edit_cx_y_str = st.text_input(
                "Edit Y Coordinates",
                ", ".join(map(str, cond["y"])),
                key=f"cy_tab_{selected_cond_idx}",
            )
            edit_cx_depth = st.number_input(
                "Edit Depth (in)",
                min_value=12,
                max_value=60,
                value=int(cond.get("depth_in", 36)),
                key=f"depth_tab_{selected_cond_idx}",
            )
            edit_cx_tape = st.checkbox(
                "Warning Tape Installed",
                value=bool(cond.get("warning_tape", True)),
                key=f"tape_tab_{selected_cond_idx}",
            )

            c_btn_col1, c_btn_col2 = st.columns(2)
            with c_btn_col1:
                if st.button("Update Utility Run", key=f"upd_c_tab_{selected_cond_idx}"):
                    up_x = parse_coords(edit_cx_x_str)
                    up_y = parse_coords(edit_cx_y_str)
                    if up_x is None or up_y is None or len(up_x) != len(up_y):
                        st.error("Error: Coordinates must be valid numeric pairs.")
                    else:
                        st.session_state.placed_conduits[selected_cond_idx] = {
                            "label": edit_cx_lbl,
                            "utility_type": edit_cx_type,
                            "x": up_x,
                            "y": up_y,
                            "depth_in": edit_cx_depth,
                            "warning_tape": edit_cx_tape,
                        }
                        st.success("Utility run updated successfully!")
                        st.rerun() if hasattr(st, "rerun") else st.experimental_rerun()

            with c_btn_col2:
                if st.button("Delete Utility Run", key=f"del_c_tab_{selected_cond_idx}"):
                    removed_c = st.session_state.placed_conduits.pop(selected_cond_idx)
                    st.warning(f"Removed utility run '{removed_c['label']}'.")
                    st.rerun() if hasattr(st, "rerun") else st.experimental_rerun()
        else:
            st.info("No utility runs currently routed.")
