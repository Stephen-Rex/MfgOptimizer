# state_manager.py
import json
import math
import pandas as pd
import streamlit as st

# --- Phase 3b additions: schema/version helpers ---

SUPPORTED_PROJECT_SCHEMA_VERSIONS = {
    "1.0",
    "1.1",
    "1.2",
    "1.3",
    "1.4",
}

LATEST_PROJECT_SCHEMA_VERSION = "1.3"


def normalize_project_schema_version(raw_version):
    """
    Return a safe string schema version.
    """
    try:
        version = str(raw_version).strip()
    except Exception:
        version = "1.0"

    if not version:
        version = "1.0"

    if version not in SUPPORTED_PROJECT_SCHEMA_VERSIONS:
        version = "1.0"

    return version

def migrate_imported_project_dict(imported_data):
    """
    Apply lightweight backward-compatible migrations to imported project data.
    Returns a normalized dict.
    """
    if not isinstance(imported_data, dict):
        raise ValueError("Imported project file must decode to a JSON object.")

    schema_version = normalize_project_schema_version(
        imported_data.get("schema_version", "1.0")
    )
    imported_data["schema_version"] = schema_version

    # Backward compatibility: missing machine_flows means empty list
    if "machine_flows" not in imported_data or imported_data["machine_flows"] is None:
        imported_data["machine_flows"] = []

    # Backward compatibility: path_points should remain list-like if present
    if "path_points" in imported_data and imported_data["path_points"] is None:
        imported_data["path_points"] = []

    # Defensive collection defaults
    for key in [
        "placed_machines",
        "placed_lighting",
        "placed_conduits",
        "placed_cranes",
    ]:
        if key not in imported_data or imported_data[key] is None:
            imported_data[key] = []

    return imported_data

# --- Phase 4.6 additions: machine flow helpers ---

VALID_FLOW_TRANSFER_MODES = {
    "human",
    "autonomous_robot",
    "robotic_arm",
    "overhead_crane",
    "forklift",
}


def build_default_machine_flow():
    """Return a default empty machine flow record."""
    return {
        "id": "",
        "from_machine_id": "",
        "to_machine_id": "",
        "part_family": "",
        "process_step_order": 1,
        "flow_rate_per_hr": 0.0,
        "transfer_mode": "human",
        "lot_size": 1,
        "buffer_max_units": 0,
        "value_added_step": True,
        "mandatory_adjacency": False,
        "preferred_max_distance_ft": 25.0,
        "notes": "",
    }


def ensure_machine_flow_fields():
    """
    Normalize all machine_flows in session state so older layouts remain usable.
    """
    if "machine_flows" not in st.session_state or st.session_state.machine_flows is None:
        st.session_state.machine_flows = []

    normalized = []
    for idx, flow in enumerate(st.session_state.machine_flows):
        base = build_default_machine_flow()
        if isinstance(flow, dict):
            base.update(flow)

        if not base.get("id"):
            base["id"] = generate_next_id("F", normalized)

        # Defensive normalization
        try:
            base["process_step_order"] = int(base.get("process_step_order", 1))
        except Exception:
            base["process_step_order"] = 1

        try:
            base["flow_rate_per_hr"] = float(base.get("flow_rate_per_hr", 0.0))
        except Exception:
            base["flow_rate_per_hr"] = 0.0

        try:
            base["lot_size"] = int(base.get("lot_size", 1))
        except Exception:
            base["lot_size"] = 1

        try:
            base["buffer_max_units"] = int(base.get("buffer_max_units", 0))
        except Exception:
            base["buffer_max_units"] = 0

        try:
            base["preferred_max_distance_ft"] = float(
                base.get("preferred_max_distance_ft", 25.0)
            )
        except Exception:
            base["preferred_max_distance_ft"] = 25.0

        base["value_added_step"] = bool(base.get("value_added_step", True))
        base["mandatory_adjacency"] = bool(base.get("mandatory_adjacency", False))
        base["part_family"] = str(base.get("part_family", "") or "")
        base["notes"] = str(base.get("notes", "") or "")

        mode = str(base.get("transfer_mode", "human") or "human")
        if mode not in VALID_FLOW_TRANSFER_MODES:
            mode = "human"
        base["transfer_mode"] = mode

        normalized.append(base)

    st.session_state.machine_flows = normalized


