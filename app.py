import json
import numpy as np
import pandas as pd
import streamlit as st
from engine import calculate_production_metrics, run_layout_analysis
from library_loader import (
    get_default_cranes,
    get_default_lighting,
    get_default_machinery,
)
from visualization import draw_asme_drawing

# Set page configuration safely
st.set_page_config(
    page_title="Factory Floor Optimizer", page_icon="🏭", layout="wide"
)

st.title("🏭 Factory Floor Optimizer & Compliance Suite")
st.markdown(
    "Designed strictly to comply with **ASME Y14.1 Drawing Sheets** and **NJ"
    " Uniform Construction Code** Standards."
)


# Helper to parse string list to coordinate floats safely
def parse_coords(coord_str):
  try:
    return [float(val.strip()) for val in coord_str.split(",") if val.strip()]
  except ValueError:
    return None


# Load Default Libraries
machinery_lib = get_default_machinery()
lighting_lib = get_default_lighting()
crane_lib = get_default_cranes()

df_machinery = pd.DataFrame(machinery_lib)
df_lighting = pd.DataFrame(lighting_lib)
df_cranes = pd.DataFrame(crane_lib)

# Setup Session State for Blueprint Controls & Placed Items
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

# Initialize crane add input keys in session state
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
  })


# Callback function to update crane input fields when library dropdown changes
def on_crane_select_change():
  if "crane_lib_select_add" in st.session_state:
    selected_idx = st.session_state["crane_lib_select_add"]
    spec = crane_lib[selected_idx]
    st.session_state["crane_make_add"] = spec["Make"]
    st.session_state["crane_model_add"] = spec["Model"]
    st.session_state["crane_wt_add"] = float(spec["MaxLiftWeight"])
    st.session_state["crane_lsp_add"] = float(spec["MaxLiftSpeed"])
    st.session_state["crane_tsp_add"] = float(spec["MaxTransversalSpeed"])


# Callback function to execute BEFORE page widgets are instantiated
def apply_imported_layout():
  if (
      "uploaded_layout_file" in st.session_state
      and st.session_state.uploaded_layout_file is not None
  ):
    try:
      content = st.session_state.uploaded_layout_file.read().decode("utf-8")
      imported_data = json.loads(content)

      if "designer_name" in imported_data:
        st.session_state.designer_name = imported_data["designer_name"]
      if "dwg_title" in imported_data:
        st.session_state.dwg_title = imported_data["dwg_title"]
      if "dwg_num" in imported_data:
        st.session_state.dwg_num = imported_data["dwg_num"]
      if "sheet_size" in imported_data:
        st.session_state.sheet_size = imported_data["sheet_size"]
      if "floor_w" in imported_data:
        st.session_state.floor_w = float(imported_data["floor_w"])
      if "floor_h" in imported_data:
        st.session_state.floor_h = float(imported_data["floor_h"])
      if "path_width_ft" in imported_data:
        st.session_state.path_width_ft = float(imported_data["path_width_ft"])
      if "show_machines" in imported_data:
        st.session_state.show_machines = imported_data["show_machines"]
      if "show_lighting" in imported_data:
        st.session_state.show_lighting = imported_data["show_lighting"]
      if "show_cranes" in imported_data:
        st.session_state.show_cranes = imported_data["show_cranes"]
      if "show_safety" in imported_data:
        st.session_state.show_safety = imported_data["show_safety"]
      if "show_contour" in imported_data:
        st.session_state.show_contour = imported_data["show_contour"]
      if "show_decibel" in imported_data:
        st.session_state.show_decibel = imported_data["show_decibel"]
      if "placed_machines" in imported_data:
        st.session_state.placed_machines = imported_data["placed_machines"]
      if "placed_lighting" in imported_data:
        st.session_state.placed_lighting = imported_data["placed_lighting"]
      if "placed_conduits" in imported_data:
        st.session_state.placed_conduits = imported_data["placed_conduits"]
      if "placed_cranes" in imported_data:
        st.session_state.placed_cranes = imported_data["placed_cranes"]
      if "machine_flows" in imported_data:
        st.session_state.machine_flows = imported_data["machine_flows"]
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


# Render Top Main ASME Blueprint Drawing View (75% Window Width)
st.header("📐 Live ASME Y14.1 Blueprint View")

