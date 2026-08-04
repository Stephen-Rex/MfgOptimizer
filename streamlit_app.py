import sys
import os

# =====================================================================
# --- RECURSIVE PATH-RESOLUTION PATCH (Samantha's Robust Module Finder) ---
# =====================================================================
found_backend = False
current_dir = os.path.dirname(os.path.abspath(__file__))

# 1. Search recursively downwards for 'backend'
for root, dirs, files in os.walk(current_dir):
    if "backend" in dirs:
        sys.path.insert(0, root)
        found_backend = True
        break

# 2. Search upwards if nested (up to 3 levels)
if not found_backend:
    temp_dir = current_dir
    for _ in range(3):
        temp_dir = os.path.dirname(temp_dir)
        for root, dirs, files in os.walk(temp_dir):
            if "backend" in dirs:
                sys.path.insert(0, root)
                found_backend = True
                break
        if found_backend:
            break
# =====================================================================

import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import subprocess
from backend.c_backend_bridge import run_analysis
from app import generate_pdf_report  # Reuses ReportLab PDF Exporter

# ==========================================
# 1. Start-up: Auto-Compile Robert's C Engine
# ==========================================
def compile_backend():
    # Find backend path dynamically
    backend_dir = None
    for root, dirs, files in os.walk(current_dir):
        if root.endswith("backend") or root.endswith("backend/"):
            backend_dir = root
            break
            
    if backend_dir and os.path.exists(backend_dir):
        try:
            # Check if GCC is installed in the Streamlit container
            res = subprocess.run(["gcc", "--version"], capture_output=True, text=True)
            if res.returncode == 0:
                subprocess.run(["make", "-C", backend_dir], capture_output=True, text=True)
        except Exception:
            pass  # Bridge automatically falls back to Python emulation

compile_backend()

# ==========================================
# 2. Page Configuration & Presets Loader
# ==========================================
st.set_page_config(layout="wide", page_title="Factory Floor Optimizer")
st.title("Factory Floor Optimizer — Streamlit Console")

# Find CSV dynamically
LIBRARY_PATH = None
for root, dirs, files in os.walk(current_dir):
    if "machinery_library.csv" in files:
        LIBRARY_PATH = os.path.join(root, "machinery_library.csv")
        break

if not LIBRARY_PATH:
    LIBRARY_PATH = os.path.join(current_dir, "data", "machinery_library.csv")

# Ensure preset CSV file exists
if not os.path.exists(LIBRARY_PATH):
    os.makedirs(os.path.dirname(LIBRARY_PATH), exist_ok=True)
    default_csv = (
        "id,name,width,height,safety_standoff,vent_diameter,vent_flow_rate,"
        "water_required,amperage,wattage,tool_heads,volume_per_hour,human_intervention,"
        "decibel_rating,yield_percentage,crane_required\n"
        "M01,CNC Milling Center,3.0,2.5,1.5,0.15,300,1,30,15000,3,120,1,85,0.98,1\n"
        "M02,Laser Cutter,2.5,2.0,1.0,0.20,500,0,20,8000,1,200,0,70,0.95,0\n"
        "M03,Plastic Injection Molder,4.0,2.0,2.0,0.10,150,1,50,25000,1,80,1,90,0.99,1\n"
        "M04,Robotic Pick-and-Place,1.8,1.8,1.2,0.0,0,0,15,5000,2,300,0,65,0.995,0\n"
        "M05,Industrial Paint Booth,5.0,4.0,3.0,0.40,1200,0,40,18000,4,50,1,75,0.92,0\n"
    )
    with open(LIBRARY_PATH, "w") as f:
        f.write(default_csv)

@st.cache_data
def load_library():
    return pd.read_csv(LIBRARY_PATH)

lib_df = load_library()

# ==========================================
# 3. Streamlit Session State Management
# ==========================================
if "placed_machines" not in st.session_state:
    st.session_state.placed_machines = []
if "flow_paths" not in st.session_state:
    st.session_state.flow_paths = []
if "crane_zones" not in st.session_state:
    st.session_state.crane_zones = []

# ==========================================
# 4. User Workspace Interface (Sidebar Controls)
# ==========================================
st.sidebar.header("Factory Design Controls")

# 4.1 Preset Library CSV Uploader
uploaded_file = st.sidebar.file_uploader("Upload CSV Presets Library", type="csv")
if uploaded_file is not None:
    with open(LIBRARY_PATH, "wb") as f:
        f.write(uploaded_file.getbuffer())
    st.cache_data.clear()
    st.sidebar.success("Library updated successfully!")