def validate_machine_flow_record(flow, placed_machines):
    """
    Validate a single machine flow record.
    Returns (ok: bool, msg: str)
    """
    required = [
        "from_machine_id",
        "to_machine_id",
        "process_step_order",
        "flow_rate_per_hr",
        "transfer_mode",
        "lot_size",
        "buffer_max_units",
        "preferred_max_distance_ft",
    ]

    for field in required:
        if field not in flow:
            return False, f"Flow missing required field: {field}"

    machine_ids = {str(m.get("id", "")).strip() for m in placed_machines}

    from_id = str(flow.get("from_machine_id", "")).strip()
    to_id = str(flow.get("to_machine_id", "")).strip()

    if not from_id:
        return False, "Flow source machine ID is required."
    if not to_id:
        return False, "Flow destination machine ID is required."
    if from_id == to_id:
        return False, "Flow source and destination cannot be the same machine."

    if from_id not in machine_ids:
        return False, f"Flow source machine '{from_id}' does not exist in layout."
    if to_id not in machine_ids:
        return False, f"Flow destination machine '{to_id}' does not exist in layout."

    try:
        process_step_order = int(flow.get("process_step_order", 1))
    except Exception:
        return False, "Process step order must be an integer."

    try:
        flow_rate_per_hr = float(flow.get("flow_rate_per_hr", 0.0))
    except Exception:
        return False, "Flow rate per hour must be numeric."

    try:
        lot_size = int(flow.get("lot_size", 1))
    except Exception:
        return False, "Lot size must be an integer."

    try:
        buffer_max_units = int(flow.get("buffer_max_units", 0))
    except Exception:
        return False, "Buffer max units must be an integer."

    try:
        preferred_max_distance_ft = float(flow.get("preferred_max_distance_ft", 25.0))
    except Exception:
        return False, "Preferred max distance must be numeric."

    if process_step_order < 1:
        return False, "Process step order must be >= 1."
    if flow_rate_per_hr < 0:
        return False, "Flow rate per hour cannot be negative."
    if lot_size < 1:
        return False, "Lot size must be >= 1."
    if buffer_max_units < 0:
        return False, "Buffer max units cannot be negative."
    if preferred_max_distance_ft < 0:
        return False, "Preferred max distance cannot be negative."

    mode = str(flow.get("transfer_mode", "human"))
    if mode not in VALID_FLOW_TRANSFER_MODES:
        return False, f"Unsupported transfer mode: {mode}"

    return True, ""


def validate_all_machine_flows(machine_flows, placed_machines):
    """
    Validate all machine flows. Returns (ok, errors)
    """
    errors = []
    seen_ids = set()

    for idx, flow in enumerate(machine_flows):
        ok, msg = validate_machine_flow_record(flow, placed_machines)
        if not ok:
            errors.append(f"Flow row {idx + 1}: {msg}")

        flow_id = str(flow.get("id", "")).strip()
        if flow_id:
            if flow_id in seen_ids:
                errors.append(f"Duplicate flow ID detected: {flow_id}")
            seen_ids.add(flow_id)

    return len(errors) == 0, errors


def get_machine_label_map(placed_machines):
    """
    Build a map of machine ID -> friendly label for UI use.
    """
    out = {}
    for i, m in enumerate(placed_machines):
        mid = str(m.get("id", f"M-{i+1:03d}"))
        make = str(m.get("Make", "")).strip()
        model = str(m.get("Model", "")).strip()
        if make or model:
            out[mid] = f"{mid} | {make} {model}".strip()
        else:
            out[mid] = mid
    return out

# --- Branch 4.7 additions: frontend scene/event state helpers ---

VALID_FRONTEND_VIEW_MODES = {"2d", "3d"}
VALID_FRONTEND_TOOL_MODES = {
    "select",
    "place_machine",
    "move_machine",
    "edit_conduit",
    "edit_workflow",
    "edit_crane",
    "place_light",
    "pan",
    "orbit",
}


def build_default_frontend_event():
    """
    Default placeholder payload for browser-canvas event exchange.
    """
    return {
        "event_id": 0,
        "event_type": "",
        "view_mode": "2d",
        "object_type": "",
        "object_id": "",
        "payload": {},
        "handled": True,
        "status": "",
    }


def normalize_frontend_state():
    """
    Ensure frontend-interaction session state keys exist and remain valid.
    Safe to call from init and after imports.
    """
    if "frontend_enabled" not in st.session_state:
        st.session_state.frontend_enabled = False

    if "frontend_renderer" not in st.session_state:
        st.session_state.frontend_renderer = "legacy"  # legacy, threejs

    if "frontend_view_mode" not in st.session_state:
        st.session_state.frontend_view_mode = "2d"

    if st.session_state.frontend_view_mode not in VALID_FRONTEND_VIEW_MODES:
        st.session_state.frontend_view_mode = "2d"

    if "frontend_tool_mode" not in st.session_state:
        st.session_state.frontend_tool_mode = "select"

    if st.session_state.frontend_tool_mode not in VALID_FRONTEND_TOOL_MODES:
        st.session_state.frontend_tool_mode = "select"

    if "frontend_scene_revision" not in st.session_state:
        st.session_state.frontend_scene_revision = 0

    if "frontend_last_event" not in st.session_state:
        st.session_state.frontend_last_event = build_default_frontend_event()

    if "frontend_pending_event" not in st.session_state:
        st.session_state.frontend_pending_event = build_default_frontend_event()

    if "frontend_last_event_id" not in st.session_state:
        st.session_state.frontend_last_event_id = 0

    if "frontend_status_msg" not in st.session_state:
        st.session_state.frontend_status_msg = ""

    if "frontend_selected_object_type" not in st.session_state:
        st.session_state.frontend_selected_object_type = ""

    if "frontend_selected_object_id" not in st.session_state:
        st.session_state.frontend_selected_object_id = ""

    if "frontend_selected_sub_index" not in st.session_state:
        st.session_state.frontend_selected_sub_index = -1

    if "frontend_hover_object_type" not in st.session_state:
        st.session_state.frontend_hover_object_type = ""

    if "frontend_hover_object_id" not in st.session_state:
        st.session_state.frontend_hover_object_id = ""

    if "frontend_snap_enabled" not in st.session_state:
        st.session_state.frontend_snap_enabled = True

    if "frontend_snap_ft" not in st.session_state:
        st.session_state.frontend_snap_ft = 10.0

    if "frontend_show_grid" not in st.session_state:
        st.session_state.frontend_show_grid = True

    if "frontend_show_labels" not in st.session_state:
        st.session_state.frontend_show_labels = True

    if "frontend_camera_target" not in st.session_state:
        st.session_state.frontend_camera_target = {"x": 0.0, "y": 0.0, "z": 0.0}

    if "frontend_camera_position" not in st.session_state:
        st.session_state.frontend_camera_position = {"x": 0.0, "y": 0.0, "z": 200.0}

    if "frontend_selection_revision" not in st.session_state:
        st.session_state.frontend_selection_revision = 0


