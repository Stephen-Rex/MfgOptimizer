import streamlit as st
import pandas as pd
import numpy as np
import subprocess
import os
import json
import math
import matplotlib.pyplot as plt
import matplotlib.patches as patches

# --- Page Configurations ---
st.set_page_config(
    page_title="Factory Floor Optimizer & Post-Processor",
    page_icon="🏭",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Default Datasets with Initial Spacing s Along Polyline ---
DEFAULT_MACHINES = [
    {"id": 1, "name": "Raw Material Intake", "s": 0.0, "dim_x": 3.0, "dim_y": 2.0, "so_px": 1.0, "so_nx": 1.0, "so_py": 1.0, "so_ny": 1.0, "process_time": 2.0, "setup_time": 5.0},
    {"id": 2, "name": "CNC Milling", "s": 8.0, "dim_x": 4.0, "dim_y": 4.0, "so_px": 1.5, "so_nx": 1.5, "so_py": 1.5, "so_ny": 1.5, "process_time": 8.5, "setup_time": 20.0},
    {"id": 3, "name": "Laser Welder", "s": 16.0, "dim_x": 3.0, "dim_y": 3.0, "so_px": 1.2, "so_nx": 1.2, "so_py": 1.2, "so_ny": 1.2, "process_time": 4.0, "setup_time": 15.0},
    {"id": 4, "name": "Surface Treatment", "s": 24.0, "dim_x": 5.0, "dim_y": 3.0, "so_px": 1.0, "so_nx": 1.0, "so_py": 1.0, "so_ny": 1.0, "process_time": 6.0, "setup_time": 10.0},
    {"id": 5, "name": "Quality Assembly", "s": 32.0, "dim_x": 3.5, "dim_y": 2.5, "so_px": 0.8, "so_nx": 0.8, "so_py": 0.8, "so_ny": 0.8, "process_time": 5.0, "setup_time": 8.0}
]

DEFAULT_FLOWS = [
    {"src_id": 1, "dest_id": 2, "volume": 120.0},
    {"src_id": 2, "dest_id": 3, "volume": 100.0},
    {"src_id": 3, "dest_id": 4, "volume": 80.0},
    {"src_id": 4, "dest_id": 5, "volume": 95.0},
    {"src_id": 2, "dest_id": 5, "volume": 15.0}
]

# --- Polyline Cartesian Mapper Helper ---
def get_point_on_polyline(s, grid_x, grid_y):
    vx = [3.0, 3.0, grid_x - 3.0, grid_x - 3.0]
    vy = [3.0, grid_y - 3.0, grid_y - 3.0, 3.0]
    
    seg_lens = []
    for i in range(3):
        seg_lens.append(math.sqrt((vx[i+1]-vx[i])**2 + (vy[i+1]-vy[i])**2))
        
    current_s = 0.0
    for i in range(3):
        if s <= current_s + seg_lens[i]:
            ratio = (s - current_s) / seg_lens[i]
            x = vx[i] + ratio * (vx[i+1] - vx[i])
            y = vy[i] + ratio * (vy[i+1] - vy[i])
            return x, y
        current_s += seg_lens[i]
    return vx[3], vy[3]

def calculate_center_distance(x1, y1, x2, y2):
    return math.sqrt((x1 - x2) ** 2 + (y1 - y2) ** 2)

def check_safe_overlap(x1, y1, w1, h1, px1, nx1, py1, ny1, x2, y2, w2, h2, px2, nx2, py2, ny2):
    min_x1 = x1 - w1 / 2.0 - nx1
    max_x1 = x1 + w1 / 2.0 + px1
    min_y1 = y1 - h1 / 2.0 - ny1
    max_y1 = y1 + h1 / 2.0 + py1
    
    min_x2 = x2 - w2 / 2.0 - nx2
    max_x2 = x2 + w2 / 2.0 + px2
    min_y2 = y2 - h2 / 2.0 - ny2
    max_y2 = y2 + h2 / 2.0 + py2
    
    return min_x1 < max_x2 and max_x1 > min_x2 and min_y1 < max_y2 and max_y1 > min_y2

def is_safe_out_of_bounds(x, y, w, h, px, nx, py, ny, grid_x, grid_y):
    return (x - w/2.0 - nx < 0) or (x + w/2.0 + px > grid_x) or (y - h/2.0 - ny < 0) or (y + h/2.0 + py > grid_y)

# --- Soft-Penalty Cost Evaluator ---
def evaluate_polyline_layout(machines, flows_list, grid_x, grid_y):
    transport_cost = 0.0
    penalty = 0.0
    
    # 1. Map 1D cumulative distances to 2D coordinates on the fly
    for m in machines:
        m["x"], m["y"] = get_point_on_polyline(m["s"], grid_x, grid_y)
        
    machines_dict = {m["id"]: m for m in machines}
    
    # 2. Material transport flow cost
    for flow in flows_list:
        src, dest = flow["src_id"], flow["dest_id"]
        if src in machines_dict and dest in machines_dict:
            m1, m2 = machines_dict[src], machines_dict[dest]
            dist = calculate_center_distance(m1["x"], m1["y"], m2["x"], m2["y"])
            transport_cost += dist * flow["volume"]
            
    # 3. Enforce boundary containment and footprint safety overlaps
    for i, m1 in enumerate(machines):
        if is_safe_out_of_bounds(m1["x"], m1["y"], m1["dim_x"], m1["dim_y"], m1["so_px"], m1["so_nx"], m1["so_py"], m1["so_ny"], grid_x, grid_y):
            penalty += 10000.0
        for j, m2 in enumerate(machines):
            if i < j:
                if check_safe_overlap(m1["x"], m1["y"], m1["dim_x"], m1["dim_y"], m1["so_px"], m1["so_nx"], m1["so_py"], m1["so_ny"],
                                   m2["x"], m2["y"], m2["dim_x"], m2["dim_y"], m2["so_px"], m2["so_nx"], m2["so_py"], m2["so_ny"]):
                    penalty += 20000.0
                    
    return transport_cost + penalty

def python_optimize_layout(machines_list, flows_list, grid_size_x=20, grid_size_y=20):
    machines = [dict(m) for m in machines_list]
    improved = True
    iterations = 0
    
    best_cost = evaluate_polyline_layout(machines, flows_list, grid_size_x, grid_size_y)
    
    while improved and iterations < 150:
        improved = False
        iterations += 1
        for i in range(1, len(machines)): # Machine 1 (Intake) is fixed at s=0
            original_s = machines[i]["s"]
            best_ds = 0.0
            
            for ds in np.arange(-4.0, 4.5, 0.5):
                if ds == 0.0:
                    continue
                
                candidate_s = original_s + ds
                min_s = machines[i-1]["s"] + (machines[i-1]["dim_x"] + machines[i]["dim_x"]) / 2.0
                if candidate_s < min_s:
                    continue
                
                machines[i]["s"] = candidate_s
                current_cost = evaluate_polyline_layout(machines, flows_list, grid_size_x, grid_size_y)
                
                if current_cost < best_cost:
                    best_cost = current_cost
                    best_ds = ds
                    improved = True
            
            machines[i]["s"] = original_s + best_ds
            
    # Calculate final status checks
    for i, m in enumerate(machines):
        m["x"], m["y"] = get_point_on_polyline(m["s"], grid_size_x, grid_size_y)
        m["is_safe"] = True
        if is_safe_out_of_bounds(m["x"], m["y"], m["dim_x"], m["dim_y"], m["so_px"], m["so_nx"], m["so_py"], m["so_ny"], grid_size_x, grid_size_y):
            m["is_safe"] = False
        else:
            for j, other in enumerate(machines):
                if i != j:
                    if check_safe_overlap(m["x"], m["y"], m["dim_x"], m["dim_y"], m["so_px"], m["so_nx"], m["so_py"], m["so_ny"],
                                       other["x"], other["y"], other["dim_x"], other["dim_y"],
                                       other["so_px"], other["so_nx"], other["so_py"], other["so_ny"]):
                        m["is_safe"] = False
                        break

    # Dwell timings
    total_dwell = 0.0
    bottleneck_time = -1.0
    bottleneck_machine = ""
    for m in machines:
        dwell = m["process_time"] + (m["setup_time"] / 50.0)
        total_dwell += dwell
        m["dwell_time"] = dwell
        m["capacity"] = 60.0 / m["process_time"] if m["process_time"] > 0 else 0
        if dwell > bottleneck_time:
            bottleneck_time = dwell
            bottleneck_machine = m["name"]

    return {
        "initial_transport_cost": evaluate_polyline_layout(machines_list, flows_list, grid_size_x, grid_size_y),
        "optimized_transport_cost": best_cost,
        "iterations": iterations,
        "dwell_time_analysis": {
            "total_dwell_time": total_dwell,
            "bottleneck_machine": bottleneck_machine,
            "bottleneck_dwell_time": bottleneck_time
        },
        "machines": machines
    }

# --- App Header layout ---
st.markdown("## 🏭 Polyline Part Flow Assembly Optimizer")
st.markdown("Aligns machinery sequentially along a 2D line segment path with an integrated fork truck & operator safety lane.")

# --- SIDEBAR Parameters ---
st.sidebar.subheader("📐 Rectangular Plant Dimensions")
grid_size_x = st.sidebar.slider("Floor Width (X) [Meters]", min_value=15, max_value=100, value=20)
grid_size_y = st.sidebar.slider("Floor Height (Y) [Meters]", min_value=15, max_value=100, value=20)

st.sidebar.subheader("🚚 Fork Truck Safety Corridor")
path_buffer = st.sidebar.slider("Standoff buffer Width (Each Side) [Meters]", min_value=0.5, max_value=1.5, value=1.0, step=0.1)

engine_selection = st.sidebar.radio(
    "🖥️ Optimizer Engine Mode",
    ["Python Simulator (Highly Recommended / No Compiler Required)", "C Binary Subprocess (Requires GCC compiler in environment)"]
)

# Initialize Session States
if "machines_df" not in st.session_state:
    st.session_state.machines_df = pd.DataFrame(DEFAULT_MACHINES)
if "flows_df" not in st.session_state:
    st.session_state.flows_df = pd.DataFrame(DEFAULT_FLOWS)

# --- TABS Layout ---
tab1, tab2, tab3 = st.tabs(["📋 Configure Parameters", "👁️ Generated C Source", "📊 Execution & Visual Analytics"])

with tab1:
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("🤖 Machine Spacings along Polyline")
        st.markdown("Set cumulative distances (`s` in meters), dimensions (`dim_x, dim_y`), and directional standoffs:")
        edited_machines = st.data_editor(
            st.session_state.machines_df,
            num_rows="dynamic",
            use_container_width=True,
            key="machine_editor"
        )
        
    with col2:
        st.subheader("🔄 Material Flow Densities")
        st.markdown("Specify conveyor transit rates between stations:")
        edited_flows = st.data_editor(
            st.session_state.flows_df,
            num_rows="dynamic",
            use_container_width=True,
            key="flow_editor"
        )

st.session_state.machines_df = edited_machines
st.session_state.flows_df = edited_flows

c_source_code = generate_c_code_template(
    edited_machines.to_dict(orient="records"),
    edited_flows.to_dict(orient="records"),
    grid_size_x,
    grid_size_y
)

with tab2:
    st.subheader("📝 Live C Backend Code View")
    st.code(c_source_code, language="c")
    st.download_button(
        "💾 Download Custom compiler.c",
        c_source_code,
        "factory_optimizer.c",
        "text/plain"
    )

with tab3:
    st.subheader("🎯 Optimizing and Post-Processing Predictions")
    
    if st.button("🚀 Run Layout Optimizer Heuristic"):
        machines_data = edited_machines.to_dict(orient="records")
        flows_data = edited_flows.to_dict(orient="records")
        
        results = None
        execution_msg = ""
        
        if "C Binary" in engine_selection:
            try:
                with open("optimizer.c", "w") as f:
                    f.write(c_source_code)
                
                compile_process = subprocess.run(
                    ["gcc", "optimizer.c", "-o", "optimizer", "-lm"],
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
                )
                
                if compile_process.returncode != 0:
                    st.error(f"Compilation Failed: {compile_process.stderr}")
                    st.warning("Defaulting to high-fidelity Python Simulator fallback instead!")
                    results = python_optimize_layout(machines_data, flows_data, grid_size_x, grid_size_y)
                    execution_msg = "Python Simulation Fallback (Compiler Error)"
                else:
                    run_process = subprocess.run(
                        ["./optimizer"],
                        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
                    )
                    
                    if os.path.exists("layout_output.json"):
                        with open("layout_output.json", "r") as f:
                            results = json.load(f)
                        execution_msg = "Compiled C Binary Backend"
                    else:
                        st.error("C Binary did not output results JSON. Using Python Engine.")
                        results = python_optimize_layout(machines_data, flows_data, grid_size_x, grid_size_y)
                        execution_msg = "Python Simulation Fallback (Execution Failure)"
            except Exception as e:
                st.error(f"Could not execute C compiler subprocess: {e}")
                st.warning("IT restricts execution. Defaulting to Python Simulation Fallback.")
                results = python_optimize_layout(machines_data, flows_data, grid_size_x, grid_size_y)
                execution_msg = "Python Simulation Fallback"
        else:
            results = python_optimize_layout(machines_data, flows_data, grid_size_x, grid_size_y)
            execution_msg = "Pure Python Simulator Engine (Instant Browser Runtime)"

        # --- Display KPI Metric Cards ---
        st.success(f"Execution Successful! Source Engine: **{execution_msg}**")
        
        opt_machines = results["machines"]
        opt_lookup = {m["id"]: m for m in opt_machines}
        init_lookup = {m["id"]: m for m in machines_data}

        # Calculate final safety overlaps
        overlaps_count = 0
        for i in range(len(machines_data)):
            for j in range(i + 1, len(machines_data)):
                m1 = opt_lookup[machines_data[i]["id"]]
                m2 = opt_lookup[machines_data[j]["id"]]
                x1, y1 = m1.get("optimized_x", m1.get("x")), m1.get("optimized_y", m1.get("y"))
                x2, y2 = m2.get("optimized_x", m2.get("x")), m2.get("optimized_y", m2.get("y"))
                if check_safe_overlap(x1, y1, m1["dim_x"], m1["dim_y"], m1["so_px"], m1["so_nx"], m1["so_py"], m1["so_ny"],
                                   x2, y2, m2["dim_x"], m2["dim_y"], m2["so_px"], m2["so_nx"], m2["so_py"], m2["so_ny"]):
                    overlaps_count += 1

        col_metric1, col_metric2, col_metric3 = st.columns(3)
        
        opt_cost = results["optimized_transport_cost"]
        
        with col_metric1:
            st.metric("Packed Layout Movement Cost", f"{opt_cost:.2f} m·parts/hr")
        with col_metric2:
            st.metric("Bottleneck Cycle Time", f"{results['dwell_time_analysis']['bottleneck_dwell_time']:.2f} mins/part")
        with col_metric3:
            st.metric("Safety Envelope Overlaps", f"{overlaps_count}", delta=f"{overlaps_count} Violations", delta_color="inverse")

        # --- Visual Post-Processing Plots ---
        col_plot1, col_plot2 = st.columns(2)
        
        # Plot 1: Floor Mapping & Safety Zones
        with col_plot1:
            st.markdown("### 🗺️ Floor Layout, Footprints & Flow Clearances")
            
            fig, ax = plt.subplots(figsize=(8, 8))
            ax.set_xlim(-2, grid_size_x + 4)
            ax.set_ylim(-2, grid_size_y + 4)
            ax.set_aspect('equal')
            ax.grid(True, which='both', linestyle='--', alpha=0.5)
            
            # Draw Dynamic Polyline Flow Path
            vx = [3.0, 3.0, grid_size_x - 3.0, grid_size_x - 3.0]
            vy = [3.0, grid_size_y - 3.0, grid_size_y - 3.0, 3.0]
            ax.plot(vx, vy, color="grey", linewidth=4, zorder=1, label="Conveyor Backbone")
            
            # Draw Parallel Forklift Lanes & Safety boundaries centered along the Polyline
            # Segment 1: Left vertical
            ax.plot([3.0 - path_buffer, 3.0 - path_buffer], [3.0 - path_buffer, grid_size_y - 3.0 + path_buffer], "y--", alpha=0.6, label="Standoff Lane Marking")
            ax.plot([3.0 + path_buffer, 3.0 + path_buffer], [3.0 + path_buffer, grid_size_y - 3.0 - path_buffer], "y--", alpha=0.6)
            # Segment 2: Top horizontal
            ax.plot([3.0 - path_buffer, grid_size_x - 3.0 + path_buffer], [grid_size_y - 3.0 + path_buffer, grid_size_y - 3.0 + path_buffer], "y--", alpha=0.6)
            ax.plot([3.0 + path_buffer, grid_size_x - 3.0 - path_buffer], [grid_size_y - 3.0 - path_buffer, grid_size_y - 3.0 - path_buffer], "y--", alpha=0.6)
            # Segment 3: Right vertical
            ax.plot([grid_size_x - 3.0 - path_buffer, grid_size_x - 3.0 - path_buffer], [3.0 + path_buffer, grid_size_y - 3.0 - path_buffer], "y--", alpha=0.6)
            ax.plot([grid_size_x - 3.0 + path_buffer, grid_size_x - 3.0 + path_buffer], [3.0 - path_buffer, grid_size_y - 3.0 + path_buffer], "y--", alpha=0.6)

            # Draw each Machine Footprint and its safety boundaries along the path
            for m in opt_machines:
                m_id = m["id"]
                w = m.get("dim_x", init_lookup[m_id].get("dim_x", 1.0))
                h = m.get("dim_y", init_lookup[m_id].get("dim_y", 1.0))
                so_px = m.get("so_px", init_lookup[m_id].get("so_px", 0.0))
                so_nx = m.get("so_nx", init_lookup[m_id].get("so_nx", 0.0))
                so_py = m.get("so_py", init_lookup[m_id].get("so_py", 0.0))
                so_ny = m.get("so_ny", init_lookup[m_id].get("so_ny", 0.0))
                
                opt_x = m.get("optimized_x", m.get("x"))
                opt_y = m.get("optimized_y", m.get("y"))
                
                # Plot Optimized Footprints (Solid colored box)
                border_color = "green" if m["is_safe"] else "red"
                fill_color = "lightgreen" if m["is_safe"] else "lightcoral"
                
                opt_box = patches.Rectangle(
                    (opt_x - w/2.0, opt_y - h/2.0), w, h,
                    linewidth=2, edgecolor=border_color, facecolor=fill_color, zorder=5, alpha=0.9
                )
                ax.add_patch(opt_box)
                
                # Label inside the rectangle
                ax.text(opt_x, opt_y, f"[{m_id}]\n{m['name']}", color="black", weight="bold", fonts
