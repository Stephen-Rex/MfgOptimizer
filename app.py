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

DEFAULT_VERTICES = [
    {"point_id": 1, "x": 3.0, "y": 3.0},
    {"point_id": 2, "x": 3.0, "y": 17.0},
    {"point_id": 3, "x": 10.0, "y": 17.0},
    {"point_id": 4, "x": 17.0, "y": 10.0},
    {"point_id": 5, "x": 17.0, "y": 3.0}
]

# --- Polyline Cartesian Mapper (Dynamic Vertex & Left Offset Support) ---
def get_offset_point_on_polyline(s, vertices, offset_dist):
    vx = [v["x"] for v in vertices]
    vy = [v["y"] for v in vertices]
    
    seg_lens = []
    for i in range(4):
        seg_lens.append(math.sqrt((vx[i+1]-vx[i])**2 + (vy[i+1]-vy[i])**2))
        
    current_s = 0.0
    for i in range(4):
        if s <= current_s + seg_lens[i]:
            ratio = (s - current_s) / seg_lens[i]
            px = vx[i] + ratio * (vx[i+1] - vx[i])
            py = vy[i] + ratio * (vy[i+1] - vy[i])
            
            dx, dy = vx[i+1] - vx[i], vy[i+1] - vy[i]
            ux, uy = dx / seg_lens[i], dy / seg_lens[i]
            nx, ny = -uy, ux # Perpendicular unit normal pointing to the left
            
            x = px + offset_dist * nx
            y = py + offset_dist * ny
            return x, y
        current_s += seg_lens[i]
        
    # Default last segment
    dx, dy = vx[4] - vx[3], vy[4] - vy[3]
    ux, uy = dx / seg_lens[3], dy / seg_lens[3]
    nx, ny = -uy, ux
    x = vx[4] + offset_dist * nx
    y = vy[4] + offset_dist * ny
    return x, y

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

def get_machine_offset(m, path_buffer):
    return path_buffer + (m["dim_y"] / 2.0) + m["so_ny"]

# --- Soft-Penalty Cost Evaluator ---
def evaluate_polyline_layout(machines, flows_list, vertices, path_buffer, grid_x, grid_y):
    transport_cost = 0.0
    penalty = 0.0
    
    for m in machines:
        offset_dist = get_machine_offset(m, path_buffer)
        m["x"], m["y"] = get_offset_point_on_polyline(m["s"], vertices, offset_dist)
        
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

def python_optimize_layout(machines_list, flows_list, vertices, path_buffer, grid_size_x=20, grid_size_y=20):
    machines = [dict(m) for m in machines_list]
    improved = True
    iterations = 0
    
    best_cost = evaluate_polyline_layout(machines, flows_list, vertices, path_buffer, grid_size_x, grid_size_y)
    
    while improved and iterations < 150:
        improved = False
        iterations += 1
        for i in range(1, len(machines)): # Machine 1 is fixed at s=0
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
                current_cost = evaluate_polyline_layout(machines, flows_list, vertices, path_buffer, grid_size_x, grid_size_y)
                
                if current_cost < best_cost:
                    best_cost = current_cost
                    best_ds = ds
                    improved = True
            
            machines[i]["s"] = original_s + best_ds
            
    # Calculate final status checks
    for i, m in enumerate(machines):
        offset_dist = get_machine_offset(m, path_buffer)
        m["x"], m["y"] = get_offset_point_on_polyline(m["s"], vertices, offset_dist)
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
        "initial_transport_cost": evaluate_polyline_layout(machines_list, flows_list, vertices, path_buffer, grid_size_x, grid_size_y),
        "optimized_transport_cost": best_cost,
        "iterations": iterations,
        "dwell_time_analysis": {
            "total_dwell_time": total_dwell,
            "bottleneck_machine": bottleneck_machine,
            "bottleneck_dwell_time": bottleneck_time
        },
        "machines": machines
    }