def bump_frontend_scene_revision(reason=""):
    """
    Increment scene revision so the browser component knows the scene changed.
    """
    normalize_frontend_state()
    st.session_state.frontend_scene_revision = int(
        st.session_state.get("frontend_scene_revision", 0)
    ) + 1

    if reason:
        st.session_state.frontend_status_msg = (
            f"Scene revision {st.session_state.frontend_scene_revision}: {reason}"
        )


def clear_frontend_pending_event():
    """
    Reset the pending frontend event buffer after it is processed.
    """
    normalize_frontend_state()
    st.session_state.frontend_pending_event = build_default_frontend_event()


def set_frontend_pending_event(event_payload):
    """
    Store a browser event payload in session state.
    """
    normalize_frontend_state()

    if not isinstance(event_payload, dict):
        st.session_state.frontend_status_msg = "Ignored non-dict frontend event payload."
        return

    event = build_default_frontend_event()
    event.update(event_payload)

    try:
        event["event_id"] = int(event.get("event_id", 0))
    except Exception:
        event["event_id"] = 0

    view_mode = str(event.get("view_mode", "2d") or "2d")
    if view_mode not in VALID_FRONTEND_VIEW_MODES:
        view_mode = "2d"
    event["view_mode"] = view_mode

    if "payload" not in event or not isinstance(event.get("payload"), dict):
        event["payload"] = {}

    event["handled"] = bool(event.get("handled", False))

    st.session_state.frontend_pending_event = event


def mark_frontend_event_handled(status_msg=""):
    """
    Mark the current pending frontend event as handled and mirror it to last_event.
    """
    normalize_frontend_state()

    event = dict(st.session_state.get("frontend_pending_event", build_default_frontend_event()))
    event["handled"] = True

    if status_msg:
        event["status"] = status_msg
        st.session_state.frontend_status_msg = status_msg

    st.session_state.frontend_last_event = event
    st.session_state.frontend_last_event_id = int(event.get("event_id", 0))
    st.session_state.frontend_pending_event = build_default_frontend_event()


def sync_frontend_selection(object_type="", object_id="", sub_index=-1):
    """
    Mirror selection state for use by a browser-native canvas.
    """
    normalize_frontend_state()

    st.session_state.frontend_selected_object_type = str(object_type or "")
    st.session_state.frontend_selected_object_id = str(object_id or "")

    try:
        st.session_state.frontend_selected_sub_index = int(sub_index)
    except Exception:
        st.session_state.frontend_selected_sub_index = -1

    st.session_state.frontend_selection_revision = int(
        st.session_state.get("frontend_selection_revision", 0)
    ) + 1

def normalize_project_state_for_export():
    """
    Normalize current project state before export.
    Safe to call prior to building export JSON.
    """
    ensure_object_ids()
    ensure_machine_dimension_fields()
    ensure_lighting_dimension_fields()
    ensure_conduit_dimension_fields()
    ensure_crane_dimension_fields()
    ensure_workflow_dimension_fields()
    ensure_machine_flow_fields()

def normalize_imported_project_state():
    """
    Normalize imported session-state structures so older project files
    remain compatible with current app expectations.
    """
    # Defensive defaults first
    if "placed_machines" not in st.session_state or st.session_state.placed_machines is None:
        st.session_state.placed_machines = []

    if "placed_lighting" not in st.session_state or st.session_state.placed_lighting is None:
        st.session_state.placed_lighting = []

    if "placed_conduits" not in st.session_state or st.session_state.placed_conduits is None:
        st.session_state.placed_conduits = []

    if "placed_cranes" not in st.session_state or st.session_state.placed_cranes is None:
        st.session_state.placed_cranes = []

    if "machine_flows" not in st.session_state or st.session_state.machine_flows is None:
        st.session_state.machine_flows = []

    if "path_points" not in st.session_state or st.session_state.path_points is None:
        st.session_state.path_points = pd.DataFrame()

    # Then normalize IDs and annotation/dimension fields
    ensure_object_ids()
    ensure_machine_dimension_fields()
    ensure_lighting_dimension_fields()
    ensure_conduit_dimension_fields()
    ensure_crane_dimension_fields()
    ensure_workflow_dimension_fields()
    ensure_machine_flow_fields()
    normalize_frontend_state()


