# engine.py
import numpy as np
from datetime import datetime

VALID_UTILITY_TYPES = {"electrical", "water", "drainage", "network", "hvac"}
VALID_MOVEMENT_MODES = {
    "human",
    "autonomous_robot",
    "robotic_arm",
    "overhead_crane",
    "forklift",
}


def machine_is_in_any_crane_zone(machine, placed_cranes):
    """Check whether a machine centerpoint falls inside at least one crane envelope."""
    mx, my = machine["x"], machine["y"]
    for crane in placed_cranes:
        if (
            crane["ll_x"] <= mx <= crane["ur_x"]
            and crane["ll_y"] <= my <= crane["ur_y"]
        ):
            return True
    return False


def polyline_length(x_vals, y_vals):
    total = 0.0
    for i in range(1, len(x_vals)):
        dx = float(x_vals[i]) - float(x_vals[i - 1])
        dy = float(y_vals[i]) - float(y_vals[i - 1])
        total += np.sqrt(dx**2 + dy**2)
    return round(float(total), 2)


def analyze_workflow_paths(workflow_paths):
    """
    Basic heuristic checks for workflow paths.
    Expects each path dict to optionally include:
    - movement_mode
    - width_ft
    - speed_fpm
    """
    warnings = []

    min_width_by_mode = {
        "human": 1.0,
        "autonomous_robot": 2.0,
        "robotic_arm": 1.0,
        "overhead_crane": 3.0,
        "forklift": 8.0,
    }

    max_speed_by_mode = {
        "human": 6.0,
        "autonomous_robot": 15.0,
        "robotic_arm": 8.0,
        "overhead_crane": 20.0,
        "forklift": 12.0,
    }

    for idx, path in enumerate(workflow_paths):
        mode = path.get("movement_mode", "human")
        width_ft = float(path.get("width_ft", 1.0))
        speed_fpm = float(path.get("speed_fpm", 5.0))
        label = path.get("id", f"WF-{idx+1:03d}")

        if mode not in VALID_MOVEMENT_MODES:
            warnings.append(
                f"Workflow Mode Warn: Path '{label}' has unsupported movement mode '{mode}'."
            )
            continue

        if width_ft < min_width_by_mode[mode]:
            warnings.append(
                f"Workflow Width Warn: Path '{label}' width {width_ft} ft is narrow for mode '{mode}'."
            )

        if speed_fpm > max_speed_by_mode[mode]:
            warnings.append(
                f"Workflow Speed Warn: Path '{label}' speed {speed_fpm} exceeds recommended heuristic for mode '{mode}'."
            )

    return warnings


def run_layout_analysis(
    placed_machines,
    placed_conduits,
    placed_cranes=None,
    workflow_paths=None,
):
    """
    Performs spatial, utility, and heuristic workflow checks.
    """
    warnings = []
    placed_cranes = placed_cranes or []
    workflow_paths = workflow_paths or []

    # 1. Utility / conduit checks
    for cond in placed_conduits:
        depth = cond.get("depth_in", 36)
        has_tape = cond.get("warning_tape", True)
        label = cond.get("label", cond.get("id", "Main Run"))
        utility_type = cond.get("utility_type", "electrical")

        if utility_type not in VALID_UTILITY_TYPES:
            warnings.append(
                f"Utility Type Warn: Conduit '{label}' has unsupported utility type '{utility_type}'."
            )

        x_pts = cond.get("x", [])
        y_pts = cond.get("y", [])
        if len(x_pts) != len(y_pts) or len(x_pts) < 2:
            warnings.append(
                f"Route Data Warn: Conduit '{label}' has invalid polyline geometry."
            )

        # Keep electrical-specific check language limited to implemented rules
        if utility_type == "electrical":
            if depth < 36:
                warnings.append(
                    f"Electrical Routing Warn: Conduit '{label}' depth of {depth} in is less than the configured 36 in rule."
                )
            if not has_tape:
                warnings.append(
                    f"Electrical Routing Warn: Conduit '{label}' is missing warning tape."
                )

    # 2. Machine standoff overlap checks
    for i, m1 in enumerate(placed_machines):
        x1, y1 = m1["x"], m1["y"]
        r1 = (max(m1["Width"], m1["Height"]) / 2.0) + m1["Standoff"]

        for j, m2 in enumerate(placed_machines):
            if i >= j:
                continue

            x2, y2 = m2["x"], m2["y"]
            r2 = (max(m2["Width"], m2["Height"]) / 2.0) + m2["Standoff"]

            dist = np.sqrt((x1 - x2) ** 2 + (y1 - y2) ** 2)
            if dist < (r1 + r2):
                warnings.append(
                    f"Safety Clearance Warn: Standoff overlap detected between "
                    f"'{m1.get('id', m1.get('Make', 'Machine A'))}' and "
                    f"'{m2.get('id', m2.get('Make', 'Machine B'))}'."
                )

    # 3. Crane-required machine coverage checks
    for m in placed_machines:
        if m.get("CraneRequired", False):
            if not machine_is_in_any_crane_zone(m, placed_cranes):
                warnings.append(
                    f"Crane Coverage Warn: Machine '{m.get('id', m.get('Make', 'Unknown'))}' "
                    "requires overhead crane access but is not inside any crane coverage zone."
                )

    # 4. Crane geometry sanity checks
    for crane in placed_cranes:
        if crane["ll_x"] >= crane["ur_x"] or crane["ll_y"] >= crane["ur_y"]:
            warnings.append(
                f"Crane Geometry Warn: Crane '{crane.get('id', crane.get('model', 'Unknown'))}' "
                "has invalid bounding-box coordinates."
            )

    # 5. Workflow heuristics
    warnings.extend(analyze_workflow_paths(workflow_paths))

    return warnings


