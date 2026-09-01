# scene_serializer.py
from copy import deepcopy


VALID_SCENE_VIEW_MODES = {"2d", "3d"}


def _safe_float(value, default=0.0):
    try:
        return float(value)
    except Exception:
        return float(default)


def _safe_int(value, default=0):
    try:
        return int(value)
    except Exception:
        return int(default)


def _safe_bool(value, default=False):
    try:
        return bool(value)
    except Exception:
        return bool(default)


def _safe_str(value, default=""):
    try:
        if value is None:
            return default
        return str(value)
    except Exception:
        return default


def _machine_to_scene_object(machine, idx=0):
    mid = _safe_str(machine.get("id", f"M-{idx+1:03d}"))
    width = _safe_float(machine.get("Width", 0.0))
    height = _safe_float(machine.get("Height", 0.0))
    x = _safe_float(machine.get("x", 0.0))
    y = _safe_float(machine.get("y", 0.0))
    standoff = _safe_float(machine.get("Standoff", 0.0))

    return {
        "id": mid,
        "object_type": "machine",
        "label": mid,
        "x": x,
        "y": y,
        "z": 0.0,
        "width": width,
        "depth": height,
        "height": max(6.0, min(height, 20.0)),  # visual extrusion proxy for 3D
        "rotation_deg": _safe_float(machine.get("rotation_deg", 0.0)),
        "standoff": standoff,
        "metadata": {
            "make": _safe_str(machine.get("Make", "")),
            "model": _safe_str(machine.get("Model", "")),
            "type": _safe_str(machine.get("Type", "")),
            "volume": _safe_float(machine.get("Volume", 0.0)),
            "yield_pct": _safe_float(machine.get("Yield", 0.0)),
            "crane_required": _safe_bool(machine.get("CraneRequired", False)),
            "decibel": _safe_float(machine.get("Decibel", 0.0)),
            "human_intervention_required": _safe_bool(
                machine.get("HumanInterventionRequired", False)
            ),
            "preferred_utility_zone": _safe_str(
                machine.get("PreferredUtilityZone", "")
            ),
            "process_family": _safe_str(machine.get("ProcessFamily", "")),
            "value_added_primary": _safe_bool(
                machine.get("ValueAddedPrimary", True)
            ),
            "water_hookup": _safe_bool(machine.get("WaterHookup", False)),
            "vapor_port": _safe_str(machine.get("VaporPort", "")),
            "amperage": _safe_float(machine.get("Amperage", 0.0)),
            "wattage": _safe_float(machine.get("Wattage", 0.0)),
            "tool_heads": _safe_int(machine.get("ToolHeads", 0)),
        },
        "raw": deepcopy(machine),
    }


def _lighting_to_scene_object(light, idx=0):
    lid = _safe_str(light.get("id", f"L-{idx+1:03d}"))

    return {
        "id": lid,
        "object_type": "lighting",
        "label": lid,
        "x": _safe_float(light.get("x", 0.0)),
        "y": _safe_float(light.get("y", 0.0)),
        "z": _safe_float(light.get("mounting_height_ft", 18.0), 18.0),
        "width": 2.0,
        "depth": 2.0,
        "height": 1.0,
        "metadata": {
            "make": _safe_str(light.get("Make", "")),
            "brand": _safe_str(light.get("Brand", "")),
            "type": _safe_str(light.get("Type", "")),
            "wattage": _safe_float(light.get("Wattage", 0.0)),
            "kelvin": _safe_float(light.get("Kelvin", 0.0)),
            "lumens": _safe_float(light.get("Lumens", 0.0)),
            "lux_target": _safe_float(light.get("LuxTarget", 0.0)),
            "dimmable": _safe_bool(light.get("Dimmable", False)),
        },
        "raw": deepcopy(light),
    }


def _crane_to_scene_object(crane, idx=0):
    cid = _safe_str(crane.get("id", f"CR-{idx+1:03d}"))
    ll_x = _safe_float(crane.get("ll_x", 0.0))
    ll_y = _safe_float(crane.get("ll_y", 0.0))
    ur_x = _safe_float(crane.get("ur_x", 0.0))
    ur_y = _safe_float(crane.get("ur_y", 0.0))

    return {
        "id": cid,
        "object_type": "crane",
        "label": cid,
        "ll_x": ll_x,
        "ll_y": ll_y,
        "ur_x": ur_x,
        "ur_y": ur_y,
        "x": (ll_x + ur_x) / 2.0,
        "y": (ll_y + ur_y) / 2.0,
        "z": _safe_float(crane.get("rail_height_ft", 20.0), 20.0),
        "width": max(0.0, ur_x - ll_x),
        "depth": max(0.0, ur_y - ll_y),
        "height": 2.0,
        "metadata": {
            "make": _safe_str(crane.get("make", crane.get("Make", ""))),
            "model": _safe_str(crane.get("model", crane.get("Model", ""))),
            "max_lift_weight": _safe_float(
                crane.get("max_lift_weight", crane.get("MaxLiftWeight", 0.0))
            ),
            "max_lift_speed": _safe_float(
                crane.get("max_lift_speed", crane.get("MaxLiftSpeed", 0.0))
            ),
            "max_transversal_speed": _safe_float(
                crane.get("max_transversal_speed", crane.get("MaxTransversalSpeed", 0.0))
            ),
            "amperage": _safe_float(crane.get("amperage", 0.0)),
            "wattage": _safe_float(crane.get("wattage", 0.0)),
        },
        "raw": deepcopy(crane),
    }


