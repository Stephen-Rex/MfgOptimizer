import streamlit as st
import subprocess
import os
import re
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as patches

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="Factory Floor Optimizer GUI",
    page_icon="🤖",
    layout="wide"
)

st.title("🤖 Factory Floor Optimizer — Parameter Panel & Post-Processor")
st.markdown("""
This web application allows engineers to dynamically tune robotic efficiency and safety bounds in the **C Optimization Backend** and visualizes the optimized layout post-processing predictions.
""")

# --- SIDEBAR PARAMETERS ---
st.sidebar.header("🛠️ Optimization Parameters")

automation_factor = st.sidebar.slider(
    "Robotics Automation Factor (Speedup)",
    min_value=0.0,
    max_value=2.0,
    value=0.5,
    step=0.05,
    help="Higher values exponentially reduce the process dwell-times of robotic nodes."
)

safety_expansion = st.sidebar.slider(
    "Robotics Safety Clearance Expansion",
    min_value=0.5,
    max_value=3.0,
    value=1.2,
    step=0.05,
    help="Scales the dynamic robotic reach-zone safety buffer to prevent human collisions."
)

iterations = st.sidebar.select_slider(
    "Optimizer Iterations",
    options=[5000, 10000, 50000, 100000, 200000, 500000],
    value=100000,
    help="Higher iterations result in highly optimized placement but take slightly longer."
)

compile_backend = st.sidebar.checkbox("Re-compile C Backend on Run", value=True)

