# ui_components/workflow.py
import pandas as pd
import streamlit as st

from state_manager import (
    generate_next_id,
    ensure_machine_flow_fields,
    validate_machine_flow_record,
    validate_all_machine_flows,
    get_machine_label_map,
)


def render_machine_flows_editor():
    """
    Render controls for adding a new machine flow link.
    """
    st.subheader("Value-Added Machine Flow Links")
    st.caption(
        "Machine flow links support heuristic layout optimization for value-added operations. "
        "Workflow path geometry and machine-to-machine flow relationships are evaluated separately."
    )    
    st.markdown(
        "Define machine-to-machine production flow relationships used for "
        "value-added placement optimization."
    )

    ensure_machine_flow_fields()

    placed_machines = st.session_state.get("placed_machines", [])
    if len(placed_machines) < 2:
        st.info("Place at least two machines before defining machine flow links.")
        return

    machine_label_map = get_machine_label_map(placed_machines)
    machine_ids = list(machine_label_map.keys())

    add_col1, add_col2, add_col3 = st.columns(3)

    with add_col1:
        from_machine_id = st.selectbox(
            "From Machine",
            machine_ids,
            format_func=lambda x: machine_label_map.get(x, x),
            key="flow_from_machine_id",
        )

        process_step_order = st.number_input(
            "Process Step Order",
            min_value=1,
            step=1,
            value=1,
            key="flow_process_step_order",
        )

        flow_rate_per_hr = st.number_input(
            "Flow Rate (parts/hr)",
            min_value=0.0,
            step=1.0,
            value=0.0,
            key="flow_rate_per_hr",
        )

        preferred_max_distance_ft = st.number_input(
            "Preferred Max Distance (ft)",
            min_value=0.0,
            step=1.0,
            value=25.0,
            key="flow_preferred_max_distance_ft",
        )

    with add_col2:
        to_machine_id = st.selectbox(
            "To Machine",
            machine_ids,
            format_func=lambda x: machine_label_map.get(x, x),
            key="flow_to_machine_id",
        )

        transfer_mode = st.selectbox(
            "Transfer Mode",
            ["human", "autonomous_robot", "robotic_arm", "overhead_crane", "forklift"],
            key="flow_transfer_mode",
        )

        lot_size = st.number_input(
            "Lot Size",
            min_value=1,
            step=1,
            value=1,
            key="flow_lot_size",
        )

        buffer_max_units = st.number_input(
            "Buffer Max Units",
            min_value=0,
            step=1,
            value=0,
            key="flow_buffer_max_units",
        )

    with add_col3:
        part_family = st.text_input(
            "Part Family",
            value="",
            key="flow_part_family",
        )

        value_added_step = st.checkbox(
            "Value-Added Step",
            value=True,
            key="flow_value_added_step",
        )

        mandatory_adjacency = st.checkbox(
            "Mandatory Adjacency",
            value=False,
            key="flow_mandatory_adjacency",
        )

        notes = st.text_area(
            "Notes",
            value="",
            key="flow_notes",
            height=120,
        )

    if st.button("Add Machine Flow Link", type="primary", key="add_machine_flow_btn"):
        new_flow = {
            "id": generate_next_id("F", st.session_state.machine_flows),
            "from_machine_id": str(from_machine_id),
            "to_machine_id": str(to_machine_id),
            "part_family": str(part_family),
            "process_step_order": int(process_step_order),
            "flow_rate_per_hr": float(flow_rate_per_hr),
            "transfer_mode": str(transfer_mode),
            "lot_size": int(lot_size),
            "buffer_max_units": int(buffer_max_units),
            "value_added_step": bool(value_added_step),
            "mandatory_adjacency": bool(mandatory_adjacency),
            "preferred_max_distance_ft": float(preferred_max_distance_ft),
            "notes": str(notes),
        }

        ok, msg = validate_machine_flow_record(new_flow, placed_machines)
        if not ok:
            st.error(msg)
        else:
            st.session_state.machine_flows.append(new_flow)
            st.success(f"Added machine flow link {new_flow['id']}.")
            st.rerun() if hasattr(st, "rerun") else st.experimental_rerun()