# 4.2 Asset Placement Wizards
with st.sidebar.expander("➕ Add Machine to Floor Layout"):
    selected_preset = st.selectbox("Select Machine Preset", lib_df["name"].tolist())
    preset_row = lib_df[lib_df["name"] == selected_preset].iloc[0]
    
    pos_x = st.number_input("Position X (meters)", min_value=0.0, max_value=50.0, value=10.0, step=0.5)
    pos_y = st.number_input("Position Y (meters)", min_value=0.0, max_value=30.0, value=10.0, step=0.5)
    custom_standoff = st.number_input("Standoff Distance (m)", value=float(preset_row["safety_standoff"]), step=0.1)
    
    if st.button("Place Machine"):
        m_id = f"M{len(st.session_state.placed_machines) + 1:02d}"
        new_machine = {
            "id": m_id,
            "name": preset_row["name"],
            "x": pos_x,
            "y": pos_y,
            "width": float(preset_row["width"]),
            "height": float(preset_row["height"]),
            "safety_standoff": custom_standoff,
            "water_required": int(preset_row["water_required"]),
            "amperage": int(preset_row["amperage"]),
            "wattage": int(preset_row["wattage"]),
            "volume_per_hour": float(preset_row["volume_per_hour"]),
            "yield_percentage": float(preset_row["yield_percentage"]),
            "crane_required": int(preset_row["crane_required"]),
            "is_bottleneck": False,
            "safety_violation": False
        }
        st.session_state.placed_machines.append(new_machine)
        st.success(f"Placed {preset_row['name']} at ({pos_x}, {pos_y})")

with st.sidebar.expander("➕ Add Flow Corridor Path"):
    p_type = st.selectbox("Flow Corridor Type", ["human", "robot"])
    p_speed = st.number_input("Travel Speed (m/s)", value=1.0 if p_type == "human" else 2.5, step=0.1)
    p_width = st.number_input("Path Width (meters)", value=1.2, step=0.1)
    
    st.write("Path Segment Coordinates:")
    coord_col1, coord_col2 = st.columns(2)
    x1 = coord_col1.number_input("Start X (m)", min_value=0.0, value=5.0, step=1.0)
    y1 = coord_col2.number_input("Start Y (m)", min_value=0.0, value=15.0, step=1.0)
    x2 = coord_col1.number_input("End X (m)", min_value=0.0, value=45.0, step=1.0)
    y2 = coord_col2.number_input("End Y (m)", min_value=0.0, value=15.0, step=1.0)
    
    if st.button("Create Flow Path"):
        p_id = f"FP{len(st.session_state.flow_paths) + 1:02d}"
        new_path = {
            "id": p_id,
            "type": p_type,
            "width": p_width,
            "speed": p_speed,
            "points": [{"x": x1, "y": y1}, {"x": x2, "y": y2}]
        }
        st.session_state.flow_paths.append(new_path)
        st.success(f"Created {p_type} flow corridor successfully!")

with st.sidebar.expander("➕ Draw Overhead Crane Zone"):
    cx1 = st.number_input("Bounding Box Start X (m)", min_value=0.0, value=5.0, step=1.0)
    cy1 = st.number_input("Bounding Box Start Y (m)", min_value=0.0, value=5.0, step=1.0)
    cx2 = st.number_input("Bounding Box End X (m)", min_value=0.0, value=25.0, step=1.0)
    cy2 = st.number_input("Bounding Box End Y (m)", min_value=0.0, value=25.0, step=1.0)
    
    if st.button("Define Crane Zone"):
        c_id = f"CZ{len(st.session_state.crane_zones) + 1:02d}"
        new_crane = {
            "id": c_id, "x1": cx1, "y1": cy1, "x2": cx2, "y2": cy2, "speed": 1.5, "weight_rating": 5.0
        }
        st.session_state.crane_zones.append(new_crane)
        st.success("Defined overhead crane zone boundaries!")

if st.sidebar.button("🧹 Clear Layout Workspace", type="primary"):
    st.session_state.placed_machines = []
    st.session_state.flow_paths = []
    st.session_state.crane_zones = []
    st.rerun()

# ==========================================
# 5. Core Simulation & Analysis Engine
# ==========================================
violations = []
bottleneck_idx = -1

if st.session_state.placed_machines:
    violations, bottleneck_idx = run_analysis(
        st.session_state.placed_machines,
        st.session_state.flow_paths,
        st.session_state.crane_zones
    )

# ==========================================
# 6. Data Visualization (Matplotlib Layout Engine)
# ==========================================
col_workspace, col_results = st.columns([3, 2])