# Extract workflow path points from session state for ASME Drawing
active_workflow_paths = []
if len(st.session_state.path_points) > 0:
  try:
    px = [
        float(v)
        for v in st.session_state.path_points["X Coordinate"].tolist()
    ]
    py = [
        float(v)
        for v in st.session_state.path_points["Y Coordinate"].tolist()
    ]
    p_so = [
        float(v)
        for v in st.session_state.path_points["Safety Standoff (ft)"].tolist()
    ]
    if len(px) >= 2:
      active_workflow_paths.append({
          "x": px,
          "y": py,
          "standoffs": p_so,
          "width_ft": float(st.session_state.path_width_ft),
      })
  except Exception:
    pass

fig = draw_asme_drawing(
    size_char=st.session_state.sheet_size,
    floor_width_ft=st.session_state.floor_w,
    floor_height_ft=st.session_state.floor_h,
    machines=st.session_state.placed_machines,
    conduits=st.session_state.placed_conduits,
    lighting=st.session_state.placed_lighting,
    workflow_paths=active_workflow_paths,
    cranes=st.session_state.placed_cranes,
    show_machines=st.session_state.show_machines,
    show_lighting=st.session_state.show_lighting,
    show_cranes=st.session_state.show_cranes,
    show_safety=st.session_state.show_safety,
    show_contour=st.session_state.show_contour,
    show_decibel=st.session_state.show_decibel,
    designer_name=st.session_state.designer_name,
    dwg_title=st.session_state.dwg_title,
    dwg_num=st.session_state.dwg_num,
)

# Display Blueprint at 75% width
bp_col, bp_space = st.columns([0.75, 0.25])
with bp_col:
  st.pyplot(fig, use_container_width=True)

# Analytics Summary
metrics = calculate_production_metrics(st.session_state.placed_machines)
warnings = run_layout_analysis(
    st.session_state.placed_machines, st.session_state.placed_conduits
)

stat1, stat2, stat3 = st.columns(3)
with stat1:
  st.metric("Line Bottleneck", metrics.get("Bottleneck Machine", "N/A"))
with stat2:
  st.metric("Line Balance Index", metrics.get("Line Balance Efficiency", "N/A"))
with stat3:
  st.metric(
      "UDP Power Sleep Savings", metrics.get("UDP Switch-Off Savings", "N/A")
  )

if warnings:
  st.error("⚠️ Spatial & Regulatory Warnings Found:")
  for warn in warnings:
    st.warning(warn)
else:
  st.success(
      "✅ Layout fully meets OSHA Clearance and NJ-UCC Section 704 Electrical"
      " Standards!"
  )

st.divider()

# TABBED NAVIGATION FOR ALL CONFIGURATION MENUS
st.header("⚙️ Layout Configuration & Component Menus")

(
    tab_proj,
    tab_dims,
    tab_plots,
    tab_mach,
    tab_cond,
    tab_light,
    tab_crane,
    tab_flow,
    tab_io,
    tab_lib,
) = st.tabs([
    "📋 Project Info",
    "📏 Floor & Sheet Dimensions",
    "📊 Plots",
    "🤖 Machinery Placement & Edits",
    "🔌 Conduit Routing & Edits",
    "💡 Lighting Fixtures & Edits",
    "🏗️ Overhead Cranes & Coverage",
    "🔄 Machine Flows & Workflow Paths",
    "💾 Import / Export Layout",
    "📚 Default Libraries",
])

# TAB 0: PROJECT INFO
with tab_proj:
  st.subheader("📋 Blueprint Title Block Parameters")
  st.markdown(
      "Edit the metadata displayed inside the ASME Y14.1 Title Block on the"
      " blueprint drawing."
  )

  p_col1, p_col2 = st.columns(2)
  with p_col1:
    st.text_input("Designer / Company Name", key="designer_name")
    st.text_input("Drawing Title", key="dwg_title")
  with p_col2:
    st.text_input("Drawing Number (DWG NO)", key="dwg_num")

# TAB 1: FLOOR & SHEET DIMENSIONS
with tab_dims:
  st.subheader("📐 Factory Floor & ASME Drawing Sheet Configuration")
  dim_col1, dim_col2 = st.columns(2)
  with dim_col1:
    st.selectbox(
        "Select ASME Sheet Boundary Size", ["A", "B", "C", "D"], key="sheet_size"
    )
    st.number_input(
        "Factory Floor Width (feet)",
        min_value=10.0,
        max_value=1000.0,
        step=10.0,
        key="floor_w",
    )
  with dim_col2:
    st.number_input(
        "Factory Floor Height (feet)",
        min_value=10.0,
        max_value=1000.0,
        step=10.0,
        key="floor_h",
    )
    st.number_input(
        "Workflow Path Width (feet)",
        min_value=0.5,
        max_value=10.0,
        step=0.5,
        key="path_width_ft",
    )

