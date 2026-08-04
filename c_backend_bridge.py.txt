import ctypes
import os
import sys

# Define ctypes structures matching Robert's C definitions in optimizer.h
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

# Try to load native compiled C library, fallback gracefully if not compiled
lib = None
lib_path = os.path.join(os.path.dirname(__file__), "liboptimizer.so")
if os.path.exists(lib_path):
    try:
        lib = ctypes.CDLL(lib_path)
        lib.check_safety_overlaps.argtypes = [
            ctypes.POINTER(MachineInstance), ctypes.c_int,
            ctypes.POINTER(SafetyViolation), ctypes.c_int
        ]
        lib.check_safety_overlaps.restype = ctypes.c_int

        lib.check_flow_intersections.argtypes = [
            ctypes.POINTER(FlowPath), ctypes.c_int,
            ctypes.POINTER(SafetyViolation), ctypes.c_int
        ]
        lib.check_flow_intersections.restype = ctypes.c_int

        lib.calculate_bottlenecks.argtypes = [
            ctypes.POINTER(MachineInstance), ctypes.c_int,
            ctypes.POINTER(FlowPath), ctypes.c_int
        ]
        lib.calculate_bottlenecks.restype = ctypes.c_int

        lib.check_crane_requirements.argtypes = [
            ctypes.POINTER(MachineInstance), ctypes.c_int,
            ctypes.POINTER(CraneZone), ctypes.c_int,
            ctypes.POINTER(SafetyViolation), ctypes.c_int
        ]
        lib.check_crane_requirements.restype = ctypes.c_int
    except Exception as e:
        print(f"Warning: Could not load C library. Using Python emulators: {e}", file=sys.stderr)
        lib = None

# ==========================================
# Pure Python Fallback Implementation
# ==========================================
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
    for m in machines:
        m['safety_violation'] = False

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

            if (m1_min_x < m2_max_x and m1_max_x > m2_min_x) and \
               (m1_min_y < m2_max_y and m1_max_y > m2_min_y):
                m1['safety_violation'] = True
                m2['safety_violation'] = True
                violations.append({
                    "machine_id_1": m1['id'],
                    "machine_id_2": m2['id'],
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
                                "machine_id_1": p1['id'],
                                "machine_id_2": p2['id'],
                                "overlap_distance": 0.0,
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
                    "machine_id_1": m['id'],
                    "machine_id_2": "",
                    "overlap_distance": 0.0,
                    "description": f"Machine '{m['name']}' requires overhead crane but is not inside a Crane Zone bounding box"
                })
    return violations

# ==========================================
# Marshalling Orchestrator
# ==========================================
def run_analysis(machines, paths, cranes):
    if lib is not None:
        try:
            # 1. Structure MachineInstance arrays in native memory
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

            # 2. Structure FlowPath arrays
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

            # 3. Structure CraneZone arrays
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

            # Invoke compiled C code APIs
            bottleneck_idx = lib.calculate_bottlenecks(m_arr, len(machines), p_arr, len(paths))
            overlap_count = lib.check_safety_overlaps(m_arr, len(machines), violations_buf, 100)
            intersect_count = lib.check_flow_intersections(p_arr, len(paths), ctypes.byref(violations_buf, overlap_count * ctypes.sizeof(SafetyViolation)), 100 - overlap_count)
            crane_count = lib.check_crane_requirements(m_arr, len(machines), c_arr, len(cranes), ctypes.byref(violations_buf, (overlap_count + intersect_count) * ctypes.sizeof(SafetyViolation)), 100 - overlap_count - intersect_count)
            total_violations = overlap_count + intersect_count + crane_count

            # Unpack results back to standard python structures
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
        except Exception as ex:
            print(f"ctypes execution failed, utilizing fallback solvers: {ex}", file=sys.stderr)

    # Executing using Python Fallback Solvers
    py_violations = []
    py_violations.extend(py_check_safety_overlaps(machines))
    py_violations.extend(py_check_flow_intersections(paths))
    py_violations.extend(py_check_crane_requirements(machines, cranes))
    bottleneck_idx = py_calculate_bottlenecks(machines)

    return py_violations, bottleneck_idx
