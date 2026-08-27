# interactive_editor.py
import math
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import streamlit as st
from streamlit_plotly_events import plotly_events
from interactive_canvas import build_interactive_canvas_figure, apply_canvas_pick

def render_dimension_regression_panel():
    with st.expander("Dimension Regression Checks", expanded=False):
        st.caption("Temporary web-based regression checks for dim-mode behavior.")

        if st.button("Run Dim Visibility Check"):
            results = []
            original_mode = st.session_state.get("editor_canvas_mode", "select")

            try:
                # Ensure at least one machine exists for the check
                if not st.session_state.get("placed_machines"):
                    st.session_state.placed_machines = [{
                        "id": "M-TEST-001",
                        "x": 20.0,
                        "y": 20.0,
                        "Width": 8.0,
                        "Height": 6.0,
                        "Standoff": 2.0,
                        "dim_visible": True,
                        "dim_x_line_offset_ft": 0.0,
                        "dim_y_line_offset_ft": 0.0,
                        "dim_x_text_offset_ft": 0.0,
                        "dim_y_text_offset_ft": 0.0,
                        "dim_x_text_anchor_ft": 0.0,
                        "dim_y_text_anchor_ft": 0.0,
                        "dim_x_side": "below",
                        "dim_y_side": "left",
                    }]

                # Select mode check
                st.session_state.editor_canvas_mode = "select"
                fig = build_interactive_canvas_figure()
                trace_types = [t["entity_type"] for t in st.session_state.editor_trace_map]
                select_ok = not any(tt.startswith("dimension_") for tt in trace_types)
                results.append(("Select mode hides dimensions", select_ok, trace_types))

                # Move mode check
                st.session_state.editor_canvas_mode = "move"
                fig = build_interactive_canvas_figure()
                trace_types = [t["entity_type"] for t in st.session_state.editor_trace_map]
                move_ok = not any(tt.startswith("dimension_") for tt in trace_types)
                results.append(("Move mode hides dimensions", move_ok, trace_types))

                # Dim mode check
                st.session_state.editor_canvas_mode = "dim"
                fig = build_interactive_canvas_figure()
                
                with st.expander("Dim Debug", expanded=True):
                    st.write("Canvas mode:", st.session_state.get("editor_canvas_mode"))
                    st.write("Placed machines:", len(st.session_state.get("placed_machines", [])))
                    st.write("Trace count:", len(fig.data))
                    st.write("Trace map:", st.session_state.get("editor_trace_map", []))
                
                trace_types = [t["entity_type"] for t in st.session_state.editor_trace_map]
                dim_ok = (
                    "dimension_machine_x_text" in trace_types
                    and "dimension_machine_y_text" in trace_types
                )
                results.append(("Dim mode shows machine dimensions", dim_ok, trace_types))

            finally:
                st.session_state.editor_canvas_mode = original_mode

            all_ok = all(item[1] for item in results)

            if all_ok:
                st.success("All dim visibility regression checks passed.")
            else:
                st.error("One or more dim visibility regression checks failed.")

            for label, passed, trace_types in results:
                if passed:
                    st.success(label)
                else:
                    st.error(label)
                st.write("Trace types:", trace_types)
        if st.button("Run Dim Move Logic Check"):
            if not st.session_state.get("placed_machines"):
                st.error("No machine available for dim move test.")
            else:
                m = st.session_state.placed_machines[0]

                # Reset known values
                m["dim_x_side"] = "below"
                m["dim_y_side"] = "left"
                m["dim_x_line_offset_ft"] = 0.0
                m["dim_y_line_offset_ft"] = 0.0
                m["dim_x_text_anchor_ft"] = 0.0
                m["dim_y_text_anchor_ft"] = 0.0

                # Test X move above
                _apply_machine_dimension_move(0, "x", click_x=10.0, click_y=80.0)
                x_above_ok = m.get("dim_x_side") == "above"

                # Test Y move right
                _apply_machine_dimension_move(0, "y", click_x=80.0, click_y=10.0)
                y_right_ok = m.get("dim_y_side") == "right"

                if x_above_ok:
                    st.success("X dimension mirrors above correctly.")
                else:
                    st.error(f"X dimension did not mirror above. Current side={m.get('dim_x_side')}")

                if y_right_ok:
                    st.success("Y dimension mirrors right correctly.")
                else:
                    st.error(f"Y dimension did not mirror right. Current side={m.get('dim_y_side')}")

                st.write("Machine dimension state:", {
                    "dim_x_side": m.get("dim_x_side"),
                    "dim_y_side": m.get("dim_y_side"),
                    "dim_x_line_offset_ft": m.get("dim_x_line_offset_ft"),
                    "dim_y_line_offset_ft": m.get("dim_y_line_offset_ft"),
                    "dim_x_text_anchor_ft": m.get("dim_x_text_anchor_ft"),
                    "dim_y_text_anchor_ft": m.get("dim_y_text_anchor_ft"),
                })                

def _snap_value(value, snap_ft, enabled=True):
    if not enabled:
        return float(value)
    snap_ft = max(float(snap_ft), 1.0)
    return round(float(value) / snap_ft) * snap_ft


def _clamp_to_floor(x, y, floor_w, floor_h):
    x = max(0.0, min(float(floor_w), float(x)))
    y = max(0.0, min(float(floor_h), float(y)))
    return x, y

def _clamp_conduit_to_floor(x_vals, y_vals, floor_w, floor_h):
    if not x_vals or not y_vals or len(x_vals) != len(y_vals):
        return x_vals, y_vals

    min_x = min(float(x) for x in x_vals)
    max_x = max(float(x) for x in x_vals)
    min_y = min(float(y) for y in y_vals)
    max_y = max(float(y) for y in y_vals)

    shift_x = 0.0
    shift_y = 0.0

    if min_x < 0.0:
        shift_x = -min_x
    elif max_x > floor_w:
        shift_x = floor_w - max_x

    if min_y < 0.0:
        shift_y = -min_y
    elif max_y > floor_h:
        shift_y = floor_h - max_y

    new_x = [float(x) + shift_x for x in x_vals]
    new_y = [float(y) + shift_y for y in y_vals]
    return new_x, new_y

def _clear_move_mode_state():
    st.session_state.editor_move_awaiting_target = False
    st.session_state.editor_move_selected_type = ""
    st.session_state.editor_move_selected_index = -1
    st.session_state.editor_move_selected_vertex_index = -1
    st.session_state.editor_move_selected_workflow_point_index = -1

def _clear_dimension_move_state():
    st.session_state.editor_dim_move_awaiting_target = False
    st.session_state.editor_dim_selected_owner_type = ""
    st.session_state.editor_dim_selected_owner_index = -1
    st.session_state.editor_dim_selected_sub_index = -1
    st.session_state.editor_dim_selected_owner_id = ""
    st.session_state.editor_dim_selected_axis = ""


def _resolve_canvas_click(point_data):
    """
    Resolve a Plotly click payload into a normalized click-info dict.

    Returns dict with:
      entity_type
      obj_index
      sub_index
      x
      y

    entity_type may be:
      machine, lighting, conduit, conduit_vertex, workflow, workflow_point, crane,
      or normalized "dimension" for dimension-text clicks.
    """
    if not point_data:
        return None

    clicked = point_data[0]
    x_val = clicked.get("x", None)
    y_val = clicked.get("y", None)
    customdata = clicked.get("customdata", None)

    if x_val is not None:
        st.session_state.editor_last_pick_x = float(x_val)
        st.session_state.editor_last_mouse_x = float(x_val)
    if y_val is not None:
        st.session_state.editor_last_pick_y = float(y_val)
        st.session_state.editor_last_mouse_y = float(y_val)

    # Preferred path: direct customdata on click payload
    if customdata and len(customdata) >= 4:
        try:
            entity_type = str(customdata[0])
            obj_index = int(customdata[1])
            obj_id = str(customdata[2])
            sub_index = int(customdata[3])

            if entity_type == "dimension_machine_x_text":
                return {
                    "entity_type": "dimension",
                    "owner_type": "machine",
                    "obj_index": obj_index,
                    "sub_index": sub_index,
                    "owner_id": obj_id,
                    "axis": "x",
                    "part": "text",
                    "x": float(x_val) if x_val is not None else None,
                    "y": float(y_val) if y_val is not None else None,
                }

            if entity_type == "dimension_machine_y_text":
                return {
                    "entity_type": "dimension",
                    "owner_type": "machine",
                    "obj_index": obj_index,
                    "sub_index": sub_index,
                    "owner_id": obj_id,
                    "axis": "y",
                    "part": "text",
                    "x": float(x_val) if x_val is not None else None,
                    "y": float(y_val) if y_val is not None else None,
                }
            if entity_type == "dimension_conduit_vertex_x_text":
                return {
                    "entity_type": "dimension",
                    "owner_type": "conduit_vertex",
                    "obj_index": obj_index,
                    "sub_index": sub_index,
                    "owner_id": obj_id,
                    "axis": "x",
                    "part": "text",
                    "x": float(x_val) if x_val is not None else None,
                    "y": float(y_val) if y_val is not None else None,
                }

            if entity_type == "dimension_conduit_vertex_y_text":
                return {
                    "entity_type": "dimension",
                    "owner_type": "conduit_vertex",
                    "obj_index": obj_index,
                    "sub_index": sub_index,
                    "owner_id": obj_id,
                    "axis": "y",
                    "part": "text",
                    "x": float(x_val) if x_val is not None else None,
                    "y": float(y_val) if y_val is not None else None,
                }

            if entity_type == "dimension_workflow_point_x_text":
                return {
                    "entity_type": "dimension",
                    "owner_type": "workflow_point",
                    "obj_index": obj_index,
                    "sub_index": sub_index,
                    "owner_id": obj_id,
                    "axis": "x",
                    "part": "text",
                    "x": float(x_val) if x_val is not None else None,
                    "y": float(y_val) if y_val is not None else None,
                }

            if entity_type == "dimension_workflow_point_y_text":
                return {
                    "entity_type": "dimension",
                    "owner_type": "workflow_point",
                    "obj_index": obj_index,
                    "sub_index": sub_index,
                    "owner_id": obj_id,
                    "axis": "y",
                    "part": "text",
                    "x": float(x_val) if x_val is not None else None,
                    "y": float(y_val) if y_val is not None else None,
                }    

            return {
                "entity_type": entity_type,
                "obj_index": obj_index,
                "sub_index": sub_index,
                "x": float(x_val) if x_val is not None else None,
                "y": float(y_val) if y_val is not None else None,
            }
        except Exception:
            pass

    # Fallback path: curveNumber -> trace map
    curve_number = clicked.get("curveNumber", None)
    trace_map = st.session_state.get("editor_trace_map", [])

    if curve_number is not None:
        try:
            curve_number = int(curve_number)
            if 0 <= curve_number < len(trace_map):
                mapped = trace_map[curve_number]
                entity_type = str(mapped.get("entity_type", ""))
                obj_index = int(mapped.get("obj_index", -1))
                sub_index = int(mapped.get("sub_index", -1))
                obj_id = str(mapped.get("id", ""))

                if entity_type == "dimension_machine_x_text":
                    return {
                        "entity_type": "dimension",
                        "owner_type": "machine",
                        "obj_index": obj_index,
                        "sub_index": sub_index,
                        "owner_id": obj_id,
                        "axis": "x",
                        "part": "text",
                        "x": float(x_val) if x_val is not None else None,
                        "y": float(y_val) if y_val is not None else None,
                    }

                if entity_type == "dimension_machine_y_text":
                    return {
                        "entity_type": "dimension",
                        "owner_type": "machine",
                        "obj_index": obj_index,
                        "sub_index": sub_index,
                        "owner_id": obj_id,
                        "axis": "y",
                        "part": "text",
                        "x": float(x_val) if x_val is not None else None,
                        "y": float(y_val) if y_val is not None else None,
                    }
                if entity_type == "dimension_conduit_vertex_x_text":
                    return {
                        "entity_type": "dimension",
                        "owner_type": "conduit_vertex",
                        "obj_index": obj_index,
                        "sub_index": sub_index,
                        "owner_id": obj_id,
                        "axis": "x",
                        "part": "text",
                        "x": float(x_val) if x_val is not None else None,
                        "y": float(y_val) if y_val is not None else None,
                    }

                if entity_type == "dimension_conduit_vertex_y_text":
                    return {
                        "entity_type": "dimension",
                        "owner_type": "conduit_vertex",
                        "obj_index": obj_index,
                        "sub_index": sub_index,
                        "owner_id": obj_id,
                        "axis": "y",
                        "part": "text",
                        "x": float(x_val) if x_val is not None else None,
                        "y": float(y_val) if y_val is not None else None,
                    }

                if entity_type == "dimension_workflow_point_x_text":
                    return {
                        "entity_type": "dimension",
                        "owner_type": "workflow_point",
                        "obj_index": obj_index,
                        "sub_index": sub_index,
                        "owner_id": obj_id,
                        "axis": "x",
                        "part": "text",
                        "x": float(x_val) if x_val is not None else None,
                        "y": float(y_val) if y_val is not None else None,
                    }

                if entity_type == "dimension_workflow_point_y_text":
                    return {
                        "entity_type": "dimension",
                        "owner_type": "workflow_point",
                        "obj_index": obj_index,
                        "sub_index": sub_index,
                        "owner_id": obj_id,
                        "axis": "y",
                        "part": "text",
                        "x": float(x_val) if x_val is not None else None,
                        "y": float(y_val) if y_val is not None else None,
                    }                    

                return {
                    "entity_type": entity_type,
                    "obj_index": obj_index,
                    "sub_index": sub_index,
                    "x": float(x_val) if x_val is not None else None,
                    "y": float(y_val) if y_val is not None else None,
                }

            if entity_type == "dimension_lighting_x_text":
                return {
                    "entity_type": "dimension",
                    "owner_type": "lighting",
                    "obj_index": obj_index,
                    "sub_index": sub_index,
                    "owner_id": obj_id,
                    "axis": "x",
                    "part": "text",
                    "x": float(x_val) if x_val is not None else None,
                    "y": float(y_val) if y_val is not None else None,
                }

            if entity_type == "dimension_lighting_y_text":
                return {
                    "entity_type": "dimension",
                    "owner_type": "lighting",
                    "obj_index": obj_index,
                    "sub_index": sub_index,
                    "owner_id": obj_id,
                    "axis": "y",
                    "part": "text",
                    "x": float(x_val) if x_val is not None else None,
                    "y": float(y_val) if y_val is not None else None,
                }

            if entity_type == "dimension_conduit_note":
                return {
                    "entity_type": "dimension",
                    "owner_type": "conduit",
                    "obj_index": obj_index,
                    "sub_index": sub_index,
                    "owner_id": obj_id,
                    "axis": "note",
                    "part": "text",
                    "x": float(x_val) if x_val is not None else None,
                    "y": float(y_val) if y_val is not None else None,
                }

            if entity_type == "dimension_workflow_note":
                return {
                    "entity_type": "dimension",
                    "owner_type": "workflow",
                    "obj_index": obj_index,
                    "sub_index": sub_index,
                    "owner_id": obj_id,
                    "axis": "note",
                    "part": "text",
                    "x": float(x_val) if x_val is not None else None,
                    "y": float(y_val) if y_val is not None else None,
                }

            if entity_type == "dimension_crane_note":
                return {
                    "entity_type": "dimension",
                    "owner_type": "crane",
                    "obj_index": obj_index,
                    "sub_index": sub_index,
                    "owner_id": obj_id,
                    "axis": "note",
                    "part": "text",
                    "x": float(x_val) if x_val is not None else None,
                    "y": float(y_val) if y_val is not None else None,
                }
        
        except Exception:
            pass

    # Last resort: coordinates only
    if x_val is not None and y_val is not None:
        return {
            "entity_type": None,
            "obj_index": -1,
            "sub_index": -1,
            "x": float(x_val),
            "y": float(y_val),
        }

    return None


