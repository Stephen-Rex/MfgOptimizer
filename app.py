import numpy as np
import pandas as pd
import streamlit as st
from engine import calculate_production_metrics, run_layout_analysis
from library_loader import get_default_lighting, get_default_machinery
from visualization import draw_asme_drawing

# Set page configuration safely
st.set_page_config(
    page_title="Factory Floor Optimizer", page_icon="🏭", layout="wide"
)

st.title("🏭 Factory Floor Optimizer & Compliance Suite")
st.markdown(
    "Designed strictly to comply with **ASME Y14.1 Drawing Sheets** and **NJ"
    " Uniform Construction Code** Standards, integrated with backend"
    " optimization engine parameters."
)


# Helper to parse string list to coordinate floats safely
def parse_coords(coord_str):
  try:
    return [float(val.strip()) for val in coord_str.split(",") if val.strip()]
  except ValueError:
    return None


# Sidebar Library Files
st.sidebar.header("📁 Material & Machinery Library")
machinery_lib = get_default_machinery()
lighting_lib = get_default_lighting()

# Display Libraries in Sidebar
st.sidebar.subheader("Default Machinery Specifications")
df_machinery = pd.DataFrame(machinery_lib)
st.sidebar.dataframe(df_machinery[["Make", "Model", "Type", "Volume", "Yield"]])

st.sidebar.subheader("Default Lighting Specifications")
df_lighting = pd.DataFrame(lighting_lib)
st.sidebar.dataframe(
    df_lighting[["Make", "Brand", "Type", "Wattage", "Lumens", "Lux"]]
)

# Setup Session State for Placed Items & Workflow Routes
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

# Main Layout split into tabs for clarity and usability
tab_layout, tab_flow = st.tabs([
    "📐 2D Layout & Blueprint Designer",
    "🔄 Machine Flows & Workflow Paths",
])