def render_machine_flows_table():
    """
    Render existing machine flow links with edit/delete actions.
    """
    ensure_machine_flow_fields()
    placed_machines = st.session_state.get("placed_machines", [])
    machine_label_map = get_machine_label_map(placed_machines)

    flows = st.session_state.get("machine_flows", [])
    if not flows:
        st.info("No machine flow links defined yet.")
        return

    st.markdown("### Existing Machine Flow Links")

    flow_labels = []
    for flow in flows:
        fid = flow.get("id", "F-???")
        fmid = flow.get("from_machine_id", "")
        tmid = flow.get("to_machine_id", "")
        flow_labels.append(
            f"{fid} | {machine_label_map.get(fmid, fmid)} -> {machine_label_map.get(tmid, tmid)}"
        )

    selected_flow_idx = st.selectbox(
        "Select Flow Link to Edit",
        range(len(flow_labels)),
        format_func=lambda x: flow_labels[x],
        key="edit_machine_flow_select",
    )

    flow = dict(flows[selected_flow_idx])

    edit_col1, edit_col2, edit_col3 = st.columns(3)
    machine_ids = list(machine_label_map.keys())

    with edit_col1:
        edit_from_machine_id = st.selectbox(
            "Edit From Machine",
            machine_ids,
            index=max(machine_ids.index(flow.get("from_machine_id")), 0)
            if flow.get("from_machine_id") in machine_ids else 0,
            format_func=lambda x: machine_label_map.get(x, x),
            key=f"edit_flow_from_{selected_flow_idx}",
        )

        edit_process_step_order = st.number_input(
            "Edit Process Step Order",
            min_value=1,
            step=1,
            value=int(flow.get("process_step_order", 1)),
            key=f"edit_flow_pso_{selected_flow_idx}",
        )

        edit_flow_rate_per_hr = st.number_input(
            "Edit Flow Rate (parts/hr)",
            min_value=0.0,
            step=1.0,
            value=float(flow.get("flow_rate_per_hr", 0.0)),
            key=f"edit_flow_rate_{selected_flow_idx}",
        )

        edit_preferred_max_distance_ft = st.number_input(
            "Edit Preferred Max Distance (ft)",
            min_value=0.0,
            step=1.0,
            value=float(flow.get("preferred_max_distance_ft", 25.0)),
            key=f"edit_flow_maxdist_{selected_flow_idx}",
        )

    with edit_col2:
        edit_to_machine_id = st.selectbox(
            "Edit To Machine",
            machine_ids,
            index=max(machine_ids.index(flow.get("to_machine_id")), 0)
            if flow.get("to_machine_id") in machine_ids else 0,
            format_func=lambda x: machine_label_map.get(x, x),
            key=f"edit_flow_to_{selected_flow_idx}",
        )

        edit_transfer_mode = st.selectbox(
            "Edit Transfer Mode",
            ["human", "autonomous_robot", "robotic_arm", "overhead_crane", "forklift"],
            index=["human", "autonomous_robot", "robotic_arm", "overhead_crane", "forklift"].index(
                flow.get("transfer_mode", "human")
            ) if flow.get("transfer_mode", "human") in
            ["human", "autonomous_robot", "robotic_arm", "overhead_crane", "forklift"] else 0,
            key=f"edit_flow_mode_{selected_flow_idx}",
        )

        edit_lot_size = st.number_input(
            "Edit Lot Size",
            min_value=1,
            step=1,
            value=int(flow.get("lot_size", 1)),
            key=f"edit_flow_lot_{selected_flow_idx}",
        )

        edit_buffer_max_units = st.number_input(
            "Edit Buffer Max Units",
            min_value=0,
            step=1,
            value=int(flow.get("buffer_max_units", 0)),
            key=f"edit_flow_buf_{selected_flow_idx}",
        )

    with edit_col3:
        edit_part_family = st.text_input(
            "Edit Part Family",
            value=str(flow.get("part_family", "")),
            key=f"edit_flow_pf_{selected_flow_idx}",
        )

        edit_value_added_step = st.checkbox(
            "Edit Value-Added Step",
            value=bool(flow.get("value_added_step", True)),
            key=f"edit_flow_va_{selected_flow_idx}",
        )

        edit_mandatory_adjacency = st.checkbox(
            "Edit Mandatory Adjacency",
            value=bool(flow.get("mandatory_adjacency", False)),
            key=f"edit_flow_adj_{selected_flow_idx}",
        )

        edit_notes = st.text_area(
            "Edit Notes",
            value=str(flow.get("notes", "")),
            key=f"edit_flow_notes_{selected_flow_idx}",
            height=120,
        )

    btn_col1, btn_col2 = st.columns(2)

    with btn_col1:
        if st.button("Update Flow Link", key=f"update_flow_btn_{selected_flow_idx}"):
            updated = dict(flow)
            updated["from_machine_id"] = str(edit_from_machine_id)
            updated["to_machine_id"] = str(edit_to_machine_id)
            updated["part_family"] = str(edit_part_family)
            updated["process_step_order"] = int(edit_process_step_order)
            updated["flow_rate_per_hr"] = float(edit_flow_rate_per_hr)
            updated["transfer_mode"] = str(edit_transfer_mode)
            updated["lot_size"] = int(edit_lot_size)
            updated["buffer_max_units"] = int(edit_buffer_max_units)
            updated["value_added_step"] = bool(edit_value_added_step)
            updated["mandatory_adjacency"] = bool(edit_mandatory_adjacency)
            updated["preferred_max_distance_ft"] = float(edit_preferred_max_distance_ft)
            updated["notes"] = str(edit_notes)

            ok, msg = validate_machine_flow_record(updated, placed_machines)
            if not ok:
                st.error(msg)
            else:
                st.session_state.machine_flows[selected_flow_idx] = updated
                st.success(f"Updated flow link {updated.get('id', 'unknown')}.")
                st.rerun() if hasattr(st, "rerun") else st.experimental_rerun()

    with btn_col2:
        if st.button("Delete Flow Link", key=f"delete_flow_btn_{selected_flow_idx}"):
            removed = st.session_state.machine_flows.pop(selected_flow_idx)
            st.warning(f"Removed flow link {removed.get('id', 'unknown')}.")
            st.rerun() if hasattr(st, "rerun") else st.experimental_rerun()


