# ui_components/machinery.py
import streamlit as st
from state_manager import generate_next_id, validate_machine_record


def render_machinery_tab(machinery_lib):
    m_col1, m_col2 = st.columns(2)

    with m_col1:
        st.subheader("🏭 Place Machine from Library")
        machine_options = [
            f"{m['Make']} {m['Model']} ({m['Type']})" for m in machinery_lib
        ]
        selected_m_idx = st.selectbox(
            "Choose Machine",
            range(len(machine_options)),
            format_func=lambda x: machine_options[x],
            key="machine_lib_select",
        )

        default_mx = min(70.0, float(st.session_state.floor_w))
        default_my = min(50.0, float(st.session_state.floor_h))

        mx_coord = st.number_input(
            "Target Placement X (ft)",
            min_value=0.0,
            max_value=float(st.session_state.floor_w),
            value=default_mx,
            key="mx_tab",
        )
        my_coord = st.number_input(
            "Target Placement Y (ft)",
            min_value=0.0,
            max_value=float(st.session_state.floor_h),
            value=default_my,
            key="my_tab",
        )

        if st.button("Add Machine to Layout", type="primary", key="add_machine_btn"):
            spec = dict(machinery_lib[selected_m_idx])
            spec["id"] = generate_next_id("M", st.session_state.placed_machines)
            spec["x"] = float(mx_coord)
            spec["y"] = float(my_coord)

            ok, msg = validate_machine_record(
                spec, st.session_state.floor_w, st.session_state.floor_h
            )
            if not ok:
                st.error(msg)
            else:
                st.session_state.placed_machines.append(spec)
                st.success(f"Added machine {spec['id']} to layout.")
                st.rerun() if hasattr(st, "rerun") else st.experimental_rerun()

    with m_col2:
        st.subheader("Edit Existing Machines")
        if st.session_state.placed_machines:
            labels = [
                f"{m.get('id', f'M-{i+1:03d}')} | {m['Make']} {m['Model']}"
                for i, m in enumerate(st.session_state.placed_machines)
            ]
            selected_placed_idx = st.selectbox(
                "Select placed machine to edit",
                range(len(labels)),
                format_func=lambda x: labels[x],
                key="edit_machine_select",
            )

            machine = st.session_state.placed_machines[selected_placed_idx]

            edit_x = st.number_input(
                "Edit X (ft)",
                min_value=0.0,
                max_value=float(st.session_state.floor_w),
                value=float(machine["x"]),
                key=f"edit_mx_{selected_placed_idx}",
            )
            edit_y = st.number_input(
                "Edit Y (ft)",
                min_value=0.0,
                max_value=float(st.session_state.floor_h),
                value=float(machine["y"]),
                key=f"edit_my_{selected_placed_idx}",
            )
            edit_standoff = st.number_input(
                "Edit Standoff (ft)",
                min_value=0.0,
                max_value=50.0,
                value=float(machine.get("Standoff", 0.0)),
                key=f"edit_mso_{selected_placed_idx}",
            )
            edit_volume = st.number_input(
                "Edit Volume (parts/hr)",
                min_value=0.0,
                max_value=100000.0,
                value=float(machine.get("Volume", 0.0)),
                key=f"edit_mvol_{selected_placed_idx}",
            )
            edit_yield = st.number_input(
                "Edit Yield (%)",
                min_value=0.0,
                max_value=100.0,
                value=float(machine.get("Yield", 100.0)),
                key=f"edit_myield_{selected_placed_idx}",
            )
            edit_decibel = st.number_input(
                "Edit Decibel (dBA)",
                min_value=0.0,
                max_value=150.0,
                value=float(machine.get("Decibel", 75.0)),
                key=f"edit_mdb_{selected_placed_idx}",
            )
            edit_crane_required = st.checkbox(
                "Requires Overhead Crane",
                value=bool(machine.get("CraneRequired", False)),
                key=f"edit_mcrane_{selected_placed_idx}",
            )
            edit_human_intervention = st.checkbox(
                "Human Intervention Required",
                value=bool(machine.get("HumanInterventionRequired", False)),
                key=f"edit_mhuman_{selected_placed_idx}",
            )

            edit_process_family = st.text_input(
                "Process Family",
                value=str(machine.get("ProcessFamily", "")),
                key=f"edit_mpf_{selected_placed_idx}",
            )

            edit_preferred_utility_zone = st.text_input(
                "Preferred Utility Zone",
                value=str(machine.get("PreferredUtilityZone", "")),
                key=f"edit_muz_{selected_placed_idx}",
            )

            edit_value_added_primary = st.checkbox(
                "Primary Value-Added Machine",
                value=bool(machine.get("ValueAddedPrimary", True)),
                key=f"edit_mva_{selected_placed_idx}",
            )            

            btn_col1, btn_col2, btn_col3 = st.columns(3)
            with btn_col1:
                if st.button("Update Machine", key=f"update_m_btn_{selected_placed_idx}"):
                    updated = dict(machine)
                    updated["x"] = float(edit_x)
                    updated["y"] = float(edit_y)
                    updated["Standoff"] = float(edit_standoff)
                    updated["Volume"] = float(edit_volume)
                    updated["Yield"] = float(edit_yield)
                    updated["Decibel"] = float(edit_decibel)
                    updated["CraneRequired"] = bool(edit_crane_required)
                    updated["HumanInterventionRequired"] = bool(edit_human_intervention)
                    updated["ProcessFamily"] = str(edit_process_family)
                    updated["PreferredUtilityZone"] = str(edit_preferred_utility_zone)
                    updated["ValueAddedPrimary"] = bool(edit_value_added_primary)  

                    ok, msg = validate_machine_record(
                        updated, st.session_state.floor_w, st.session_state.floor_h
                    )
                    if not ok:
                        st.error(msg)
                    else:
                        st.session_state.placed_machines[selected_placed_idx] = updated
                        st.success(f"Machine {updated['id']} updated successfully.")
                        st.rerun() if hasattr(st, "rerun") else st.experimental_rerun()

            with btn_col2:
                if st.button("Duplicate Machine", key=f"dup_m_btn_{selected_placed_idx}"):
                    duplicated = dict(machine)
                    duplicated["id"] = generate_next_id("M", st.session_state.placed_machines)
                    duplicated["x"] = min(
                        float(machine["x"]) + 5.0, float(st.session_state.floor_w)
                    )
                    duplicated["y"] = min(
                        float(machine["y"]) + 5.0, float(st.session_state.floor_h)
                    )
                    st.session_state.placed_machines.append(duplicated)
                    st.success(f"Duplicated machine as {duplicated['id']}.")
                    st.rerun() if hasattr(st, "rerun") else st.experimental_rerun()

            with btn_col3:
                if st.button("Delete Machine", key=f"delete_m_btn_{selected_placed_idx}"):
                    removed = st.session_state.placed_machines.pop(selected_placed_idx)
                    st.warning(
                        f"Removed {removed.get('id', 'machine')} "
                        f"({removed['Make']} {removed['Model']}) from layout."
                    )
                    st.rerun() if hasattr(st, "rerun") else st.experimental_rerun()
        else:
            st.info("No machines currently placed on the layout.")