def _apply_selection_from_click_info(click_info):
    if not click_info:
        return

    entity_type = click_info.get("entity_type", None)
    obj_index = int(click_info.get("obj_index", -1))
    sub_index = int(click_info.get("sub_index", -1))

    if not entity_type:
        x_val = click_info.get("x", None)
        y_val = click_info.get("y", None)
        if x_val is not None and y_val is not None:
            apply_canvas_pick(float(x_val), float(y_val))
            st.session_state.editor_phase3_status = (
                f"Canvas metadata missing; fallback used at "
                f"X={float(x_val):.2f}, Y={float(y_val):.2f}."
            )
        else:
            st.session_state.editor_phase3_status = (
                "Canvas click could not be resolved."
            )
        return

    if entity_type == "floor":
        st.session_state.editor_phase3_status = (
            "Floor clicked. No object selected."
        )
        return

    if entity_type == "machine":
        st.session_state["editor_selected_type"] = "machine"
        st.session_state["editor_selected_index"] = obj_index
        st.session_state["editor_selected_vertex_index"] = 0
        st.session_state["editor_workflow_selected_point_index"] = 0
        st.session_state.editor_phase3_status = f"Canvas selected machine {obj_index}."

    elif entity_type == "lighting":
        st.session_state["editor_selected_type"] = "lighting"
        st.session_state["editor_selected_index"] = obj_index
        st.session_state["editor_selected_vertex_index"] = 0
        st.session_state["editor_workflow_selected_point_index"] = 0
        st.session_state.editor_phase3_status = f"Canvas selected lighting {obj_index}."

    elif entity_type == "conduit":
        st.session_state["editor_selected_type"] = "conduit"
        st.session_state["editor_selected_index"] = obj_index
        st.session_state["editor_selected_vertex_index"] = 0
        st.session_state["editor_workflow_selected_point_index"] = 0
        st.session_state.editor_phase3_status = f"Canvas selected conduit {obj_index}."

    elif entity_type == "conduit_vertex":
        st.session_state["editor_selected_type"] = "conduit"
        st.session_state["editor_selected_index"] = obj_index
        st.session_state["editor_selected_vertex_index"] = sub_index
        st.session_state["editor_workflow_selected_point_index"] = 0
        st.session_state.editor_phase3_status = (
            f"Canvas selected conduit {obj_index} vertex {sub_index}."
        )

    elif entity_type == "workflow":
        st.session_state["editor_selected_type"] = "workflow"
        st.session_state["editor_selected_index"] = 0
        st.session_state["editor_selected_vertex_index"] = 0
        if sub_index >= 0:
            st.session_state["editor_workflow_selected_point_index"] = sub_index
        st.session_state.editor_phase3_status = "Canvas selected workflow."

    elif entity_type == "workflow_point":
        st.session_state["editor_selected_type"] = "workflow"
        st.session_state["editor_selected_index"] = 0
        st.session_state["editor_selected_vertex_index"] = 0
        st.session_state["editor_workflow_selected_point_index"] = sub_index
        st.session_state.editor_phase3_status = (
            f"Canvas selected workflow point {sub_index}."
        )

    elif entity_type == "crane":
        st.session_state["editor_selected_type"] = "crane"
        st.session_state["editor_selected_index"] = obj_index
        st.session_state["editor_selected_vertex_index"] = 0
        st.session_state["editor_workflow_selected_point_index"] = 0
        st.session_state.editor_phase3_status = f"Canvas selected crane {obj_index}."

    else:
        st.session_state.editor_phase3_status = (
            f"Canvas click received unknown entity type: {entity_type}"
        )
        return

    st.session_state.editor_prime_inputs = True
    st.session_state.editor_canvas_refresh_token += 1

def _apply_canvas_click_selection(point_data):
    click_info = _resolve_canvas_click(point_data)
    _apply_selection_from_click_info(click_info)


def _begin_move_from_click_info(click_info):
    if not click_info:
        _clear_move_mode_state()
        st.session_state.editor_phase3_status = "Move mode: no clickable object was found."
        return

    entity_type = click_info.get("entity_type", None)
    obj_index = int(click_info.get("obj_index", -1))
    sub_index = int(click_info.get("sub_index", -1))

    if entity_type is None or entity_type == "floor":
        _clear_move_mode_state()
        st.session_state.editor_phase3_status = (
            "Move mode requires clicking a selectable object first."
        )
        return

    def _safe_machine_label(idx):
        items = st.session_state.get("placed_machines", [])
        if 0 <= idx < len(items):
            return str(items[idx].get("id", f"M-{idx+1:03d}"))
        return f"machine {idx}"

    def _safe_lighting_label(idx):
        items = st.session_state.get("placed_lighting", [])
        if 0 <= idx < len(items):
            return str(items[idx].get("id", f"L-{idx+1:03d}"))
        return f"lighting {idx}"

    def _safe_conduit_label(idx):
        items = st.session_state.get("placed_conduits", [])
        if 0 <= idx < len(items):
            return str(items[idx].get("id", f"C-{idx+1:03d}"))
        return f"conduit {idx}"

    def _safe_crane_label(idx):
        items = st.session_state.get("placed_cranes", [])
        if 0 <= idx < len(items):
            return str(items[idx].get("id", f"CR-{idx+1:03d}"))
        return f"crane {idx}"

    move_label = ""

    if entity_type == "machine":
        st.session_state.editor_move_selected_type = "machine"
        st.session_state.editor_move_selected_index = obj_index
        st.session_state.editor_move_selected_vertex_index = -1
        st.session_state.editor_move_selected_workflow_point_index = -1
        move_label = f"machine {_safe_machine_label(obj_index)}"

    elif entity_type == "lighting":
        st.session_state.editor_move_selected_type = "lighting"
        st.session_state.editor_move_selected_index = obj_index
        st.session_state.editor_move_selected_vertex_index = -1
        st.session_state.editor_move_selected_workflow_point_index = -1
        move_label = f"lighting {_safe_lighting_label(obj_index)}"

    elif entity_type == "conduit":
        st.session_state.editor_move_selected_type = "conduit"
        st.session_state.editor_move_selected_index = obj_index
        st.session_state.editor_move_selected_vertex_index = -1
        st.session_state.editor_move_selected_workflow_point_index = -1
        move_label = f"conduit {_safe_conduit_label(obj_index)}"

    elif entity_type == "conduit_vertex":
        st.session_state.editor_move_selected_type = "conduit_vertex"
        st.session_state.editor_move_selected_index = obj_index
        st.session_state.editor_move_selected_vertex_index = sub_index
        st.session_state.editor_move_selected_workflow_point_index = -1
        move_label = f"conduit {_safe_conduit_label(obj_index)} vertex {sub_index + 1}"

    elif entity_type == "workflow":
        st.session_state.editor_move_selected_type = "workflow_point"
        st.session_state.editor_move_selected_index = 0
        st.session_state.editor_move_selected_vertex_index = -1
        st.session_state.editor_move_selected_workflow_point_index = int(
            st.session_state.get("editor_workflow_selected_point_index", 0)
        )
        move_label = (
            f"workflow point "
            f"{st.session_state.editor_move_selected_workflow_point_index + 1}"
        )

    elif entity_type == "workflow_point":
        st.session_state.editor_move_selected_type = "workflow_point"
        st.session_state.editor_move_selected_index = 0
        st.session_state.editor_move_selected_vertex_index = -1
        st.session_state.editor_move_selected_workflow_point_index = sub_index
        move_label = f"workflow point {sub_index + 1}"

    elif entity_type == "crane":
        st.session_state.editor_move_selected_type = "crane"
        st.session_state.editor_move_selected_index = obj_index
        st.session_state.editor_move_selected_vertex_index = -1
        st.session_state.editor_move_selected_workflow_point_index = -1
        move_label = f"crane {_safe_crane_label(obj_index)}"

    else:
        _clear_move_mode_state()
        st.session_state.editor_phase3_status = (
            f"Move mode does not support entity type: {entity_type}"
        )
        return

    st.session_state.editor_move_awaiting_target = True
    st.session_state.editor_phase3_status = f"Moving {move_label}: click destination."