def validate_imported_project_state():
    """
    Validate all imported layout objects after normalization.
    Raises ValueError on failure.
    """
    # Validate machines
    for m in st.session_state.placed_machines:
        ok, msg = validate_machine_record(
            m,
            st.session_state.floor_w,
            st.session_state.floor_h,
        )
        if not ok:
            raise ValueError(
                f"Imported machine {m.get('id', '?')} invalid: {msg}"
            )

    # Validate conduits
    for c in st.session_state.placed_conduits:
        ok, msg = validate_polyline(
            c.get("x", []),
            c.get("y", []),
            st.session_state.floor_w,
            st.session_state.floor_h,
        )
        if not ok:
            raise ValueError(
                f"Imported conduit {c.get('id', '?')} invalid: {msg}"
            )

    # Validate cranes
    for cr in st.session_state.placed_cranes:
        ok, msg = validate_bbox(
            cr.get("ll_x", 0),
            cr.get("ll_y", 0),
            cr.get("ur_x", 0),
            cr.get("ur_y", 0),
            st.session_state.floor_w,
            st.session_state.floor_h,
        )
        if not ok:
            raise ValueError(
                f"Imported crane {cr.get('id', '?')} invalid: {msg}"
            )

    # Phase 3b: validate machine flows
    ok, flow_errors = validate_all_machine_flows(
        st.session_state.machine_flows,
        st.session_state.placed_machines,
    )
    if not ok:
        raise ValueError(" ; ".join(flow_errors))




def parse_coords(coord_str):
    """Parses comma-separated string list to a list of coordinate floats safely."""
    try:
        return [float(val.strip()) for val in coord_str.split(",") if val.strip()]
    except ValueError:
        return None


def generate_next_id(prefix, items):
    """Generate stable incrementing IDs like M-001, C-002, L-003, CR-001."""
    nums = []
    for item in items:
        item_id = str(item.get("id", ""))
        if item_id.startswith(f"{prefix}-"):
            try:
                nums.append(int(item_id.split("-")[-1]))
            except ValueError:
                pass
    next_num = max(nums, default=0) + 1
    return f"{prefix}-{next_num:03d}"


def validate_point_in_floor(x, y, floor_w, floor_h):
    """Returns True if a point is inside the floor boundary."""
    try:
        x = float(x)
        y = float(y)
        floor_w = float(floor_w)
        floor_h = float(floor_h)
    except Exception:
        return False
    return 0.0 <= x <= floor_w and 0.0 <= y <= floor_h


def validate_machine_record(machine, floor_w, floor_h):
    """Validate machine placement and core dimensions."""
    required = ["x", "y", "Width", "Height", "Standoff"]
    for field in required:
        if field not in machine:
            return False, f"Machine missing required field: {field}"

    try:
        x = float(machine["x"])
        y = float(machine["y"])
        width = float(machine["Width"])
        height = float(machine["Height"])
        standoff = float(machine["Standoff"])
        floor_w = float(floor_w)
        floor_h = float(floor_h)
    except Exception:
        return False, "Machine fields must be numeric where applicable."

    if not (0.0 <= x <= floor_w and 0.0 <= y <= floor_h):
        return False, "Machine placement must be inside the factory floor."

    if width <= 0 or height <= 0:
        return False, "Machine width and height must be positive."

    if standoff < 0:
        return False, "Machine standoff cannot be negative."

    return True, ""


def validate_polyline(x_vals, y_vals, floor_w, floor_h):
    """Validate conduit/workflow polyline points."""
    if not x_vals or not y_vals:
        return False, "Coordinate lists cannot be empty."
    if len(x_vals) != len(y_vals):
        return False, "X and Y coordinate counts must match."
    if len(x_vals) < 2:
        return False, "A route must contain at least two points."

    for x, y in zip(x_vals, y_vals):
        if not validate_point_in_floor(x, y, floor_w, floor_h):
            return False, f"Point ({x}, {y}) is outside the floor boundary."

    return True, ""


def validate_bbox(ll_x, ll_y, ur_x, ur_y, floor_w, floor_h):
    """Validate crane bounding box geometry."""
    try:
        ll_x = float(ll_x)
        ll_y = float(ll_y)
        ur_x = float(ur_x)
        ur_y = float(ur_y)
    except Exception:
        return False, "Crane coordinates must be numeric."

    if ll_x >= ur_x or ll_y >= ur_y:
        return False, "Crane lower-left must be below/left of upper-right."

    if not (0 <= ll_x <= floor_w and 0 <= ur_x <= floor_w):
        return False, "Crane X bounds must stay inside the floor."
    if not (0 <= ll_y <= floor_h and 0 <= ur_y <= floor_h):
        return False, "Crane Y bounds must stay inside the floor."

    return True, ""


def polyline_length(x_vals, y_vals):
    """Calculate route length for a polyline."""
    total = 0.0
    for i in range(1, len(x_vals)):
        dx = float(x_vals[i]) - float(x_vals[i - 1])
        dy = float(y_vals[i]) - float(y_vals[i - 1])
        total += math.sqrt(dx * dx + dy * dy)
    return round(total, 2)


def ensure_object_ids():
    """Backfill missing IDs in session state objects."""
    if "placed_machines" in st.session_state:
        for item in st.session_state.placed_machines:
            if "id" not in item:
                item["id"] = generate_next_id("M", st.session_state.placed_machines)

    if "placed_lighting" in st.session_state:
        for item in st.session_state.placed_lighting:
            if "id" not in item:
                item["id"] = generate_next_id("L", st.session_state.placed_lighting)

    if "placed_conduits" in st.session_state:
        for item in st.session_state.placed_conduits:
            if "id" not in item:
                item["id"] = generate_next_id("C", st.session_state.placed_conduits)

    if "placed_cranes" in st.session_state:
        for item in st.session_state.placed_cranes:
            if "id" not in item:
                item["id"] = generate_next_id("CR", st.session_state.placed_cranes)