# TAB 2: PLOTS
with tab_plots:
  st.subheader("📊 Blueprint Layer Visibility & Contour Underlays")
  st.markdown("Toggle component layers and analysis underlay visualizations.")

  st.markdown("##### 👁️ Component Layer Visibility Toggles")
  lyr_col1, lyr_col2, lyr_col3 = st.columns(3)
  with lyr_col1:
    st.checkbox("Show Machinery Layer", key="show_machines")
  with lyr_col2:
    st.checkbox("Show Lighting Fixtures Layer", key="show_lighting")
  with lyr_col3:
    st.checkbox("Show Overhead Cranes Layer", key="show_cranes")

  st.markdown("##### 🎨 Analysis Plot Underlays")
  plt_col1, plt_col2, plt_col3 = st.columns(3)
  with plt_col1:
    st.checkbox("Show Safety Heatmap underlay", key="show_safety")
  with plt_col2:
    st.checkbox("Show Part Volume Contour plots", key="show_contour")
  with plt_col3:
    st.checkbox(
        "Show Machine Decibel Contour plot (Inverse Square Law)",
        key="show_decibel",
    )

# TAB 3: MACHINERY PLACEMENT & EDITS
with tab_mach:
  m_col1, m_col2 = st.columns(2)
  with m_col1:
    st.subheader("🤖 Place Machine from Library")
    machine_options = [
        f"{m['Make']} {m['Model']} ({m['Type']})" for m in machinery_lib
    ]
    selected_m_idx = st.selectbox(
        "Choose Machine",
        range(len(machine_options)),
        format_func=lambda x: machine_options[x],
    )
    mx_coord = st.number_input(
        "Target Placement X (ft)",
        min_value=0.0,
        max_value=float(st.session_state.floor_w),
        value=70.0,
        key="mx_tab",
    )
    my_coord = st.number_input(
        "Target Placement Y (ft)",
        min_value=0.0,
        max_value=float(st.session_state.floor_h),
        value=50.0,
        key="my_tab",
    )

    if st.button("Drop Machine onto Floor", type="primary"):
      spec = machinery_lib[selected_m_idx].copy()
      spec["x"] = mx_coord
      spec["y"] = my_coord
      st.session_state.placed_machines.append(spec)
      st.success(
          f"Placed {spec['Make']} {spec['Model']} at ({mx_coord}, {my_coord})!"
      )
      st.rerun() if hasattr(st, "rerun") else st.experimental_rerun()

  with m_col2:
    if len(st.session_state.placed_machines) > 0:
      st.subheader("🛠️ Modify or Delete Placed Machinery")
      placed_options = [
          f"M{i+1}: {m['Make']} {m['Model']} at ({m['x']:.1f} ft, {m['y']:.1f}"
          " ft)"
          for i, m in enumerate(st.session_state.placed_machines)
      ]
      selected_placed_idx = st.selectbox(
          "Select Machine on Floor to Edit",
          range(len(placed_options)),
          format_func=lambda x: placed_options[x],
      )

      mach = st.session_state.placed_machines[selected_placed_idx]
      edit_x = st.number_input(
          "Adjust Coordinate X (ft)",
          min_value=0.0,
          max_value=float(st.session_state.floor_w),
          value=float(mach["x"]),
          key=f"edit_x_tab_{selected_placed_idx}",
      )
      edit_y = st.number_input(
          "Adjust Coordinate Y (ft)",
          min_value=0.0,
          max_value=float(st.session_state.floor_h),
          value=float(mach["y"]),
          key=f"edit_y_tab_{selected_placed_idx}",
      )

      btn_col1, btn_col2 = st.columns(2)
      with btn_col1:
        if st.button(
            "Update Position", key=f"update_m_btn_{selected_placed_idx}"
        ):
          st.session_state.placed_machines[selected_placed_idx]["x"] = edit_x
          st.session_state.placed_machines[selected_placed_idx]["y"] = edit_y
          st.success(f"Machine M{selected_placed_idx+1} moved successfully!")
          st.rerun() if hasattr(st, "rerun") else st.experimental_rerun()
      with btn_col2:
        if st.button(
            "Delete Machine", key=f"delete_m_btn_{selected_placed_idx}"
        ):
          removed = st.session_state.placed_machines.pop(selected_placed_idx)
          st.warning(
              f"Removed M{selected_placed_idx+1} ({removed['Make']}"
              f" {removed['Model']}) from layout."
          )
          st.rerun() if hasattr(st, "rerun") else st.experimental_rerun()
    else:
      st.info("No machines currently placed on the layout.")