def _begin_dimension_move_from_click_info(click_info):
    if not click_info:
        _clear_dimension_move_state()
        st.session_state.editor_phase3_status = "Dim mode: no dimension was clicked."
        return

    if click_info.get("entity_type") != "dimension":
        _clear_dimension_move_state()
        st.session_state.editor_phase3_status = "Dim mode: click a dimension label."
        return

    if click_info.get("part") != "text":
        st.session_state.editor_phase3_status = "Dim mode: click the dimension text."
        return

    owner_type = str(click_info.get("owner_type", ""))
    obj_index = int(click_info.get("obj_index", -1))
    sub_index = int(click_info.get("sub_index", -1))
    owner_id = str(click_info.get("owner_id", ""))
    axis = str(click_info.get("axis", ""))

    st.session_state.editor_selected_dimension_kind = owner_type
    st.session_state.editor_selected_dimension_owner_id = owner_id
    st.session_state.editor_selected_dimension_axis = axis

    st.session_state.editor_dim_move_awaiting_target = True
    st.session_state.editor_dim_selected_owner_type = owner_type
    st.session_state.editor_dim_selected_owner_index = obj_index
    st.session_state.editor_dim_selected_sub_index = sub_index
    st.session_state.editor_dim_selected_owner_id = owner_id
    st.session_state.editor_dim_selected_axis = axis

    st.session_state.editor_phase3_status = (
        f"Moving {owner_type} {owner_id} {axis.upper()} dimension: click destination."
    )


def _apply_move_to_click(point_data):
    click_info = _resolve_canvas_click(point_data)
    if not click_info:
        st.session_state["editor_phase3_status"] = "Move target click was not resolved."
        return

    x_val = click_info.get("x", None)
    y_val = click_info.get("y", None)

    if x_val is None or y_val is None:
        st.session_state["editor_phase3_status"] = (
            "Move target click did not include coordinates."
        )
        return

    floor_w = float(st.session_state.floor_w)
    floor_h = float(st.session_state.floor_h)
    x_val, y_val = _clamp_to_floor(float(x_val), float(y_val), floor_w, floor_h)

    move_type = st.session_state.get("editor_move_selected_type", "")
    move_index = int(st.session_state.get("editor_move_selected_index", -1))
    move_vertex_index = int(
        st.session_state.get("editor_move_selected_vertex_index", -1)
    )
    move_workflow_point_index = int(
        st.session_state.get("editor_move_selected_workflow_point_index", -1)
    )

    if move_type == "machine":
        st.session_state["editor_selected_type"] = "machine"
        st.session_state["editor_selected_index"] = move_index
        st.session_state["editor_selected_vertex_index"] = 0
        st.session_state["editor_workflow_selected_point_index"] = 0
        _set_selected_xy(x_val, y_val)
        st.session_state.editor_phase3_status = (
            f"Moved machine {move_index} to X={x_val:.2f}, Y={y_val:.2f}."
        )

    elif move_type == "lighting":
        st.session_state["editor_selected_type"] = "lighting"
        st.session_state["editor_selected_index"] = move_index
        st.session_state["editor_selected_vertex_index"] = 0
        st.session_state["editor_workflow_selected_point_index"] = 0
        _set_selected_xy(x_val, y_val)
        st.session_state.editor_phase3_status = (
            f"Moved lighting {move_index} to X={x_val:.2f}, Y={y_val:.2f}."
        )

    elif move_type == "conduit":
        st.session_state["editor_selected_type"] = "conduit"
        st.session_state["editor_selected_index"] = move_index
        st.session_state["editor_selected_vertex_index"] = 0
        st.session_state["editor_workflow_selected_point_index"] = 0
        _set_selected_xy(x_val, y_val)
        st.session_state.editor_phase3_status = (
            f"Moved conduit {move_index} to X={x_val:.2f}, Y={y_val:.2f}."
        )

    elif move_type == "conduit_vertex":
        st.session_state["editor_selected_type"] = "conduit"
        st.session_state["editor_selected_index"] = move_index
        st.session_state["editor_selected_vertex_index"] = move_vertex_index
        st.session_state["editor_pending_vertex_index"] = move_vertex_index
        _apply_pending_vertex_selection_if_any()
        st.session_state["editor_workflow_selected_point_index"] = 0
        st.session_state["editor_prime_inputs"] = True

        _set_selected_conduit_vertex_xy(x_val, y_val)

        st.session_state.editor_phase3_status = (
            f"Moved conduit {move_index} vertex {move_vertex_index} "
            f"to X={x_val:.2f}, Y={y_val:.2f}."
        )

    elif move_type == "workflow_point":
        st.session_state["editor_selected_type"] = "workflow"
        st.session_state["editor_selected_index"] = 0
        st.session_state["editor_selected_vertex_index"] = 0
        st.session_state["editor_workflow_selected_point_index"] = (
            move_workflow_point_index
        )
        st.session_state["editor_pending_workflow_point_index"] = (
            move_workflow_point_index
        )
        _apply_pending_workflow_point_selection_if_any()
        st.session_state["editor_prime_inputs"] = True

        _set_selected_workflow_point_xy(x_val, y_val)

        st.session_state.editor_phase3_status = (
            f"Moved workflow point {move_workflow_point_index} "
            f"to X={x_val:.2f}, Y={y_val:.2f}."
        )

    elif move_type == "crane":
        st.session_state["editor_selected_type"] = "crane"
        st.session_state["editor_selected_index"] = move_index
        st.session_state["editor_selected_vertex_index"] = 0
        st.session_state["editor_workflow_selected_point_index"] = 0
        _set_selected_crane_center_xy(x_val, y_val)
        st.session_state.editor_phase3_status = (
            f"Moved crane {move_index} to X={x_val:.2f}, Y={y_val:.2f}."
        )

    else:
        st.session_state["editor_phase3_status"] = (
            f"Unsupported move target type: {move_type}"
        )
        return

    st.session_state["editor_last_mouse_x"] = x_val
    st.session_state["editor_last_mouse_y"] = y_val
    st.session_state["editor_last_pick_x"] = x_val
    st.session_state["editor_last_pick_y"] = y_val
    st.session_state["editor_prime_inputs"] = True
    st.session_state["editor_canvas_refresh_token"] += 1
    _clear_move_mode_state()

def _apply_machine_dimension_move(idx, axis, click_x, click_y):
    machines = st.session_state.placed_machines
    if idx < 0 or idx >= len(machines):
        st.session_state.editor_phase3_status = "Invalid machine dimension target."
        return

    m = machines[idx]
    mx = float(m.get("x", 0.0))
    my = float(m.get("y", 0.0))
    mw = float(m.get("Width", 0.0))
    mh = float(m.get("Height", 0.0))
    so = float(m.get("Standoff", 0.0))

    half_w = mw / 2.0
    half_h = mh / 2.0
    clear_pad = max(1.0, 0.6 * so, 0.12 * max(mw, mh))

    if axis == "x":
        top_ref = my + half_h + so + clear_pad
        bot_ref = my - half_h - so - clear_pad

        if click_y >= my:
            m["dim_x_side"] = "above"
            m["dim_x_line_offset_ft"] = max(0.0, click_y - top_ref)
            m["dim_x_text_offset_ft"] = 0.0
        else:
            m["dim_x_side"] = "below"
            m["dim_x_line_offset_ft"] = max(0.0, bot_ref - click_y)
            m["dim_x_text_offset_ft"] = 0.0

        m["dim_x_text_anchor_ft"] = click_x - ((0.0 + mx) / 2.0)

    elif axis == "y":
        right_ref = mx + half_w + so + clear_pad
        left_ref = mx - half_w - so - clear_pad

        if click_x >= mx:
            m["dim_y_side"] = "right"
            m["dim_y_line_offset_ft"] = max(0.0, click_x - right_ref)
            m["dim_y_text_offset_ft"] = 0.0
        else:
            m["dim_y_side"] = "left"
            m["dim_y_line_offset_ft"] = max(0.0, left_ref - click_x)
            m["dim_y_text_offset_ft"] = 0.0

        m["dim_y_text_anchor_ft"] = click_y - ((0.0 + my) / 2.0)

    st.session_state.editor_phase3_status = (
        f"Moved machine {m.get('id', idx)} {axis.upper()} dimension."
    )

def _apply_lighting_dimension_move(idx, axis, click_x, click_y):
    lights = st.session_state.placed_lighting
    if idx < 0 or idx >= len(lights):
        st.session_state.editor_phase3_status = "Invalid lighting dimension target."
        return

    l = lights[idx]
    lx = float(l.get("x", 0.0))
    ly = float(l.get("y", 0.0))
    clear_pad = 1.0

    if axis == "x":
        top_ref = ly + clear_pad
        bot_ref = ly - clear_pad

        if click_y >= ly:
            l["dim_x_side"] = "above"
            l["dim_x_line_offset_ft"] = max(0.0, click_y - top_ref)
            l["dim_x_text_offset_ft"] = 0.0
        else:
            l["dim_x_side"] = "below"
            l["dim_x_line_offset_ft"] = max(0.0, bot_ref - click_y)
            l["dim_x_text_offset_ft"] = 0.0

        l["dim_x_text_anchor_ft"] = click_x - ((0.0 + lx) / 2.0)

    elif axis == "y":
        right_ref = lx + clear_pad
        left_ref = lx - clear_pad

        if click_x >= lx:
            l["dim_y_side"] = "right"
            l["dim_y_line_offset_ft"] = max(0.0, click_x - right_ref)
            l["dim_y_text_offset_ft"] = 0.0
        else:
            l["dim_y_side"] = "left"
            l["dim_y_line_offset_ft"] = max(0.0, left_ref - click_x)
            l["dim_y_text_offset_ft"] = 0.0

        l["dim_y_text_anchor_ft"] = click_y - ((0.0 + ly) / 2.0)

    st.session_state.editor_phase3_status = (
        f"Moved lighting {l.get('id', idx)} {axis.upper()} dimension."
    )


def _apply_conduit_dimension_move(idx, click_x, click_y):
    conduits = st.session_state.placed_conduits
    if idx < 0 or idx >= len(conduits):
        st.session_state.editor_phase3_status = "Invalid conduit dimension target."
        return

    c = conduits[idx]
    xs = [float(v) for v in c.get("x", [])]
    ys = [float(v) for v in c.get("y", [])]
    if not xs or not ys or len(xs) != len(ys):
        st.session_state.editor_phase3_status = "Conduit geometry invalid."
        return

    cx = sum(xs) / len(xs)
    cy = sum(ys) / len(ys)

    c["dim_label_x_offset_ft"] = click_x - cx
    c["dim_label_y_offset_ft"] = click_y - cy

    st.session_state.editor_phase3_status = (
        f"Moved conduit {c.get('id', idx)} note."
    )


def _apply_workflow_dimension_move(click_x, click_y):
    if "path_points" not in st.session_state or len(st.session_state.path_points) == 0:
        st.session_state.editor_phase3_status = "Workflow geometry invalid."
        return

    wdf = st.session_state.path_points
    xs = [float(v) for v in wdf["X Coordinate"].tolist()]
    ys = [float(v) for v in wdf["Y Coordinate"].tolist()]
    cx = sum(xs) / len(xs)
    cy = sum(ys) / len(ys)

    st.session_state.workflow_dim_label_x_offset_ft = click_x - cx
    st.session_state.workflow_dim_label_y_offset_ft = click_y - cy

    st.session_state.editor_phase3_status = "Moved workflow note."

