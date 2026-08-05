# app.py
import streamlit as st
import pandas as pd
from library_loader import get_default_machinery, get_default_lighting
from engine import run_layout_analysis, calculate_production_metrics
from visualization import draw_asme_drawing

st.set_page_size = "wide"
st.title("🏭 Factory Floor Optimizer & Compliance Suite")
st.markdown("Designed strictly to comply with **ASME Y14.1 Drawing Sheets** and **NJ Uniform Construction Code** Standards.")

# Sidebar Library Files
st.sidebar.header("📁 Material & Machinery Library")
machinery_lib = get_default_machinery()
lighting_lib = get_default_lighting()

st.sidebar.subheader("Default Machinery specifications")
st.sidebar.dataframe(pd.DataFrame(machinery_lib)[["Make", "Model", "Type", "Volume", "Yield"]])

# Setup Layout State
if "placed_machines" not in st.session_state:
    st.session_state.placed_machines = [
        {"Make": "Mazak", "Model": "Integrex i-200", "Width": 12, "Height": 10, "Standoff": 5.0, "Volume": 45, "Yield": 98.0, "x": 40.0, "y": 60.0},
        {"Make": "Arburg", "Model": "Allrounder 370", "Width": 15, "Height": 8, "Standoff": 4.0, "Volume": 60, "Yield": 95.0, "x": 100.0, "y": 45.0}
    ]
if "placed_conduits" not in st.session_state:
    st.session_state.placed_conduits = [
        {"label": "Power Main", "x": [40.0, 100.0], "y": [60.0, 45.0], "depth_in": 36, "warning_tape": True}
    ]

# Layout Placement Panel
col1, col2 = st.columns([2, 1])

with col2:
    st.header("⚙️ Layout Configuration")
    sheet_size = st.selectbox("Select ASME Sheet Boundary Size", ["A", "B", "C", "D"])
    show_safety = st.checkbox("Show Safety Heatmap underlay", value=True)
    show_contour = st.checkbox("Show Part Volume Contour plots")
    
    st.subheader("Add Conduit Routing")
    cx_lbl = st.text_input("Conduit Label", "Main Power Drop")
    cx_depth = st.number_input("Trench Burial Depth (inches)", min_value=12, max_value=60, value=36)
    cx_tape = st.checkbox("Contains Orange 4 mil Warning Tape", value=True)
    
    if st.button("Add Conduit"):
        st.session_state.placed_conduits.append({
            "label": cx_lbl, "x": [30.0, 80.0], "y": [30.0, 80.0],
            "depth_in": cx_depth, "warning_tape": cx_tape
        })
        st.experimental_rerun()

with col1:
    # Render Drawing
    fig = draw_asme_drawing(
        size_char=sheet_size,
        machines=st.session_state.placed_machines,
        conduits=st.session_state.placed_conduits,
        show_safety=show_safety,
        show_contour=show_contour
    )
    st.pyplot(fig)

# Analysis Panels
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