# TAB 4: CONDUIT ROUTING & EDITS
with tab_cond:
  c_col1, c_col2 = st.columns(2)
  with c_col1:
    st.subheader("🔌 Route Conduit Run (Polyline)")
    cx_lbl = st.text_input(
        "Conduit Run Label", "Sub-Station Hookup", key="cx_lbl_tab"
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
        "Contains Orange 4 mil Warning Tape", value=True, key="cx_tape_tab"
    )

    if st.button("Route Conduit Path", type="primary"):
      parsed_x = parse_coords(cx_x_str)
      parsed_y = parse_coords(cx_y_str)

      if (
          parsed_x is None
          or parsed_y is None
          or len(parsed_x) != len(parsed_y)
      ):
        st.error(
            "Error: Coordinates must be valid numeric values, and X and Y must"
            " contain matching point counts."
        )
      else:
        st.session_state.placed_conduits.append({
            "label": cx_lbl,
            "x": parsed_x,
            "y": parsed_y,
            "depth_in": cx_depth,
            "warning_tape": cx_tape,
        })
        st.success(f"Successfully routed conduit '{cx_lbl}'!")
        st.rerun() if hasattr(st, "rerun") else st.experimental_rerun()

  with c_col2:
    if len(st.session_state.placed_conduits) > 0:
      st.subheader("🛠️ Modify or Delete Placed Conduits")
      conduit_options = [
          f"{i+1}: {c['label']} ({len(c['x'])} points)"
          for i, c in enumerate(st.session_state.placed_conduits)
      ]
      selected_cond_idx = st.selectbox(
          "Select Conduit to Edit",
          range(len(conduit_options)),
          format_func=lambda x: conduit_options[x],
      )

      cond = st.session_state.placed_conduits[selected_cond_idx]
      edit_cx_lbl = st.text_input(
          "Edit Conduit Label", cond["label"], key=f"lbl_tab_{selected_cond_idx}"
      )
      edit_cx_x_str = st.text_input(
          "Edit X Coordinates",
          ", ".join(map(str, cond["x"])),
          key=f"cx_tab_{selected_cond_idx}",
      )
      edit_cx_y_str = st.text_input(
          "Edit Y Coordinates",
          ", ".join(map(str, cond["y"])),
          key=f"cy_tab_{selected_cond_idx}",
      )
      edit_cx_depth = st.number_input(
          "Edit Burial Depth (inches)",
          min_value=12,
          max_value=60,
          value=int(cond["depth_in"]),
          key=f"dp_tab_{selected_cond_idx}",
      )
      edit_cx_tape = st.checkbox(
          "Edit Warning Tape Status",
          value=cond["warning_tape"],
          key=f"tp_tab_{selected_cond_idx}",
      )

      c_btn_col1, c_btn_col2 = st.columns(2)
      with c_btn_col1:
        if st.button(
            "Update Conduit Run", key=f"up_c_tab_{selected_cond_idx}"
        ):
          up_x = parse_coords(edit_cx_x_str)
          up_y = parse_coords(edit_cx_y_str)
          if up_x is None or up_y is None or len(up_x) != len(up_y):
            st.error("Error: Coordinates must be valid numeric pairs.")
          else:
            st.session_state.placed_conduits[selected_cond_idx] = {
                "label": edit_cx_lbl,
                "x": up_x,
                "y": up_y,
                "depth_in": edit_cx_depth,
                "warning_tape": edit_cx_tape,
            }
            st.success("Conduit run updated successfully!")
            st.rerun() if hasattr(st, "rerun") else st.experimental_rerun()
      with c_btn_col2:
        if st.button(
            "Delete Conduit Run", key=f"del_c_tab_{selected_cond_idx}"
        ):
          removed_c = st.session_state.placed_conduits.pop(selected_cond_idx)
          st.warning(f"Removed conduit run '{removed_c['label']}'.")
          st.rerun() if hasattr(st, "rerun") else st.experimental_rerun()
    else:
      st.info("No conduits currently routed.")