def _conduit_to_scene_object(conduit, idx=0):
    cid = _safe_str(conduit.get("id", f"C-{idx+1:03d}"))
    xs = [_safe_float(v) for v in conduit.get("x", [])]
    ys = [_safe_float(v) for v in conduit.get("y", [])]
    points = [{"x": x, "y": y, "z": 0.1} for x, y in zip(xs, ys)]

    return {
        "id": cid,
        "object_type": "conduit",
        "label": cid,
        "points": points,
        "metadata": {
            "label": _safe_str(conduit.get("label", "")),
            "utility_type": _safe_str(conduit.get("utility_type", "")),
            "depth_in": _safe_float(conduit.get("depth_in", 0.0)),
            "warning_tape": _safe_bool(conduit.get("warning_tape", False)),
            "dim_visible": _safe_bool(conduit.get("dim_visible", True)),
        },
        "raw": deepcopy(conduit),
    }


def _workflow_paths_to_scene_objects(session_state):
    out = []

    path_points = session_state.get("path_points", None)
    if path_points is None or len(path_points) < 1:
        return out

    try:
        xs = [_safe_float(v) for v in path_points["X Coordinate"].tolist()]
        ys = [_safe_float(v) for v in path_points["Y Coordinate"].tolist()]
        standoffs = [_safe_float(v) for v in path_points["Safety Standoff (ft)"].tolist()]
        speeds = [_safe_float(v) for v in path_points["Movement Speed"].tolist()]

        if "Movement Mode" in path_points.columns:
            modes = path_points["Movement Mode"].astype(str).tolist()
            movement_mode = modes[0] if len(modes) > 0 else "human"
        else:
            movement_mode = "human"

        points = []
        for idx, (x, y) in enumerate(zip(xs, ys)):
            points.append(
                {
                    "index": idx,
                    "x": x,
                    "y": y,
                    "z": 0.1,
                    "standoff": standoffs[idx] if idx < len(standoffs) else 0.0,
                    "speed": speeds[idx] if idx < len(speeds) else 0.0,
                }
            )

        out.append(
            {
                "id": "WF-001",
                "object_type": "workflow_path",
                "label": "WF-001",
                "points": points,
                "metadata": {
                    "movement_mode": _safe_str(movement_mode, "human"),
                    "path_width_ft": _safe_float(session_state.get("path_width_ft", 1.0)),
                    "workflow_dim_visible": _safe_bool(
                        session_state.get("workflow_dim_visible", True)
                    ),
                    "workflow_dim_show_length": _safe_bool(
                        session_state.get("workflow_dim_show_length", True)
                    ),
                    "workflow_dim_show_metadata": _safe_bool(
                        session_state.get("workflow_dim_show_metadata", True)
                    ),
                },
                "raw": {
                    "path_points_rows": path_points.to_dict(orient="records"),
                },
            }
        )
    except Exception:
        return []

    return out


def _machine_flows_to_scene_objects(machine_flows):
    out = []
    for idx, flow in enumerate(machine_flows):
        fid = _safe_str(flow.get("id", f"F-{idx+1:03d}"))
        out.append(
            {
                "id": fid,
                "object_type": "machine_flow",
                "label": fid,
                "from_machine_id": _safe_str(flow.get("from_machine_id", "")),
                "to_machine_id": _safe_str(flow.get("to_machine_id", "")),
                "metadata": {
                    "part_family": _safe_str(flow.get("part_family", "")),
                    "process_step_order": _safe_int(flow.get("process_step_order", 1)),
                    "flow_rate_per_hr": _safe_float(flow.get("flow_rate_per_hr", 0.0)),
                    "transfer_mode": _safe_str(flow.get("transfer_mode", "human")),
                    "lot_size": _safe_int(flow.get("lot_size", 1)),
                    "buffer_max_units": _safe_int(flow.get("buffer_max_units", 0)),
                    "value_added_step": _safe_bool(flow.get("value_added_step", True)),
                    "mandatory_adjacency": _safe_bool(
                        flow.get("mandatory_adjacency", False)
                    ),
                    "preferred_max_distance_ft": _safe_float(
                        flow.get("preferred_max_distance_ft", 25.0)
                    ),
                    "notes": _safe_str(flow.get("notes", "")),
                },
                "raw": deepcopy(flow),
            }
        )
    return out


def _build_selection_payload(session_state):
    return {
        "selected_object_type": _safe_str(
            session_state.get("frontend_selected_object_type", "")
        ),
        "selected_object_id": _safe_str(
            session_state.get("frontend_selected_object_id", "")
        ),
        "selected_sub_index": _safe_int(
            session_state.get("frontend_selected_sub_index", -1), -1
        ),
        "selection_revision": _safe_int(
            session_state.get("frontend_selection_revision", 0), 0
        ),
    }