def _apply_conduit_vertex_dimension_move(obj_index, vertex_index, axis, click_x, click_y):
    conduits = st.session_state.get("placed_conduits", [])
    if obj_index < 0 or obj_index >= len(conduits):
        st.session_state.editor_phase3_status = "Invalid conduit vertex dimension target."
        return

    c = conduits[obj_index]
    xs = [float(v) for v in c.get("x", [])]
    ys = [float(v) for v in c.get("y", [])]

    if vertex_index < 0 or vertex_index >= len(xs) or vertex_index >= len(ys):
        st.session_state.editor_phase3_status = "Invalid conduit vertex index."
        return

    px = xs[vertex_index]
    py = ys[vertex_index]

    if "vertex_dim_offsets" not in c or not isinstance(c.get("vertex_dim_offsets"), dict):
        c["vertex_dim_offsets"] = {}

    key = str(vertex_index)
    if key not in c["vertex_dim_offsets"] or not isinstance(c["vertex_dim_offsets"][key], dict):
        c["vertex_dim_offsets"][key] = {
            "x_line_dy_ft": 0.0,
            "y_line_dx_ft": 0.0,
            "x_text_dx_ft": 0.0,
            "x_text_dy_ft": 0.0,
            "y_text_dx_ft": 0.0,
            "y_text_dy_ft": 0.0,
        }

    if axis == "x":
        default_line_y = 0.0 - 2.5 - (vertex_index * 1.0)
        default_text_x = (0.0 + px) / 2.0

        c["vertex_dim_offsets"][key]["x_line_dy_ft"] = float(click_y) - default_line_y
        c["vertex_dim_offsets"][key]["x_text_dx_ft"] = float(click_x) - default_text_x
        c["vertex_dim_offsets"][key]["x_text_dy_ft"] = 0.0

    elif axis == "y":
        default_line_x = 0.0 - 2.5 - (vertex_index * 1.0)
        default_text_y = (0.0 + py) / 2.0

        c["vertex_dim_offsets"][key]["y_line_dx_ft"] = float(click_x) - default_line_x
        c["vertex_dim_offsets"][key]["y_text_dx_ft"] = 0.0
        c["vertex_dim_offsets"][key]["y_text_dy_ft"] = float(click_y) - default_text_y

    st.session_state.editor_phase3_status = (
        f"Moved conduit {c.get('id', obj_index)} vertex {vertex_index + 1} {axis.upper()} dimension."
    )

def _apply_workflow_point_dimension_move(point_index, axis, click_x, click_y):
    if "path_points" not in st.session_state or len(st.session_state.path_points) == 0:
        st.session_state.editor_phase3_status = "Workflow geometry invalid."
        return

    _normalize_workflow_df()
    df = st.session_state.path_points.copy()

    if point_index < 0 or point_index >= len(df):
        st.session_state.editor_phase3_status = "Invalid workflow point dimension target."
        return

    px = float(df.iloc[point_index]["X Coordinate"])
    py = float(df.iloc[point_index]["Y Coordinate"])

    for col in [
        "dim_x_line_dy_ft",
        "dim_y_line_dx_ft",
        "dim_x_text_dx_ft",
        "dim_x_text_dy_ft",
        "dim_y_text_dx_ft",
        "dim_y_text_dy_ft",
    ]:
        if col not in df.columns:
            df[col] = 0.0

    if axis == "x":
        default_line_y = 0.0 - 3.0 - (point_index * 1.0)
        default_text_x = (0.0 + px) / 2.0

        # Move line vertically to clicked Y
        df.at[point_index, "dim_x_line_dy_ft"] = float(click_y) - default_line_y

        # Move text only along X; keep its vertical gap tied to the moved line
        df.at[point_index, "dim_x_text_dx_ft"] = float(click_x) - default_text_x
        df.at[point_index, "dim_x_text_dy_ft"] = 0.0

    elif axis == "y":
        default_line_x = 0.0 - 3.0 - (point_index * 1.0)
        default_text_y = (0.0 + py) / 2.0

        # Move line horizontally to clicked X
        df.at[point_index, "dim_y_line_dx_ft"] = float(click_x) - default_line_x

        # Move text only along Y; keep its horizontal gap tied to the moved line
        df.at[point_index, "dim_y_text_dx_ft"] = 0.0
        df.at[point_index, "dim_y_text_dy_ft"] = float(click_y) - default_text_y

    st.session_state.path_points = df
    st.session_state.editor_phase3_status = (
        f"Moved workflow point {point_index + 1} {axis.upper()} dimension."
    )


def _apply_crane_dimension_move(idx, click_x, click_y):
    cranes = st.session_state.placed_cranes
    if idx < 0 or idx >= len(cranes):
        st.session_state.editor_phase3_status = "Invalid crane dimension target."
        return

    cr = cranes[idx]
    ll_x = float(cr.get("ll_x", 0.0))
    ll_y = float(cr.get("ll_y", 0.0))
    ur_x = float(cr.get("ur_x", 0.0))
    ur_y = float(cr.get("ur_y", 0.0))
    cx = (ll_x + ur_x) / 2.0
    cy = (ll_y + ur_y) / 2.0

    cr["dim_label_x_offset_ft"] = click_x - cx
    cr["dim_label_y_offset_ft"] = click_y - cy

    st.session_state.editor_phase3_status = (
        f"Moved crane {cr.get('id', idx)} note."
    )


def _apply_dimension_move_to_click(point_data):
    click_info = _resolve_canvas_click(point_data)
    if not click_info:
        return

    x_val = float(click_info.get("x", 0.0))
    y_val = float(click_info.get("y", 0.0))

    if st.session_state.get("editor_snap_enabled", False):
        x_val = _snap_value(x_val, st.session_state.editor_snap_ft, True)
        y_val = _snap_value(y_val, st.session_state.editor_snap_ft, True)

    x_val, y_val = _clamp_to_floor(
        x_val,
        y_val,
        st.session_state.floor_w,
        st.session_state.floor_h,
    )

    owner_type = st.session_state.get("editor_dim_selected_owner_type", "")
    owner_index = int(st.session_state.get("editor_dim_selected_owner_index", -1))
    owner_sub_index = int(st.session_state.get("editor_dim_selected_sub_index", -1))
    axis = st.session_state.get("editor_dim_selected_axis", "")

    if owner_type == "machine":
        _apply_machine_dimension_move(owner_index, axis, x_val, y_val)
    elif owner_type == "lighting":
        _apply_lighting_dimension_move(owner_index, axis, x_val, y_val)
    elif owner_type == "conduit":
        _apply_conduit_dimension_move(owner_index, x_val, y_val)
    elif owner_type == "workflow":
        _apply_workflow_dimension_move(x_val, y_val)
    elif owner_type == "crane":
        _apply_crane_dimension_move(owner_index, x_val, y_val)
    elif owner_type == "conduit_vertex":
        _apply_conduit_vertex_dimension_move(owner_index, owner_sub_index, axis, x_val, y_val)
    elif owner_type == "workflow_point":
        _apply_workflow_point_dimension_move(owner_sub_index, axis, x_val, y_val)
    else:
        st.session_state.editor_phase3_status = (
            f"Unsupported dimension owner type: {owner_type}"
        )
        return
        
    st.session_state.editor_last_mouse_x = x_val
    st.session_state.editor_last_mouse_y = y_val
    st.session_state.editor_last_pick_x = x_val
    st.session_state.editor_last_pick_y = y_val
    st.session_state.editor_prime_inputs = True
    st.session_state.editor_canvas_refresh_token += 1
    _clear_dimension_move_state()

def _clamp_crane_box(ll_x, ll_y, ur_x, ur_y, floor_w, floor_h):
    ll_x = float(ll_x)
    ll_y = float(ll_y)
    ur_x = float(ur_x)
    ur_y = float(ur_y)
    floor_w = float(floor_w)
    floor_h = float(floor_h)

    width = max(0.1, ur_x - ll_x)
    height = max(0.1, ur_y - ll_y)

    ll_x = max(0.0, min(ll_x, floor_w - width))
    ll_y = max(0.0, min(ll_y, floor_h - height))
    ur_x = ll_x + width
    ur_y = ll_y + height

    return ll_x, ll_y, ur_x, ur_y


def _get_object_list(obj_type):
    if obj_type == "machine":
        return st.session_state.placed_machines
    if obj_type == "lighting":
        return st.session_state.placed_lighting
    if obj_type == "conduit":
        return st.session_state.placed_conduits
    if obj_type == "crane":
        return st.session_state.placed_cranes
    if obj_type == "workflow":
        return [{"id": "WF-001"}] if len(st.session_state.path_points) > 0 else []
    return []


def _get_object_label(obj_type, obj, idx):
    obj_id = obj.get("id", f"{obj_type[:1].upper()}-{idx+1:03d}")

    if obj_type == "machine":
        make = str(obj.get("Make", "")).strip()
        model = str(obj.get("Model", "")).strip()
        suffix = f"{make} {model}".strip()
        return f"{obj_id} - {suffix}" if suffix else obj_id

    if obj_type == "lighting":
        make = str(obj.get("Make", "")).strip()
        fixture_type = str(obj.get("Type", "")).strip()
        suffix = f"{make} {fixture_type}".strip()
        return f"{obj_id} - {suffix}" if suffix else obj_id

    if obj_type == "conduit":
        label = str(obj.get("label", "")).strip()
        points = len(obj.get("x", []))
        suffix = f"{label} ({points} pts)".strip()
        return f"{obj_id} - {suffix}" if suffix else obj_id

    if obj_type == "crane":
        make = str(obj.get("make", "")).strip()
        model = str(obj.get("model", "")).strip()
        suffix = f"{make} {model}".strip()
        return f"{obj_id} - {suffix}" if suffix else obj_id

    if obj_type == "workflow":
        return "WF-001 - Workflow Path"

    return obj_id


def _normalize_selected_index():
    obj_type = st.session_state.editor_selected_type
    items = _get_object_list(obj_type)

    if not items:
        st.session_state.editor_selected_index = 0
        return

    idx = int(st.session_state.get("editor_selected_index", 0))
    idx = max(0, min(idx, len(items) - 1))
    st.session_state.editor_selected_index = idx


def _get_selected_object():
    obj_type = st.session_state.editor_selected_type
    items = _get_object_list(obj_type)

    if not items:
        return None, None, None

    _normalize_selected_index()
    idx = int(st.session_state.editor_selected_index)
    return obj_type, idx, items[idx]


def _object_center(obj_type, obj):
    if obj_type in ["machine", "lighting"]:
        return float(obj.get("x", 0.0)), float(obj.get("y", 0.0))

    if obj_type == "conduit":
        xs = [float(v) for v in obj.get("x", [])]
        ys = [float(v) for v in obj.get("y", [])]
        if xs and ys and len(xs) == len(ys):
            return sum(xs) / len(xs), sum(ys) / len(ys)
        return 0.0, 0.0

    if obj_type == "crane":
        ll_x = float(obj.get("ll_x", 0.0))
        ll_y = float(obj.get("ll_y", 0.0))
        ur_x = float(obj.get("ur_x", 0.0))
        ur_y = float(obj.get("ur_y", 0.0))
        return (ll_x + ur_x) / 2.0, (ll_y + ur_y) / 2.0

    if obj_type == "workflow":
        _normalize_workflow_df()
        df = _workflow_df()
        if len(df) > 0:
            xs = [float(v) for v in df["X Coordinate"].tolist()]
            ys = [float(v) for v in df["Y Coordinate"].tolist()]
            return sum(xs) / len(xs), sum(ys) / len(ys)
        return 0.0, 0.0

    return 0.0, 0.0