# TAB 5: LIGHTING FIXTURES & EDITS
with tab_light:
  l_col1, l_col2 = st.columns(2)
  with l_col1:
    st.subheader("💡 Place Light from Library")
    light_options = [
        f"{l['Make']} {l['Brand']} ({l['Type']})" for l in lighting_lib
    ]
    selected_l_idx = st.selectbox(
        "Choose Lighting Fixture",
        range(len(light_options)),
        format_func=lambda x: light_options[x],
        key="l_sel_tab",
    )
    lx_coord = st.number_input(
        "Placement X (ft)",
        min_value=0.0,
        max_value=float(st.session_state.floor_w),
        value=50.0,
        key="lx_tab",
    )
    ly_coord = st.number_input(
        "Placement Y (ft)",
        min_value=0.0,
        max_value=float(st.session_state.floor_h),
        value=80.0,
        key="ly_tab",
    )

    if st.button("Drop Light onto Floor", type="primary"):
      spec_l = lighting_lib[selected_l_idx].copy()
      spec_l["x"] = lx_coord
      spec_l["y"] = ly_coord
      st.session_state.placed_lighting.append(spec_l)
      st.success(f"Placed Lighting Fixture at ({lx_coord}, {ly_coord})!")
      st.rerun() if hasattr(st, "rerun") else st.experimental_rerun()

  with l_col2:
    if len(st.session_state.placed_lighting) > 0:
      st.subheader("🛠️ Modify or Delete Placed Lighting")
      placed_l_opts = [
          f"L{i+1}: {li['Make']} {li['Brand']} at ({li['x']:.1f} ft,"
          f" {li['y']:.1f} ft)"
          for i, li in enumerate(st.session_state.placed_lighting)
      ]
      selected_placed_l_idx = st.selectbox(
          "Select Light on Floor to Edit",
          range(len(placed_l_opts)),
          format_func=lambda x: placed_l_opts[x],
      )
      active_light = st.session_state.placed_lighting[selected_placed_l_idx]
      edit_lx = st.number_input(
          "Adjust Light Coordinate X (ft)",
          min_value=0.0,
          max_value=float(st.session_state.floor_w),
          value=float(active_light["x"]),
          key=f"elx_tab_{selected_placed_l_idx}",
      )
      edit_ly = st.number_input(
          "Adjust Light Coordinate Y (ft)",
          min_value=0.0,
          max_value=float(st.session_state.floor_h),
          value=float(active_light["y"]),
          key=f"ely_tab_{selected_placed_l_idx}",
      )

      l_btn_col1, l_btn_col2 = st.columns(2)
      with l_btn_col1:
        if st.button(
            "Update Light Position", key=f"up_l_tab_{selected_placed_l_idx}"
        ):
          st.session_state.placed_lighting[selected_placed_l_idx]["x"] = edit_lx
          st.session_state.placed_lighting[selected_placed_l_idx]["y"] = edit_ly
          st.success(f"Lighting L{selected_placed_l_idx+1} position updated!")
          st.rerun() if hasattr(st, "rerun") else st.experimental_rerun()
      with l_btn_col2:
        if st.button(
            "Delete Light Fixture", key=f"del_l_tab_{selected_placed_l_idx}"
        ):
          removed_light = st.session_state.placed_lighting.pop(
              selected_placed_l_idx
          )
          st.warning(
              f"Removed L{selected_placed_l_idx+1} ({removed_light['Make']}"
              f" {removed_light['Brand']})."
          )
          st.rerun() if hasattr(st, "rerun") else st.experimental_rerun()
    else:
      st.info("No lighting fixtures currently placed.")

