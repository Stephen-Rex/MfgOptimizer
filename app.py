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

# --- Default Datasets with Geometric Footprints & Directional Standoffs ---
DEFAULT_MACHINES = [
    {"id": 1, "name": "Raw Material Intake", "x": 3.0, "y": 2.0, "dim_x": 3.0, "dim_y": 2.0, "so_px": 1.0, "so_nx": 1.0, "so_py": 1.0, "so_ny": 1.0, "process_time": 2.0, "setup_time": 5.0},
    {"id": 2, "name": "CNC Milling", "x": 12.0, "y": 14.0, "dim_x": 4.0, "dim_y": 4.0, "so_px": 1.5, "so_nx": 1.5, "so_py": 1.5, "so_ny": 1.5, "process_time": 8.5, "setup_time": 20.0},
    {"id": 3, "name": "Laser Welder", "x": 5.0, "y": 8.0, "dim_x": 3.0, "dim_y": 3.0, "so_px": 1.2, "so_nx": 1.2, "so_py": 1.2, "so_ny": 1.2, "process_time": 4.0, "setup_time": 15.0},
    {"id": 4, "name": "Surface Treatment", "x": 17.0, "y": 3.0, "dim_x": 5.0, "dim_y": 3.0, "so_px": 1.0, "so_nx": 1.0, "so_py": 1.0, "so_ny": 1.0, "process_time": 6.0, "setup_time": 10.0},
    {"id": 5, "name": "Quality Assembly", "x": 15.0, "y": 10.0, "dim_x": 3.5, "dim_y": 2.5, "so_px": 0.8, "so_nx": 0.8, "so_py": 0.8, "so_ny": 0.8, "process_time": 5.0, "setup_time": 8.0}
]

DEFAULT_FLOWS = [
    {"src_id": 1, "dest_id": 2, "volume": 120.0},
    {"src_id": 2, "dest_id": 3, "volume": 100.0},
    {"src_id": 3, "dest_id": 4, "volume": 80.0},
    {"src_id": 4, "dest_id": 5, "volume": 95.0},
    {"src_id": 2, "dest_id": 5, "volume": 15.0}
]

# --- Python Engine Math & Fallback Logic (Directional Standoffs) ---
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

def evaluate_layout(machines_dict, flows_list):
    total_cost = 0.0
    for flow in flows_list:
        src = flow["src_id"]
        dest = flow["dest_id"]
        if src in machines_dict and dest in machines_dict:
            m1 = machines_dict[src]
            m2 = machines_dict[dest]
            dist = calculate_center_distance(m1["x"], m1["y"], m2["x"], m2["y"])
            total_cost += dist * flow["volume"]
    return total_cost