# --- RUN OPTIMIZER LOGIC ---
if st.button("🚀 Run Layout Placement Optimization", type="primary"):
    
    # 1. Compilation Step (Optional)
    if compile_backend:
        st.info("Compiling C-backend optimization engine...")
        compile_process = subprocess.run(
            ["gcc", "optimizer.c", "-o", "optimizer", "-lm"], 
            capture_output=True, 
            text=True
        )
        if compile_process.returncode != 0:
            st.error(f"Compilation Failed:\n{compile_process.stderr}")
            st.stop()
        else:
            st.success("Compilation successful!")

    # Check if executable exists
    executable = "./optimizer" if os.name != 'nt' else "optimizer.exe"
    if not os.path.exists(executable):
        st.error("Executable binary not found. Please compile the C file first.")
        st.stop()

    # 2. Execution Step
    st.info("Executing Hill-Climbing Layout Optimization...")
    with st.spinner("Processing coordinate configurations..."):
        run_process = subprocess.run(
            [executable, str(automation_factor), str(safety_expansion), str(iterations)],
            capture_output=True,
            text=True
        )
        
        if run_process.returncode != 0:
            st.error(f"Optimizer Execution Failed:\n{run_process.stderr}")
            st.stop()
        
        output_text = run_process.stdout

    # --- 3. POST-PROCESSING & REGEX PARSING ---
    # Parse floor dimensions
    dims = re.search(r"Floor Dimensions:\s+([\d.]+)m x ([\d.]+)m", output_text)
    floor_w = float(dims.group(1)) if dims else 30.0
    floor_h = float(dims.group(2)) if dims else 20.0

    # Parse Flow Cost and Safety Penalty
    flow_cost_match = re.search(r"Total Workflow Flow Cost:\s+([\d.]+)", output_text)
    safety_penalty_match = re.search(r"Safety Violation Penalty Score:\s+([\d.]+)", output_text)
    
    flow_cost = float(flow_cost_match.group(1)) if flow_cost_match else 0.0
    safety_penalty = float(safety_penalty_match.group(1)) if safety_penalty_match else 0.0

    # Parse Machine Table
    machine_pattern = re.compile(
        r"^\s*(\d+)\s+([\w\s]+?)\s{2,}([\d.-]+)\s+([\d.-]+)\s+(\w+)\s+([\d.-]+)\s+([\d.-]+)", 
        re.MULTILINE
    )
    machines = []
    for match in machine_pattern.finditer(output_text):
        machines.append({
            "ID": int(match.group(1)),
            "Name": match.group(2).strip(),
            "X": float(match.group(3)),
            "Y": float(match.group(4)),
            "Type": match.group(5),
            "Dwell Time (min)": float(match.group(6)),
            "Safety Envelope (m)": float(match.group(7))
        })
    
    df_machines = pd.DataFrame(machines)

    # --- 4. PRESENT RESULTS IN GUI ---
    st.success("Optimization Run Completed successfully!")
    
    # KPI Columns
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Workflow Flow Cost", f"{flow_cost:,.2f} units", help="Lower is better.")
    with col2:
        st.metric(
            "Safety Violation Penalty Score", 
            f"{safety_penalty:,.2f}", 
            delta="Safe Layout" if safety_penalty == 0 else "Violations Present",
            delta_color="normal" if safety_penalty == 0 else "inverse"
        )
    with col3:
        st.metric("Optimized Machinery Nodes", len(df_machines))

    # Layout Visualizer Section (Matplotlib Post-Processing)
    st.header("🗺️ Optimized Factory Layout Visualizer")
    
    fig, ax = plt.subplots(figsize=(12, 8))
    ax.set_xlim(0, floor_w)
    ax.set_ylim(0, floor_h)
    ax.set_aspect('equal')
    ax.set_xlabel("Floor Width (meters)")
    ax.set_ylabel("Floor Height (meters)")
    ax.grid(True, linestyle="--", alpha=0.5)
    ax.set_title(f"2D Factory Layout Plan ({floor_w}m x {floor_h}m)", fontsize=14, fontweight='bold')

    # Draw sequential material flow lines
    if len(df_machines) >= 4:
        for idx in range(len(df_machines) - 1):
            start_m = df_machines.iloc[idx]
            end_m = df_machines.iloc[idx + 1]
            ax.annotate(
                "", 
                xy=(end_m["X"], end_m["Y"]), 
                xytext=(start_m["X"], start_m["Y"]),
                arrowprops=dict(arrowstyle="->", color="gray", lw=2, ls="--", alpha=0.7)
            )

    # Draw individual machinery footprints and safety sweeps
    for idx, row in df_machines.iterrows():
        w, h = 2.0, 2.0
        if "Welder" in row["Name"]:
            w, h = 3.0, 3.0
        elif "Assembly" in row["Name"]:
            w, h = 4.0, 4.0

        # Compute bottom-left coordinate of the machine rectangle
        rect_x = row["X"] - w / 2.0
        rect_y = row["Y"] - h / 2.0

        is_robotic = row["Type"] == "Robotic"
        color = "#1f77b4" if not is_robotic else "#ff7f0e"

        # 1. Draw Physical Machine
        rect = patches.Rectangle((rect_x, rect_y), w, h, linewidth=2, edgecolor=color, facecolor=color, alpha=0.6)
        ax.add_patch(rect)
        
        # 2. Post-Process Safety Clearance: Draw Dynamic Clearance Zone (Safety Envelope)
        safety_r = row["Safety Envelope (m)"]
        safety_circle = patches.Circle((row["X"], row["Y"]), safety_r, linewidth=1.5, edgecolor=color, facecolor=color, fill=True, alpha=0.15, linestyle=':')
        ax.add_patch(safety_circle)

        # 3. Label Machine
        ax.text(row["X"], row["Y"], f"{row['Name']}\n({row['X']:.1f}, {row['Y']:.1f})", 
                color="black", ha="center", va="center", fontsize=9, fontweight='bold')

    # Add legend
    legend_elements = [
        patches.Patch(facecolor='#1f77b4', edgecolor='#1f77b4', alpha=0.6, label='Standard Machine footprint'),
        patches.Patch(facecolor='#ff7f0e', edgecolor='#ff7f0e', alpha=0.6, label='Robotic Machine footprint'),
        patches.Patch(facecolor='grey', edgecolor='grey', alpha=0.15, linestyle=':', label='Robotic Safety clearance boundary')
    ]
    ax.legend(handles=legend_elements, loc='upper right')
    
    st.pyplot(fig)

    # --- 5. DATA TABLES & CSV EXPORT ---
    st.header("📋 Machine Coordinates & Processing Metrics")
    st.dataframe(df_machines, use_container_width=True)

    # Allow downloading data as CSV
    csv_data = df_machines.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="📥 Export Optimized Layout Configurations to CSV",
        data=csv_data,
        file_name="optimized_factory_layout.csv",
        mime="text/csv"
    )

    # Output log expander
    with st.expander("📝 View Raw C Backend Optimizer Console Output"):
        st.code(output_text, language="text")