# TAB 6: OVERHEAD CRANES & COVERAGE
with tab_crane:
  crane_col1, crane_col2 = st.columns(2)

  with crane_col1:
    st.subheader("🏗️ Add Overhead Crane Coverage Area")
    st.markdown(
        "Select a crane model from the default library to auto-populate"
        " specifications, then define the 2 corner points (Lower Left & Upper"
        " Right) for the coverage area."
    )

    crane_lib_options = [
        f"{c['Make']} {c['Model']} ({c['MaxLiftWeight']} T Max Weight)"
        for c in crane_lib
    ]
    st.selectbox(
        "Choose Crane Model from Library",
        range(len(crane_lib_options)),
        format_func=lambda x: crane_lib_options[x],
        key="crane_lib_select_add",
        on_change=on_crane_select_change,
    )

    crane_make = st.text_input("Crane Make", key="crane_make_add")
    crane_model = st.text_input("Crane Model", key="crane_model_add")

    specs_col1, specs_col2, specs_col3 = st.columns(3)
    with specs_col1:
      crane_lift_wt = st.number_input(
          "Max Lift Weight (tons)",
          min_value=0.5,
          max_value=200.0,
          step=0.5,
          key="crane_wt_add",
      )
    with specs_col2:
      crane_lift_sp = st.number_input(
          "Max Lift Speed (ft/min)",
          min_value=1.0,
          max_value=200.0,
          step=1.0,
          key="crane_lsp_add",
      )
    with specs_col3:
      crane_trans_sp = st.number_input(
          "Max Transversal Speed (ft/min)",
          min_value=1.0,
          max_value=500.0,
          step=5.0,
          key="crane_tsp_add",
      )

    st.markdown("##### 📍 Define Rectangular Coverage Corner Points (ft)")
    ll_col1, ll_col2 = st.columns(2)
    with ll_col1:
      ll_x_val = st.number_input(
          "Lower Left X (ft)", value=20.0, key="crane_ll_x_add"
      )
    with ll_col2:
      ll_y_val = st.number_input(
          "Lower Left Y (ft)", value=20.0, key="crane_ll_y_add"
      )

    ur_col1, ur_col2 = st.columns(2)
    with ur_col1:
      ur_x_val = st.number_input(
          "Upper Right X (ft)", value=180.0, key="crane_ur_x_add"
      )
    with ur_col2:
      ur_y_val = st.number_input(
          "Upper Right Y (ft)", value=80.0, key="crane_ur_y_add"
      )

    if st.button("Add Crane Coverage to Floor", type="primary"):
      new_crane = {
          "make": crane_make,
          "model": crane_model,
          "max_lift_weight": crane_lift_wt,
          "max_lift_speed": crane_lift_sp,
          "max_transversal_speed": crane_trans_sp,
          "ll_x": ll_x_val,
          "ll_y": ll_y_val,
          "ur_x": ur_x_val,
          "ur_y": ur_y_val,
      }
      st.session_state.placed_cranes.append(new_crane)
      st.success(
          f"Added Crane C{len(st.session_state.placed_cranes)} ({crane_make}"
          f" {crane_model}) coverage area!"
      )
      st.rerun() if hasattr(st, "rerun") else st.experimental_rerun()

  with crane_col2:
    st.subheader("🛠️ Edit or Delete Placed Cranes")
    if len(st.session_state.placed_cranes) > 0:
      crane_opts = [
          f"C{i+1}: {c.get('make', 'Crane')} {c.get('model', '')}"
          f" ({c.get('max_lift_weight', 0)} T)"
          for i, c in enumerate(st.session_state.placed_cranes)
      ]
      selected_crane_idx = st.selectbox(
          "Select Crane to Modify",
          range(len(crane_opts)),
          format_func=lambda x: crane_opts[x],
          key="edit_crane_select",
      )

      c_edit = st.session_state.placed_cranes[selected_crane_idx]

      e_make = st.text_input(
          "Edit Make",
          c_edit.get("make", ""),
          key=f"e_cr_make_{selected_crane_idx}",
      )
      e_model = st.text_input(
          "Edit Model",
          c_edit.get("model", ""),
          key=f"e_cr_model_{selected_crane_idx}",
      )

      e_col1, e_col2, e_col3 = st.columns(3)
      with e_col1:
        e_wt = st.number_input(
            "Max Weight (T)",
            value=float(c_edit.get("max_lift_weight", 10.0)),
            key=f"e_cr_wt_{selected_crane_idx}",
        )
      with e_col2:
        e_lsp = st.number_input(
            "Lift Speed (ft/min)",
            value=float(c_edit.get("max_lift_speed", 25.0)),
            key=f"e_cr_lsp_{selected_crane_idx}",
        )
      with e_col3:
        e_tsp = st.number_input(
            "Transversal Speed",
            value=float(c_edit.get("max_transversal_speed", 120.0)),
            key=f"e_cr_tsp_{selected_crane_idx}",
        )

      st.markdown("##### 📍 Edit Corner Coordinates (ft)")
      ell_col1, ell_col2 = st.columns(2)
      with ell_col1:
        e_ll_x = st.number_input(
            "Lower Left X (ft)",
            value=float(c_edit.get("ll_x", c_edit.get("x1", 20.0))),
            key=f"e_cr_ll_x_{selected_crane_idx}",
        )
      with ell_col2:
        e_ll_y = st.number_input(
            "Lower Left Y (ft)",
            value=float(c_edit.get("ll_y", c_edit.get("y1", 20.0))),
            key=f"e_cr_ll_y_{selected_crane_idx}",
        )

      eur_col1, eur_col2 = st.columns(2)
      with eur_col1:
        e_ur_x = st.number_input(
            "Upper Right X (ft)",
            value=float(c_edit.get("ur_x", c_edit.get("x3", 180.0))),
            key=f"e_cr_ur_x_{selected_crane_idx}",
        )
      with eur_col2:
        e_ur_y = st.number_input(
            "Upper Right Y (ft)",
            value=float(c_edit.get("ur_y", c_edit.get("y3", 80.0))),
            key=f"e_cr_ur_y_{selected_crane_idx}",
        )

      c_btn_c1, c_btn_c2 = st.columns(2)
      with c_btn_c1:
        if st.button(
            "Update Crane Data", key=f"up_cr_btn_{selected_crane_idx}"
        ):
          st.session_state.placed_cranes[selected_crane_idx] = {
              "make": e_make,
              "model": e_model,
              "max_lift_weight": e_wt,
              "max_lift_speed": e_lsp,
              "max_transversal_speed": e_tsp,
              "ll_x": e_ll_x,
              "ll_y": e_ll_y,
              "ur_x": e_ur_x,
              "ur_y": e_ur_y,
          }
          st.success(f"Updated Crane C{selected_crane_idx+1} configuration!")
          st.rerun() if hasattr(st, "rerun") else st.experimental_rerun()
      with c_btn_c2:
        if st.button("Delete Crane", key=f"del_cr_btn_{selected_crane_idx}"):
          removed_crane = st.session_state.placed_cranes.pop(
              selected_crane_idx
          )
          st.warning(
              f"Removed Crane C{selected_crane_idx+1}"
              f" ({removed_crane.get('make', '')}"
              f" {removed_crane.get('model', '')})."
          )
          st.rerun() if hasattr(st, "rerun") else st.experimental_rerun()
    else:
      st.info("No overhead cranes currently placed.")