def python_optimize_layout(machines_list, flows_list, grid_size_x=20, grid_size_y=20):
    machines = [dict(m) for m in machines_list]
    improved = True
    iterations = 0
    
    machines_dict = {m["id"]: m for m in machines}
    initial_cost = evaluate_layout(machines_dict, flows_list)
    best_cost = initial_cost
    
    while improved and iterations < 100:
        improved = False
        iterations += 1
        for i in range(len(machines)):
            original_x = machines[i]["x"]
            original_y = machines[i]["y"]
            w = machines[i]["dim_x"]
            h = machines[i]["dim_y"]
            px = machines[i]["so_px"]
            nx = machines[i]["so_nx"]
            py = machines[i]["so_py"]
            ny = machines[i]["so_ny"]
            
            best_dx, best_dy = 0.0, 0.0
            
            for dx in np.arange(-2.0, 2.5, 0.5):
                for dy in np.arange(-2.0, 2.5, 0.5):
                    if dx == 0.0 and dy == 0.0:
                        continue
                    
                    nx_coord = original_x + dx
                    ny_coord = original_y + dy
                    
                    # Boundary check for entire safe bounding box
                    if is_safe_out_of_bounds(nx_coord, ny_coord, w, h, px, nx, py, ny, grid_size_x, grid_size_y):
                        continue
                    
                    # Overlap check with other machine's safe footprints
                    overlap = False
                    for k in range(len(machines)):
                        if k != i:
                            if check_safe_overlap(nx_coord, ny_coord, w, h, px, nx, py, ny,
                                               machines[k]["x"], machines[k]["y"], machines[k]["dim_x"], machines[k]["dim_y"],
                                               machines[k]["so_px"], machines[k]["so_nx"], machines[k]["so_py"], machines[k]["so_ny"]):
                                overlap = True
                                break
                    if overlap:
                        continue
                    
                    # Temporarily apply move
                    machines[i]["x"] = nx_coord
                    machines[i]["y"] = ny_coord
                    
                    current_cost = evaluate_layout({m["id"]: m for m in machines}, flows_list)
                    if current_cost < best_cost:
                        best_cost = current_cost
                        best_dx = dx
                        best_dy = dy
                        improved = True
            
            # Apply best step
            if improved:
                machines[i]["x"] = original_x + best_dx
                machines[i]["y"] = original_y + best_dy
            else:
                machines[i]["x"] = original_x
                machines[i]["y"] = original_y
                
    # Evaluate safety compliance status (Boundary and overlap checks)
    for i, m in enumerate(machines):
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

    # Manufacturing Dwell times
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
        "initial_transport_cost": initial_cost,
        "optimized_transport_cost": best_cost,
        "iterations": iterations,
        "dwell_time_analysis": {
            "total_dwell_time": total_dwell,
            "bottleneck_machine": bottleneck_machine,
            "bottleneck_dwell_time": bottleneck_time
        },
        "machines": machines
    }