def render_workflow_tab():
    st.header("Part Transportation Path Configuration")
st.markdown(
    "Specify the floor-level part transportation path, movement mode, and path parameters. "
    "Use the machine workflow section below for machine-to-machine process linkage."
)

    mode_options = [
        "human",
        "autonomous_robot",
        "robotic_arm",
        "overhead_crane",
        "forklift",
    ]

    wf_col1, wf_col2 = st.columns(2)
    with wf_col1:
        selected_mode = st.selectbox(
            "Movement Mode",
            mode_options,
            key="workflow_mode_select",
        )
        #st.number_input(
        #    "Default Workflow Path Width (ft)",
        #    min_value=0.5,
        #    max_value=20.0,
        #    step=0.5,
        #    key="path_width_ft",
        #)
    st.markdown(
    f"**Current Workflow Path Width:** {st.session_state.path_width_ft} ft "
    "(edit in the Floor & Sheet Dimensions tab)"
    )

    with wf_col2:
        st.markdown(
            "Edit workflow waypoints directly in the table below. "
            "All points in the path will use the selected movement mode."
        )

    if "Movement Mode" not in st.session_state.path_points.columns:
        st.session_state.path_points["Movement Mode"] = selected_mode
    else:
        st.session_state.path_points["Movement Mode"] = selected_mode

    edited_df = st.data_editor(
        st.session_state.path_points,
        num_rows="dynamic",
        use_container_width=True,
        key="workflow_editor",
    )

    if st.button("Apply Workflow Edits", type="primary", key="apply_workflow_edits"):
        try:
            required_cols = [
                "X Coordinate",
                "Y Coordinate",
                "Safety Standoff (ft)",
                "Movement Speed",
                "Movement Mode",
            ]
            for col in required_cols:
                if col not in edited_df.columns:
                    st.error(f"Workflow table missing required column: {col}")
                    return

            edited_df["Movement Mode"] = selected_mode
            st.session_state.path_points = edited_df
            st.success("Workflow path configuration updated.")
            st.rerun() if hasattr(st, "rerun") else st.experimental_rerun()
        except Exception as e:
            st.error(f"Error updating workflow data: {e}")

    st.divider()

    render_machine_flows_editor()
    render_machine_flows_table()

    ok, errors = validate_all_machine_flows(
        st.session_state.get("machine_flows", []),
        st.session_state.get("placed_machines", []),
    )
    if not ok:
        st.warning("Machine flow link validation issues detected:")
        for err in errors:
            st.write(f"- {err}")