def prime_drag_drop_from_selection():
    result = _get_selected_object()
    if result == (None, None, None):
        return

    obj_type, idx, obj = result

    if obj_type in ["machine", "lighting"]:
        cx = float(obj.get("x", 0.0))
        cy = float(obj.get("y", 0.0))
    elif obj_type == "conduit":
        if st.session_state.get("editor_drag_mode", "object") == "conduit_vertex":
            vx = obj.get("x", [])
            vy = obj.get("y", [])
            if vx and vy and len(vx) == len(vy):
                vidx = _get_safe_selected_vertex_index()
                cx = float(vx[vidx])
                cy = float(vy[vidx])
            else:
                cx, cy = _object_center(obj_type, obj)
        else:
            cx, cy = _object_center(obj_type, obj)
    elif obj_type == "workflow":
        _normalize_workflow_df()
        wdf = st.session_state.path_points
        widx = _get_safe_workflow_point_index()
        cx = float(wdf.iloc[widx]["X Coordinate"])
        cy = float(wdf.iloc[widx]["Y Coordinate"])
    elif obj_type == "crane":
        cx = (float(obj.get("ll_x", 0.0)) + float(obj.get("ur_x", 0.0))) / 2.0
        cy = (float(obj.get("ll_y", 0.0)) + float(obj.get("ur_y", 0.0))) / 2.0
    else:
        return

    st.session_state.editor_drag_drop_x_ft = cx
    st.session_state.editor_drag_drop_y_ft = cy


def _get_safe_selected_vertex_index():
    result = _get_selected_object()
    if result == (None, None, None):
        return 0

    obj_type, _, obj = result
    if obj_type != "conduit":
        return 0

    point_count = len(obj.get("x", []))
    if point_count <= 0:
        return 0

    idx = int(st.session_state.get("editor_selected_vertex_index", 0))
    idx = max(0, min(idx, point_count - 1))
    return idx


def _apply_pending_vertex_selection_if_any():
    pending_idx = st.session_state.get("editor_pending_vertex_index", None)
    if pending_idx is not None:
        st.session_state["editor_selected_vertex_index"] = int(pending_idx)
        st.session_state["editor_pending_vertex_index"] = None


def _workflow_df():
    return st.session_state.path_points.copy()


def _workflow_point_count():
    df = _workflow_df()
    return len(df)


def _normalize_workflow_df():
    df = _workflow_df()

    expected_cols = [
        "Point",
        "X Coordinate",
        "Y Coordinate",
        "Safety Standoff (ft)",
        "Movement Speed",
        "dim_x_line_dy_ft",
        "dim_y_line_dx_ft",        
        "dim_x_text_dx_ft",
        "dim_x_text_dy_ft",
        "dim_y_text_dx_ft",
        "dim_y_text_dy_ft",
    ]

    for col in expected_cols:
        if col not in df.columns:
            if col == "Point":
                df[col] = list(range(1, len(df) + 1))
            elif col == "Safety Standoff (ft)":
                df[col] = 5.0
            elif col == "Movement Speed":
                df[col] = 5.0
            else:
                df[col] = 0.0

    df = df[expected_cols].copy()
    df["Point"] = list(range(1, len(df) + 1))
    st.session_state.path_points = df


def _get_safe_workflow_point_index():
    _normalize_workflow_df()
    point_count = _workflow_point_count()
    if point_count <= 0:
        return 0

    idx = int(st.session_state.get("editor_workflow_selected_point_index", 0))
    idx = max(0, min(idx, point_count - 1))
    return idx


def _apply_pending_workflow_point_selection_if_any():
    pending_idx = st.session_state.get("editor_pending_workflow_point_index", None)
    if pending_idx is not None:
        st.session_state["editor_workflow_selected_point_index"] = int(pending_idx)
        st.session_state["editor_pending_workflow_point_index"] = None


def _prime_workflow_inputs_from_selection():
    _normalize_workflow_df()
    df = _workflow_df()

    if len(df) == 0:
        st.session_state["editor_workflow_x_input"] = 0.0
        st.session_state["editor_workflow_y_input"] = 0.0
        st.session_state["editor_workflow_standoff_input"] = 0.0
        st.session_state["editor_workflow_speed_input"] = 0.0
        return

    idx = _get_safe_workflow_point_index()

    st.session_state["editor_workflow_x_input"] = float(df.iloc[idx]["X Coordinate"])
    st.session_state["editor_workflow_y_input"] = float(df.iloc[idx]["Y Coordinate"])
    st.session_state["editor_workflow_standoff_input"] = float(
        df.iloc[idx]["Safety Standoff (ft)"]
    )
    st.session_state["editor_workflow_speed_input"] = float(
        df.iloc[idx]["Movement Speed"]
    )


def _prime_editor_inputs_from_selection():
    result = _get_selected_object()
    if result == (None, None, None):
        st.session_state["editor_coord_x_input"] = 0.0
        st.session_state["editor_coord_y_input"] = 0.0
        st.session_state["editor_box_ll_x_input"] = 0.0
        st.session_state["editor_box_ll_y_input"] = 0.0
        st.session_state["editor_box_ur_x_input"] = 0.0
        st.session_state["editor_box_ur_y_input"] = 0.0
        st.session_state["editor_vertex_x_input"] = 0.0
        st.session_state["editor_vertex_y_input"] = 0.0
        return

    obj_type, _, obj = result

    cx, cy = _object_center(obj_type, obj)
    st.session_state["editor_coord_x_input"] = float(cx)
    st.session_state["editor_coord_y_input"] = float(cy)

    if obj_type == "crane":
        st.session_state["editor_box_ll_x_input"] = float(obj.get("ll_x", 0.0))
        st.session_state["editor_box_ll_y_input"] = float(obj.get("ll_y", 0.0))
        st.session_state["editor_box_ur_x_input"] = float(obj.get("ur_x", 0.0))
        st.session_state["editor_box_ur_y_input"] = float(obj.get("ur_y", 0.0))

    if obj_type == "conduit":
        vx = obj.get("x", [])
        vy = obj.get("y", [])
        if vx and vy and len(vx) == len(vy):
            vidx = _get_safe_selected_vertex_index()
            st.session_state["editor_vertex_x_input"] = float(vx[vidx])
            st.session_state["editor_vertex_y_input"] = float(vy[vidx])
        else:
            st.session_state["editor_vertex_x_input"] = 0.0
            st.session_state["editor_vertex_y_input"] = 0.0

    if obj_type == "workflow":
        _prime_workflow_inputs_from_selection()


def _set_selected_xy(new_x, new_y):
    result = _get_selected_object()
    if result == (None, None, None):
        st.session_state.editor_status_msg = "No object selected."
        return

    obj_type, idx, obj = result
    floor_w = float(st.session_state.floor_w)
    floor_h = float(st.session_state.floor_h)

    new_x = float(new_x)
    new_y = float(new_y)

    if st.session_state.editor_snap_enabled:
        new_x = _snap_value(new_x, st.session_state.editor_snap_ft, True)
        new_y = _snap_value(new_y, st.session_state.editor_snap_ft, True)

    if obj_type in ["machine", "lighting"]:
        new_x, new_y = _clamp_to_floor(new_x, new_y, floor_w, floor_h)
        obj["x"] = new_x
        obj["y"] = new_y
        st.session_state.editor_status_msg = (
            f"Moved {obj_type} {obj.get('id', idx)} to "
            f"X={new_x:.2f} ft, Y={new_y:.2f} ft."
        )
        return

    if obj_type == "conduit":
        old_cx, old_cy = _object_center(obj_type, obj)
        dx = new_x - old_cx
        dy = new_y - old_cy

        x_vals = [float(v) + dx for v in obj.get("x", [])]
        y_vals = [float(v) + dy for v in obj.get("y", [])]

        if st.session_state.editor_snap_enabled:
            x_vals = [_snap_value(v, st.session_state.editor_snap_ft, True) for v in x_vals]
            y_vals = [_snap_value(v, st.session_state.editor_snap_ft, True) for v in y_vals]

        x_vals, y_vals = _clamp_conduit_to_floor(x_vals, y_vals, floor_w, floor_h)
        obj["x"] = x_vals
        obj["y"] = y_vals

        new_cx, new_cy = _object_center(obj_type, obj)
        st.session_state.editor_status_msg = (
            f"Moved conduit {obj.get('id', idx)} to "
            f"center X={new_cx:.2f} ft, Y={new_cy:.2f} ft."
        )
        return

    if obj_type == "crane":
        ll_x = float(obj.get("ll_x", 0.0))
        ll_y = float(obj.get("ll_y", 0.0))
        ur_x = float(obj.get("ur_x", 0.0))
        ur_y = float(obj.get("ur_y", 0.0))

        old_cx = (ll_x + ur_x) / 2.0
        old_cy = (ll_y + ur_y) / 2.0
        dx = new_x - old_cx
        dy = new_y - old_cy

        ll_x += dx
        ll_y += dy
        ur_x += dx
        ur_y += dy

        if st.session_state.editor_snap_enabled:
            ll_x = _snap_value(ll_x, st.session_state.editor_snap_ft, True)
            ll_y = _snap_value(ll_y, st.session_state.editor_snap_ft, True)
            ur_x = _snap_value(ur_x, st.session_state.editor_snap_ft, True)
            ur_y = _snap_value(ur_y, st.session_state.editor_snap_ft, True)

        ll_x, ll_y, ur_x, ur_y = _clamp_crane_box(
            ll_x, ll_y, ur_x, ur_y, floor_w, floor_h
        )

        obj["ll_x"] = ll_x
        obj["ll_y"] = ll_y
        obj["ur_x"] = ur_x
        obj["ur_y"] = ur_y

        st.session_state.editor_status_msg = (
            f"Moved crane {obj.get('id', idx)} to "
            f"center X={(ll_x + ur_x)/2.0:.2f} ft, Y={(ll_y + ur_y)/2.0:.2f} ft."
        )
        return


def _set_selected_crane_box(ll_x, ll_y, ur_x, ur_y):
    result = _get_selected_object()
    if result == (None, None, None):
        st.session_state.editor_status_msg = "No object selected."
        return

    obj_type, idx, obj = result
    if obj_type != "crane":
        st.session_state.editor_status_msg = "Bounding box edit applies to cranes only."
        return

    floor_w = float(st.session_state.floor_w)
    floor_h = float(st.session_state.floor_h)

    ll_x = float(ll_x)
    ll_y = float(ll_y)
    ur_x = float(ur_x)
    ur_y = float(ur_y)

    if ur_x <= ll_x or ur_y <= ll_y:
        st.session_state.editor_status_msg = (
            "Invalid crane box: upper-right must be greater than lower-left."
        )
        return

    if st.session_state.editor_snap_enabled:
        ll_x = _snap_value(ll_x, st.session_state.editor_snap_ft, True)
        ll_y = _snap_value(ll_y, st.session_state.editor_snap_ft, True)
        ur_x = _snap_value(ur_x, st.session_state.editor_snap_ft, True)
        ur_y = _snap_value(ur_y, st.session_state.editor_snap_ft, True)

    ll_x, ll_y, ur_x, ur_y = _clamp_crane_box(ll_x, ll_y, ur_x, ur_y, floor_w, floor_h)

    obj["ll_x"] = ll_x
    obj["ll_y"] = ll_y
    obj["ur_x"] = ur_x
    obj["ur_y"] = ur_y

    st.session_state.editor_status_msg = (
        f"Updated crane {obj.get('id', idx)} bounding box."
    )


def _set_selected_conduit_vertex(new_x, new_y):
    result = _get_selected_object()
    if result == (None, None, None):
        st.session_state.editor_status_msg = "No conduit selected."
        return

    obj_type, idx, obj = result
    if obj_type != "conduit":
        st.session_state.editor_status_msg = "Vertex editing applies to conduits only."
        return

    x_vals = [float(v) for v in obj.get("x", [])]
    y_vals = [float(v) for v in obj.get("y", [])]

    if len(x_vals) < 2 or len(x_vals) != len(y_vals):
        st.session_state.editor_status_msg = "Selected conduit has invalid point data."
        return

    vidx = _get_safe_selected_vertex_index()

    floor_w = float(st.session_state.floor_w)
    floor_h = float(st.session_state.floor_h)

    new_x = float(new_x)
    new_y = float(new_y)

    if st.session_state.editor_snap_enabled:
        new_x = _snap_value(new_x, st.session_state.editor_snap_ft, True)
        new_y = _snap_value(new_y, st.session_state.editor_snap_ft, True)

    new_x, new_y = _clamp_to_floor(new_x, new_y, floor_w, floor_h)

    x_vals[vidx] = new_x
    y_vals[vidx] = new_y

    obj["x"] = x_vals
    obj["y"] = y_vals

    st.session_state.editor_status_msg = (
        f"Updated conduit vertex P{vidx+1} for {obj.get('id', idx)} "
        f"to X={new_x:.2f} ft, Y={new_y:.2f} ft."
    )