# TAB 7: MACHINE FLOWS & WORKFLOW PATHS
with tab_flow:
  st.header("🔄 Machine Part Flow Configuration")
  st.markdown(
      "Specify how parts will flow from source to destination machines for"
      " backend analysis."
  )

  with st.container():
    f_col1, f_col2 = st.columns(2)
    with f_col1:
      source_id = st.text_input(
          "Source Machine ID", placeholder="e.g., M-100", key="src_flow_tab"
      )
    with f_col2:
      dest_id = st.text_input(
          "Destination Machine ID", placeholder="e.g., M-200", key="dst_flow_tab"
      )

    if st.button("Add Machine Flow", type="primary", key="add_flow_btn"):
      if source_id and dest_id:
        st.session_state.machine_flows.append(
            {"Source": source_id, "Destination": dest_id}
        )
        st.success(
            f"✅ Route successfully defined: **{source_id}** ➔ **{dest_id}**"
        )
      else:
        st.warning("Please provide both Source and Destination Machine IDs.")

  if len(st.session_state.machine_flows) > 0:
    st.subheader("Active Defined Machine Flow Routes")
    st.dataframe(
        pd.DataFrame(st.session_state.machine_flows), use_container_width=True
    )

  st.divider()

  st.header("GM Workflow Path Definition")
  st.markdown(
      "Input and edit the sequential X/Y coordinate points that define the"
      " workflow path. Parts will travel sequentially from the first to the"
      " last point."
  )

  with st.form("path_point_form_tab"):
    st.subheader("Add Point to Workflow Path")
    col_x, col_y, col_standoff, col_speed = st.columns(4)

    with col_x:
      x_val = st.number_input("X Coordinate", value=0.0, format="%.2f")
    with col_y:
      y_val = st.number_input("Y Coordinate", value=0.0, format="%.2f")
    with col_standoff:
      standoff_val = st.number_input(
          "Safety Standoff (ft)", min_value=0.0, value=2.0, format="%.2f"
      )
    with col_speed:
      speed_val = st.number_input(
          "Part Movement Speed", min_value=0.0, value=5.0, format="%.2f"
      )

    submit_point = st.form_submit_button("Add Point")

    if submit_point:
      new_point_idx = len(st.session_state.path_points) + 1
      new_row = pd.DataFrame({
          "Point": [new_point_idx],
          "X Coordinate": [x_val],
          "Y Coordinate": [y_val],
          "Safety Standoff (ft)": [standoff_val],
          "Movement Speed": [speed_val],
      })
      st.session_state.path_points = pd.concat(
          [st.session_state.path_points, new_row], ignore_index=True
      )
      st.success("Point added to the path!")

  st.subheader("Edit/Review Path Points")
  st.markdown(
      "Use the table below to review or directly modify path parameters. You can"
      " also delete rows or add rows directly via the grid."
  )

  edited_path_df = st.data_editor(
      st.session_state.path_points,
      num_rows="dynamic",
      use_container_width=True,
      hide_index=True,
      key="data_editor_path_tab",
  )

  st.session_state.path_points = edited_path_df
  st.divider()

  if st.button(
      "💾 Save & Send to Optimization Engine",
      type="primary",
      key="save_c_engine_btn",
  ):
    st.info(
        "Configuration data and workflow paths are ready and serialized for"
        " execution."
    )

