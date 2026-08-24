# engine.py
import numpy as np


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


def run_layout_analysis(placed_machines, placed_conduits, placed_cranes=None):
    """
    Performs comprehensive spatial and regulatory checks on layout components.
    """
    warnings = []
    placed_cranes = placed_cranes or []

    # 1. NJ-UCC Depth and Warning Tape Checks
    for cond in placed_conduits:
        depth = cond.get("depth_in", 36)
        has_tape = cond.get("warning_tape", True)
        label = cond.get("label", cond.get("id", "Main Run"))

        if depth < 36:
            warnings.append(
                f"NJ-UCC Viol: Conduit '{label}' depth of {depth} in is less than the required 36 in."
            )
        if not has_tape:
            warnings.append(
                f"NJ-UCC Viol: Conduit '{label}' must have standard orange 4 mil warning tape."
            )

        x_pts = cond.get("x", [])
        y_pts = cond.get("y", [])
        if len(x_pts) != len(y_pts) or len(x_pts) < 2:
            warnings.append(
                f"Route Data Warn: Conduit '{label}' has invalid polyline geometry."
            )

    # 2. Safety Overlap Check
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
                    f"OSHA Safety Viol: Standoff overlap detected between "
                    f"'{m1.get('id', m1.get('Make', 'Machine A'))}' and "
                    f"'{m2.get('id', m2.get('Make', 'Machine B'))}'."
                )

    # 3. Crane coverage check for crane-required machines
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