def ensure_machine_dimension_fields():
    """Backfill editable machine dimension override fields in feet."""
    if "placed_machines" not in st.session_state:
        return

    for item in st.session_state.placed_machines:
        if "dim_visible" not in item:
            item["dim_visible"] = True
        if "dim_x_line_offset_ft" not in item:
            item["dim_x_line_offset_ft"] = 0.0
        if "dim_y_line_offset_ft" not in item:
            item["dim_y_line_offset_ft"] = 0.0
        if "dim_x_text_offset_ft" not in item:
            item["dim_x_text_offset_ft"] = 0.0
        if "dim_y_text_offset_ft" not in item:
            item["dim_y_text_offset_ft"] = 0.0
        if "dim_x_text_anchor_ft" not in item:
            item["dim_x_text_anchor_ft"] = 0.0
        if "dim_y_text_anchor_ft" not in item:
            item["dim_y_text_anchor_ft"] = 0.0
        if "dim_x_side" not in item:
            item["dim_x_side"] = "below"
        if "dim_y_side" not in item:
            item["dim_y_side"] = "left"        
        if "dim_show_footprint" not in item:
            item["dim_show_footprint"] = True


def ensure_lighting_dimension_fields():
    """Backfill editable lighting annotation override fields in feet."""
    if "placed_lighting" not in st.session_state:
        return

    for item in st.session_state.placed_lighting:
        if "dim_visible" not in item:
            item["dim_visible"] = True
        if "dim_x_line_offset_ft" not in item:
            item["dim_x_line_offset_ft"] = 0.0
        if "dim_y_line_offset_ft" not in item:
            item["dim_y_line_offset_ft"] = 0.0
        if "dim_x_text_offset_ft" not in item:
            item["dim_x_text_offset_ft"] = 0.0
        if "dim_y_text_offset_ft" not in item:
            item["dim_y_text_offset_ft"] = 0.0
        if "dim_x_text_anchor_ft" not in item:
            item["dim_x_text_anchor_ft"] = 0.0
        if "dim_y_text_anchor_ft" not in item:
            item["dim_y_text_anchor_ft"] = 0.0
        if "dim_x_side" not in item:
            item["dim_x_side"] = "below"
        if "dim_y_side" not in item:
            item["dim_y_side"] = "left"        
        if "dim_show_fixture_note" not in item:
            item["dim_show_fixture_note"] = True


def ensure_conduit_dimension_fields():
    """Backfill editable conduit annotation fields in feet."""
    if "placed_conduits" not in st.session_state:
        return

    for item in st.session_state.placed_conduits:
        if "dim_visible" not in item:
            item["dim_visible"] = True
        if "dim_label_x_offset_ft" not in item:
            item["dim_label_x_offset_ft"] = 4.0
        if "dim_label_y_offset_ft" not in item:
            item["dim_label_y_offset_ft"] = 4.0
        if "dim_show_length" not in item:
            item["dim_show_length"] = True
        if "dim_show_metadata" not in item:
            item["dim_show_metadata"] = True
        if "vertex_dim_offsets" not in item or not isinstance(item.get("vertex_dim_offsets"), dict):
            item["vertex_dim_offsets"] = {}

def ensure_crane_dimension_fields():
    """Backfill editable crane annotation fields in feet."""
    if "placed_cranes" not in st.session_state:
        return

    for item in st.session_state.placed_cranes:
        if "dim_visible" not in item:
            item["dim_visible"] = True
        if "dim_label_x_offset_ft" not in item:
            item["dim_label_x_offset_ft"] = 0.0
        if "dim_label_y_offset_ft" not in item:
            item["dim_label_y_offset_ft"] = 0.0
        if "dim_show_metadata" not in item:
            item["dim_show_metadata"] = True

def ensure_workflow_dimension_fields():
    """Backfill workflow annotation settings stored in session state, in feet."""
    if "workflow_dim_visible" not in st.session_state:
        st.session_state.workflow_dim_visible = True
    if "workflow_dim_label_x_offset_ft" not in st.session_state:
        st.session_state.workflow_dim_label_x_offset_ft = 4.0
    if "workflow_dim_label_y_offset_ft" not in st.session_state:
        st.session_state.workflow_dim_label_y_offset_ft = 4.0
    if "workflow_dim_show_length" not in st.session_state:
        st.session_state.workflow_dim_show_length = True
    if "workflow_dim_show_metadata" not in st.session_state:
        st.session_state.workflow_dim_show_metadata = True
    if "path_points" in st.session_state and len(st.session_state.path_points) > 0:
        df = st.session_state.path_points.copy()

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

        st.session_state.path_points = df

def on_crane_select_change(crane_lib):
    """Callback function to update crane input fields when library dropdown changes."""
    if "crane_lib_select_add" in st.session_state:
        selected_idx = st.session_state["crane_lib_select_add"]
        spec = crane_lib[selected_idx]
        st.session_state["crane_make_add"] = spec["Make"]
        st.session_state["crane_model_add"] = spec["Model"]
        st.session_state["crane_wt_add"] = float(spec["MaxLiftWeight"])
        st.session_state["crane_lsp_add"] = float(spec["MaxLiftSpeed"])
        st.session_state["crane_tsp_add"] = float(spec["MaxTransversalSpeed"])

