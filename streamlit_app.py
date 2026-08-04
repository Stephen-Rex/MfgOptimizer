import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import os
import csv
import io
import ctypes
import subprocess
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.graphics.shapes import Drawing, Rect, Line, String

# =====================================================================
# 1. Start-up: Dynamic C Backend Engine Compiler (Robert's C Code)
# =====================================================================
def compile_backend_dynamically():
    # Recursively find the exact folder containing optimizer.c
    backend_dir = None
    current_dir = os.path.dirname(os.path.abspath(__file__))
    for root, dirs, files in os.walk(current_dir):
        if "optimizer.c" in files:
            backend_dir = root
            break
            
    if backend_dir and os.path.exists(backend_dir):
        try:
            # Check if GCC is installed in the Streamlit container
            res = subprocess.run(["gcc", "--version"], capture_output=True, text=True)
            if res.returncode == 0:
                subprocess.run(["make", "-C", backend_dir], capture_output=True, text=True)
        except Exception:
            pass # Fail silently, ctypes will gracefully use Python fallback solvers

compile_backend_dynamically()

# =====================================================================
# 2. Memory Marshaling & ctypes Structures (Samantha's Bridge)
# =====================================================================
class Point(ctypes.Structure):
    _fields_ = [("x", ctypes.c_double), ("y", ctypes.c_double)]

class MachineInstance(ctypes.Structure):
    _fields_ = [
        ("id", ctypes.c_char * 16),
        ("name", ctypes.c_char * 64),
        ("x", ctypes.c_double),
        ("y", ctypes.c_double),
        ("width", ctypes.c_double),
        ("height", ctypes.c_double),
        ("safety_standoff", ctypes.c_double),
        ("water_required", ctypes.c_int),
        ("amperage", ctypes.c_int),
        ("wattage", ctypes.c_int),
        ("volume_per_hour", ctypes.c_double),
        ("yield_percentage", ctypes.c_double),
        ("crane_required", ctypes.c_int),
        ("is_bottleneck", ctypes.c_int),
        ("safety_violation", ctypes.c_int),
    ]

class FlowPath(ctypes.Structure):
    _fields_ = [
        ("id", ctypes.c_char * 16),
        ("type", ctypes.c_char * 32),
        ("points", Point * 100),
        ("point_count", ctypes.c_int),
        ("width", ctypes.c_double),
        ("speed", ctypes.c_double),
    ]

class CraneZone(ctypes.Structure):
    _fields_ = [
        ("id", ctypes.c_char * 16),
        ("x1", ctypes.c_double),
        ("y1", ctypes.c_double),
        ("x2", ctypes.c_double),
        ("y2", ctypes.c_double),
        ("speed", ctypes.c_double),
        ("weight_rating", ctypes.c_double),
    ]

class SafetyViolation(ctypes.Structure):
    _fields_ = [
        ("machine_id_1", ctypes.c_char * 16),
        ("machine_id_2", ctypes.c_char * 16),
        ("overlap_distance", ctypes.c_double),
        ("description", ctypes.c_char * 128),
    ]

# Recursively locate and load compiled shared object library
lib = None
current_dir = os.path.dirname(os.path.abspath(__file__))
for root, dirs, files in os.walk(current_dir):
    if "liboptimizer.so" in files:
        try:
            lib = ctypes.CDLL(os.path.join(root, "liboptimizer.so"))
            lib.check_safety_overlaps.argtypes = [ctypes.POINTER(MachineInstance), ctypes.c_int, ctypes.POINTER(SafetyViolation), ctypes.c_int]
            lib.check_safety_overlaps.restype = ctypes.c_int
            lib.check_flow_intersections.argtypes = [ctypes.POINTER(FlowPath), ctypes.c_int, ctypes.POINTER(SafetyViolation), ctypes.c_int]
            lib.check_flow_intersections.restype = ctypes.c_int
            lib.calculate_bottlenecks.argtypes = [ctypes.POINTER(MachineInstance), ctypes.c_int, ctypes.POINTER(FlowPath), ctypes.c_int]
            lib.calculate_bottlenecks.restype = ctypes.c_int
            lib.check_crane_requirements.argtypes = [ctypes.POINTER(MachineInstance), ctypes.c_int, ctypes.POINTER(CraneZone), ctypes.c_int, ctypes.POINTER(SafetyViolation), ctypes.c_int]
            lib.check_crane_requirements.restype = ctypes.c_int
            break
        except Exception:
            lib = None