def _add_conduit_vertex_after_selected():
    result = _get_selected_object()
    if result == (None, None, None):
        st.session_state.editor_status_msg = "No conduit selected."
        return

    obj_type, idx, obj = result
    if obj_type != "conduit":
        st.session_state.editor_status_msg = "Vertex editing applies to conduits only."
        return

    x_vals = [float(v) for v in obj.get("x", [])]
    y_vals = [float(v) for v in obj.get("y", [])]

    if len(x_vals) < 2 or len(x_vals) != len(y_vals):
        st.session_state.editor_status_msg = "Selected conduit has invalid point data."
        return

    vidx = _get_safe_selected_vertex_index()

    if vidx < len(x_vals) - 1:
        new_x = (x_vals[vidx] + x_vals[vidx + 1]) / 2.0
        new_y = (y_vals[vidx] + y_vals[vidx + 1]) / 2.0
        insert_at = vidx + 1
    else:
        if len(x_vals) >= 2:
            dx = x_vals[-1] - x_vals[-2]
            dy = y_vals[-1] - y_vals[-2]
        else:
            dx = 5.0
            dy = 0.0
        new_x = x_vals[-1] + dx * 0.5
        new_y = y_vals[-1] + dy * 0.5
        insert_at = len(x_vals)

    floor_w = float(st.session_state.floor_w)
    floor_h = float(st.session_state.floor_h)

    if st.session_state.editor_snap_enabled:
        new_x = _snap_value(new_x, st.session_state.editor_snap_ft, True)
        new_y = _snap_value(new_y, st.session_state.editor_snap_ft, True)

    new_x, new_y = _clamp_to_floor(new_x, new_y, floor_w, floor_h)

    x_vals.insert(insert_at, new_x)
    y_vals.insert(insert_at, new_y)

    obj["x"] = x_vals
    obj["y"] = y_vals
    st.session_state.editor_pending_vertex_index = insert_at

    st.session_state.editor_status_msg = (
        f"Inserted conduit vertex P{insert_at+1} for {obj.get('id', idx)}."
    )


def _delete_selected_conduit_vertex():
    result = _get_selected_object()
    if result == (None, None, None):
        st.session_state.editor_status_msg = "No conduit selected."
        return

    obj_type, idx, obj = result
    if obj_type != "conduit":
        st.session_state.editor_status_msg = "Vertex editing applies to conduits only."
        return

    x_vals = [float(v) for v in obj.get("x", [])]
    y_vals = [float(v) for v in obj.get("y", [])]

    if len(x_vals) <= 2 or len(x_vals) != len(y_vals):
        st.session_state.editor_status_msg = (
            "Cannot delete vertex: a conduit must retain at least two points."
        )
        return

    vidx = _get_safe_selected_vertex_index()

    x_vals.pop(vidx)
    y_vals.pop(vidx)

    obj["x"] = x_vals
    obj["y"] = y_vals

    st.session_state.editor_pending_vertex_index = max(
        0, min(vidx, len(x_vals) - 1)
    )
    st.session_state.editor_status_msg = (
        f"Deleted conduit vertex P{vidx+1} for {obj.get('id', idx)}."
    )


def apply_editor_coordinate_update():
    try:
        new_x = float(st.session_state.editor_coord_x_input)
        new_y = float(st.session_state.editor_coord_y_input)
    except Exception:
        st.session_state.editor_status_msg = "Invalid coordinate input."
        return

    _set_selected_xy(new_x, new_y)
    st.session_state.editor_prime_inputs = True
    st.rerun()


def apply_editor_nudge(dx, dy):
    result = _get_selected_object()
    if result == (None, None, None):
        st.session_state.editor_status_msg = "No object selected."
        return

    obj_type, _, obj = result

    if obj_type == "workflow":
        apply_workflow_point_nudge(dx, dy)
        return

    cur_x, cur_y = _object_center(obj_type, obj)
    _set_selected_xy(cur_x + dx, cur_y + dy)
    st.session_state.editor_prime_inputs = True
    st.rerun()


def apply_crane_box_update():
    try:
        ll_x = float(st.session_state.editor_box_ll_x_input)
        ll_y = float(st.session_state.editor_box_ll_y_input)
        ur_x = float(st.session_state.editor_box_ur_x_input)
        ur_y = float(st.session_state.editor_box_ur_y_input)
    except Exception:
        st.session_state.editor_status_msg = "Invalid crane box input."
        return

    _set_selected_crane_box(ll_x, ll_y, ur_x, ur_y)
    st.session_state.editor_prime_inputs = True
    st.rerun()


def apply_conduit_vertex_update():
    try:
        vx = float(st.session_state.editor_vertex_x_input)
        vy = float(st.session_state.editor_vertex_y_input)
    except Exception:
        st.session_state.editor_status_msg = "Invalid conduit vertex input."
        return

    _set_selected_conduit_vertex(vx, vy)
    st.session_state.editor_prime_inputs = True
    st.rerun()


def apply_conduit_vertex_nudge(dx, dy):
    result = _get_selected_object()
    if result == (None, None, None):
        st.session_state.editor_status_msg = "No conduit selected."
        return

    obj_type, _, obj = result
    if obj_type != "conduit":
        st.session_state.editor_status_msg = "Vertex nudge applies to conduits only."
        return

    vidx = _get_safe_selected_vertex_index()
    x_vals = obj.get("x", [])
    y_vals = obj.get("y", [])
    if len(x_vals) <= vidx or len(y_vals) <= vidx:
        st.session_state.editor_status_msg = "Invalid conduit vertex selection."
        return

    vx = float(x_vals[vidx]) + dx
    vy = float(y_vals[vidx]) + dy
    _set_selected_conduit_vertex(vx, vy)
    st.session_state.editor_prime_inputs = True
    st.rerun()


def apply_add_conduit_vertex():
    _add_conduit_vertex_after_selected()
    st.session_state.editor_prime_inputs = True
    st.rerun()


def apply_delete_conduit_vertex():
    _delete_selected_conduit_vertex()
    st.session_state.editor_prime_inputs = True
    st.rerun()


def apply_workflow_point_update():
    _normalize_workflow_df()
    df = _workflow_df()

    if len(df) == 0:
        st.session_state.editor_status_msg = "No workflow points available."
        return

    try:
        x_val = float(st.session_state.editor_workflow_x_input)
        y_val = float(st.session_state.editor_workflow_y_input)
        standoff_val = float(st.session_state.editor_workflow_standoff_input)
        speed_val = float(st.session_state.editor_workflow_speed_input)
    except Exception:
        st.session_state.editor_status_msg = "Invalid workflow point input."
        return

    floor_w = float(st.session_state.floor_w)
    floor_h = float(st.session_state.floor_h)

    if st.session_state.editor_snap_enabled:
        x_val = _snap_value(x_val, st.session_state.editor_snap_ft, True)
        y_val = _snap_value(y_val, st.session_state.editor_snap_ft, True)

    x_val, y_val = _clamp_to_floor(x_val, y_val, floor_w, floor_h)
    standoff_val = max(0.0, standoff_val)
    speed_val = max(0.0, speed_val)

    idx = _get_safe_workflow_point_index()

    df.at[idx, "X Coordinate"] = x_val
    df.at[idx, "Y Coordinate"] = y_val
    df.at[idx, "Safety Standoff (ft)"] = standoff_val
    df.at[idx, "Movement Speed"] = speed_val
    df["Point"] = list(range(1, len(df) + 1))

    st.session_state.path_points = df
    st.session_state.editor_status_msg = (
        f"Updated workflow point W{idx+1} to "
        f"X={x_val:.2f} ft, Y={y_val:.2f} ft."
    )
    st.session_state.editor_prime_inputs = True
    st.rerun()


def apply_workflow_point_nudge(dx, dy):
    _normalize_workflow_df()
    df = _workflow_df()

    if len(df) == 0:
        st.session_state.editor_status_msg = "No workflow points available."
        return

    idx = _get_safe_workflow_point_index()

    cur_x = float(df.iloc[idx]["X Coordinate"])
    cur_y = float(df.iloc[idx]["Y Coordinate"])
    cur_s = float(df.iloc[idx]["Safety Standoff (ft)"])
    cur_v = float(df.iloc[idx]["Movement Speed"])

    new_x = cur_x + float(dx)
    new_y = cur_y + float(dy)

    floor_w = float(st.session_state.floor_w)
    floor_h = float(st.session_state.floor_h)

    if st.session_state.editor_snap_enabled:
        new_x = _snap_value(new_x, st.session_state.editor_snap_ft, True)
        new_y = _snap_value(new_y, st.session_state.editor_snap_ft, True)

    new_x, new_y = _clamp_to_floor(new_x, new_y, floor_w, floor_h)

    df.at[idx, "X Coordinate"] = new_x
    df.at[idx, "Y Coordinate"] = new_y
    df.at[idx, "Safety Standoff (ft)"] = max(0.0, cur_s)
    df.at[idx, "Movement Speed"] = max(0.0, cur_v)
    df["Point"] = list(range(1, len(df) + 1))

    st.session_state.path_points = df
    st.session_state.editor_status_msg = (
        f"Nudged workflow point W{idx+1} to "
        f"X={new_x:.2f} ft, Y={new_y:.2f} ft."
    )
    st.session_state.editor_prime_inputs = True
    st.rerun()


def apply_add_workflow_point():
    _normalize_workflow_df()
    df = _workflow_df()

    if len(df) == 0:
        new_row = {
            "Point": 1,
            "X Coordinate": 0.0,
            "Y Coordinate": 0.0,
            "Safety Standoff (ft)": 5.0,
            "Movement Speed": 5.0,
        }
        df = pd.DataFrame([new_row])
        st.session_state.path_points = df
        st.session_state.editor_pending_workflow_point_index = 0
        st.session_state.editor_status_msg = "Added first workflow point W1."
        st.session_state.editor_prime_inputs = True
        st.rerun()
        return

    idx = _get_safe_workflow_point_index()

    x1 = float(df.iloc[idx]["X Coordinate"])
    y1 = float(df.iloc[idx]["Y Coordinate"])
    s1 = float(df.iloc[idx]["Safety Standoff (ft)"])
    v1 = float(df.iloc[idx]["Movement Speed"])

    if idx < len(df) - 1:
        x2 = float(df.iloc[idx + 1]["X Coordinate"])
        y2 = float(df.iloc[idx + 1]["Y Coordinate"])
        s2 = float(df.iloc[idx + 1]["Safety Standoff (ft)"])
        v2 = float(df.iloc[idx + 1]["Movement Speed"])

        new_x = (x1 + x2) / 2.0
        new_y = (y1 + y2) / 2.0
        new_s = (s1 + s2) / 2.0
        new_v = (v1 + v2) / 2.0
        insert_at = idx + 1
    else:
        if len(df) >= 2:
            px = float(df.iloc[idx - 1]["X Coordinate"])
            py = float(df.iloc[idx - 1]["Y Coordinate"])
            dx = x1 - px
            dy = y1 - py
        else:
            dx = 10.0
            dy = 0.0

        new_x = x1 + dx * 0.5
        new_y = y1 + dy * 0.5
        new_s = s1
        new_v = v1
        insert_at = len(df)

    floor_w = float(st.session_state.floor_w)
    floor_h = float(st.session_state.floor_h)

    if st.session_state.editor_snap_enabled:
        new_x = _snap_value(new_x, st.session_state.editor_snap_ft, True)
        new_y = _snap_value(new_y, st.session_state.editor_snap_ft, True)

    new_x, new_y = _clamp_to_floor(new_x, new_y, floor_w, floor_h)

    top = df.iloc[:insert_at].copy()
    bottom = df.iloc[insert_at:].copy()

    new_row = pd.DataFrame([{
        "Point": 0,
        "X Coordinate": new_x,
        "Y Coordinate": new_y,
        "Safety Standoff (ft)": max(0.0, new_s),
        "Movement Speed": max(0.0, new_v),
    }])

    df = pd.concat([top, new_row, bottom], ignore_index=True)
    df["Point"] = list(range(1, len(df) + 1))

    st.session_state.path_points = df
    st.session_state.editor_pending_workflow_point_index = insert_at
    st.session_state.editor_status_msg = f"Inserted workflow point W{insert_at+1}."
    st.session_state.editor_prime_inputs = True
    st.rerun()


