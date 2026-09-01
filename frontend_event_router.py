# frontend_event_router.py
import pandas as pd

from state_manager import (
    validate_machine_record,
    validate_bbox,
    validate_polyline,
    validate_point_in_floor,
    set_frontend_pending_event,
    mark_frontend_event_handled,
    clear_frontend_pending_event,
    sync_frontend_selection,
    bump_frontend_scene_revision,
)


VALID_FRONTEND_EVENT_TYPES = {
    "select_object",
    "move_machine",
    "move_light",
    "update_crane_box",
    "update_conduit_vertex",
    "update_workflow_point",
    "set_tool_mode",
    "set_view_mode",
    "set_camera_state",
    "noop",
}


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


def _safe_str(value, default=""):
    try:
        if value is None:
            return default
        return str(value)
    except Exception:
        return default


def _safe_dict(value):
    return value if isinstance(value, dict) else {}


def _find_object_index_by_id(items, object_id):
    object_id = _safe_str(object_id, "")
    for idx, item in enumerate(items):
        if _safe_str(item.get("id", ""), "") == object_id:
            return idx
    return -1


def _set_status(session_state, msg):
    session_state.frontend_status_msg = str(msg)


def _handle_select_object(session_state, event):
    payload = _safe_dict(event.get("payload", {}))
    object_type = _safe_str(
        event.get("object_type", payload.get("object_type", "")),
        "",
    )
    object_id = _safe_str(
        event.get("object_id", payload.get("object_id", "")),
        "",
    )
    sub_index = _safe_int(payload.get("sub_index", -1), -1)

    sync_frontend_selection(object_type, object_id, sub_index)

    # Mirror into legacy editor selection where practical
    if object_type == "machine":
        idx = _find_object_index_by_id(session_state.placed_machines, object_id)
        if idx >= 0:
            session_state.editor_selected_type = "machine"
            session_state.editor_selected_index = idx

    elif object_type == "lighting":
        idx = _find_object_index_by_id(session_state.placed_lighting, object_id)
        if idx >= 0:
            session_state.editor_selected_type = "lighting"
            session_state.editor_selected_index = idx

    elif object_type == "conduit":
        idx = _find_object_index_by_id(session_state.placed_conduits, object_id)
        if idx >= 0:
            session_state.editor_selected_type = "conduit"
            session_state.editor_selected_index = idx
            session_state.editor_pending_vertex_index = sub_index

    elif object_type == "crane":
        idx = _find_object_index_by_id(session_state.placed_cranes, object_id)
        if idx >= 0:
            session_state.editor_selected_type = "crane"
           
