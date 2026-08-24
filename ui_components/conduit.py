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
        st.subheader("🔌 Route Conduit Run (Polyline)")
        cx_lbl = st.text_input(
            "Conduit Run Label", "Sub-Station Hookup", key="cx_lbl_tab"
        )
        utility_type = st.selectbox(
            "Utility Type",
            ["electrical", "water", "network", "hvac", "drainage"],
            key="utility_type_tab",
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

        if st.button("Add Conduit Run", type="primary", key="add_conduit_btn"):
            x_vals = parse_coords(cx_x_str)
            y_vals = parse_coords(cx_y_str)

            if x_vals is None or y_vals is None:
                st.error("Coordinates must be valid numeric lists.")
            else:
                ok, msg = validate_polyline(
                    x_vals, y_vals, st.session_state.floor_w, st.session_state.floor_h
                )
                if not ok:
                    st.error(msg)
                else:
                    record = {
                        "id": generate_next_id("C", st.session_state.placed_conduits),
                        "label": cx_lbl,
                        "utility_type": utility_type,
                        "x": x_vals,
                        "y": y_vals,
                        "depth_in": int(cx_depth),
                        "warning_tape": bool(cx_tape),
                    }
                    st.session_state.placed_conduits.append(record)
                    length_ft = polyline_length(x_vals, y_vals)
                    st.success(f"Added conduit {record['id']} ({length_ft} ft route length).")
                    st.rerun() if hasattr(st, "rerun") else st.experimental_rerun()

    with c_col2:
        st.subheader("Edit Existing Conduit Runs")
        if st.session_state.placed_conduits:
            labels = [
                f"{c.get('id', f'C-{i+1:03d}')} | {c.get('label', 'Unnamed')} ({c.get('utility_type', 'electrical')})"
                for i, c in enumerate(st.session_state.placed_conduits)
            ]
            selected_cond_idx = st.selectbox(
                "Select conduit run to edit",
                range(len(labels)),
                format_func=lambda x: labels[x],
                key="edit_conduit_select",
            )

            cond = st.session_state.placed_conduits[selected_cond_idx]

            edit_cx_lbl = st.text_input(
                "Edit Label",
                value=cond.get("label", ""),
                key=f"edit_c_lbl_{selected_cond_idx}",
            )
            edit_utility_type = st.selectbox(
                "Edit Utility Type",
                ["electrical", "water", "network", "hvac", "drainage"],
                index=["electrical", "water", "network", "hvac", "drainage"].index(
                    cond.get("utility_type", "electrical")
                )
                if cond.get("utility_type", "electrical") in ["electrical", "water", "network", "hvac", "drainage"]
                else 0,
                key=f"edit_c_type_{selected_cond_idx}",
            )
            edit_cx_x = st.text_input(
                "Edit X Coordinates",
                value=", ".join(map(str, cond.get("x", []))),
                key=f"edit_c_x_{selected_cond_idx}",
            )
            edit_cx_y = st.text_input(
                "Edit Y Coordinates",
                value=", ".join(map(str, cond.get("y", []))),
                key=f"edit_c_y_{selected_cond_idx}",
            )
            edit_cx_depth = st.number_input(
                "Edit Depth (in)",
                min_value=12,
                max_value=60,
                value=int(cond.get("depth_in", 36)),
                key=f"edit_c_depth_{selected_cond_idx}",
            )
            edit_cx_tape = st.checkbox(
                "Edit Warning Tape Installed",
                value=bool(cond.get("warning_tape", True)),
                key=f"edit_c_tape_{selected_cond_idx}",
            )

            c_btn_col1, c_btn_col2 = st.columns(2)
            with c_btn_col1:
                if st.button("Update Conduit Run", key=f"upd_c_tab_{selected_cond_idx}"):
                    up_x = parse_coords(edit_cx_x)
                    up_y = parse_coords(edit_cx_y)

                    if up_x is None or up_y is None:
                        st.error("Error: Coordinates must be valid numeric pairs.")
                    else:
                        ok, msg = validate_polyline(
                            up_x, up_y, st.session_state.floor_w, st.session_state.floor_h
                        )
                        if not ok:
                            st.error(msg)
                        else:
                            st.session_state.placed_conduits[selected_cond_idx] = {
                                "id": cond.get("id", generate_next_id("C", st.session_state.placed_conduits)),
                                "label": edit_cx_lbl,
                                "utility_type": edit_utility_type,
                                "x": up_x,
                                "y": up_y,
                                "depth_in": int(edit_cx_depth),
                                "warning_tape": bool(edit_cx_tape),
                            }
                            st.success(
                                f"Conduit run updated successfully! "
                                f"Length: {polyline_length(up_x, up_y)} ft"
                            )
                            st.rerun() if hasattr(st, "rerun") else st.experimental_rerun()

            with c_btn_col2:
                if st.button("Delete Conduit Run", key=f"del_c_tab_{selected_cond_idx}"):
                    removed_c = st.session_state.placed_conduits.pop(selected_cond_idx)
                    st.warning(f"Removed conduit run '{removed_c.get('label', removed_c.get('id', 'unknown'))}'.")
                    st.rerun() if hasattr(st, "rerun") else st.experimental_rerun()
        else:
            st.info("No conduits currently routed.")
