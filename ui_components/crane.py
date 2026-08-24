# ui_components/crane.py
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


def render_crane_tab(crane_lib):
    crane_col1, crane_col2 = st.columns(2)

    with crane_col1:
        st.subheader("🏗 Add Overhead Crane Coverage")
        crane_options = [
            f"{c['Make']} {c['Model']}" for c in crane_lib
        ]
        selected_idx = st.selectbox(
            "Choose Crane",
            range(len(crane_options)),
            format_func=lambda x: crane_options[x],
            key="crane_lib_select_add",
            on_change=on_crane_select_change,
            args=(crane_lib,),
        )

        ll_x = st.number_input(
            "Lower Left X (ft)",
            min_value=0.0,
            max_value=float(st.session_state.floor_w),
            value=20.0,
            key="cr_ll_x",
        )
        ll_y = st.number_input(
            "Lower Left Y (ft)",
            min_value=0.0,
            max_value=float(st.session_state.floor_h),
            value=20.0,
            key="cr_ll_y",
        )
        ur_x = st.number_input(
            "Upper Right X (ft)",
            min_value=0.0,
            max_value=float(st.session_state.floor_w),
            value=180.0,
            key="cr_ur_x",
        )
        ur_y = st.number_input(
            "Upper Right Y (ft)",
            min_value=0.0,
            max_value=float(st.session_state.floor_h),
            value=80.0,
            key="cr_ur_y",
        )

        crane_amp = st.number_input(
            "Crane Amperage",
            min_value=0.0,
            max_value=5000.0,
            value=60.0,
            key="cr_amp_add",
        )
        crane_watt = st.number_input(
            "Crane Wattage",
            min_value=0.0,
            max_value=500000.0,
            value=12000.0,
            key="cr_watt_add",
        )

        if st.button("Add Crane Coverage", type="primary", key="add_crane_btn"):
            ok, msg = validate_bbox(
                ll_x, ll_y, ur_x, ur_y, st.session_state.floor_w, st.session_state.floor_h
            )
            if not ok:
                st.error(msg)
            else:
                spec = crane_lib[selected_idx]
                record = {
                    "id": generate_next_id("CR", st.session_state.placed_cranes),
                    "make": spec["Make"],
                    "model": spec["Model"],
                    "max_lift_weight": float(st.session_state["crane_wt_add"]),
                    "max_lift_speed": float(st.session_state["crane_lsp_add"]),
                    "max_transversal_speed": float(st.session_state["crane_tsp_add"]),
                    "amperage": float(crane_amp),
                    "wattage": float(crane_watt),
                    "ll_x": float(ll_x),
                    "ll_y": float(ll_y),
                    "ur_x": float(ur_x),
                    "ur_y": float(ur_y),
                }
                st.session_state.placed_cranes.append(record)
                st.success(f"Added crane coverage {record['id']}.")
                st.rerun() if hasattr(st, "rerun") else st.experimental_rerun()

    with crane_col2:
        st.subheader("Edit Existing Cranes")
        if st.session_state.placed_cranes:
            labels = [
                f"{c.get('id', f'CR-{i+1:03d}')} | {c.get('make', '')} {c.get('model', '')}"
                for i, c in enumerate(st.session_state.placed_cranes)
            ]
            selected_crane_idx = st.selectbox(
                "Select crane to edit",
                range(len(labels)),
                format_func=lambda x: labels[x],
                key="edit_crane_select",
            )

            crane = st.session_state.placed_cranes[selected_crane_idx]

            e_ll_x = st.number_input(
                "Edit Lower Left X",
                min_value=0.0,
                max_value=float(st.session_state.floor_w),
                value=float(crane["ll_x"]),
                key=f"e_cr_llx_{selected_crane_idx}",
            )
            e_ll_y = st.number_input(
                "Edit Lower Left Y",
                min_value=0.0,
                max_value=float(st.session_state.floor_h),
                value=float(crane["ll_y"]),
                key=f"e_cr_lly_{selected_crane_idx}",
            )
            e_ur_x = st.number_input(
                "Edit Upper Right X",
                min_value=0.0,
                max_value=float(st.session_state.floor_w),
                value=float(crane["ur_x"]),
                key=f"e_cr_urx_{selected_crane_idx}",
            )
            e_ur_y = st.number_input(
                "Edit Upper Right Y",
                min_value=0.0,
                max_value=float(st.session_state.floor_h),
                value=float(crane["ur_y"]),
                key=f"e_cr_ury_{selected_crane_idx}",
            )
            e_amp = st.number_input(
                "Edit Amperage",
                min_value=0.0,
                max_value=5000.0,
                value=float(crane.get("amperage", 60.0)),
                key=f"e_cr_amp_{selected_crane_idx}",
            )
            e_watt = st.number_input(
                "Edit Wattage",
                min_value=0.0,
                max_value=500000.0,
                value=float(crane.get("wattage", 12000.0)),
                key=f"e_cr_watt_{selected_crane_idx}",
            )

            c_btn_c1, c_btn_c2 = st.columns(2)
            with c_btn_c1:
                if st.button("Update Crane", key=f"upd_cr_btn_{selected_crane_idx}"):
                    ok, msg = validate_bbox(
                        e_ll_x,
                        e_ll_y,
                        e_ur_x,
                        e_ur_y,
                        st.session_state.floor_w,
                        st.session_state.floor_h,
                    )
                    if not ok:
                        st.error(msg)
                    else:
                        updated = dict(crane)
                        updated["ll_x"] = float(e_ll_x)
                        updated["ll_y"] = float(e_ll_y)
                        updated["ur_x"] = float(e_ur_x)
                        updated["ur_y"] = float(e_ur_y)
                        updated["amperage"] = float(e_amp)
                        updated["wattage"] = float(e_watt)
                        st.session_state.placed_cranes[selected_crane_idx] = updated
                        st.success(f"Updated crane {updated.get('id', 'unknown')} configuration!")
                        st.rerun() if hasattr(st, "rerun") else st.experimental_rerun()

            with c_btn_c2:
                if st.button("Delete Crane", key=f"del_cr_btn_{selected_crane_idx}"):
                    removed_crane = st.session_state.placed_cranes.pop(selected_crane_idx)
                    st.warning(
                        f"Removed {removed_crane.get('id', 'crane')} "
                        f"({removed_crane.get('make', '')} {removed_crane.get('model', '')})."
                    )
                    st.rerun() if hasattr(st, "rerun") else st.experimental_rerun()
        else:
            st.info("No overhead cranes currently placed.")