def apply_imported_layout():
    """Callback function to apply uploaded project JSON/TXT data to session state."""
    if (
        "uploaded_layout_file" in st.session_state
        and st.session_state.uploaded_layout_file is not None
    ):
        try:
            content = st.session_state.uploaded_layout_file.read().decode("utf-8")
            imported_data = json.loads(content)

            # Phase 3b: normalize imported payload first
            imported_data = migrate_imported_project_dict(imported_data)

            schema_version = normalize_project_schema_version(
                imported_data.get("schema_version", "1.0")
            )
            st.session_state.schema_version = schema_version

            # Copy simple fields
            for key in [
                "designer_name",
                "dwg_title",
                "dwg_num",
                "sheet_size",
                "show_machines",
                "show_lighting",
                "show_cranes",
                "show_workflow",
                "show_electrical",
                "show_safety",
                "show_contour",
                "show_decibel",
                "placed_machines",
                "placed_lighting",
                "placed_conduits",
                "placed_cranes",
                "machine_flows",
                "show_locator_dims",
                "editor_enabled",
                "editor_selected_type",
                "editor_selected_index",
                "editor_snap_enabled",
                "editor_snap_ft",
                "editor_show_grid",
                "editor_show_labels",
                "workflow_dim_visible",
                "workflow_dim_label_x_offset_ft",
                "workflow_dim_label_y_offset_ft",
                "workflow_dim_show_length",
                "workflow_dim_show_metadata",
            ]:
                if key in imported_data:
                    st.session_state[key] = imported_data[key]

            # Coerce key numeric/state fields
            if "floor_w" in imported_data:
                st.session_state.floor_w = float(imported_data["floor_w"])
            if "floor_h" in imported_data:
                st.session_state.floor_h = float(imported_data["floor_h"])
            if "path_width_ft" in imported_data:
                st.session_state.path_width_ft = float(imported_data["path_width_ft"])

            # Restore workflow points
            if "path_points" in imported_data:
                st.session_state.path_points = pd.DataFrame(imported_data["path_points"])

            # Phase 3b: normalize all imported state
            normalize_imported_project_state()

            # Phase 3b: validate all imported state
            validate_imported_project_state()

            st.session_state["import_status"] = (
                "success",
                f"✅ Layout imported successfully (schema {schema_version}).",
            )

        except Exception as e:
            st.session_state["import_status"] = (
                "error",
                f"Error parsing layout file: {e}",
            )