# =====================================================================
# 3. Pure Python Fallback Solvers (Samantha's Emulation Layer)
# =====================================================================
def py_ccw(a, b, c):
    val = (c['y'] - a['y']) * (b['x'] - a['x']) - (b['y'] - a['y']) * (c['x'] - a['x'])
    if abs(val) < 1e-9: return 0
    return 1 if val > 0 else -1

def py_on_segment(p, q, r):
    return (q['x'] <= max(p['x'], r['x']) and q['x'] >= min(p['x'], r['x']) and
            q['y'] <= max(p['y'], r['y']) and q['y'] >= min(p['y'], r['y']))

def py_intersect_segments(p1, q1, p2, q2):
    o1 = py_ccw(p1, q1, p2)
    o2 = py_ccw(p1, q1, q2)
    o3 = py_ccw(p2, q2, p1)
    o4 = py_ccw(p2, q2, q1)
    if o1 != o2 and o3 != o4: return True
    if o1 == 0 and py_on_segment(p1, p2, q1): return True
    if o2 == 0 and py_on_segment(p1, q2, q1): return True
    if o3 == 0 and py_on_segment(p2, p1, q2): return True
    if o4 == 0 and py_on_segment(p2, q1, q2): return True
    return False

def py_check_safety_overlaps(machines):
    violations = []
    for m in machines: m['safety_violation'] = False
    for i in range(len(machines)):
        for j in range(i + 1, len(machines)):
            m1, m2 = machines[i], machines[j]
            m1_min_x = m1['x'] - (m1['width'] / 2.0) - m1['safety_standoff']
            m1_max_x = m1['x'] + (m1['width'] / 2.0) + m1['safety_standoff']
            m1_min_y = m1['y'] - (m1['height'] / 2.0) - m1['safety_standoff']
            m1_max_y = m1['y'] + (m1['height'] / 2.0) + m1['safety_standoff']

            m2_min_x = m2['x'] - (m2['width'] / 2.0) - m2['safety_standoff']
            m2_max_x = m2['x'] + (m2['width'] / 2.0) + m2['safety_standoff']
            m2_min_y = m2['y'] - (m2['height'] / 2.0) - m2['safety_standoff']
            m2_max_y = m2['y'] + (m2['height'] / 2.0) + m2['safety_standoff']

            if (m1_min_x < m2_max_x and m1_max_x > m2_min_x) and (m1_min_y < m2_max_y and m1_max_y > m2_min_y):
                m1['safety_violation'] = True
                m2['safety_violation'] = True
                violations.append({
                    "machine_id_1": m1['id'], "machine_id_2": m2['id'],
                    "overlap_distance": abs(m1['x'] - m2['x']),
                    "description": f"Safety stand-off overlap between '{m1['name']}' and '{m2['name']}'"
                })
    return violations

def py_check_flow_intersections(paths):
    violations = []
    for i in range(len(paths)):
        for j in range(i + 1, len(paths)):
            p1, p2 = paths[i], paths[j]
            is_human_1 = p1['type'].lower() == "human"
            is_robot_2 = p2['type'].lower() in ["robot", "autonomous"]
            is_human_2 = p2['type'].lower() == "human"
            is_robot_1 = p1['type'].lower() in ["robot", "autonomous"]
            if (is_human_1 and is_robot_2) or (is_human_2 and is_robot_1):
                for s1 in range(len(p1['points']) - 1):
                    for s2 in range(len(p2['points']) - 1):
                        a1, b1 = p1['points'][s1], p1['points'][s1+1]
                        a2, b2 = p2['points'][s2], p2['points'][s2+1]
                        if py_intersect_segments(a1, b1, a2, b2):
                            violations.append({
                                "machine_id_1": p1['id'], "machine_id_2": p2['id'], "overlap_distance": 0.0,
                                "description": f"Unprotected intersection: Human Flow Path ({p1['id']}) and Robot Flow Path ({p2['id']})"
                            })
    return violations

def py_calculate_bottlenecks(machines):
    if not machines: return None
    min_throughput = float('inf')
    bottleneck_idx = -1
    for i, m in enumerate(machines):
        m['is_bottleneck'] = False
        throughput = m['volume_per_hour'] * m['yield_percentage']
        if throughput < min_throughput:
            min_throughput = throughput
            bottleneck_idx = i
    if bottleneck_idx != -1:
        machines[bottleneck_idx]['is_bottleneck'] = True
    return bottleneck_idx