# --- C Code Template Generator ---
def generate_c_code_template(machines, flows, vertices, path_buffer, grid_size_x, grid_size_y):
    machines_str = ""
    for m in machines:
        machines_str += f'    {{{m["id"]}, "{m["name"]}", {m["s"]}, 0.0, 0.0, {m["dim_x"]}, {m["dim_y"]}, {m["so_px"]}, {m["so_nx"]}, {m["so_py"]}, {m["so_ny"]}, {m["process_time"]}, {m["setup_time"]}}},\n'
    machines_str = machines_str.rstrip(",\n")

    flows_str = ""
    for f in flows:
        flows_str += f'    {{{int(f["src_id"])}, {int(f["dest_id"])}, {f["volume"]}}},\n'
    flows_str = flows_str.rstrip(",\n")

    vx_str = ", ".join([f"{v['x']:.2f}" for v in vertices])
    vy_str = ", ".join([f"{v['y']:.2f}" for v in vertices])

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
    double s;             /* Cumulative distance along polyline */
    double x;             /* Calculated Cartesian X coordinate */
    double y;             /* Calculated Cartesian Y coordinate */
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

/* Dynamic vertices arrays generated from user GUI inputs */
double polyline_x[5] = {{{vx_str}}};
double polyline_y[5] = {{{vy_str}}};

double path_buffer_val = {path_buffer:.2f};

double calculate_center_distance(double x1, double y1, double x2, double y2) {{
    return sqrt((x1 - x2) * (x1 - x2) + (y1 - y2) * (y1 - y2));
}}

void get_offset_point_on_polyline(double s, double offset_dist, double *out_x, double *out_y) {{
    double seg_lens[4];
    int i;
    for (i = 0; i < 4; i++) {{
        seg_lens[i] = sqrt((polyline_x[i+1]-polyline_x[i])*(polyline_x[i+1]-polyline_x[i]) + 
                           (polyline_y[i+1]-polyline_y[i])*(polyline_y[i+1]-polyline_y[i]));
    }}
    
    double current_s = 0.0;
    for (i = 0; i < 4; i++) {{
        if (s <= current_s + seg_lens[i]) {{
            double ratio = (s - current_s) / seg_lens[i];
            double px = polyline_x[i] + ratio * (polyline_x[i+1] - polyline_x[i]);
            double py = polyline_y[i] + ratio * (polyline_y[i+1] - polyline_y[i]);
            
            double dx = polyline_x[i+1] - polyline_x[i];
            double dy = polyline_y[i+1] - polyline_y[i];
            double ux = dx / seg_lens[i];
            double uy = dy / seg_lens[i];
            
            double nx = -uy;
            double ny = ux;
            
            *out_x = px + offset_dist * nx;
            *out_y = py + offset_dist * ny;
            return;
        }}
        current_s += seg_lens[i];
    }}
    *out_x = polyline_x[4];
    *out_y = polyline_y[4];
}}