def apply_delete_workflow_point():
    _normalize_workflow_df()
    df = _workflow_df()

    if len(df) <= 2:
        st.session_state.editor_status_msg = (
            "Cannot delete workflow point: path must retain at least two points."
        )
        return

    idx = _get_safe_workflow_point_index()
    df = df.drop(df.index[idx]).reset_index(drop=True)
    df["Point"] = list(range(1, len(df) + 1))

    st.session_state.path_points = df
    st.session_state.editor_pending_workflow_point_index = max(
        0, min(idx, len(df) - 1)
    )
    st.session_state.editor_status_msg = f"Deleted workflow point W{idx+1}."
    st.session_state.editor_prime_inputs = True
    st.rerun()


def _select_nearest_object(obj_type, pick_x, pick_y):
    items = _get_object_list(obj_type)
    if not items:
        st.session_state.editor_status_msg = f"No {obj_type} objects available."
        return

    best_idx = None
    best_dist = None

    for idx, obj in enumerate(items):
        ox, oy = _object_center(obj_type, obj)
        d = math.sqrt((ox - pick_x) ** 2 + (oy - pick_y) ** 2)
        if best_dist is None or d < best_dist:
            best_dist = d
            best_idx = idx

    if best_idx is None:
        st.session_state.editor_status_msg = f"Could not select a {obj_type}."
        return

    st.session_state.editor_selected_index = best_idx
    st.session_state.editor_selected_vertex_index = 0
    st.session_state.editor_workflow_selected_point_index = 0
    sel_obj = items[best_idx]
    st.session_state.editor_status_msg = (
        f"Selected nearest {obj_type}: "
        f"{sel_obj.get('id', best_idx)} at distance {best_dist:.2f} ft."
    )
    st.session_state.editor_prime_inputs = True


def apply_pick_selection():
    try:
        pick_x = float(st.session_state.editor_pick_x_input)
        pick_y = float(st.session_state.editor_pick_y_input)
    except Exception:
        st.session_state.editor_status_msg = "Invalid pick coordinate input."
        return

    floor_w = float(st.session_state.floor_w)
    floor_h = float(st.session_state.floor_h)
    pick_x, pick_y = _clamp_to_floor(pick_x, pick_y, floor_w, floor_h)

    st.session_state.editor_last_pick_x = pick_x
    st.session_state.editor_last_pick_y = pick_y

    obj_type = st.session_state.editor_selected_type
    _select_nearest_object(obj_type, pick_x, pick_y)
    st.rerun()


def _on_object_type_change():
    st.session_state.editor_selected_index = 0
    st.session_state.editor_selected_vertex_index = 0
    st.session_state.editor_workflow_selected_point_index = 0
    st.session_state.editor_prime_inputs = True


def _on_selected_object_change():
    labels = st.session_state.get("editor_object_labels", [])
    selected_label = st.session_state.get("editor_selected_label_select", "")

    if selected_label in labels:
        st.session_state.editor_selected_index = labels.index(selected_label)
        st.session_state.editor_selected_vertex_index = 0
        st.session_state.editor_workflow_selected_point_index = 0
        st.session_state.editor_prime_inputs = True


def _on_selected_vertex_change():
    st.session_state.editor_prime_inputs = True


def draw_interactive_editor_figure():
    floor_w = float(st.session_state.floor_w)
    floor_h = float(st.session_state.floor_h)

    fig, ax = plt.subplots(figsize=(12, 6.5))
    fig.patch.set_facecolor("#0B1E2D")
    ax.set_facecolor("#0B1E2D")

    floor_rect = patches.Rectangle(
        (0, 0),
        floor_w,
        floor_h,
        fill=False,
        edgecolor="#39FF14",
        linewidth=2.0,
        zorder=2,
    )
    ax.add_patch(floor_rect)

    if st.session_state.editor_show_grid:
        grid_step = float(st.session_state.editor_snap_ft)
        if grid_step <= 0:
            grid_step = 1.0

        x = 0.0
        while x <= floor_w:
            ax.plot([x, x], [0, floor_h], color="#1F3B4D", lw=0.7, zorder=1)
            x += grid_step

        y = 0.0
        while y <= floor_h:
            ax.plot([0, floor_w], [y, y], color="#1F3B4D", lw=0.7, zorder=1)
            y += grid_step

    selected_type = st.session_state.editor_selected_type
    selected_index = int(st.session_state.editor_selected_index)
    selected_vertex_index = _get_safe_selected_vertex_index()

    # Conduits
    for idx, cond in enumerate(st.session_state.placed_conduits):
        xs = [float(v) for v in cond.get("x", [])]
        ys = [float(v) for v in cond.get("y", [])]
        if len(xs) >= 2 and len(xs) == len(ys):
            is_selected = selected_type == "conduit" and idx == selected_index
            ax.plot(
                xs,
                ys,
                color="#FFA500" if not is_selected else "#00E5FF",
                lw=2.0 if not is_selected else 3.0,
                zorder=3,
            )

            for p_idx, (px, py) in enumerate(zip(xs, ys)):
                is_sel_vertex = is_selected and p_idx == selected_vertex_index
                ax.scatter(
                    [px],
                    [py],
                    color="#FFD700" if not is_sel_vertex else "#FF00FF",
                    s=20 if not is_sel_vertex else 70,
                    zorder=4,
                    edgecolors="black",
                )
                if st.session_state.editor_show_labels:
                    ax.text(
                        px,
                        py + 1.0,
                        f"P{p_idx+1}",
                        color="white",
                        fontsize=7,
                        ha="center",
                        zorder=5,
                    )

            if st.session_state.editor_show_labels:
                cx, cy = _object_center("conduit", cond)
                ax.text(
                    cx,
                    cy,
                    cond.get("id", f"C-{idx+1:03d}"),
                    color="white",
                    fontsize=8,
                    weight="bold",
                    ha="center",
                    va="bottom",
                    zorder=5,
                )

    # Workflow path
    if "path_points" in st.session_state and len(st.session_state.path_points) >= 2:
        _normalize_workflow_df()
        wdf = _workflow_df()

        wx = [float(v) for v in wdf["X Coordinate"].tolist()]
        wy = [float(v) for v in wdf["Y Coordinate"].tolist()]

        ax.plot(
            wx,
            wy,
            color="#808080",
            lw=3.0,
            zorder=3,
        )

        selected_w_idx = _get_safe_workflow_point_index()

        for p_idx, (px, py) in enumerate(zip(wx, wy)):
            is_sel = (
                st.session_state.editor_selected_type == "workflow"
                and p_idx == selected_w_idx
            )
            ax.scatter(
                [px],
                [py],
                color="#FFD700" if not is_sel else "#FF00FF",
                s=25 if not is_sel else 75,
                zorder=4,
                edgecolors="black",
            )
            if st.session_state.editor_show_labels:
                ax.text(
                    px,
                    py + 1.0,
                    f"W{p_idx+1}",
                    color="white",
                    fontsize=7,
                    ha="center",
                    zorder=5,
                )

    # Cranes
    for idx, cr in enumerate(st.session_state.placed_cranes):
        ll_x = float(cr.get("ll_x", 0.0))
        ll_y = float(cr.get("ll_y", 0.0))
        ur_x = float(cr.get("ur_x", 0.0))
        ur_y = float(cr.get("ur_y", 0.0))

        is_selected = selected_type == "crane" and idx == selected_index

        rect = patches.Rectangle(
            (ll_x, ll_y),
            ur_x - ll_x,
            ur_y - ll_y,
            fill=True,
            facecolor="#A0A0A0",
            alpha=0.25 if not is_selected else 0.35,
            edgecolor="#D3D3D3" if not is_selected else "#FFD700",
            linewidth=1.5 if not is_selected else 2.5,
            linestyle="--",
            zorder=2,
        )
        ax.add_patch(rect)

        if st.session_state.editor_show_labels:
            cx, cy = _object_center("crane", cr)
            ax.text(
                cx,
                cy,
                cr.get("id", f"CR-{idx+1:03d}"),
                color="white",
                fontsize=8,
                weight="bold",
                ha="center",
                va="center",
                zorder=5,
            )

    # Machines
    for idx, m in enumerate(st.session_state.placed_machines):
        mx = float(m.get("x", 0.0))
        my = float(m.get("y", 0.0))
        mw = float(m.get("Width", 0.0))
        mh = float(m.get("Height", 0.0))
        so = float(m.get("Standoff", 0.0))

        is_selected = selected_type == "machine" and idx == selected_index

        rect = patches.Rectangle(
            (mx - mw / 2.0, my - mh / 2.0),
            mw,
            mh,
            facecolor="#87CEEB" if not is_selected else "#00E5FF",
            edgecolor="white" if not is_selected else "#FFD700",
            linewidth=1.5 if not is_selected else 2.5,
            alpha=0.9,
            zorder=4,
        )
        ax.add_patch(rect)

        standoff_circle = patches.Circle(
            (mx, my),
            radius=max(mw, mh) / 2.0 + so,
            fill=False,
            edgecolor="#FF6666" if not is_selected else "#FFD700",
            linestyle=":",
            linewidth=1.0 if not is_selected else 1.8,
            zorder=3,
        )
        ax.add_patch(standoff_circle)

        if st.session_state.editor_show_labels:
            ax.text(
                mx,
                my,
                m.get("id", f"M-{idx+1:03d}"),
                ha="center",
                va="center",
                color="white",
                fontsize=8,
                weight="bold",
                zorder=5,
            )

    # Lighting
    for idx, l in enumerate(st.session_state.placed_lighting):
        lx = float(l.get("x", 0.0))
        ly = float(l.get("y", 0.0))
        is_selected = selected_type == "lighting" and idx == selected_index

        ax.plot(
            lx,
            ly,
            marker="o",
            markersize=10 if not is_selected else 13,
            color="gold" if not is_selected else "#00E5FF",
            markeredgecolor="black" if not is_selected else "#FFD700",
            markeredgewidth=1.0 if not is_selected else 1.8,
            zorder=5,
        )

        if st.session_state.editor_show_labels:
            ax.text(
                lx + 1.0,
                ly + 1.0,
                l.get("id", f"L-{idx+1:03d}"),
                color="gold" if not is_selected else "#00E5FF",
                fontsize=8,
                weight="bold",
                zorder=6,
            )

    if "editor_last_pick_x" in st.session_state and "editor_last_pick_y" in st.session_state:
        px = float(st.session_state.editor_last_pick_x)
        py = float(st.session_state.editor_last_pick_y)
        ax.plot(
            px,
            py,
            marker="x",
            markersize=12,
            color="#FF00FF",
            markeredgewidth=2.0,
            zorder=7,
        )
        ax.text(
            px + 1.0,
            py + 1.0,
            "Pick",
            color="#FF00FF",
            fontsize=8,
            weight="bold",
            zorder=7,
        )

    ax.set_xlim(0, floor_w)
    ax.set_ylim(0, floor_h)
    ax.set_aspect("equal")
    ax.set_xlabel("X (ft)", color="white")
    ax.set_ylabel("Y (ft)", color="white")
    ax.tick_params(colors="white")

    for spine in ax.spines.values():
        spine.set_color("white")

    ax.set_title("Interactive 2D Layout Editor", color="white", fontsize=14)
    return fig