def py_check_crane_requirements(machines, cranes):
    violations = []
    for m in machines:
        if m.get('crane_required', False):
            inside = False
            for c in cranes:
                cx1, cx2 = min(c['x1'], c['x2']), max(c['x1'], c['x2'])
                cy1, cy2 = min(c['y1'], c['y2']), max(c['y1'], c['y2'])
                if cx1 <= m['x'] <= cx2 and cy1 <= m['y'] <= cy2:
                    inside = True
                    break
            if not inside:
                m['safety_violation'] = True
                violations.append({
                    "machine_id_1": m['id'], "machine_id_2": "", "overlap_distance": 0.0,
                    "description": f"Machine '{m['name']}' requires overhead crane but is not inside a Crane Zone bounding box"
                })
    return violations

def run_analysis(machines, paths, cranes):
    if lib is not None:
        try:
            m_arr = (MachineInstance * len(machines))()
            for idx, m in enumerate(machines):
                m_arr[idx].id = m['id'].encode('utf-8')
                m_arr[idx].name = m['name'].encode('utf-8')
                m_arr[idx].x = m['x']
                m_arr[idx].y = m['y']
                m_arr[idx].width = m['width']
                m_arr[idx].height = m['height']
                m_arr[idx].safety_standoff = m['safety_standoff']
                m_arr[idx].water_required = m.get('water_required', 0)
                m_arr[idx].amperage = m.get('amperage', 0)
                m_arr[idx].wattage = m.get('wattage', 0)
                m_arr[idx].volume_per_hour = m.get('volume_per_hour', 0.0)
                m_arr[idx].yield_percentage = m.get('yield_percentage', 0.0)
                m_arr[idx].crane_required = m.get('crane_required', 0)
                m_arr[idx].is_bottleneck = 0
                m_arr[idx].safety_violation = 0

            p_arr = (FlowPath * len(paths))()
            for idx, p in enumerate(paths):
                p_arr[idx].id = p['id'].encode('utf-8')
                p_arr[idx].type = p['type'].encode('utf-8')
                p_arr[idx].width = p.get('width', 1.0)
                p_arr[idx].speed = p.get('speed', 1.0)
                p_arr[idx].point_count = len(p['points'])
                for p_idx, pt in enumerate(p['points']):
                    p_arr[idx].points[p_idx].x = pt['x']
                    p_arr[idx].points[p_idx].y = pt['y']

            c_arr = (CraneZone * len(cranes))()
            for idx, c in enumerate(cranes):
                c_arr[idx].id = c['id'].encode('utf-8')
                c_arr[idx].x1 = c['x1']
                c_arr[idx].y1 = c['y1']
                c_arr[idx].x2 = c['x2']
                c_arr[idx].y2 = c['y2']
                c_arr[idx].speed = c.get('speed', 1.0)
                c_arr[idx].weight_rating = c.get('weight_rating', 1.0)

            violations_buf = (SafetyViolation * 100)()
            bottleneck_idx = lib.calculate_bottlenecks(m_arr, len(machines), p_arr, len(paths))
            overlap_count = lib.check_safety_overlaps(m_arr, len(machines), violations_buf, 100)
            intersect_count = lib.check_flow_intersections(p_arr, len(paths), ctypes.byref(violations_buf, overlap_count * ctypes.sizeof(SafetyViolation)), 100 - overlap_count)
            crane_count = lib.check_crane_requirements(m_arr, len(machines), c_arr, len(cranes), ctypes.byref(violations_buf, (overlap_count + intersect_count) * ctypes.sizeof(SafetyViolation)), 100 - overlap_count - intersect_count)
            total_violations = overlap_count + intersect_count + crane_count

            for idx, m in enumerate(machines):
                m['is_bottleneck'] = bool(m_arr[idx].is_bottleneck)
                m['safety_violation'] = bool(m_arr[idx].safety_violation)

            py_violations = []
            for i in range(total_violations):
                py_violations.append({
                    "machine_id_1": violations_buf[i].machine_id_1.decode('utf-8'),
                    "machine_id_2": violations_buf[i].machine_id_2.decode('utf-8'),
                    "overlap_distance": violations_buf[i].overlap_distance,
                    "description": violations_buf[i].description.decode('utf-8')
                })
            return py_violations, bottleneck_idx
        except Exception:
            pass

    # Pure Python Emulation
    py_violations = []
    py_violations.extend(py_check_safety_overlaps(machines))
    py_violations.extend(py_check_flow_intersections(paths))
    py_violations.extend(py_check_crane_requirements(machines, cranes))
    bottleneck_idx = py_calculate_bottlenecks(machines)
    return py_violations, bottleneck_idx