with col_workspace:
    st.subheader("2D Factory Scale Canvas")
    
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.set_xlim(0, 50)
    ax.set_ylim(0, 30)
    ax.set_aspect('equal')
    ax.grid(True, which='both', color='#e0e0e0', linestyle='--', linewidth=0.5)
    ax.set_xlabel("Factory Width (meters)")
    ax.set_ylabel("Factory Length (meters)")
    
    # Render Cranes (Background)
    for c in st.session_state.crane_zones:
        cx_min, cy_min = min(c['x1'], c['x2']), min(c['y1'], c['y2'])
        cw, ch = abs(c['x2'] - c['x1']), abs(c['y2'] - c['y1'])
        rect = patches.Rectangle((cx_min, cy_min), cw, ch, fill=True, color='#f3e5f5', alpha=0.5, edgecolor='#9b59b6', linestyle='--', linewidth=1.5)
        ax.add_patch(rect)
        ax.text(cx_min + 0.5, cy_min + 0.5, f"Crane {c['id']}", color='#9b59b6', fontsize=8, fontweight='bold')

    # Render Flow Corridor Paths
    for p in st.session_state.flow_paths:
        pts = p['points']
        px = [pt['x'] for pt in pts]
        py = [pt['y'] for pt in pts]
        p_col = "#3498db" if p['type'] == "human" else "#e74c3c"
        ax.plot(px, py, color=p_col, linewidth=p['width'] * 5, alpha=0.25)
        ax.plot(px, py, color=p_col, linewidth=1.5, linestyle='-')
        ax.text(px[0] + 0.5, py[0] + 0.5, f"Path {p['id']}", color=p_col, fontsize=7)

    # Render Placing Machines & Safety Buffer
    for m in st.session_state.placed_machines:
        mx = m['x'] - m['width']/2
        my = m['y'] - m['height']/2
        
        soff = m['safety_standoff']
        standoff_color = 'rgba(231, 76, 60, 0.15)' if m.get('safety_violation', False) else 'rgba(46, 204, 113, 0.1)'
        standoff_edge = '#e74c3c' if m.get('safety_violation', False) else '#2ecc71'
        
        buffer_rect = patches.Rectangle(
            (mx - soff, my - soff), m['width'] + 2*soff, m['height'] + 2*soff,
            fill=True, color=standoff_color, alpha=0.2, edgecolor=standoff_edge, linestyle=':', linewidth=1
        )
        ax.add_patch(buffer_rect)
        
        m_color = "#f1c40f" if m.get('is_bottleneck', False) else "#2c3e50"
        m_edge = "#f39c12" if m.get('is_bottleneck', False) else "#34495e"
        
        machine_rect = patches.Rectangle((mx, my), m['width'], m['height'], fill=True, color=m_color, edgecolor=m_edge, linewidth=2)
        ax.add_patch(machine_rect)
        
        ax.text(m['x'], m['y'], m['name'][:14], color='white' if not m.get('is_bottleneck', False) else 'black', 
                fontsize=8, fontweight='bold', ha='center', va='center')
        ax.text(m['x'], m['y'] - m['height']/2 - 0.4, f"ID: {m['id']}", color='#7f8c8d', fontsize=7, ha='center')

    st.pyplot(fig)
    plt.close(fig)

# ==========================================
# 7. Metrics & Analytics Outputs
# ==========================================
with col_results:
    st.subheader("Compliance Metrics")
    
    if st.session_state.placed_machines:
        st.write("Placed Workstations Configuration:")
        layout_grid = []
        for m in st.session_state.placed_machines:
            layout_grid.append({
                "ID": m["id"],
                "Machine": m["name"],
                "Location (X,Y)": f"({m['x']}, {m['y']})",
                "Load": f"{m['wattage']/1000:.1f} kW",
                "Rate (Units/hr)": m["volume_per_hour"],
                "Yield": f"{m['yield_percentage']*100:.1f}%",
                "Safety": "🔴 OVERLAP" if m.get("safety_violation") else "🟢 OK",
                "Status": "⚡ BOTTLENECK" if m.get("is_bottleneck") else "Active"
            })
        st.table(pd.DataFrame(layout_grid))
        
        total_p = sum(m["wattage"] for m in st.session_state.placed_machines)
        total_w = sum(1 for m in st.session_state.placed_machines if m["water_required"])
        st.metric("Electrical Load", f"{total_p/1000:.1f} kW")
        st.metric("Water Drops", f"{total_w} Connections")
    else:
        st.info("No machines placed on the layout yet.")

    st.subheader("Safety Compliance Log")
    if violations:
        for v in violations:
            st.error(f"⚠️ {v['description']}")
    elif st.session_state.placed_machines:
        st.success("✔ Layout has passed all OSHA safety clearances.")
    else:
        st.write("Log is empty. Place machinery to trigger checks.")

# ==========================================
# 8. Report Export & Business Rules Enforcement
# ==========================================
st.markdown("---")
st.subheader("Exports")

if st.session_state.placed_machines:
    has_violations = any(m.get("safety_violation", False) for m in st.session_state.placed_machines)
    
    if has_violations:
        st.warning("🔒 Exporter Disabled: Resolve safety standoff overlaps (marked in red) before exporting blueprints.")
        st.button("Export Engineering Blueprint (PDF)", disabled=True)
    else:
        pdf_bytes = generate_pdf_report(
            st.session_state.placed_machines,
            st.session_state.flow_paths,
            st.session_state.crane_zones,
            violations,
            bottleneck_idx
        )
        
        st.success("✔ Engineering Document Release Approved.")
        st.download_button(
            label="📥 Download Engineering Blueprint Report (PDF)",
            data=pdf_bytes,
            file_name="FactoryFloor_Optimization_Report.pdf",
            mime="application/pdf"
        )
else:
    st.info("Release pipeline inactive. Design a layout workspace to generate deliverables.")