def render_interactive_editor_controls():
    st.subheader("Interactive 2D Layout Editor Controls")

    st.markdown("### Phase 3 Canvas")

    top1, top2, top3, top4 = st.columns(4)

    with top1:
        st.selectbox(
            "Canvas Mode",
            options=["select", "move", "dim"],
            key="editor_canvas_mode",
        )

    with top2:
        st.checkbox("Snap to Grid", key="editor_snap_enabled")

    with top3:
        st.number_input(
            "Snap/Grid Increment (ft)",
            min_value=1.0,
            step=1.0,
            key="editor_snap_ft",
        )

    with top4:
        st.checkbox("Show Grid", key="editor_show_grid")

    show_labels_col, spacer_col = st.columns([1, 3])

    with show_labels_col:
        st.checkbox("Show Labels", key="editor_show_labels")

    st.markdown("### Selected Item")

    sel_type = st.session_state.get("editor_selected_type", "machine")
    sel_idx = int(st.session_state.get("editor_selected_index", 0))

    st.write(f"**Type:** {sel_type}")

    items = _get_object_list(sel_type)
    if items and 0 <= sel_idx < len(items):
        sel_obj = items[sel_idx]
        sel_label = _get_object_label(sel_type, sel_obj, sel_idx)
        st.write(f"**Selection:** {sel_label}")
    else:
        st.write("**Selection:** None")

    if sel_type == "workflow":
        _normalize_workflow_df()
        wdf = _workflow_df()
        if len(wdf) > 0:
            widx = _get_safe_workflow_point_index()
            st.write(f"**Workflow Point:** W{widx+1}")
            st.write(
                f"**Point Coordinates:** "
                f"({float(wdf.iloc[widx]['X Coordinate']):.2f}, "
                f"{float(wdf.iloc[widx]['Y Coordinate']):.2f})"
            )

    elif items and 0 <= sel_idx < len(items):
        try:
            cx, cy = _object_center(sel_type, items[sel_idx])
            st.write(f"**Center:** X={float(cx):.2f} ft, Y={float(cy):.2f} ft")
        except Exception:
            pass

    with st.expander("Precision Edit / Center Move", expanded=False):
        st.caption(
            "Use these controls for exact numeric positioning after selecting an item on the canvas."
        )

        # Keep your existing downstream precision controls alive by calling
        # the original object-specific edit blocks if you want to reinsert them here.
        st.write("Precision edit controls can be reattached here in the next pass.")
    if st.session_state.get("editor_canvas_mode", "select") == "move":
        if st.session_state.get("editor_move_awaiting_target", False):
            st.warning("Move mode active: click a destination point.")
        else:
            st.info("Move mode active: click an object to move.")        

def _apply_pending_canvas_selection_if_any():
    pending_type = st.session_state.get("editor_pending_selected_type", None)
    pending_index = st.session_state.get("editor_pending_selected_index", None)
    pending_vertex = st.session_state.get("editor_pending_selected_vertex_index", None)
    pending_workflow_point = st.session_state.get(
        "editor_pending_workflow_selected_point_index", None
    )
    pending_status = st.session_state.get("editor_pending_phase3_status", None)

    if pending_type is None and pending_index is None:
        return

    if pending_type is not None:
        st.session_state["editor_selected_type"] = pending_type

    if pending_index is not None:
        st.session_state["editor_selected_index"] = int(pending_index)

    if pending_vertex is not None:
        st.session_state["editor_selected_vertex_index"] = int(pending_vertex)

    if pending_workflow_point is not None:
        st.session_state["editor_workflow_selected_point_index"] = int(
            pending_workflow_point
        )

    if pending_status is not None:
        st.session_state["editor_phase3_status"] = str(pending_status)

    st.session_state["editor_prime_inputs"] = True

    st.session_state["editor_pending_selected_type"] = None
    st.session_state["editor_pending_selected_index"] = None
    st.session_state["editor_pending_selected_vertex_index"] = None
    st.session_state["editor_pending_workflow_selected_point_index"] = None
    st.session_state["editor_pending_phase3_status"] = None

def render_interactive_editor():
    _apply_pending_canvas_selection_if_any()
    _apply_pending_vertex_selection_if_any()
    _apply_pending_workflow_point_selection_if_any()

    if st.session_state.get("editor_prime_inputs", True):
        _prime_editor_inputs_from_selection()
        _prime_workflow_inputs_from_selection()
        st.session_state.editor_prime_inputs = False

    render_interactive_editor_controls()

    fig = build_interactive_canvas_figure()
    fig.update_layout(
        dragmode = False,  # Defaults the active tool to panning (great for scroll-to-zoom)
        hovermode="closest"
    )
    selected_points = plotly_events(
        fig,
        click_event=True,
        hover_event=False,
        select_event=False,
        override_height=650,
        override_width="100%",
        key=f"interactive_canvas_events_{st.session_state.get('editor_canvas_refresh_token', 0)}",
    )

    if selected_points:
        canvas_mode = st.session_state.get("editor_canvas_mode", "select")
        move_waiting = st.session_state.get("editor_move_awaiting_target", False)
        dim_waiting = st.session_state.get("editor_dim_move_awaiting_target", False)

        if canvas_mode == "move" and move_waiting:
            _apply_move_to_click(selected_points)
            st.rerun()

        elif canvas_mode == "dim" and dim_waiting:
            _apply_dimension_move_to_click(selected_points)
            st.rerun()

        else:
            click_info = _resolve_canvas_click(selected_points)

            if canvas_mode == "dim":
                if click_info and click_info.get("entity_type") == "dimension":
                    _begin_dimension_move_from_click_info(click_info)
                    st.session_state.editor_canvas_refresh_token += 1
                    st.session_state.editor_prime_inputs = True
                    return
                else:
                    clicked_type = None
                    if click_info:
                        clicked_type = click_info.get("entity_type", None)

                    st.session_state.editor_phase3_status = (
                        f"Dim mode: click a dimension label. "
                        f"Last click resolved as: {clicked_type}"
                    )
                    return
            else:
                _apply_selection_from_click_info(click_info)

                if canvas_mode == "move":
                    _begin_move_from_click_info(click_info)

                st.rerun()

    st.caption(
        "Canvas modes: Select = click to select. "
        "Move = click object, then click destination. "
        "Dim = click a dimension label, then click its new location."
    )

    if st.session_state.get("editor_canvas_mode", "select") == "move":
        if st.session_state.get("editor_move_awaiting_target", False):
            st.warning("Move mode active: click a destination point.")
        else:
            st.info("Move mode active: click an object to move.")
    
    if st.session_state.get("editor_canvas_mode", "select") == "dim":
        if st.session_state.get("editor_dim_move_awaiting_target", False):
            st.warning("Dim mode active: click a destination point.")
        else:
            st.info("Dim mode active: click a dimension label to move it.")        
    
    phase3_msg = st.session_state.get("editor_phase3_status", "")
    if phase3_msg:
        st.info(phase3_msg)

    if st.session_state.get("editor_canvas_mode", "select") == "dim":
        st.caption(
            f"dim_waiting={st.session_state.get('editor_dim_move_awaiting_target', False)} | "
            f"owner={st.session_state.get('editor_dim_selected_owner_type', '')} | "
            f"index={st.session_state.get('editor_dim_selected_owner_index', -1)} | "
            f"axis={st.session_state.get('editor_dim_selected_axis', '')}"
        )
    

def _set_selected_conduit_vertex_xy(new_x, new_y):
    result = _get_selected_object()
    if result == (None, None, None):
        st.session_state.editor_status_msg = "No conduit selected."
        return

    obj_type, idx, obj = result
    if obj_type != "conduit":
        st.session_state.editor_status_msg = "Selected object is not a conduit."
        return

    floor_w = float(st.session_state.floor_w)
    floor_h = float(st.session_state.floor_h)

    new_x = float(new_x)
    new_y = float(new_y)

    if st.session_state.editor_snap_enabled:
        new_x = _snap_value(new_x, st.session_state.editor_snap_ft, True)
        new_y = _snap_value(new_y, st.session_state.editor_snap_ft, True)

    new_x, new_y = _clamp_to_floor(new_x, new_y, floor_w, floor_h)

    vx = list(obj.get("x", []))
    vy = list(obj.get("y", []))

    if not vx or not vy or len(vx) != len(vy):
        st.session_state.editor_status_msg = "Selected conduit has invalid geometry."
        return

    vidx = _get_safe_selected_vertex_index()
    vx[vidx] = float(new_x)
    vy[vidx] = float(new_y)

    obj["x"] = vx
    obj["y"] = vy
    st.session_state.editor_status_msg = (
        f"Moved conduit vertex P{vidx+1} to X={new_x:.2f} ft, Y={new_y:.2f} ft."
    )
    st.session_state.editor_prime_inputs = True

def _set_selected_workflow_point_xy(new_x, new_y):
    _normalize_workflow_df()

    if "path_points" not in st.session_state or len(st.session_state.path_points) == 0:
        st.session_state.editor_status_msg = "No workflow path available."
        return

    floor_w = float(st.session_state.floor_w)
    floor_h = float(st.session_state.floor_h)

    new_x = float(new_x)
    new_y = float(new_y)

    if st.session_state.editor_snap_enabled:
        new_x = _snap_value(new_x, st.session_state.editor_snap_ft, True)
        new_y = _snap_value(new_y, st.session_state.editor_snap_ft, True)

    new_x, new_y = _clamp_to_floor(new_x, new_y, floor_w, floor_h)

    wdf = st.session_state.path_points.copy()
    widx = _get_safe_workflow_point_index()

    wdf.at[widx, "X Coordinate"] = float(new_x)
    wdf.at[widx, "Y Coordinate"] = float(new_y)

    st.session_state.path_points = wdf
    st.session_state.editor_status_msg = (
        f"Moved workflow point W{widx+1} to X={new_x:.2f} ft, Y={new_y:.2f} ft."
    )
    st.session_state.editor_prime_inputs = True

def _set_selected_crane_center_xy(new_x, new_y):
    result = _get_selected_object()
    if result == (None, None, None):
        st.session_state.editor_status_msg = "No crane selected."
        return

    obj_type, idx, obj = result
    if obj_type != "crane":
        st.session_state.editor_status_msg = "Selected object is not a crane."
        return

    floor_w = float(st.session_state.floor_w)
    floor_h = float(st.session_state.floor_h)

    ll_x = float(obj.get("ll_x", 0.0))
    ll_y = float(obj.get("ll_y", 0.0))
    ur_x = float(obj.get("ur_x", 0.0))
    ur_y = float(obj.get("ur_y", 0.0))

    width = ur_x - ll_x
    height = ur_y - ll_y

    new_x = float(new_x)
    new_y = float(new_y)

    if st.session_state.editor_snap_enabled:
        new_x = _snap_value(new_x, st.session_state.editor_snap_ft, True)
        new_y = _snap_value(new_y, st.session_state.editor_snap_ft, True)

    new_ll_x = new_x - width / 2.0
    new_ll_y = new_y - height / 2.0

    new_ll_x = max(0.0, min(new_ll_x, floor_w - width))
    new_ll_y = max(0.0, min(new_ll_y, floor_h - height))

    obj["ll_x"] = new_ll_x
    obj["ll_y"] = new_ll_y
    obj["ur_x"] = new_ll_x + width
    obj["ur_y"] = new_ll_y + height

    st.session_state.editor_status_msg = (
        f"Moved crane to center X={new_x:.2f} ft, Y={new_y:.2f} ft."
    )
    st.session_state.editor_prime_inputs = True
    