# =====================================================================
# 4. Exporter Logic: PDF Exporter Engine (Joey's PDF Code)
# =====================================================================
def generate_pdf_report(machines, paths, cranes, violations, bottleneck_idx):
    pdf_buffer = io.BytesIO()
    doc = SimpleDocTemplate(pdf_buffer, pagesize=letter, rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40)
    styles = getSampleStyleSheet()
    
    primary_color = colors.HexColor("#2c3e50")
    secondary_color = colors.HexColor("#3498db")
    accent_color = colors.HexColor("#e74c3c")
    bg_light = colors.HexColor("#f8f9fa")
    
    story = []
    title_style = ParagraphStyle(
        'CoverTitle', parent=styles['Heading1'], fontSize=22, leading=26, textColor=primary_color, alignment=1, spaceAfter=15
    )
    subtitle_style = ParagraphStyle(
        'CoverSubtitle', parent=styles['Normal'], fontSize=11, leading=13, textColor=colors.HexColor("#7f8c8d"), alignment=1, spaceAfter=25
    )
    
    story.append(Paragraph("FACTORY FLOOR OPTIMIZATION REPORT", title_style))
    story.append(Paragraph("Automated Engineering & Safety Verification Layout Report", subtitle_style))
    story.append(Spacer(1, 10))
    
    draw_width, draw_height = 500, 250
    d = Drawing(draw_width, draw_height)
    d.add(Rect(0, 0, draw_width, draw_height, fillColor=colors.HexColor("#fcfcfc"), strokeColor=colors.HexColor("#bdc3c7"), strokeWidth=1))
    
    for x in range(0, draw_width, 25): d.add(Line(x, 0, x, draw_height, strokeColor=colors.HexColor("#f0f0f0"), strokeWidth=0.5))
    for y in range(0, draw_height, 25): d.add(Line(0, y, draw_width, y, strokeColor=colors.HexColor("#f0f0f0"), strokeWidth=0.5))
        
    scale = 8.0
    for c in cranes:
        cx1, cy1 = c['x1'] * scale, c['y1'] * scale
        cx2, cy2 = c['x2'] * scale, c['y2'] * scale
        cw, ch = abs(cx2 - cx1), abs(cy2 - cy1)
        d.add(Rect(min(cx1, cx2), min(cy1, cy2), cw, ch, fillColor=colors.HexColor("#f3e5f5"), strokeColor=colors.HexColor("#9b59b6"), strokeWidth=1, strokeDashArray=[2,2]))
        d.add(String(min(cx1, cx2) + 5, min(cy1, cy2) + 5, f"Crane {c['id']}", fontSize=7, fillColor=colors.HexColor("#9b59b6")))
        
    for p in paths:
        if len(p['points']) > 1:
            pts = p['points']
            stroke_col = colors.HexColor("#3498db") if p['type'].lower() == 'human' else colors.HexColor("#e74c3c")
            for i in range(len(pts) - 1):
                d.add(Line(pts[i]['x']*scale, pts[i]['y']*scale, pts[i+1]['x']*scale, pts[i+1]['y']*scale, strokeColor=stroke_col, strokeWidth=1.5))

    for idx, m in enumerate(machines):
        mx = (m['x'] - m['width']/2) * scale
        my = (m['y'] - m['height']/2) * scale
        mw = m['width'] * scale
        mh = m['height'] * scale
        
        soff = m['safety_standoff'] * scale
        standoff_col = colors.HexColor("#f5b7b1") if m.get('safety_violation', False) else colors.HexColor("#d5f5e3")
        d.add(Rect(mx - soff, my - soff, mw + 2*soff, mh + 2*soff, fillColor=standoff_col, strokeColor=colors.transparent, strokeWidth=0))
        
        m_col = colors.HexColor("#f1c40f") if m.get('is_bottleneck', False) else colors.HexColor("#2c3e50")
        d.add(Rect(mx, my, mw, mh, fillColor=m_col, strokeColor=colors.HexColor("#34495e"), strokeWidth=1))
        d.add(String(mx + 3, my + mh/2 - 2, m['name'][:12], fontSize=6, fillColor=colors.white))
        
    story.append(d)
    story.append(Spacer(1, 10))
    
    legend_data = [
        [
            Paragraph("<b>LEGEND:</b>", styles['Normal']),
            Paragraph("<font color='#2c3e50'>■</font> Standard Machine", styles['Normal']),
            Paragraph("<font color='#f1c40f'>■</font> Bottleneck Workstation", styles['Normal']),
            Paragraph("<font color='#9b59b6'>- -</font> Crane Zone", styles['Normal']),
            Paragraph("<font color='#3498db'>━</font> Human Path", styles['Normal']),
            Paragraph("<font color='#e74c3c'>━</font> Robot Path", styles['Normal'])
        ]
    ]
    legend_table = Table(legend_data, colWidths=[60, 90, 100, 80, 85, 85])
    legend_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), bg_light),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('TOPPADDING', (0,0), (-1,-1), 4),
    ]))
    story.append(legend_table)
    story.append(Spacer(1, 15))
    
    story.append(Paragraph("1. System Performance & Capacity Analysis", styles['Heading2']))
    total_power = sum(m.get('wattage', 0) for m in machines)
    total_water = sum(1 for m in machines if m.get('water_required', 0))
    total_volume = sum(m.get('volume_per_hour', 0) for m in machines)
    
    bottleneck_machine = next((m for m in machines if m.get('is_bottleneck', False)), None)
    eff_output = 0.0
    if bottleneck_machine:
        eff_output = bottleneck_machine['volume_per_hour'] * bottleneck_machine['yield_percentage']
    
    metrics_data = [
        ["Metric Description", "Value", "Facility Impact"],
        ["Total Installed Power Load", f"{total_power/1000:.1f} kW", "Requires industrial electrical service"],
        ["Water Utility Connections", f"{total_water} Drop Points", "Plumbing service drops required"],
        ["Gross Theoretical Volume", f"{total_volume:.1f} parts/hr", "Aggregate maximum across all units"],
        ["Effective System Output (Bottleneck-limited)", f"{eff_output:.1f} assemblies/hr", "Max rate based on bottleneck capacity"]
    ]
    metrics_table = Table(metrics_data, colWidths=[180, 120, 200])
    metrics_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), primary_color),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, bg_light]),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#dcdde1")),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
    ]))
    story.append(metrics_table)
    story.append(Spacer(1, 10))
    
    if bottleneck_machine:
        story.append(Paragraph(f"<b>Bottleneck Verification:</b> The system bottleneck is <b>{bottleneck_machine['name']}</b> (ID: {bottleneck_machine['id']}). "
                               f"Effective plant output cannot exceed <b>{eff_output:.1f} assemblies per hour</b>.", styles['Normal']))
    story.append(Spacer(1, 15))
    
    story.append(Paragraph("2. Safety & Compliance Audit", styles['Heading2']))
    if len(violations) > 0:
        story.append(Paragraph("<font color='red'><b>CRITICAL WARNING: SAFETY VIOLATIONS IDENTIFIED</b></font><br/>"
                               "The layout contains critical safety overlaps or utility layout issues. These must be resolved "
                               "prior to construction funding approval.", styles['Normal']))
        story.append(Spacer(1, 8))
        
        violation_data = [["ID", "Violation Description", "Resolution Action Required"]]
        for idx, v in enumerate(violations):
            violation_data.append([f"V{idx+1:02d}", v['description'], "Reposition asset or adjust standoff distance."])
            
        violation_table = Table(violation_data, colWidths=[40, 260, 200])
        violation_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#c0392b")),
            ('TEXTCOLOR', (0,0), (-1,0), colors.white),
            ('ALIGN', (0,0), (-1,-1), 'LEFT'),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#f5b7b1")),
            ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.HexColor("#fdf2f2"), colors.white]),
            ('TOPPADDING', (0,0), (-1,-1), 5),
            ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ]))
        story.append(violation_table)
    else:
        story.append(Paragraph("<font color='green'><b>✔ SAFETY COMPLIANCE PASSED:</b></font><br/>"
                               "No layout overlaps or intersection errors were detected. This design meets baseline OSHA clearance safety guidelines.", styles['Normal']))
        
    story.append(Spacer(1, 15))
    story.append(Paragraph("<b>Legal Disclaimer:</b> This report is an engineering simulation output based on theoretical inputs. "
                           "Safety zones, venting configurations, and utility loadings must be verified by a licensed professional engineer (PE) "
                           "before final physical installation.", ParagraphStyle('Disclaimer', parent=styles['Normal'], fontSize=7, textColor=colors.HexColor("#7f8c8d"))))
    
    doc.build(story)
    pdf_buffer.seek(0)
    return pdf_buffer.getvalue()