# --- C Code Generation (Directional Standoff Support) ---
def generate_c_code_template(machines, flows, grid_size_x, grid_size_y):
    machines_str = ""
    for m in machines:
        machines_str += f'    {{{m["id"]}, "{m["name"]}", {m["x"]}, {m["y"]}, {m["dim_x"]}, {m["dim_y"]}, {m["so_px"]}, {m["so_nx"]}, {m["so_py"]}, {m["so_ny"]}, {m["process_time"]}, {m["setup_time"]}}},\n'
    machines_str = machines_str.rstrip(",\n")

    flows_str = ""
    for f in flows:
        flows_str += f'    {{{int(f["src_id"])}, {int(f["dest_id"])}, {f["volume"]}}},\n'
    flows_str = flows_str.rstrip(",\n")

    return f"""#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <stdbool.h>

#define MAX_MACHINES 15
#define GRID_SIZE_X {grid_size_x}
#define GRID_SIZE_Y {grid_size_y}

typedef struct {{
    int id;
    char name[30];
    double x;             /* Center X coordinate */
    double y;             /* Center Y coordinate */
    double dim_x;         /* Geometric Width */
    double dim_y;         /* Geometric Height */
    double so_px;         /* Positive X Standoff */
    double so_nx;         /* Negative X Standoff */
    double so_py;         /* Positive Y Standoff */
    double so_ny;         /* Negative Y Standoff */
    double process_time;
    double setup_time;
}} Machine;

typedef struct {{
    int src_id;
    int dest_id;
    double volume;
}} MaterialFlow;

Machine machines[] = {{
{machines_str}
}};
int num_machines = {len(machines)};

MaterialFlow flows[] = {{
{flows_str}
}};
int num_flows = {len(flows)};

double calculate_center_distance(double x1, double y1, double x2, double y2) {{
    return sqrt((x1 - x2) * (x1 - x2) + (y1 - y2) * (y1 - y2));
}}

bool check_safe_overlap(double x1, double y1, double w1, double h1, double px1, double nx1, double py1, double ny1,
                        double x2, double y2, double w2, double h2, double px2, double nx2, double py2, double ny2) {{
    double min_x1 = x1 - w1 / 2.0 - nx1;
    double max_x1 = x1 + w1 / 2.0 + px1;
    double min_y1 = y1 - h1 / 2.0 - ny1;
    double max_y1 = y1 + h1 / 2.0 + py1;
    
    double min_x2 = x2 - w2 / 2.0 - nx2;
    double max_x2 = x2 + w2 / 2.0 + px2;
    double min_y2 = y2 - h2 / 2.0 - ny2;
    double max_y2 = y2 + h2 / 2.0 + py2;
    
    return min_x1 < max_x2 && max_x1 > min_x2 && min_y1 < max_y2 && max_y1 > min_y2;
}}

bool is_safe_out_of_bounds(double x, double y, double w, double h, double px, double nx, double py, double ny) {{
    return (x - w/2.0 - nx < 0.0) || (x + w/2.0 + px > GRID_SIZE_X) || (y - h/2.0 - ny < 0.0) || (y + h/2.0 + py > GRID_SIZE_Y);
}}

double evaluate_layout(void) {{
    double total_cost = 0.0;
    int i, j;
    for (i = 0; i < num_flows; i++) {{
        int src = flows[i].src_id;
        int dest = flows[i].dest_id;
        int idx_src = -1, idx_dest = -1;
        for (j = 0; j < num_machines; j++) {{
            if (machines[j].id == src) idx_src = j;
            if (machines[j].id == dest) idx_dest = j;
        }}
        if (idx_src != -1 && idx_dest != -1) {{
            double dist = calculate_center_distance(machines[idx_src].x, machines[idx_src].y, 
                                                    machines[idx_dest].x, machines[idx_dest].y);
            total_cost += dist * flows[i].volume;
        }}
    }}
    return total_cost;
}}

void optimize_placement(void) {{
    double best_cost = evaluate_layout();
    bool improved = true;
    int iterations = 0;
    int i, k;
    double dx, dy;
    
    while (improved && iterations < 100) {{
        improved = false;
        iterations++;
        for (i = 0; i < num_machines; i++) {{
            double original_x = machines[i].x;
            double original_y = machines[i].y;
            double w = machines[i].dim_x;
            double h = machines[i].dim_y;
            double px = machines[i].so_px;
            double nx = machines[i].so_nx;
            double py = machines[i].so_py;
            double ny = machines[i].so_ny;
            double best_dx = 0.0, best_dy = 0.0;
            
            for (dx = -2.0; dx <= 2.0; dx += 0.5) {{
                for (dy = -2.0; dy <= 2.0; dy += 0.5) {{
                    double nx_coord, ny_coord;
                    bool overlap = false;
                    double current_cost;
                    if (dx == 0.0 && dy == 0.0) continue;
                    
                    nx_coord = original_x + dx;
                    ny_coord = original_y + dy;
                    if (is_safe_out_of_bounds(nx_coord, ny_coord, w, h, px, nx, py, ny)) continue;
                    
                    for (k = 0; k < num_machines; k++) {{
                        if (k != i && check_safe_overlap(nx_coord, ny_coord, w, h, px, nx, py, ny,
                                                         machines[k].x, machines[k].y, machines[k].dim_x, machines[k].dim_y,
                                                         machines[k].so_px, machines[k].so_nx, machines[k].so_py, machines[k].so_ny)) {{
                            overlap = true;
                            break;
                        }}
                    }}
                    if (overlap) continue;
                    
                    machines[i].x = nx_coord;
                    machines[i].y = ny_coord;
                    current_cost = evaluate_layout();
                    
                    if (current_cost < best_cost) {{
                        best_cost = current_cost;
                        best_dx = dx;
                        best_dy = dy;
                        improved = true;
                    }}
                }}
            }}
            if (improved) {{
                machines[i].x = original_x + best_dx;
                machines[i].y = original_y + best_dy;
            }} else {{
                machines[i].x = original_x;
                machines[i].y = original_y;
            }}
        }}
    }}
}}

int main(void) {{
    double init_cost = evaluate_layout();
    optimize_placement();
    double opt_cost = evaluate_layout();
    
    FILE *fp = fopen("layout_output.json", "w");
    if (!fp) return 1;
    
    fprintf(fp, "{{\\n");
    fprintf(fp, "  \\\"initial_transport_cost\\\": %.2f,\\n", init_cost);
    fprintf(fp, "  \\\"optimized_transport_cost\\\": %.2f,\\n", opt_cost);
    
    double total_dwell = 0.0;
    double bottleneck_time = -1.0;
    char bottleneck_name[30] = "";
    int i;
    for(i=0; i<num_machines; i++) {{
        double dwell = machines[i].process_time + (machines[i].setup_time / 50.0);
        total_dwell += dwell;
        if(dwell > bottleneck_time) {{
            bottleneck_time = dwell;
            strcpy(bottleneck_name, machines[i].name);
        }}
    }}
    
    fprintf(fp, "  \\\"dwell_time_analysis\\\": {{\\n");
    fprintf(fp, "    \\\"total_dwell_time\\\": %.2f,\\n", total_dwell);
    fprintf(fp, "    \\\"bottleneck_machine\\\": \\\"%s\\\",\\n", bottleneck_name);
    fprintf(fp, "    \\\"bottleneck_dwell_time\\\": %.2f\\n", bottleneck_time);
    fprintf(fp, "  }},\\n");
    
    fprintf(fp, "  \\\"machines\\\": [\\n");
    for (i = 0; i < num_machines; i++) {{
        bool safe = true;
        if (is_safe_out_of_bounds(machines[i].x, machines[i].y, machines[i].dim_x, machines[i].dim_y,
                                  machines[i].so_px, machines[i].so_nx, machines[i].so_py, machines[i].so_ny)) {{
            safe = false;
        }} else {{
            for (int j = 0; j < num_machines; j++) {{
                if (i != j && check_safe_overlap(machines[i].x, machines[i].y, machines[i].dim_x, machines[i].dim_y,
                                                 machines[i].so_px, machines[i].so_nx, machines[i].so_py, machines[i].so_ny,
                                                 machines[j].x, machines[j].y, machines[j].dim_x, machines[j].dim_y,
                                                 machines[j].so_px, machines[j].so_nx, machines[j].so_py, machines[j].so_ny)) {{
                    safe = false;
                    break;
                }}
            }}
        }}
        fprintf(fp, "    {{\\n");
        fprintf(fp, "      \\\"id\\\": %d,\\n", machines[i].id);
        fprintf(fp, "      \\\"name\\\": \\\"%s\\\",\\n", machines[i].name);
        fprintf(fp, "      \\\"optimized_x\\\": %.2f,\\n", machines[i].x);
        fprintf(fp, "      \\\"optimized_y\\\": %.2f,\\n", machines[i].y);
        fprintf(fp, "      \\\"is_safe\\\": %s\\n", safe ? "true" : "false");
        fprintf(fp, "    }}%s\\n", (i == num_machines - 1) ? "" : ",");
    }}
    fprintf(fp, "  ]\\n");
    fprintf(fp, "}}\\n");
    fclose(fp);
    return 0;
}}
"""

