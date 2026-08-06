# state_manager.py
import json
import pandas as pd
import streamlit as st


def parse_coords(coord_str):
  """Parses comma-separated string list to a list of coordinate floats safely."""
  try:
    return [float(val.strip()) for val in coord_str.split(",") if val.strip()]
  except ValueError:
    return None


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
        st.session_state.path_points = pd.DataFrame(
            imported_data["path_points"]
        )

      st.session_state["import_status"] = (
          "success",
          "✅ Saved layout successfully imported and applied to the blueprint"
          " view!",
      )
    except Exception as e:
      st.session_state["import_status"] = (
          "error",
          f"Error parsing layout file: {e}",
      )


def init_session_state(machinery_lib, lighting_lib, crane_lib):
  """Initializes all required session_state variables."""
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
            "Make": "Mazak",
            "Model": "Integrex i-200",
            "Width": 12.0,
            "Height": 10.0,
            "Standoff": 5.0,
            "Volume": 45,
            "Yield": 98.0,
            "x": 40.0,
            "y": 60.0,
            "Decibel": 75.0,
        },
        {
            "Make": "Arburg",
            "Model": "Allrounder 370",
            "Width": 15.0,
            "Height": 8.0,
            "Standoff": 4.0,
            "Volume": 60,
            "Yield": 95.0,
            "x": 100.0,
            "y": 45.0,
            "Decibel": 65.0,
        },
    ]
  if "placed_lighting" not in st.session_state:
    st.session_state.placed_lighting = [{
        "Make": "Lithonia",
        "Brand": "I-Beam",
        "Type": "LED",
        "Wattage": 150.0,
        "x": 50.0,
        "y": 80.0,
        "Lumens": 18000,
    }]
  if "placed_conduits" not in st.session_state:
    st.session_state.placed_conduits = [{
        "label": "Power Main",
        "x": [40.0, 100.0],
        "y": [60.0, 45.0],
        "depth_in": 36,
        "warning_tape": True,
    }]
  if "placed_cranes" not in st.session_state:
    st.session_state.placed_cranes = [{
        "make": "Konecranes",
        "model": "CXT 10T",
        "max_lift_weight": 10.0,
        "max_lift_speed": 25.0,
        "max_transversal_speed": 120.0,
        "ll_x": 20.0,
        "ll_y": 20.0,
        "ur_x": 180.0,
        "ur_y": 80.0,
    }]

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
    st.session_state["crane_tsp_add"] = float(
        crane_lib[0]["MaxTransversalSpeed"]
    )

  if "machine_flows" not in st.session_state:
    st.session_state.machine_flows = []

  if "path_points" not in st.session_state:
    st.session_state.path_points = pd.DataFrame({
        "Point": [1, 2, 3],
        "X Coordinate": [20.00, 70.00, 150.00],
        "Y Coordinate": [80.00, 50.00, 25.00],
        "Safety Standoff (ft)": [5.00, 5.00, 5.00],
        "Movement Speed": [5.00, 5.00, 5.00],
    })
