# app.py
import streamlit as st
import pandas as pd
from library_loader import get_default_machinery, get_default_lighting
from engine import run_layout_analysis, calculate_production_metrics
from visualization import draw_asme_drawing

# Set page configuration safely
st.set_page_config(layout="wide")

st.title("🏭 Factory Floor Optimizer & Compliance Suite")
st.markdown("Designed strictly to comply with **ASME Y14.1 Drawing Sheets** and **NJ Uniform Construction Code** Standards.")

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
st.sidebar.dataframe(df_lighting[["Make", "Brand", "Type", "Wattage", "Lumens", "Lux"]])

# Setup Session State for Placed Items
if "placed_machines" not in st.session_state:
    st.session_state.placed_machines = [
        {"Make": "Mazak", "Model": "Integrex i-200", "Width": 12.0, "Height": 10.0, "Standoff": 5.0, "Volume": 45, "Yield": 98.0, "x": 40.0, "y": 60.0},
        {"Make": "Arburg", "Model": "Allrounder 370", "Width": 15.0, "Height": 8.0, "Standoff": 4.0, "Volume": 60, "Yield": 95.0, "x": 100.0, "y": 45.0}
    ]
if "placed_lighting" not in st.session_state:
    st.session_state.placed_lighting = [
        {"Make": "Lithonia", "Brand": "I-Beam", "Type": "LED", "Wattage": 150.0, "x": 50.0, "y": 80.0, "Lumens": 18000}
    ]
if "placed_conduits" not in st.session_state:
    st.session_state.placed_conduits = [
        {"label": "Power Main", "x": [40.0, 100.0], "y": [60.0, 45.0], "depth_in": 36, "warning_tape": True}
    ]

# Layout Placement Panel
col1, col2 = st.columns([2, 1])

with col2:
    st.header("⚙️ Interactive Floor Layout Designer")
    sheet_size = st.selectbox("Select ASME Sheet Boundary Size", ["A", "B", "C", "D"])
    show_safety = st.checkbox("Show Safety Heatmap underlay", value=True)
    show_contour = st.checkbox("Show Part Volume Contour plots")
    
    # 1. Machinery Placement form
    st.subheader("🤖 Place Machine from Library")
    machine_options = [f"{m['Make']} {m['Model']} ({m['Type']})" for m in machinery_lib]
    selected_m_idx = st.selectbox("Choose Machine", range(len(machine_options)), format_func=lambda x: machine_options[x])
    mx_coord = st.number_input("Target Placement X (ft)", min_value=0.0, max_value=200.0, value=70.0, key="mx")
    my_coord = st.number_input("Target Placement Y (ft)", min_value=0.0, max_value=200.0, value=50.0, key="my")
    
    if st.button("Drop Machine onto Floor"):
        spec = machinery_lib[selected_m_idx].copy()
        spec["x"] = mx_coord
        spec["y"] = my_coord
        st.session_state.placed_machines.append(spec)
        st.success(f"Placed {spec['Make']} {spec['Model']} at ({mx_coord}, {my_coord})!")
        st.rerun() if hasattr(st, "rerun") else st.experimental_rerun()

    # 2. Modify or Delete Placed Machinery
    if len(st.session_state.placed_machines) > 0:
        st.subheader("🛠️ Modify or Delete Placed Machinery")
        placed_options = [
            f"{i+1}: {m['Make']} {m['Model']} at ({m['x']:.1f} ft, {m['y']:.1f} ft)" 
            for i, m in enumerate(st.session_state.placed_machines)
        ]
        selected_placed_idx = st.selectbox(
            "Select Machine on Floor to Edit", 
            range(len(placed_options)), 
            format_func=lambda x: placed_options[x]
        )
        
        mach = st.session_state.placed_machines[selected_placed_idx]
        
        # Position modification fields populated with active machine's coordinates
        edit_x = st.number_input("Adjust Coordinate X (ft)", min_value=0.0, max_value=200.0, value=float(mach["x"]), key=f"edit_x_{selected_placed_idx}")
        edit_y = st.number_input("Adjust Coordinate Y (ft)", min_value=0.0, max_value=200.0, value=float(mach["y"]), key=f"edit_y_{selected_placed_idx}")
        
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
                st.warning(f"Removed {removed['Make']} {removed['Model']} from layout.")
                st.rerun() if hasattr(st, "rerun") else st.experimental_rerun()
        
    # 3. Lighting Placement Form
    st.subheader("💡 Place Light from Library")
    light_options = [f"{l['Make']} {l['Brand']} ({l['Type']})" for l in lighting_lib]
    selected_l_idx = st.selectbox("Choose Lighting Fixture", range(len(light_options)), format_func=lambda x: light_options[x])
    lx_coord = st.number_input("Placement X (ft)", min_value=0.0, max_value=200.0, value=50.0, key="lx")
    ly_coord = st.number_input("Placement Y (ft)", min_value=0.0, max_value=200.0, value=80.0, key="ly")
    
    if st.button("Drop Light onto Floor"):
        spec_l = lighting_lib[selected_l_idx].copy()
        spec_l["x"] = lx_coord
        spec_l["y"] = ly_coord
        st.session_state.placed_lighting.append(spec_l)
        st.success(f"Placed Lighting Fixture at ({lx_coord}, {ly_coord})!")
        st.rerun() if hasattr(st, "rerun") else st.experimental_rerun()

    # 4. Conduit Routing
    st.subheader("🔌 Add Conduit Run")
    cx_lbl = st.text_input("Conduit Label", "Main Power Drop")
    cx_depth = st.number_input("Trench Burial Depth (inches)", min_value=12, max_value=60, value=36)
    cx_tape = st.checkbox("Contains Orange 4 mil Warning Tape", value=True)
    
    if st.button("Route Conduit Path"):
        st.session_state.placed_conduits.append({
            "label": cx_lbl, 
            "x": [30.0, 80.0], 
            "y": [30.0, 80.0],
            "depth_in": cx_depth, 
            "warning_tape": cx_tape
        })
        st.rerun() if hasattr(st, "rerun") else st.experimental_rerun()

with col1:
    # Render ASME Drawing Sheet with updated configurations
    fig = draw_asme_drawing(
        size_char=sheet_size,
        machines=st.session_state.placed_machines,
        conduits=st.session_state.placed_conduits,
        show_safety=show_safety,
        show_contour=show_contour
    )
    st.pyplot(fig)

# Analysis & Compliance Reporting
st.header("📈 Layout Analytics & OSHA / NJ-UCC Verification")

warnings = run_layout_analysis(st.session_state.placed_machines, st.session_state.placed_conduits)
metrics = calculate_production_metrics(st.session_state.placed_machines)

stat1, stat2, stat3 = st.columns(3)
with stat1:
    st.metric("Line Bottleneck", metrics.get("Bottleneck Machine", "N/A"))
with stat2:
    st.metric("Line Balance Index", metrics.get("Line Balance Efficiency", "N/A"))
with stat3:
    st.metric("UDP Power Sleep Savings", metrics.get("UDP Switch-Off Savings", "N/A"))

if warnings:
    st.error("⚠️ Spatial & Regulatory Warnings Found:")
    for warn in warnings:
        st.warning(warn)
else:
    st.success("✅ Layout fully meets OSHA Clearance and NJ-UCC Section 704 Electrical Standards!")

st.info(f"⚡ Estimated Throughput (MPDI Bucket Brigade Dynamic Model): {metrics.get('Bucket Brigade Throughput', '0')}")