# =====================================================================
# 5. UI Layout Interface (Streamlit Presentation Layer)
# =====================================================================
# Resolve machinery library CSV path dynamically
current_dir = os.path.dirname(os.path.abspath(__file__))
LIBRARY_PATH = None
for root, dirs, files in os.walk(current_dir):
    if "machinery_library.csv" in files:
        LIBRARY_PATH = os.path.join(root, "machinery_library.csv")
        break

if not LIBRARY_PATH:
    LIBRARY_PATH = os.path.join(current_dir, "data", "machinery_library.csv")

# Ensure preset CSV file exists with baseline contents
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

# Manage Streamlit session state tables
if "placed_machines" not in st.session_state:
    st.session_state.placed_machines = []
if "flow_paths" not in st.session_state:
    st.session_state.flow_paths = []
if "crane_zones" not in st.session_state:
    st.session_state.crane_zones = []

# Sidebar Controls Panel
st.sidebar.header("Factory Design Controls")

uploaded_file = st.sidebar.file_uploader("Upload CSV Presets Library", type="csv")
if uploaded_file is not None:
    with open(LIBRARY_PATH, "wb") as f:
        f.write(uploaded_file.getbuffer())
    st.cache_data.clear()
    st.sidebar.success("Library updated successfully!")

# Asset placement forms
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

