import numpy as np
import pandas as pd
import streamlit as st
from engine import calculate_production_metrics, run_layout_analysis
from library_loader import (
    get_default_cranes,
    get_default_lighting,
    get_default_machinery,
)
from state_manager import init_session_state
from ui_components import (
    render_conduit_tab,
    render_crane_tab,
    render_dimensions_tab,
    render_import_export_tab,
    render_libraries_tab,
    render_lighting_tab,
    render_machinery_tab,
    render_plots_tab,
    render_project_info_tab,
    render_workflow_tab,
)
from visualization import draw_3d_asme_factory_viewport, draw_asme_drawing

# Set page configuration safely
st.set_page_config(
    page_title="Factory Floor Optimizer", page_icon="🏭", layout="wide"
)

st.title("🏭 Factory Floor Optimizer & Compliance Suite")
st.markdown(
    "Designed strictly to comply with **ASME Y14.1 Drawing Sheets** and **NJ"
    " Uniform Construction Code** Standards."
)

# Load Default Libraries
machinery_lib = get_default_machinery()
lighting_lib = get_default_lighting()
crane_lib = get_default_cranes()

# Initialize Session State
init_session_state(machinery_lib, lighting_lib, crane_lib)

# Top Viewport Selection Switcher
viewport_mode = st.radio(
    "Select Display Mode",
    ["📐 2D ASME Y14.1 Blueprint View", "🕶️ Interactive 3D Factory Viewport"],
    horizontal=True,
)

# Extract workflow path points from session state for Drawing
active_workflow_paths = []
if len(st.session_state.path_points) > 0:
    try:
        px = [float(v) for v in st.session_state.path_points["X Coordinate"].tolist()]
        py = [float(v) for v in st.session_state.path_points["Y Coordinate"].tolist()]
        p_so = [
            float(v)
            for v in st.session_state.path_points["Safety Standoff (ft)"].tolist()
        ]
        p_speed = [
            float(v)
            for v in st.session_state.path_points["Movement Speed"].tolist()
        ]

        if "Movement Mode" in st.session_state.path_points.columns:
            p_mode_list = st.session_state.path_points["Movement Mode"].astype(str).tolist()
            movement_mode = p_mode_list[0] if len(p_mode_list) > 0 else "human"
        else:
            movement_mode = "human"

        if len(px) >= 2:
            avg_speed = sum(p_speed) / len(p_speed) if len(p_speed) > 0 else 5.0
            active_workflow_paths.append({
                "id": "WF-001",
                "x": px,
                "y": py,
                "standoffs": p_so,
                "width_ft": float(st.session_state.path_width_ft),
                "speed_fpm": float(avg_speed),
                "movement_mode": movement_mode,
            })
    except Exception:
        pass

if viewport_mode == "📐 2D ASME Y14.1 Blueprint View":
  st.header("📐 Live ASME Y14.1 Blueprint View")
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
      show_workflow=st.session_state.show_workflow,
      show_electrical=st.session_state.show_electrical,
      show_safety=st.session_state.show_safety,
      show_contour=st.session_state.show_contour,
      show_decibel=st.session_state.show_decibel,
      designer_name=st.session_state.designer_name,
      dwg_title=st.session_state.dwg_title,
      dwg_num=st.session_state.dwg_num,
  )

  bp_col, bp_space = st.columns([0.75, 0.25])
  with bp_col:
    st.pyplot(fig, use_container_width=True)

else:
  st.header("🕶️ Interactive 3D Factory Floor Viewport")
  fig_3d = draw_3d_asme_factory_viewport(
      floor_w=st.session_state.floor_w,
      floor_h=st.session_state.floor_h,
      ceiling_h=25.0,
      machines=st.session_state.placed_machines,
      lighting=st.session_state.placed_lighting,
      cranes=st.session_state.placed_cranes,
      conduits=st.session_state.placed_conduits,
      workflow_paths=active_workflow_paths,
      show_machines=st.session_state.show_machines,
      show_lighting=st.session_state.show_lighting,
      show_cranes=st.session_state.show_cranes,
      show_workflow=st.session_state.show_workflow,
      show_electrical=st.session_state.show_electrical,
  )
  st.plotly_chart(fig_3d, use_container_width=True)

# Analytics Summary
metrics = calculate_production_metrics(st.session_state.placed_machines)
warnings = run_layout_analysis(
    st.session_state.placed_machines,
    st.session_state.placed_conduits,
    st.session_state.placed_cranes,
    active_workflow_paths,
)

stat1, stat2, stat3, stat4 = st.columns(4)
with stat1:
    st.metric("Line Bottleneck", metrics.get("Bottleneck Machine", "N/A"))
with stat2:
    st.metric("Line Balance Index", metrics.get("Line Balance Efficiency", "N/A"))
with stat3:
    st.metric(
        "Finished Assemblies / Hr",
        metrics.get("Estimated Finished Assemblies / Hr", "N/A"),
    )
with stat4:
    st.metric(
        "UDP Power Sleep Savings", metrics.get("UDP Switch-Off Savings", "N/A")
    )

if warnings:
  st.error("⚠️ Spatial & Regulatory Warnings Found:")
  for warn in warnings:
    st.warning(warn)
else:
  st.success(
      "✅ No implemented spatial/compliance warnings detected."
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

with tab_proj:
  render_project_info_tab()

with tab_dims:
  render_dimensions_tab()

with tab_plots:
  render_plots_tab()

with tab_mach:
  render_machinery_tab(machinery_lib)

with tab_cond:
  render_conduit_tab()

with tab_light:
  render_lighting_tab(lighting_lib)

with tab_crane:
  render_crane_tab(crane_lib)

with tab_flow:
  render_workflow_tab()

with tab_io:
  render_import_export_tab()

with tab_lib:
  render_libraries_tab(machinery_lib, lighting_lib, crane_lib)