def _build_display_payload(session_state, view_mode):
    return {
        "view_mode": view_mode,
        "renderer": _safe_str(session_state.get("frontend_renderer", "legacy")),
        "show_machines": _safe_bool(session_state.get("show_machines", True)),
        "show_lighting": _safe_bool(session_state.get("show_lighting", True)),
        "show_cranes": _safe_bool(session_state.get("show_cranes", True)),
        "show_workflow": _safe_bool(session_state.get("show_workflow", True)),
        "show_electrical": _safe_bool(session_state.get("show_electrical", True)),
        "show_safety": _safe_bool(session_state.get("show_safety", False)),
        "show_contour": _safe_bool(session_state.get("show_contour", False)),
        "show_decibel": _safe_bool(session_state.get("show_decibel", False)),
        "show_grid": _safe_bool(session_state.get("frontend_show_grid", True)),
        "show_labels": _safe_bool(session_state.get("frontend_show_labels", True)),
        "snap_enabled": _safe_bool(session_state.get("frontend_snap_enabled", True)),
        "snap_ft": _safe_float(session_state.get("frontend_snap_ft", 10.0)),
        "tool_mode": _safe_str(session_state.get("frontend_tool_mode", "select")),
    }


def _build_camera_payload(session_state, view_mode):
    default_position = (
        {"x": 0.0, "y": 250.0, "z": 0.0}
        if view_mode == "2d"
        else {"x": 140.0, "y": 160.0, "z": 140.0}
    )
    default_target = {"x": 0.0, "y": 0.0, "z": 0.0}

    camera_position = session_state.get("frontend_camera_position", default_position)
    camera_target = session_state.get("frontend_camera_target", default_target)

    if not isinstance(camera_position, dict):
        camera_position = default_position
    if not isinstance(camera_target, dict):
        camera_target = default_target

    return {
        "position": {
            "x": _safe_float(camera_position.get("x", default_position["x"])),
            "y": _safe_float(camera_position.get("y", default_position["y"])),
            "z": _safe_float(camera_position.get("z", default_position["z"])),
        },
        "target": {
            "x": _safe_float(camera_target.get("x", default_target["x"])),
            "y": _safe_float(camera_target.get("y", default_target["y"])),
            "z": _safe_float(camera_target.get("z", default_target["z"])),
        },
        "projection": "orthographic" if view_mode == "2d" else "perspective",
    }


def build_threejs_scene_payload(session_state, view_mode="2d"):
    """
    Convert current Streamlit session state into a frontend-friendly scene payload
    for a future Three.js canvas component.
    """
    view_mode = _safe_str(view_mode, "2d").lower()
    if view_mode not in VALID_SCENE_VIEW_MODES:
        view_mode = "2d"

    placed_machines = session_state.get("placed_machines", [])
    placed_lighting = session_state.get("placed_lighting", [])
    placed_conduits = session_state.get("placed_conduits", [])
    placed_cranes = session_state.get("placed_cranes", [])
    machine_flows = session_state.get("machine_flows", [])

    scene_payload = {
        "schema_version": "threejs_scene_1.0",
        "scene_revision": _safe_int(session_state.get("frontend_scene_revision", 0)),
        "project": {
            "designer_name": _safe_str(session_state.get("designer_name", "")),
            "dwg_title": _safe_str(session_state.get("dwg_title", "")),
            "dwg_num": _safe_str(session_state.get("dwg_num", "")),
            "sheet_size": _safe_str(session_state.get("sheet_size", "")),
        },
        "floor": {
            "width_ft": _safe_float(session_state.get("floor_w", 0.0)),
            "height_ft": _safe_float(session_state.get("floor_h", 0.0)),
            "path_width_ft": _safe_float(session_state.get("path_width_ft", 1.0)),
        },
        "display": _build_display_payload(session_state, view_mode),
        "camera": _build_camera_payload(session_state, view_mode),
        "selection": _build_selection_payload(session_state),
        "objects": {
            "machines": [
                _machine_to_scene_object(m, idx) for idx, m in enumerate(placed_machines)
            ],
            "lighting": [
                _lighting_to_scene_object(l, idx) for idx, l in enumerate(placed_lighting)
            ],
            "conduits": [
                _conduit_to_scene_object(c, idx) for idx, c in enumerate(placed_conduits)
            ],
            "cranes": [
                _crane_to_scene_object(cr, idx) for idx, cr in enumerate(placed_cranes)
            ],
            "workflow_paths": _workflow_paths_to_scene_objects(session_state),
            "machine_flows": _machine_flows_to_scene_objects(machine_flows),
        },
        "counts": {
            "machines": len(placed_machines),
            "lighting": len(placed_lighting),
            "conduits": len(placed_conduits),
            "cranes": len(placed_cranes),
            "machine_flows": len(machine_flows),
        },
    }

    return scene_payload