def init_session_state(machinery_lib, lighting_lib, crane_lib):
    """Initializes all required session_state variables."""
    if "schema_version" not in st.session_state:
        st.session_state.schema_version = LATEST_PROJECT_SCHEMA_VERSION

    if "sheet_size" not in st.session_state:
        st.session_state.sheet_size = "B"
    if "floor_w" not in st.session_state:
        st.session_state.floor_w = 200.0
    if "floor_h" not in st.session_state:
        st.session_state.floor_h = 100.0
    if "path_width_ft" not in st.session_state:
        st.session_state.path_width_ft = 1.0

    # Layer Visibility Toggles
    if "show_machines" not in st.session_state:
        st.session_state.show_machines = True
    if "show_lighting" not in st.session_state:
        st.session_state.show_lighting = True
    if "show_cranes" not in st.session_state:
        st.session_state.show_cranes = True
    if "show_workflow" not in st.session_state:
        st.session_state.show_workflow = True
    if "show_electrical" not in st.session_state:
        st.session_state.show_electrical = True

    # Underlay Plot Toggles
    if "show_safety" not in st.session_state:
        st.session_state.show_safety = False
    if "show_contour" not in st.session_state:
        st.session_state.show_contour = False
    if "show_decibel" not in st.session_state:
        st.session_state.show_decibel = False
    if "show_locator_dims" not in st.session_state:
        st.session_state.show_locator_dims = False

    if "designer_name" not in st.session_state:
        st.session_state.designer_name = "Facility Architects Inc."
    if "dwg_title" not in st.session_state:
        st.session_state.dwg_title = "Factory Layout Blueprint"
    if "dwg_num" not in st.session_state:
        st.session_state.dwg_num = "FFO-001"

    # Interactive 2D Editor State
    if "editor_enabled" not in st.session_state:
        st.session_state.editor_enabled = False
    if "editor_selected_type" not in st.session_state:
        st.session_state.editor_selected_type = "machine"
    if "editor_selected_index" not in st.session_state:
        st.session_state.editor_selected_index = 0
    if "editor_snap_enabled" not in st.session_state:
        st.session_state.editor_snap_enabled = True
    if "editor_snap_ft" not in st.session_state:
        st.session_state.editor_snap_ft = 10.0
    if "editor_show_grid" not in st.session_state:
        st.session_state.editor_show_grid = True
    if "editor_show_labels" not in st.session_state:
        st.session_state.editor_show_labels = True
    if "editor_pending_dx_ft" not in st.session_state:
        st.session_state.editor_pending_dx_ft = 0.0
    if "editor_pending_dy_ft" not in st.session_state:
        st.session_state.editor_pending_dy_ft = 0.0
    if "editor_pending_dx_ft_input" not in st.session_state:
        st.session_state.editor_pending_dx_ft_input = 0.0
    if "editor_pending_dy_ft_input" not in st.session_state:
        st.session_state.editor_pending_dy_ft_input = 0.0
    if "editor_clear_pending_move" not in st.session_state:
        st.session_state.editor_clear_pending_move = False    
    if "editor_status_msg" not in st.session_state:
        st.session_state.editor_status_msg = ""
    if "editor_move_step_ft" not in st.session_state:
        st.session_state.editor_move_step_ft = 1.0
    if "editor_coord_x_input" not in st.session_state:
        st.session_state.editor_coord_x_input = 0.0
    if "editor_coord_y_input" not in st.session_state:
        st.session_state.editor_coord_y_input = 0.0
    if "editor_clear_coord_inputs" not in st.session_state:
        st.session_state.editor_clear_coord_inputs = False
    if "editor_pick_x_input" not in st.session_state:
        st.session_state.editor_pick_x_input = 0.0
    if "editor_pick_y_input" not in st.session_state:
        st.session_state.editor_pick_y_input = 0.0
    if "editor_box_ll_x_input" not in st.session_state:
        st.session_state.editor_box_ll_x_input = 0.0
    if "editor_box_ll_y_input" not in st.session_state:
        st.session_state.editor_box_ll_y_input = 0.0
    if "editor_box_ur_x_input" not in st.session_state:
        st.session_state.editor_box_ur_x_input = 0.0
    if "editor_box_ur_y_input" not in st.session_state:
        st.session_state.editor_box_ur_y_input = 0.0
    if "editor_selected_vertex_index" not in st.session_state:
        st.session_state.editor_selected_vertex_index = 0
    if "editor_vertex_x_input" not in st.session_state:
        st.session_state.editor_vertex_x_input = 0.0
    if "editor_vertex_y_input" not in st.session_state:
        st.session_state.editor_vertex_y_input = 0.0
    if "editor_pending_vertex_index" not in st.session_state:
        st.session_state.editor_pending_vertex_index = None
    if "editor_workflow_selected_point_index" not in st.session_state:
        st.session_state.editor_workflow_selected_point_index = 0
    if "editor_workflow_x_input" not in st.session_state:
        st.session_state.editor_workflow_x_input = 0.0
    if "editor_workflow_y_input" not in st.session_state:
        st.session_state.editor_workflow_y_input = 0.0
    if "editor_workflow_standoff_input" not in st.session_state:
        st.session_state.editor_workflow_standoff_input = 0.0
    if "editor_workflow_speed_input" not in st.session_state:
        st.session_state.editor_workflow_speed_input = 0.0
    if "editor_pending_workflow_point_index" not in st.session_state:
        st.session_state.editor_pending_workflow_point_index = None
    if "editor_drag_mode" not in st.session_state:
        st.session_state.editor_drag_mode = "object"  # object, conduit_vertex, workflow_point

    if "editor_drag_armed" not in st.session_state:
        st.session_state.editor_drag_armed = False

    if "editor_drag_drop_x_ft" not in st.session_state:
        st.session_state.editor_drag_drop_x_ft = 0.0

    if "editor_drag_drop_y_ft" not in st.session_state:
        st.session_state.editor_drag_drop_y_ft = 0.0

    if "editor_drag_preview_dx_ft" not in st.session_state:
        st.session_state.editor_drag_preview_dx_ft = 0.0

    if "editor_drag_preview_dy_ft" not in st.session_state:
        st.session_state.editor_drag_preview_dy_ft = 0.0
    if "editor_surface_mode" not in st.session_state:
        st.session_state.editor_surface_mode = "Phase 3 Interactive Canvas"
    if "editor_trace_map" not in st.session_state:
        st.session_state.editor_trace_map = []        
    if "editor_pending_selected_type" not in st.session_state:
        st.session_state.editor_pending_selected_type = None
    if "editor_pending_selected_index" not in st.session_state:
        st.session_state.editor_pending_selected_index = None
    if "editor_pending_selected_vertex_index" not in st.session_state:
        st.session_state.editor_pending_selected_vertex_index = None
    if "editor_pending_workflow_selected_point_index" not in st.session_state:
        st.session_state.editor_pending_workflow_selected_point_index = None
    if "editor_pending_phase3_status" not in st.session_state:
        st.session_state.editor_pending_phase3_status = None
    if "editor_trace_map" not in st.session_state:
        st.session_state.editor_trace_map = []

    if "editor_move_awaiting_target" not in st.session_state:
        st.session_state.editor_move_awaiting_target = False
    if "editor_move_selected_type" not in st.session_state:
        st.session_state.editor_move_selected_type = ""
    if "editor_move_selected_index" not in st.session_state:
        st.session_state.editor_move_selected_index = -1
    if "editor_move_selected_vertex_index" not in st.session_state:
        st.session_state.editor_move_selected_vertex_index = -1
    if "editor_move_selected_workflow_point_index" not in st.session_state:
        st.session_state.editor_move_selected_workflow_point_index = -1
    

    if "placed_machines" not in st.session_state:
        st.session_state.placed_machines = [
            {
                "id": "M-001",
                "Make": "Mazak",
                "Model": "Integrex i-200",
                "Type": "Multi axis CNC",
                "Width": 12.0,
                "Height": 10.0,
                "Standoff": 5.0,
                "Volume": 45,
                "Yield": 98.0,
                "CraneRequired": True,
                "Decibel": 75.0,
                "x": 40.0,
                "y": 60.0,
            },
            {
                "id": "M-002",
                "Make": "Arburg",
                "Model": "Allrounder 370",
                "Type": "Injection Molding",
                "Width": 15.0,
                "Height": 8.0,
                "Standoff": 4.0,
                "Volume": 60,
                "Yield": 95.0,
                "CraneRequired": False,
                "Decibel": 65.0,
                "x": 100.0,
                "y": 45.0,
            },
        ]

    if "placed_lighting" not in st.session_state:
        st.session_state.placed_lighting = [
            {
                "id": "L-001",
                "Make": "Lithonia",
                "Brand": "I-Beam",
                "Type": "LED",
                "Wattage": 150.0,
                "Kelvin": 5000,
                "Dimmable": True,
                "Lumens": 18000,
                "LuxTarget": 300,
                "x": 50.0,
                "y": 80.0,
            }
        ]

    if "placed_conduits" not in st.session_state:
        st.session_state.placed_conduits = [
            {
                "id": "C-001",
                "label": "Power Main",
                "utility_type": "electrical",
                "x": [40.0, 100.0],
                "y": [60.0, 45.0],
                "depth_in": 36,
                "warning_tape": True,
            }
        ]

    if "placed_cranes" not in st.session_state:
        st.session_state.placed_cranes = [
            {
                "id": "CR-001",
                "make": "Konecranes",
                "model": "CXT 10T",
                "max_lift_weight": 10.0,
                "max_lift_speed": 25.0,
                "max_transversal_speed": 120.0,
                "amperage": 60.0,
                "wattage": 12000.0,
                "ll_x": 20.0,
                "ll_y": 20.0,
                "ur_x": 180.0,
                "ur_y": 80.0,
            }
        ]

    # Crane inputs
    if "crane_make_add" not in st.session_state:
        st.session_state["crane_make_add"] = crane_lib[0]["Make"]
    if "crane_model_add" not in st.session_state:
        st.session_state["crane_model_add"] = crane_lib[0]["Model"]
    if "crane_wt_add" not in st.session_state:
        st.session_state["crane_wt_add"] = float(crane_lib[0]["MaxLiftWeight"])
    if "crane_lsp_add" not in st.session_state:
        st.session_state["crane_lsp_add"] = float(crane_lib[0]["MaxLiftSpeed"])
    if "crane_tsp_add" not in st.session_state:
        st.session_state["crane_tsp_add"] = float(crane_lib[0]["MaxTransversalSpeed"])

    if "machine_flows" not in st.session_state:
        st.session_state.machine_flows = []

    if "path_points" not in st.session_state:
        st.session_state.path_points = pd.DataFrame(
            {
                "Point": [1, 2, 3],
                "X Coordinate": [20.00, 70.00, 150.00],
                "Y Coordinate": [80.00, 50.00, 25.00],
                "Safety Standoff (ft)": [5.00, 5.00, 5.00],
                "Movement Speed": [5.00, 5.00, 5.00],
                "Movement Mode": ["human", "human", "human"],
            }
        )
    
    # Phase 3 drag/canvas editor state
    if "editor_canvas_mode" not in st.session_state:
        st.session_state.editor_canvas_mode = "select"  # select, move, dim

