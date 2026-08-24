# state_manager.py
import json
import math
import pandas as pd
import streamlit as st


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

    if not validate_point_in_floor(machine["x"], machine["y"], floor_w, floor_h):
        return False, "Machine placement must be inside the factory floor."

    try:
        if float(machine["Width"]) <= 0 or float(machine["Height"]) <= 0:
            return False, "Machine width and height must be positive."
        if float(machine["Standoff"]) < 0:
            return False, "Machine standoff cannot be negative."
    except Exception:
        return False, "Machine dimensions/standoff must be numeric."

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

            # Minimal schema handling
            schema_version = imported_data.get("schema_version", "1.0")

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
            ]:
                if key in imported_data:
                    st.session_state[key] = imported_data[key]

            if "floor_w" in imported_data:
                st.session_state.floor_w = float(imported_data["floor_w"])
            if "floor_h" in imported_data:
                st.session_state.floor_h = float(imported_data["floor_h"])
            if "path_width_ft" in imported_data:
                st.session_state.path_width_ft = float(imported_data["path_width_ft"])
            if "path_points" in imported_data:
                st.session_state.path_points = pd.DataFrame(imported_data["path_points"])

            ensure_object_ids()

            # Validate imported objects
            for m in st.session_state.placed_machines:
                ok, msg = validate_machine_record(
                    m, st.session_state.floor_w, st.session_state.floor_h
                )
                if not ok:
                    raise ValueError(f"Imported machine {m.get('id', '?')} invalid: {msg}")

            for c in st.session_state.placed_conduits:
                ok, msg = validate_polyline(
                    c.get("x", []),
                    c.get("y", []),
                    st.session_state.floor_w,
                    st.session_state.floor_h,
                )
                if not ok:
                    raise ValueError(f"Imported conduit {c.get('id', '?')} invalid: {msg}")

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
                    raise ValueError(f"Imported crane {cr.get('id', '?')} invalid: {msg}")

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
        st.session_state.schema_version = "1.1"

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

    if "designer_name" not in st.session_state:
        st.session_state.designer_name = "Facility Architects Inc."
    if "dwg_title" not in st.session_state:
        st.session_state.dwg_title = "Factory Layout Blueprint"
    if "dwg_num" not in st.session_state:
        st.session_state.dwg_num = "FFO-001"

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
    st.session_state.placed_conduits = [{
        "id": "C-001",
        "label": "Power Main",
        "utility_type": "electrical",
        "x": [40.0, 100.0],
        "y": [60.0, 45.0],
        "depth_in": 36,
        "warning_tape": True,
    }]

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
    st.session_state.path_points = pd.DataFrame({
        "Point": [1, 2, 3],
        "X Coordinate": [20.00, 70.00, 150.00],
        "Y Coordinate": [80.00, 50.00, 25.00],
        "Safety Standoff (ft)": [5.00, 5.00, 5.00],
        "Movement Speed": [5.00, 5.00, 5.00],
        "Movement Mode": ["human", "human", "human"],
    })

    ensure_object_ids()
