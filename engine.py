# engine.py
import numpy as np


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
    Simplified production metrics:
    - bottleneck machine
    - line balance efficiency
    - estimated finished assemblies / hr
    - simplified energy-saving estimate
    """
    if not placed_machines:
        return {}

    volumes = [float(m["Volume"]) for m in placed_machines]
    yields = [float(m["Yield"]) / 100.0 for m in placed_machines]
    eff_vols = [v * y for v, y in zip(volumes, yields)]

    bn_idx = int(np.argmin(eff_vols))
    bottleneck_rate = eff_vols[bn_idx]

    avg_eff = float(np.mean(eff_vols)) if len(eff_vols) > 0 else 0.0
    max_eff = float(np.max(eff_vols)) if len(eff_vols) > 0 else 1.0
    line_balance = round((avg_eff / max_eff) * 100.0, 1) if max_eff > 0 else 0.0

    total_watts = sum(float(m.get("Wattage", 0.0)) for m in placed_machines)
    udp_switch_off_savings_kw = round(total_watts * 0.08 / 1000.0, 2)

    finished_assemblies_per_hr = round(float(bottleneck_rate), 1)

    return {
        "Bottleneck Machine": placed_machines[bn_idx].get(
            "id",
            f"{placed_machines[bn_idx].get('Make', 'Unknown')} {placed_machines[bn_idx].get('Model', '')}".strip()
        ),
        "Line Balance Efficiency": f"{line_balance}%",
        "Estimated Finished Assemblies / Hr": finished_assemblies_per_hr,
        "UDP Switch-Off Savings": f"{udp_switch_off_savings_kw} kW",
    }