# --- App Header Layout ---
st.markdown("## 🏭 Industrial Optimizer: Bounding Box & Directional Standoffs Edition")
st.markdown("Prevent floor plans from clipping. Define asymmetric clearance zones (Positive X, Negative X, Positive Y, Negative Y) per machine footprint.")

# --- SIDEBAR: Global Parameters & Dynamic Rectangular Inputs ---
st.sidebar.subheader("📐 Rectangular Plant Dimensions")
grid_size_x = st.sidebar.slider("Floor Width (X) [Meters]", min_value=10, max_value=100, value=20)
grid_size_y = st.sidebar.slider("Floor Height (Y) [Meters]", min_value=10, max_value=100, value=20)

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
        st.subheader("🤖 Machine Geometry & Dynamic Standoffs")
        st.markdown("Configure custom width/height and asymmetric clearance standoffs (**so_px, so_nx, so_py, so_ny**) in meters:")
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
        
        col_metric1, col_metric2, col_metric3, col_metric4 = st.columns(4)
        
        init_cost = results["initial_transport_cost"]
        opt_cost = results["optimized_transport_cost"]
        reduction = ((init_cost - opt_cost) / init_cost) * 100 if init_cost > 0 else 0
        
        with col_metric1:
            st.metric("Initial Layout Cost", f"{init_cost:.2f} m·parts/hr")
        with col_metric2:
            st.metric("Optimized Layout Cost", f"{opt_cost:.2f} m·parts/hr", delta=f"-{reduction:.1f}% Layout Cost")
        with col_metric3:
            st.metric("Bottleneck Machine", results["dwell_time_analysis"]["bottleneck_machine"])
        with col_metric4:
            st.metric("Production Cycle Time", f"{results['dwell_time_analysis']['bottleneck_dwell_time']:.2f} mins/part")

        # --- Visual Post-Processing Plots ---
        col_plot1, col_plot2 = st.columns(2)
        
        # Plot 1: Floor Mapping & Safety Zones
        with col_plot1:
            st.markdown("### 🗺️ Floor Layout, Footprints & Asymmetric Standoffs")
            
            fig, ax = plt.subplots(figsize=(8, 8))
            ax.set_xlim(-2, grid_size_x + 4)
            ax.set_ylim(-2, grid_size_y + 4)
            ax.set_aspect('equal')
            ax.grid(True, which='both', linestyle='--', alpha=0.5)
            
            init_lookup = {m["id"]: m for m in machines_data}
            opt_machines = results["machines"]
            opt_lookup = {m["id"]: m for m in opt_machines}
            
            # Draw flow vector lines between optimized centers
            for flow in flows_data:
                src = flow["src_id"]
                dest = flow["dest_id"]
                vol = flow["volume"]
                if src in opt_lookup and dest in opt_lookup:
                    m1 = opt_lookup[src]
                    m2 = opt_lookup[dest]
                    
                    m1_x = m1.get("optimized_x", m1.get("x"))
                    m1_y = m1.get("optimized_y", m1.get("y"))
                    m2_x = m2.get("optimized_x", m2.get("x"))
                    m2_y = m2.get("optimized_y", m2.get("y"))
                    
                    width = max(1.0, min(5.0, vol / 30.0))
                    ax.annotate(
                        "",
                        xy=(m2_x, m2_y),
                        xytext=(m1_x, m1_y),
                        arrowprops=dict(arrowstyle="->", color="teal", alpha=0.5, lw=width, shrinkA=10, shrinkB=10)
                    )
            
            # Draw each Machine Footprint and its ISO Safety envelope
            for m in opt_machines:
                m_id = m["id"]
                
                # Retrieve dimensions and directional standoffs
                w = m.get("dim_x", init_lookup[m_id].get("dim_x", 1.0))
                h = m.get("dim_y", init_lookup[m_id].get("dim_y", 1.0))
                so_px = m.get("so_px", init_lookup[m_id].get("so_px", 0.0))
                so_nx = m.get("so_nx", init_lookup[m_id].get("so_nx", 0.0))
                so_py = m.get("so_py", init_lookup[m_id].get("so_py", 0.0))
                so_ny = m.get("so_ny", init_lookup[m_id].get("so_ny", 0.0))
                
                # Coordinates
                opt_x = m.get("optimized_x", m.get("x"))
                opt_y = m.get("optimized_y", m.get("y"))
                m_init = init_lookup.get(m_id, {"x": opt_x, "y": opt_y})
                
                # 1. Plot Initial Footprints (Dotted gray box)
                init_box = patches.Rectangle(
                    (m_init["x"] - w/2.0, m_init["y"] - h/2.0), w, h,
                    linewidth=1, linestyle=":", edgecolor="gray", facecolor="none", alpha=0.4
                )
                ax.add_patch(init_box)
                
                # 2. Plot Optimized Footprints (Solid colored box)
                border_color = "green" if m["is_safe"] else "red"
                fill_color = "lightgreen" if m["is_safe"] else "lightcoral"
                
                opt_box = patches.Rectangle(
                    (opt_x - w/2.0, opt_y - h/2.0), w, h,
                    linewidth=2, edgecolor=border_color, facecolor=fill_color, zorder=5, alpha=0.8
                )
                ax.add_patch(opt_box)
                
                # Label machine name and ID inside the rectangle
                ax.text(opt_x, opt_y, f"[{m_id}]\n{m['name']}", color="black", weight="bold", fontsize=8, ha="center", va="center", zorder=6)
                
                # 3. Draw Travel Trajectory Vectors
                ax.plot([m_init["x"], opt_x], [m_init["y"], opt_y], "r:", alpha=0.4)
                
                # 4. Draw Asymmetric Safe Bounding Box (Dashed Boundary Box: Standoffs + Dimensions)
                # Bottom-left coordinate: (Center_X - w/2 - Standoff_NX, Center_Y - h/2 - Standoff_NY)
                # Box Width: w + Standoff_NX + Standoff_PX
                # Box Height: h + Standoff_NY + Standoff_PY
                safety_box = patches.Rectangle(
                    (opt_x - w/2.0 - so_nx, opt_y - h/2.0 - so_ny),
                    w + so_nx + so_px, h + so_ny + so_py,
                    linewidth=1.5, linestyle="--", edgecolor=border_color, facecolor="none", zorder=3, alpha=0.9
                )
                ax.add_patch(safety_box)
                
            ax.set_title(f"Floor Map ({grid_size_x}m x {grid_size_y}m)\nSolid Box = Footprint, Dashed Box = Asymmetrical Safe Zone", fontsize=11)
            ax.set_xlabel("X coordinate (m)")
            ax.set_ylabel("Y coordinate (m)")
            st.pyplot(fig)
            
        # Plot 2: Manufacturing dwell time analysis & bottleneck
        with col_plot2:
            st.markdown("### ⏱️ Manufacturing Dwell Times & Throughput Cap")
            
            opt_machines = results["machines"]
            names = [m["name"] for m in opt_machines]
            
            dwells = [m["process_time"] + (m["setup_time"] / 50.0) for m in opt_machines]
            capacities = [60.0 / m["process_time"] if m["process_time"] > 0 else 0 for m in opt_machines]
            
            fig2, (ax_dwell, ax_cap) = plt.subplots(2, 1, figsize=(8, 8))
            
            colors = ["orange" if d == max(dwells) else "skyblue" for d in dwells]
            ax_dwell.barh(names, dwells, color=colors)
            ax_dwell.set_xlabel("Dwell Time per Part (minutes)")
            ax_dwell.set_title("Station Cycle Dwell times (Setup Amortized on 50 Parts)")
            ax_dwell.invert_yaxis()
            ax_dwell.grid(axis='x', linestyle='--', alpha=0.5)
            
            ax_cap.barh(names, capacities, color="lightgreen")
            ax_cap.set_xlabel("Maximum Processing Capacity (Parts / Hour)")
            ax_cap.set_title("Machine Hourly Throughput Limits")
            ax_cap.invert_yaxis()
            ax_cap.grid(axis='x', linestyle='--', alpha=0.5)
            
            plt.tight_layout()
            st.pyplot(fig2)

        # Output Detailed Post-Optimization Report Table
        st.markdown("### 📋 Station Safety Clearance & Compliance Detail Report")
        detailed_report = []
        for m in results["machines"]:
            opt_x = m.get("optimized_x", m.get("x"))
            opt_y = m.get("optimized_y", m.get("y"))
            w = m.get("dim_x", init_lookup[m["id"]].get("dim_x", 1.0))
            h = m.get("dim_y", init_lookup[m["id"]].get("dim_y", 1.0))
            so_px = m.get("so_px", init_lookup[m["id"]].get("so_px", 0.0))
            so_nx = m.get("so_nx", init_lookup[m["id"]].get("so_nx", 0.0))
            so_py = m.get("so_py", init_lookup[m["id"]].get("so_py", 0.0))
            so_ny = m.get("so_ny", init_lookup[m["id"]].get("so_ny", 0.0))
            
            detailed_report.append({
                "ID": m["id"],
                "Machine Name": m["name"],
                "Footprint Size": f"{w}m x {h}m",
                "Center Coord": f"({opt_x:.2f}, {opt_y:.2f})",
                "Standoffs (NX, PX, NY, PY)": f"({so_nx}m, {so_px}m, {so_ny}m, {so_py}m)",
                "Safe Footprint Envelope": f"({w + so_nx + so_px:.2f}m x {h + so_ny + so_py:.2f}m)",
                "Status": "✅ SAFE" if m["is_safe"] else "❌ WARNING: STANDOFF COLLISION / OUT-OF-BOUNDS"
            })
        st.table(pd.DataFrame(detailed_report))