with tab_layout:
  col1, col2 = st.columns([2, 1])

  with col2:
    st.header("⚙️ Interactive Floor Layout Designer")

    # 1. Sheet configurations
    sheet_size = st.selectbox(
        "Select ASME Sheet Boundary Size", ["A", "B", "C", "D"], index=1
    )

    # 2. Independent Factory Floor physical dimensions
    st.subheader("📐 Physical Floor Dimensions")
    floor_w = st.number_input(
        "Factory Floor Width (feet)",
        min_value=10.0,
        max_value=1000.0,
        value=200.0,
        step=10.0,
    )
    floor_h = st.number_input(
        "Factory Floor Height (feet)",
        min_value=10.0,
        max_value=1000.0,
        value=100.0,
        step=10.0,
    )

    path_width_ft = st.number_input(
        "Workflow Path Width (feet)",
        min_value=1.0,
        max_value=20.0,
        value=6.0,
        step=0.5,
    )

    show_safety = st.checkbox("Show Safety Heatmap underlay", value=False)
    show_contour = st.checkbox("Show Part Volume Contour plots")

    # 3. Machinery Placement Form
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
        max_value=float(floor_w),
        value=70.0,
        key="mx",
    )
    my_coord = st.number_input(
        "Target Placement Y (ft)",
        min_value=0.0,
        max_value=float(floor_h),
        value=50.0,
        key="my",
    )

    if st.button("Drop Machine onto Floor"):
      spec = machinery_lib[selected_m_idx].copy()
      spec["x"] = mx_coord
      spec["y"] = my_coord
      st.session_state.placed_machines.append(spec)
      st.success(
          f"Placed {spec['Make']} {spec['Model']} at ({mx_coord}, {my_coord})!"
      )
      st.rerun() if hasattr(st, "rerun") else st.experimental_rerun()

    # 4. Modify or Delete Placed Machinery
    if len(st.session_state.placed_machines) > 0:
      st.subheader("🛠️ Modify or Delete Placed Machinery")
      placed_options = [
          f"{i+1}: {m['Make']} {m['Model']} at ({m['x']:.1f} ft, {m['y']:.1f}"
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
          max_value=float(floor_w),
          value=float(mach["x"]),
          key=f"edit_x_{selected_placed_idx}",
      )
      edit_y = st.number_input(
          "Adjust Coordinate Y (ft)",
          min_value=0.0,
          max_value=float(floor_h),
          value=float(mach["y"]),
          key=f"edit_y_{selected_placed_idx}",
      )

      btn_col1, btn_col2 = st.columns(2)
      with btn_col1:
        if st.button("Update Position", key=f"update_btn_{selected_placed_idx}"):
          st.session_state.placed_machines[selected_placed_idx]["x"] = edit_x
          st.session_state.placed_machines[selected_placed_idx]["y"] = edit_y
          st.success("Machine moved successfully!")
          st.rerun() if hasattr(st, "rerun") else st.experimental_rerun()
      with btn_col2:
        if st.button("Delete Machine", key=f"delete_btn_{selected_placed_idx}"):
          removed = st.session_state.placed_machines.pop(selected_placed_idx)
          st.warning(
              f"Removed {removed['Make']} {removed['Model']} from layout."
          )
          st.rerun() if hasattr(st, "rerun") else st.experimental_rerun()

    # 5. Custom Conduit Creation Form
    st.subheader("🔌 Route Conduit Run (Polyline)")
    cx_lbl = st.text_input("Conduit Run Label", "Sub-Station Hookup")
    cx_x_str = st.text_input("X Coordinates (comma separated)", "40.0, 120.0")
    cx_y_str = st.text_input("Y Coordinates (comma separated)", "80.0, 35.0")
    cx_depth = st.number_input(
        "Trench Burial Depth (inches)",
        min_value=12,
        max_value=60,
        value=36,
        key="cx_depth",
    )
    cx_tape = st.checkbox(
        "Contains Orange 4 mil Warning Tape", value=True, key="cx_tape"
    )

    if st.button("Route Conduit Path"):
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

    # 6. Modify or Delete Placed Conduits
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
          "Edit Conduit Label", cond["label"], key=f"lbl_{selected_cond_idx}"
      )
      edit_cx_x_str = st.text_input(
          "Edit X Coordinates",
          ", ".join(map(str, cond["x"])),
          key=f"cx_{selected_cond_idx}",
      )
      edit_cx_y_str = st.text_input(
          "Edit Y Coordinates",
          ", ".join(map(str, cond["y"])),
          key=f"cy_{selected_cond_idx}",
      )
      edit_cx_depth = st.number_input(
          "Edit Burial Depth (inches)",
          min_value=12,
          max_value=60,
          value=int(cond["depth_in"]),
          key=f"dp_{selected_cond_idx}",
      )
      edit_cx_tape = st.checkbox(
          "Edit Warning Tape Status",
          value=cond["warning_tape"],
          key=f"tp_{selected_cond_idx}",
      )

      c_btn_col1, c_btn_col2 = st.columns(2)
      with c_btn_col1:
        if st.button("Update Conduit Run", key=f"up_c_{selected_cond_idx}"):
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
        if st.button("Delete Conduit Run", key=f"del_c_{selected_cond_idx}"):
          removed_c = st.session_state.placed_conduits.pop(selected_cond_idx)
          st.warning(f"Removed conduit run '{removed_c['label']}'.")
          st.rerun() if hasattr(st, "rerun") else st.experimental_rerun()

    # 7. Lighting Placement Form
    st.subheader("💡 Place Light from Library")
    light_options = [
        f"{l['Make']} {l['Brand']} ({l['Type']})" for l in lighting_lib
    ]
    selected_l_idx = st.selectbox(
        "Choose Lighting Fixture",
        range(len(light_options)),
        format_func=lambda x: light_options[x],
    )
    lx_coord = st.number_input(
        "Placement X (ft)",
        min_value=0.0,
        max_value=float(floor_w),
        value=50.0,
        key="lx",
    )
    ly_coord = st.number_input(
        "Placement Y (ft)",
        min_value=0.0,
        max_value=float(floor_h),
        value=80.0,
        key="ly",
    )

    if st.button("Drop Light onto Floor"):
      spec_l = lighting_lib[selected_l_idx].copy()
      spec_l["x"] = lx_coord
      spec_l["y"] = ly_coord
      st.session_state.placed_lighting.append(spec_l)
      st.success(f"Placed Lighting Fixture at ({lx_coord}, {ly_coord})!")
      st.rerun() if hasattr(st, "rerun") else st.experimental_rerun()

    # 8. Modify or Delete Placed Lighting
    if len(st.session_state.placed_lighting) > 0:
      st.subheader("🛠️ Modify or Delete Placed Lighting")
      placed_l_opts = [
          f"{i+1}: {li['Make']} {li['Brand']} at ({li['x']:.1f} ft,"
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
          max_value=float(floor_w),
          value=float(active_light["x"]),
          key=f"elx_{selected_placed_l_idx}",
      )
      edit_ly = st.number_input(
          "Adjust Light Coordinate Y (ft)",
          min_value=0.0,
          max_value=float(floor_h),
          value=float(active_light["y"]),
          key=f"ely_{selected_placed_l_idx}",
      )

      l_btn_col1, l_btn_col2 = st.columns(2)
      with l_btn_col1:
        if st.button(
            "Update Light Position", key=f"up_l_{selected_placed_l_idx}"
        ):
          st.session_state.placed_lighting[selected_placed_l_idx]["x"] = edit_lx
          st.session_state.placed_lighting[selected_placed_l_idx]["y"] = edit_ly
          st.success("Lighting position updated!")
          st.rerun() if hasattr(st, "rerun") else st.experimental_rerun()
      with l_btn_col2:
        if st.button(
            "Delete Light Fixture", key=f"del_l_{selected_placed_l_idx}"
        ):
          removed_light = st.session_state.placed_lighting.pop(
              selected_placed_l_idx
          )
          st.warning(
              "Removed light fixture"
              f" '{removed_light['Make']} {removed_light['Brand']}'."
          )
          st.rerun() if hasattr(st, "rerun") else st.experimental_rerun()

  with col1:
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
              "width_ft": float(path_width_ft),
          })
      except Exception:
        pass

    # Render ASME Drawing Sheet with updated workflow path rendering
    fig = draw_asme_drawing(
        size_char=sheet_size,
        floor_width_ft=floor_w,
        floor_height_ft=floor_h,
        machines=st.session_state.placed_machines,
        conduits=st.session_state.placed_conduits,
        lighting=st.session_state.placed_lighting,
        workflow_paths=active_workflow_paths,
        show_safety=show_safety,
        show_contour=show_contour,
    )
    st.pyplot(fig)

  # Analysis & Compliance Reporting
  st.header("📈 Layout Analytics & OSHA / NJ-UCC Verification")

  warnings = run_layout_analysis(
      st.session_state.placed_machines, st.session_state.placed_conduits
  )
  metrics = calculate_production_metrics(st.session_state.placed_machines)

  stat1, stat2, stat3 = st.columns(3)
  with stat1:
    st.metric("Line Bottleneck", metrics.get("Bottleneck Machine", "N/A"))
  with stat2:
    st.metric(
        "Line Balance Index", metrics.get("Line Balance Efficiency", "N/A")
    )
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

  st.info(
      "⚡ Estimated Throughput (MPDI Bucket Brigade Dynamic Model):"
      f" {metrics.get('Bucket Brigade Throughput', '0')}"
  )

with tab_flow:
  st.header("🔄 Machine Part Flow Configuration")
  st.markdown(
      "Specify how parts will flow from source to destination machines for"
      " backend analysis."
  )

  with st.container():
    f_col1, f_col2 = st.columns(2)
    with f_col1:
      source_id = st.text_input("Source Machine ID", placeholder="e.g., M-100")
    with f_col2:
      dest_id = st.text_input(
          "Destination Machine ID", placeholder="e.g., M-200"
      )

    if st.button("Add Machine Flow", type="primary"):
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

  st.header("🛣️ Workflow Path Definition")
  st.markdown(
      "Input and edit the sequential X/Y coordinate points that define the"
      " workflow path. Parts will travel sequentially from the first to the"
      " last point."
  )

  # Form to add a new coordinate point
  with st.form("path_point_form"):
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
  )

  # Save the edits back to session state
  st.session_state.path_points = edited_path_df
  st.divider()

  if st.button("💾 Save & Send to Optimization Engine", type="primary"):
    st.info(
        "Configuration data and workflow paths are ready and serialized for"
        " execution."
    )