# Legacy drag/drop state retained temporarily during Phase 3C cleanup.
# Remove after canvas-first move workflow is fully implemented.
    if "editor_drag_enabled" not in st.session_state:
        st.session_state.editor_drag_enabled = True

    if "editor_drag_active" not in st.session_state:
        st.session_state.editor_drag_active = False

    if "editor_drag_entity_type" not in st.session_state:
        st.session_state.editor_drag_entity_type = ""

    if "editor_drag_entity_id" not in st.session_state:
        st.session_state.editor_drag_entity_id = ""

    if "editor_drag_vertex_index" not in st.session_state:
        st.session_state.editor_drag_vertex_index = -1

    if "editor_drag_dimension_target" not in st.session_state:
        st.session_state.editor_drag_dimension_target = ""

    if "editor_last_mouse_x" not in st.session_state:
        st.session_state.editor_last_mouse_x = None

    if "editor_last_mouse_y" not in st.session_state:
        st.session_state.editor_last_mouse_y = None

    if "editor_canvas_refresh_token" not in st.session_state:
        st.session_state.editor_canvas_refresh_token = 0

    if "editor_click_x_ft" not in st.session_state:
        st.session_state.editor_click_x_ft = 0.0

    if "editor_click_y_ft" not in st.session_state:
        st.session_state.editor_click_y_ft = 0.0

    if "editor_selected_dimension_kind" not in st.session_state:
        st.session_state.editor_selected_dimension_kind = ""

    if "editor_selected_dimension_owner_id" not in st.session_state:
        st.session_state.editor_selected_dimension_owner_id = ""

    if "editor_selected_dimension_axis" not in st.session_state:
        st.session_state.editor_selected_dimension_axis = ""

    if "editor_phase3_status" not in st.session_state:
        st.session_state.editor_phase3_status = ""
        
    if "editor_dim_move_awaiting_target" not in st.session_state:
        st.session_state.editor_dim_move_awaiting_target = False

    if "editor_dim_selected_owner_type" not in st.session_state:
        st.session_state.editor_dim_selected_owner_type = ""

    if "editor_dim_selected_owner_index" not in st.session_state:
        st.session_state.editor_dim_selected_owner_index = -1

    if "editor_dim_selected_sub_index" not in st.session_state:
        st.session_state.editor_dim_selected_sub_index = -1

    if "editor_dim_selected_owner_id" not in st.session_state:
        st.session_state.editor_dim_selected_owner_id = ""

    if "editor_dim_selected_axis" not in st.session_state:
        st.session_state.editor_dim_selected_axis = ""  

    

    ensure_object_ids()
    ensure_machine_dimension_fields()
    ensure_lighting_dimension_fields()
    ensure_conduit_dimension_fields()
    ensure_crane_dimension_fields()
    ensure_workflow_dimension_fields()
    ensure_machine_flow_fields()
    normalize_frontend_state()

