import sys
import os

# =====================================================================
# --- RECURSIVE PATH-RESOLUTION PATCH ( Samantha's Robust Module Finder) ---
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

import http.server
import socketserver
import json
import csv
import io
import urllib.parse
from backend.c_backend_bridge import run_analysis
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.graphics.shapes import Drawing, Rect, Line, String

PORT = 8000

# Locate machinery database dynamically
LIBRARY_PATH = None
for root, dirs, files in os.walk(current_dir):
    if "machinery_library.csv" in files:
        LIBRARY_PATH = os.path.join(root, "machinery_library.csv")
        break

if not LIBRARY_PATH:
    LIBRARY_PATH = os.path.join(current_dir, "data", "machinery_library.csv")

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
        ["Effective System Output (Bottleneck-limited)", f"{eff_output:.1f} assemblies/hr", "Max finished rate based on bottleneck flow"]
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
        story.append(Paragraph(f"<b>Bottleneck Verification:</b> The production system is throttled by <b>{bottleneck_machine['name']}</b> (ID: {bottleneck_machine['id']}). "
                               f"Plant cannot exceed <b>{eff_output:.1f} assemblies per hour</b>. "
                               f"To optimize, focus cycle-time reduction efforts at this workstation.", styles['Normal']))
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

class FactoryOptimizerHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/" or self.path == "/index.html":
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            try:
                # Find templates index.html dynamically
                html_path = None
                for root, dirs, files in os.walk(current_dir):
                    if "index.html" in files:
                        html_path = os.path.join(root, "index.html")
                        break
                if not html_path:
                    html_path = "frontend/templates/index.html"
                with open(html_path, "r") as f:
                    self.wfile.write(f.read().encode("utf-8"))
            except Exception as e:
                self.wfile.write(f"Error loading index.html: {e}".encode("utf-8"))
                
        elif self.path == "/api/library":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            machines = []
            if os.path.exists(LIBRARY_PATH):
                with open(LIBRARY_PATH, "r") as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        row["width"] = float(row["width"])
                        row["height"] = float(row["height"])
                        row["safety_standoff"] = float(row["safety_standoff"])
                        row["water_required"] = int(row["water_required"])
                        row["amperage"] = int(row["amperage"])
                        row["wattage"] = int(row["wattage"])
                        row["volume_per_hour"] = float(row["volume_per_hour"])
                        row["yield_percentage"] = float(row["yield_percentage"])
                        row["crane_required"] = int(row["crane_required"])
                        machines.append(row)
            self.wfile.write(json.dumps(machines).encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        if self.path == "/api/library":
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length)
            boundary = self.headers.get_boundary()
            if boundary:
                parts = body.split(f"--{boundary}".encode())
                for part in parts:
                    if b'filename="' in part:
                        head, csv_data = part.split(b'\r\n\r\n', 1)
                        csv_text = csv_data.rsplit(b'\r\n', 1)[0].decode('utf-8')
                        lines = csv_text.strip().split('\n')
                        if len(lines) > 1:
                            with open(LIBRARY_PATH, "w") as f:
                                f.write(csv_text)
                            self.send_response(200)
                            self.send_header("Content-Type", "text/html")
                            self.end_headers()
                            self.wfile.write("<h3>Successfully updated machinery library! Reload page.</h3>".encode("utf-8"))
                            return
            self.send_response(400)
            self.end_headers()
            self.wfile.write("Failed to parse CSV upload".encode("utf-8"))

        elif self.path == "/api/analyze":
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            req_json = json.loads(post_data.decode('utf-8'))
            machines = req_json.get("machines", [])
            paths = req_json.get("paths", [])
            cranes = req_json.get("cranes", [])
            
            violations, bottleneck_idx = run_analysis(machines, paths, cranes)
            resp_data = {"machines": machines, "violations": violations, "bottleneck_idx": bottleneck_idx}
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(resp_data).encode("utf-8"))

        elif self.path == "/api/export":
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            req_json = json.loads(post_data.decode('utf-8'))
            machines = req_json.get("machines", [])
            paths = req_json.get("paths", [])
            cranes = req_json.get("cranes", [])
            
            violations, bottleneck_idx = run_analysis(machines, paths, cranes)
            pdf_bytes = generate_pdf_report(machines, paths, cranes, violations, bottleneck_idx)
            
            self.send_response(200)
            self.send_header("Content-Type", "application/pdf")
            self.send_header("Content-Disposition", 'attachment; filename="FactoryFloor_Report.pdf"')
            self.end_headers()
            self.wfile.write(pdf_bytes)
        else:
            self.send_response(404)
            self.end_headers()

class ThreadingHTTPServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    pass

if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    print(f"Starting server on http://localhost:{PORT}")
    with ThreadingHTTPServer(("", PORT), FactoryOptimizerHandler) as server:
        try: server.serve_forever()
        except KeyboardInterrupt: server.shutdown()