double get_machine_offset(Machine m, double path_buffer) {{
    return path_buffer + (m.dim_y / 2.0) + m.so_ny;
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
                    best_ds = ds;
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
st.markdown("## 🏭 Custom Polyline Material Flow Assembly Optimizer")
st.markdown("Specify a custom 5-point polyline to define your conveyor transit path. The GUI maps directional safety envelopes and manned truck corridors centered along your custom route.")

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
if "vertices_df" not in st.session_state:
    st.session_state.vertices_df = pd.DataFrame(DEFAULT_VERTICES)

# --- TABS Layout ---
tab1, tab2, tab3 = st.tabs(["📋 Configure Parameters", "👁️ Generated C Source", "📊 Execution & Visual Analytics"])

with tab1:
    col_v, col_m, col_f = st.columns([1, 1.2, 0.8])
    with col_v:
        st.subheader("📍 Custom Polyline Vertices (5 Points)")
        st.markdown("Edit coordinates to dynamically define your raw material conveyor path:")
        edited_vertices = st.data_editor(
            st.session_state.vertices_df,
            num_rows="fixed", # Locked at exactly 5 points
            use_container_width=True,
            key="vertices_editor"
        )
    with col_m:
        st.subheader("🤖 Machine Spacings along Path")
        st.markdown("Configure cumulative spacings `s` (m) and footprints:")
        edited_machines = st.data_editor(
            st.session_state.machines_df,
            num_rows="dynamic",
            use_container_width=True,
            key="machine_editor"
        )
    with col_f:
        st.subheader("🔄 Material Flow Densities")
        st.markdown("Specify station conveyor volumes:")
        edited_flows = st.data_editor(
            st.session_state.flows_df,
            num_rows="dynamic",
            use_container_width=True,
            key="flow_editor"
        )

st.session_state.machines_df = edited_machines
st.session_state.flows_df = edited_flows
st.session_state.vertices_df = edited_vertices

# Extract vertices to list
vertices_list = edited_vertices.to_dict(orient="records")

c_source_code = generate_c_code_template(
    edited_machines.to_dict(orient="records"),
    edited_flows.to_dict(orient="records"),
    vertices_list,
    path_buffer,
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
                    results = python_optimize_layout(machines_data, flows_data, vertices_list, path_buffer, grid_size_x, grid_size_y)
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
                        results = python_optimize_layout(machines_data, flows_data, vertices_list, path_buffer, grid_size_x, grid_size_y)
                        execution_msg = "Python Simulation Fallback (Execution Failure)"
            except Exception as e:
                st.error(f"Could not execute C compiler subprocess: {e}")
                st.warning("IT restricts execution. Defaulting to Python Simulation Fallback.")
                results = python_optimize_layout(machines_data, flows_data, vertices_list, path_buffer, grid_size_x, grid_size_y)
                execution_msg = "Python Simulation Fallback"
        else:
            results = python_optimize_layout(machines_data, flows_data, vertices_list, path_buffer, grid_size_x, grid_size_y)
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
            
            # --- THE BLUEPRINT ENHANCEMENT ---
            # Set canvas outer background to neutral light gray
            fig.patch.set_facecolor('#EFEFEF')
            # Set the room area background (inside ax) to deep blueprint blue (#002D62)
            # Anything outside coordinates (0,0) and (grid_size_x, grid_size_y) represents "out of bounds" and has no blue color!
            ax.set_facecolor('#D0D0D0') # Background of plot outside active floor area
            
            # Add traditional blueprint-blue background patch for active floor space
            blueprint_bg = patches.Rectangle((0.0, 0.0), grid_size_x, grid_size_y, facecolor='#002D62', edgecolor='white', linewidth=3, zorder=0, label="Facility Walls")
            ax.add_patch(blueprint_bg)
            
            # Configure custom white drafting-style grid lines
            ax.grid(True, which='both', color='white', linestyle='--', alpha=0.3, zorder=0.5)
            # --- END OF BLUEPRINT ENHANCEMENT ---

            # 1. Draw custom 5-point Polyline Path inputted by user (Conveyor backbone)
            vx = [v["x"] for v in vertices_list]
            vy = [v["y"] for v in vertices_list]
            # Drawn in light gray to stand out beautifully on dark blueprint blue
            ax.plot(vx, vy, color="#D3D3D3", linewidth=4, zorder=1, label="Conveyor Backbone")
            
            # 2. Draw Parallel Forklift Lanes & Safety boundaries offset on both sides of the path
            for i in range(len(vx) - 1):
                x1, y1 = vx[i], vy[i]
                x2, y2 = vx[i+1], vy[i+1]
                
                dx, dy = x2 - x1, y2 - y1
                length = math.sqrt(dx**2 + dy**2)
                if length > 1e-5:
                    ux, uy = dx / length, dy / length
                    nx, ny = -uy, ux # Normal vector perpendicular to segment
                    
                    # Left boundary line (dashed yellow)
                    lx1, ly1 = x1 + path_buffer * nx, y1 + path_buffer * ny
                    lx2, ly2 = x2 + path_buffer * nx, y2 + path_buffer * ny
                    ax.plot([lx1, lx2], [ly1, ly2], color="#FFD700", linestyle="--", alpha=0.8, zorder=2, label="Standoff Lane Marking" if i == 0 else "")
                    
                    # Right boundary line (dashed yellow)
                    rx1, ry1 = x1 - path_buffer * nx, y1 - path_buffer * ny
                    rx2, ry2 = x2 - path_buffer * nx, y2 - path_buffer * ny
                    ax.plot([rx1, rx2], [ry1, ry2], color="#FFD700", linestyle="--", alpha=0.8, zorder=2)

            # 3. Draw each Machine Footprint and its safety boundaries along the custom path
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
                
                # Fetch initial position coordinate
                m_init_offset = get_machine_offset(init_lookup[m_id], path_buffer)
                m_init_x, m_init_y = get_offset_point_on_polyline(init_lookup[m_id]["s"], vertices_list, m_init_offset)
                
                # Plot Initial Footprints (Dotted gray box)
                init_box = patches.Rectangle(
                    (m_init_x - w/2.0, m_init_y - h/2.0), w, h,
                    linewidth=1, linestyle=":", edgecolor="#A9A9A9", facecolor="none", alpha=0.4, zorder=3
                )
                ax.add_patch(init_box)
                
                # Plot Optimized Footprints (Solid colored box)
                border_color = "#32CD32" if m["is_safe"] else "#FF3333" # Bright lime-green or neon-red
                fill_color = "lightgreen" if m["is_safe"] else "lightcoral"
                
                opt_box = patches.Rectangle(
                    (opt_x - w/2.0, opt_y - h/2.0), w, h,
                    linewidth=2, edgecolor=border_color, facecolor=fill_color, zorder=5, alpha=0.8
                )
                ax.add_patch(opt_box)
            # --- UPGRADE 1: Check toggled state for machine name display ---
                if show_machine_names:
                    label_text = f"[{m_id}]\n{m['name']}"
                else:
                    label_text = f"[{m_id}]"
                    
                ax.text(opt_x, opt_y, label_text, color="black", weight="bold", fontsize=8, ha="center", va="center", zorder=6)
                
                ax.plot([m_init_x, opt_x], [m_init_y, opt_y], color="#FF4500", linestyle=":", alpha=0.5, zorder=4)
                
                safety_box = patches.Rectangle(
                    (opt_x - w/2.0 - so_nx, opt_y - h/2.0 - so_ny),
                    w + so_nx + so_px, h + so_ny + so_py,
                    linewidth=1.2, linestyle="--", edgecolor=border_color, facecolor="none", zorder=3, alpha=0.8
                )
                ax.add_patch(safety_box)
                
            ax.set_title(f"Dynamic Polyline Layout Map ({grid_size_x}m x {grid_size_y}m)\nDashed Yellow = Manned Corridor ({path_buffer}m)", fontsize=11)
            ax.set_xlabel("X coordinate (m)")
            ax.set_ylabel("Y coordinate (m)")
            
            # --- UPGRADE 2: Matplotlib Plot Legend stating ID and machine name under the plot ---
            legend_labels_list = [f"[{m['id']}] {m['name']}" for m in opt_machines]
            legend_str = "  |  ".join(legend_labels_list)
            fig.text(0.5, -0.05, f"Legend:\n{legend_str}", ha='center', fontsize=9, weight='bold', style='italic', bbox=dict(boxstyle='round,pad=0.5', facecolor='#F0F2F6', edgecolor='#1F2937', alpha=0.9))
            
            st.pyplot(fig)
            
            # --- UPGRADE 3: Streamlit Layout Legend underneath the plot ---
            st.markdown("#### 🔑 Layout ID Legend")
            st.markdown(" | ".join([f"**[{m['id']}]** {m['name']}" for m in opt_machines]))



                
            # Label inside the rectangle
            ax.text(opt_x, opt_y, f"[{m_id}]\n{m['name']}", color="black", weight="bold", fontsize=8, ha="center", va="center", zorder=6)
            # Draw Travel Vectors
            ax.plot([m_init_x, opt_x], [m_init_y, opt_y], color="#FF4500", linestyle=":", alpha=0.5, zorder=4) # Orange dotted vector
                
            # Draw Asymmetric Safe Bounding Box (Standoff boundaries)
            safety_box = patches.Rectangle(
                (opt_x - w/2.0 - so_nx, opt_y - h/2.0 - so_ny),
                w + so_nx + so_px, h + so_ny + so_py,
                linewidth=1.2, linestyle="--", edgecolor=border_color, facecolor="none", zorder=3, alpha=0.8
            )
            ax.add_patch(safety_box)
                
            ax.set_title(f"Dynamic Polyline Layout Map ({grid_size_x}m x {grid_size_y}m)\nDashed Yellow = Manned Corridor ({path_buffer}m)", fontsize=11)
            ax.set_xlabel("X coordinate (m)")
            ax.set_ylabel("Y coordinate (m)")
            st.pyplot(fig)
            
        # Plot 2: Manufacturing dwell time analysis & bottleneck
        with col_plot2:
            st.markdown("### ⏱️ Manufacturing Dwell Times & Throughput Cap")
            
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
        for m in opt_machines:
            opt_x = m.get("optimized_x", m.get("x"))
            opt_y = m.get("optimized_y", m.get("y"))
            w = m.get("dim_x", init_lookup[m["id"]].get("dim_x", 1.0))
            h = m.get("dim_y", init_lookup[m["id"]].get("dim_y", 1.0))
            so_px = m.get("so_px", init_lookup[m["id"]].get("so_px", 0.0))
            so_nx = m.get("so_nx", init_lookup[m["id"]].get("so_nx", 0.0))
            so_py = m.get("so_py", init_lookup[m["id"]].get("so_py", 0.0))
            so_ny = m.get("so_ny", init_lookup[m["id"]].get("so_ny", 0.0))
            
            # Recalculate overlaps
            is_overlapping = False
            for other in opt_machines:
                if m["id"] != other["id"]:
                    ox = other.get("optimized_x", other.get("x"))
                    oy = other.get("optimized_y", other.get("y"))
                    
                    other_init = init_lookup[other["id"]]
                    other_w = other_init.get("dim_x", 1.0)
                    other_h = other_init.get("dim_y", 1.0)
                    other_so_px = other_init.get("so_px", 0.0)
                    other_so_nx = other_init.get("so_nx", 0.0)
                    other_so_py = other_init.get("so_py", 0.0)
                    other_so_ny = other_init.get("so_ny", 0.0)
                    
                    if check_safe_overlap(opt_x, opt_y, w, h, so_px, so_nx, so_py, so_ny,
                                       ox, oy, other_w, other_h,
                                       other_so_px, other_so_nx, other_so_py, other_so_ny):
                        is_overlapping = True
                        break
                        
            status = "✅ COMPLIANT"
            if is_overlapping:
                status = "❌ FAIL: STANDOFF ZONE OVERLAP"
            elif is_safe_out_of_bounds(opt_x, opt_y, w, h, so_px, so_nx, so_py, so_ny, grid_size_x, grid_size_y):
                status = "❌ FAIL: OUT-OF-BOUNDS PROTRUSION"
                
            detailed_report.append({
                "ID": m["id"],
                "Machine Name": m["name"],
                "Polyline Spacing (s)": f"{m['s']:.1f} m",
                "Center Coord": f"({opt_x:.2f}, {opt_y:.2f})",
                "Standoffs (NX, PX, NY, PY)": f"({so_nx}m, {so_px}m, {so_ny}m, {so_py}m)",
                "Safe Footprint Envelope": f"({w + so_nx + so_px:.2f}m x {h + so_ny + so_py:.2f}m)",
                "Compliance Status": status
            })
        st.table(pd.DataFrame(detailed_report))