def calculate_production_metrics(placed_machines, m_workers=3, cv_task=0.5):
    """
    Implements simplified production metrics:
    - Bottleneck machine
    - Line balance efficiency
    - Estimated finished assemblies per hour
    - Simplified energy-saving estimate
    """
    if not placed_machines:
        return {}

    # Standard values
    volumes = [float(m["Volume"]) for m in placed_machines]
    yields = [float(m["Yield"]) / 100.0 for m in placed_machines]
    eff_vols = [v * y for v, y in zip(volumes, yields)]

    # Bottleneck is minimum effective throughput
    bn_idx = int(np.argmin(eff_vols))
    bottleneck_rate = float(eff_vols[bn_idx])

    # Basic line balance heuristic
    avg_eff = float(np.mean(eff_vols)) if len(eff_vols) > 0 else 0.0
    max_eff = float(np.max(eff_vols)) if len(eff_vols) > 0 else 1.0
    line_balance = round((avg_eff / max_eff) * 100.0, 1) if max_eff > 0 else 0.0

    # Simplified "switch-off savings" heuristic
    total_watts = sum(float(m.get("Wattage", 0.0)) for m in placed_machines)
    udp_switch_off_savings_kw = round(total_watts * 0.08 / 1000.0, 2)

    # Explicit finished assemblies / hr metric
    finished_assemblies_per_hr = round(bottleneck_rate, 1)

    return {
        "Bottleneck Machine": placed_machines[bn_idx].get(
            "id",
            f"{placed_machines[bn_idx].get('Make', 'Unknown')} {placed_machines[bn_idx].get('Model', '')}".strip()
        ),
        "Line Balance Efficiency": f"{line_balance}%",
        "Estimated Finished Assemblies / Hr": finished_assemblies_per_hr,
        "UDP Switch-Off Savings": f"{udp_switch_off_savings_kw} kW",
    }

def build_project_summary_report(session_state):
    return {
        "report_type": "project_summary",
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "designer_name": session_state.get("designer_name", ""),
        "dwg_title": session_state.get("dwg_title", ""),
        "dwg_num": session_state.get("dwg_num", ""),
        "sheet_size": session_state.get("sheet_size", ""),
        "floor_w": session_state.get("floor_w", 0.0),
        "floor_h": session_state.get("floor_h", 0.0),
        "path_width_ft": session_state.get("path_width_ft", 0.0),
        "counts": {
            "machines": len(session_state.get("placed_machines", [])),
            "lighting": len(session_state.get("placed_lighting", [])),
            "conduits": len(session_state.get("placed_conduits", [])),
            "cranes": len(session_state.get("placed_cranes", [])),
        },
    }


def build_safety_report(placed_machines, placed_conduits, placed_cranes=None, workflow_paths=None):
    warnings = run_layout_analysis(
        placed_machines,
        placed_conduits,
        placed_cranes or [],
        workflow_paths or [],
    )
    return {
        "report_type": "safety_report",
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "warning_count": len(warnings),
        "warnings": warnings,
    }


def build_production_report(placed_machines):
    metrics = calculate_production_metrics(placed_machines)
    return {
        "report_type": "production_report",
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "metrics": metrics,
    }


def build_utility_report(placed_conduits):
    utility_rows = []
    for idx, cond in enumerate(placed_conduits):
        x_pts = cond.get("x", [])
        y_pts = cond.get("y", [])
        route_length = 0.0
        if len(x_pts) >= 2 and len(x_pts) == len(y_pts):
            for i in range(1, len(x_pts)):
                dx = float(x_pts[i]) - float(x_pts[i - 1])
                dy = float(y_pts[i]) - float(y_pts[i - 1])
                route_length += float(np.sqrt(dx**2 + dy**2))

        utility_rows.append({
            "id": cond.get("id", f"C-{idx+1:03d}"),
            "label": cond.get("label", f"Utility-{idx+1}"),
            "utility_type": cond.get("utility_type", "electrical"),
            "depth_in": cond.get("depth_in", None),
            "warning_tape": cond.get("warning_tape", None),
            "point_count": len(x_pts),
            "route_length_ft": round(route_length, 2),
        })

    return {
        "report_type": "utility_report",
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "utilities": utility_rows,
    }


def build_machine_schedule_report(placed_machines):
    rows = []
    for idx, m in enumerate(placed_machines):
        rows.append({
            "id": m.get("id", f"M-{idx+1:03d}"),
            "make": m.get("Make", ""),
            "model": m.get("Model", ""),
            "x": m.get("x", 0.0),
            "y": m.get("y", 0.0),
            "width": m.get("Width", 0.0),
            "height": m.get("Height", 0.0),
            "standoff": m.get("Standoff", 0.0),
            "volume_per_hr": m.get("Volume", 0.0),
            "yield_pct": m.get("Yield", 0.0),
            "decibel": m.get("Decibel", 0.0),
            "crane_required": m.get("CraneRequired", False),
            "amperage": m.get("Amperage", None),
            "wattage": m.get("Wattage", None),
        })

    return {
        "report_type": "machine_schedule",
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "machines": rows,
    }


def build_full_report_bundle(session_state, workflow_paths=None):
    placed_machines = session_state.get("placed_machines", [])
    placed_conduits = session_state.get("placed_conduits", [])
    placed_cranes = session_state.get("placed_cranes", [])

    return {
        "schema_version": "report_bundle_1.0",
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "project_summary": build_project_summary_report(session_state),
        "safety_report": build_safety_report(
            placed_machines,
            placed_conduits,
            placed_cranes,
            workflow_paths or [],
        ),
        "production_report": build_production_report(placed_machines),
        "utility_report": build_utility_report(placed_conduits),
        "machine_schedule": build_machine_schedule_report(placed_machines),
    }