# TAB 8: IMPORT / EXPORT LAYOUT DESIGN
with tab_io:
  st.header("💾 Import & Export Factory Layout Designs")
  st.markdown(
      "Save your current project configuration as a formatted text file (JSON"
      " format) or import a previously saved design file."
  )

  io_col1, io_col2 = st.columns(2)

  with io_col1:
    st.subheader("📤 Export Current Project Layout")
    st.markdown(
        "Click the button below to download your complete factory floor"
        " configuration file."
    )

    export_data = {
        "designer_name": st.session_state.designer_name,
        "dwg_title": st.session_state.dwg_title,
        "dwg_num": st.session_state.dwg_num,
        "sheet_size": st.session_state.sheet_size,
        "floor_w": st.session_state.floor_w,
        "floor_h": st.session_state.floor_h,
        "path_width_ft": st.session_state.path_width_ft,
        "show_machines": st.session_state.show_machines,
        "show_lighting": st.session_state.show_lighting,
        "show_cranes": st.session_state.show_cranes,
        "show_safety": st.session_state.show_safety,
        "show_contour": st.session_state.show_contour,
        "show_decibel": st.session_state.show_decibel,
        "placed_machines": st.session_state.placed_machines,
        "placed_lighting": st.session_state.placed_lighting,
        "placed_conduits": st.session_state.placed_conduits,
        "placed_cranes": st.session_state.placed_cranes,
        "machine_flows": st.session_state.machine_flows,
        "path_points": st.session_state.path_points.to_dict(orient="records"),
    }

    export_str = json.dumps(export_data, indent=2)

    st.download_button(
        label="⬇️ Download Project File (.txt)",
        data=export_str,
        file_name=(
            "factory_layout_"
            f"{st.session_state.dwg_num.replace(' ', '_')}.txt"
        ),
        mime="text/plain",
        type="primary",
    )

    with st.expander("Preview Formatted Export File Content"):
      st.code(export_str, language="json")

  with io_col2:
    st.subheader("📥 Import Saved Project Layout")
    st.markdown(
        "Upload a formatted project text file (`.txt`) to restore a saved"
        " layout."
    )

    uploaded_file = st.file_uploader(
        "Choose a layout text file",
        type=["txt", "json"],
        key="uploaded_layout_file",
    )

    if uploaded_file is not None:
      st.button(
          "🔄 Apply Imported Layout to Floor",
          type="primary",
          on_click=apply_imported_layout,
      )

    if "import_status" in st.session_state:
      status_type, msg = st.session_state["import_status"]
      if status_type == "success":
        st.success(msg)
      elif status_type == "error":
        st.error(msg)

# TAB 9: DEFAULT LIBRARIES
with tab_lib:
  st.header("📚 Default Machinery, Lighting & Crane Libraries")
  st.markdown(
      "Reference specification tables loaded from default library"
      " configurations."
  )

  lib_col1, lib_col2, lib_col3 = st.columns(3)

  with lib_col1:
    st.subheader("🤖 Default Machinery Library")
    st.dataframe(df_machinery, use_container_width=True)

  with lib_col2:
    st.subheader("💡 Default Lighting Library")
    st.dataframe(df_lighting, use_container_width=True)

  with lib_col3:
    st.subheader("🏗️ Default Overhead Crane Library")
    st.dataframe(df_cranes, use_container_width=True)
