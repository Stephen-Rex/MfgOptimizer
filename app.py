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

# --- Default Datasets ---
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
    
    for m in machines:
        m["x"], m["y"] = get_point_on_polyline(m["s"], grid_x, grid_y)
        
    machines_dict = {m["id"]: m for m in machines}
    
    for flow in flows_list:
        src, dest = flow["src_id"], flow["dest_id"]
        if src in machines_dict and dest in machines_dict:
            m1, m2 = machines_dict[src], machines_dict[dest]
            dist = calculate_center_distance(m1["x"], m1["y"], m2["x"], m2["y"])
            transport_cost += dist * flow["volume"]
            
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

# --- C Code Template String ---
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

double evaluate_polyline_layout_with_penalties(void) {{
    double transport_cost = 0.0;
    double penalty = 0.0;
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
            transport_cost += dist * flows[i].volume;
        }}
    }}
    for (i = 0; i < num_machines; i++) {{
        if (is_safe_out_of_bounds(machines[i].x, machines[i].y, machines[i].dim_x, machines[i].dim_y,
                                  machines[i].so_px, machines[i].so_nx, machines[i].so_py, machines[i].so_ny)) {{
            penalty += 10000.0;
        }}
        for (j = i + 1; j < num_machines; j++) {{
            if (check_safe_overlap(machines[i].x, machines[i].y, machines[i].dim_x, machines[i].dim_y,
                                   machines[i].so_px, machines[i].so_nx, machines[i].so_py, machines[i].so_ny,
                                   machines[j].x, machines[j].y, machines[j].dim_x, machines[j].dim_y,
                                   machines[j].so_px, machines[j].so_nx, machines[j].so_py, machines[j].so_ny)) {{
                penalty += 20000.0;
            }}
        }}
    }}
    return transport_cost + penalty;
}}

void optimize_placement(void) {{
    double best_cost = evaluate_polyline_layout_with_penalties();
    bool improved = true;
    int iterations = 0;
    int i;
    double ds;
    while (improved && iterations < 100) {{
        improved = false;
        iterations++;
        for (i = 1; i < num_machines; i++) {{
            double original_s = machines[i].s;
            double best_ds = 0.0;
            for (ds = -3.0; ds <= 3.0; ds += 0.5) {{
                if (ds == 0.0) continue;
                double candidate_s = original_s + ds;
                double min_s = machines[i-1].s + (machines[i-1].dim_x + machines[i].dim_x)/2.0;
                if (candidate_s < min_s) continue;
                machines[i].s = candidate_s;
                double current_cost = evaluate_polyline_layout_with_penalties();
                if (current_cost < best_cost) {{
                    best_cost = current_cost;
                    best_dx = ds;
                    improved = true;
                }}
            }}
            machines[i].s = original_s + best_ds;
        }}
    }}
}}

int main(void) {{
    double init_cost = evaluate_polyline_layout_with_penalties();
    optimize_placement();
    double opt_cost = evaluate_polyline_layout_with_penalties();
    FILE *fp = fopen("layout_output.json", "w");
    if (!fp) return 1;
    fprintf(fp, "{{\n");
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
  