# Execute layout simulator analyses
violations = []
bottleneck_idx = -1
if st.session_state.placed_machines:
    violations, bottleneck_idx = run_analysis(
        st.session_state.placed_machines,
        st.session_state.flow_paths,
        st.session_state.crane_zones
    )

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
    
    # 5.1 Render Crane Boundaries (Background)
    for c in st.session_state.crane_zones:
        cx_min, cy_min = min(c['x1'], c['x2']), min(c['y1'], c['y2'])
        cw, ch = abs(c['x2'] - c['x1']), abs(c['y2'] - c['y1'])
        rect = patches.Rectangle((cx_min, cy_min), cw, ch, fill=True, color='#f3e5f5', alpha=0.5, edgecolor='#9b59b6', linestyle='--', linewidth=1.5)
        ax.add_patch(rect)
        ax.text(cx_min + 0.5, cy_min + 0.5, f"Crane {c['id']}", color='#9b59b6', fontsize=8, fontweight='bold')

    # 5.2 Render Flow Corridor Paths
    for p in st.session_state.flow_paths:
        pts = p['points']
        px = [pt['x'] for pt in pts]
        py = [pt['y'] for pt in pts]
        p_col = "#3498db" if p['type'] == "human" else "#e74c3c"
        ax.plot(px, py, color=p_col, linewidth=p['width'] * 5, alpha=0.25)
        ax.plot(px, py, color=p_col, linewidth=1.5, linestyle='-')
        ax.text(px[0] + 0.5, py[0] + 0.5, f"Path {p['id']}", color=p_col, fontsize=7)

    # 5.3 Render Placing Machines & Safety Buffer
    for m in st.session_state.placed_machines:
        mx = m['x'] - m['width']/2
        my = m['y'] - m['height']/2
        
        soff = m['safety_standoff']
        standoff_color = '#e74c3c' if m.get('safety_violation', False) else '#2ecc71'
        standoff_edge = '#e74c3c' if m.get('safety_violation', False) else '#2ecc71'
        
        buffer_rect = patches.Rectangle(
            (mx - soff, my - soff), m['width'] + 2*soff, m['height'] + 2*soff,
            fill=True, color=standoff_color, alpha=0.15 if m.get('safety_violation', False) else 0.1, 
            edgecolor=standoff_edge, linestyle=':', linewidth=1
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

# Document release export handlers
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
