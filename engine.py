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

# --- Phase 4.6 placeholders: optimization engine hooks ---

TRANSFER_MODE_FACTORS = {
    "human": 1.00,
    "autonomous_robot": 0.85,
    "robotic_arm": 0.60,
    "overhead_crane": 1.10,
    "forklift": 1.25,
}

FLOW_EFFICIENCY_MAX_SCORE = 35.0
BOTTLENECK_SUPPORT_MAX_SCORE = 20.0
SAFETY_COMPLIANCE_MAX_SCORE = 20.0
UTILITY_SERVICEABILITY_MAX_SCORE = 10.0
HANDLING_WIP_MAX_SCORE = 15.0


def index_machines_by_id(placed_machines):
    """
    Return a dict of machine_id -> machine record.
    """
    out = {}
    for idx, m in enumerate(placed_machines):
        mid = str(m.get("id", f"M-{idx+1:03d}")).strip()
        out[mid] = m
    return out


def safe_machine_effective_rate(machine):
    """
    Effective production rate using current model:
    effective_rate = Volume * Yield%
    """
    try:
        volume = float(machine.get("Volume", 0.0))
    except Exception:
        volume = 0.0

    try:
        yield_pct = float(machine.get("Yield", 0.0))
    except Exception:
        yield_pct = 0.0

    return max(0.0, volume * (yield_pct / 100.0))


def machine_center_distance_ft(machine_a, machine_b):
    """
    Euclidean distance between machine center points.
    """
    try:
        ax = float(machine_a.get("x", 0.0))
        ay = float(machine_a.get("y", 0.0))
        bx = float(machine_b.get("x", 0.0))
        by = float(machine_b.get("y", 0.0))
    except Exception:
        return 0.0

    return round(float(np.sqrt((ax - bx) ** 2 + (ay - by) ** 2)), 2)

def find_bottleneck_machine(placed_machines):
    """
    Return (machine_id, effective_rate) for the slowest effective machine.
    """
    if not placed_machines:
        return None, 0.0

    best_id = None
    min_rate = None

    for idx, m in enumerate(placed_machines):
        mid = str(m.get("id", f"M-{idx+1:03d}")).strip()
        eff = safe_machine_effective_rate(m)
        if min_rate is None or eff < min_rate:
            min_rate = eff
            best_id = mid

    return best_id, float(min_rate or 0.0)

def empty_optimization_report():
    """
    Safe default optimization report.
    """
    return {
        "report_type": "optimization_report",
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "overall_score": None,
        "subscores": {
            "flow_efficiency": None,
            "bottleneck_support": None,
            "safety_compliance": None,
            "utility_serviceability": None,
            "handling_wip": None,
        },
        "bottleneck_machine": None,
        "critical_links": [],
        "recommendations": [],
        "findings": {
            "flow": [],
            "bottleneck": [],
            "wip": [],
            "safety": [],
            "utility": [],
        },
        "status": "No optimization analysis available.",
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

def build_lighting_report(placed_lighting):
    rows = []
    for idx, l in enumerate(placed_lighting):
        rows.append({
            "id": l.get("id", f"L-{idx+1:03d}"),
            "make": l.get("Make", ""),
            "brand": l.get("Brand", ""),
            "type": l.get("Type", ""),
            "wattage": l.get("Wattage", 0.0),
            "kelvin": l.get("Kelvin", 0.0),
            "lumens": l.get("Lumens", 0.0),
            "x": l.get("x", 0.0),
            "y": l.get("y", 0.0),
        })

    return {
        "report_type": "lighting_report",
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "lighting": rows,
    }


def build_crane_report(placed_cranes):
    rows = []
    for idx, cr in enumerate(placed_cranes):
        ll_x = float(cr.get("ll_x", 0.0))
        ll_y = float(cr.get("ll_y", 0.0))
        ur_x = float(cr.get("ur_x", 0.0))
        ur_y = float(cr.get("ur_y", 0.0))

        rows.append({
            "id": cr.get("id", f"CR-{idx+1:03d}"),
            "center_x": (ll_x + ur_x) / 2.0,
            "center_y": (ll_y + ur_y) / 2.0,
            "width": ur_x - ll_x,
            "height": ur_y - ll_y,
            "ll_x": ll_x,
            "ll_y": ll_y,
            "ur_x": ur_x,
            "ur_y": ur_y,
        })

    return {
        "report_type": "crane_report",
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "cranes": rows,
    }


def build_workflow_report(workflow_paths):
    rows = []
    for idx, path in enumerate(workflow_paths or []):
        points = path.get("points", [])
        xs = [float(p.get("x", 0.0)) for p in points]
        ys = [float(p.get("y", 0.0)) for p in points]

        total_len = 0.0
        if len(xs) >= 2 and len(xs) == len(ys):
            for i in range(1, len(xs)):
                dx = xs[i] - xs[i - 1]
                dy = ys[i] - ys[i - 1]
                total_len += float(np.sqrt(dx**2 + dy**2))

        rows.append({
            "id": path.get("id", f"WF-{idx+1:03d}"),
            "point_count": len(points),
            "route_length_ft": round(total_len, 2),
            "movement_mode": path.get("movement_mode", ""),
            "speed_fpm": path.get("speed_fpm", None),
            "width_ft": path.get("width_ft", None),
            "centroid_x": (sum(xs) / len(xs)) if xs else 0.0,
            "centroid_y": (sum(ys) / len(ys)) if ys else 0.0,
        })

    return {
        "report_type": "workflow_report",
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "workflow_paths": rows,
    }

def build_full_report_bundle(session_state, workflow_paths=None):
    placed_machines = session_state.get("placed_machines", [])
    placed_lighting = session_state.get("placed_lighting", [])
    placed_conduits = session_state.get("placed_conduits", [])
    placed_cranes = session_state.get("placed_cranes", [])

    return {
        "schema_version": "report_bundle_1.1",
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
        "lighting_report": build_lighting_report(placed_lighting),
        "crane_report": build_crane_report(placed_cranes),
        "workflow_report": build_workflow_report(workflow_paths or []),
        "optimization_report": build_optimization_report(session_state, workflow_paths or []),
    }

def score_all_flow_links(machine_flows, machine_index):
    """
    Score value-added machine-to-machine links based on distance, flow rate,
    and transfer mode. Returns a dict with score, findings, and critical links.
    """
    if not machine_flows:
        return {
            "score": FLOW_EFFICIENCY_MAX_SCORE,
            "findings": [],
            "critical_links": [],
            "status": "No machine flow links defined.",
        }

    total_penalty = 0.0
    findings = []
    critical_links = []

    active_flow_count = 0

    for flow in machine_flows:
        if not bool(flow.get("value_added_step", True)):
            # Skip non-value-added links for primary flow-efficiency scoring
            continue

        active_flow_count += 1

        flow_id = str(flow.get("id", ""))
        from_id = str(flow.get("from_machine_id", "")).strip()
        to_id = str(flow.get("to_machine_id", "")).strip()

        if from_id not in machine_index or to_id not in machine_index:
            findings.append({
                "type": "invalid_flow_reference",
                "flow_id": flow_id,
                "from_machine_id": from_id,
                "to_machine_id": to_id,
                "message": "Flow references machine ID not present in current layout.",
            })
            total_penalty += 4.0
            continue

        m1 = machine_index[from_id]
        m2 = machine_index[to_id]
        dist_ft = machine_center_distance_ft(m1, m2)

        try:
            rate = float(flow.get("flow_rate_per_hr", 0.0))
        except Exception:
            rate = 0.0

        try:
            preferred_max = float(flow.get("preferred_max_distance_ft", 25.0))
        except Exception:
            preferred_max = 25.0

        mode = str(flow.get("transfer_mode", "human") or "human")
        mode_factor = float(TRANSFER_MODE_FACTORS.get(mode, 1.0))
        mandatory = bool(flow.get("mandatory_adjacency", False))

        rate_factor = min(max(rate / 25.0, 0.25), 4.0)
        excess_dist = max(0.0, dist_ft - preferred_max)

        penalty = excess_dist * mode_factor * rate_factor * 0.35

        if mandatory and dist_ft > preferred_max:
            penalty += 8.0

        total_penalty += penalty

        if dist_ft > preferred_max:
            findings.append({
                "type": "long_value_added_link",
                "flow_id": flow_id,
                "from_machine_id": from_id,
                "to_machine_id": to_id,
                "distance_ft": round(dist_ft, 2),
                "preferred_max_distance_ft": round(preferred_max, 2),
                "flow_rate_per_hr": round(rate, 2),
                "transfer_mode": mode,
                "mandatory_adjacency": mandatory,
                "message": (
                    f"Value-added flow {flow_id} exceeds preferred distance "
                    f"({dist_ft} ft > {preferred_max} ft)."
                ),
            })

        if penalty >= 5.0:
            critical_links.append({
                "flow_id": flow_id,
                "from_machine_id": from_id,
                "to_machine_id": to_id,
                "distance_ft": round(dist_ft, 2),
                "flow_rate_per_hr": round(rate, 2),
                "transfer_mode": mode,
                "issue": "High transfer distance on value-added link.",
            })

    if active_flow_count == 0:
        return {
            "score": FLOW_EFFICIENCY_MAX_SCORE,
            "findings": [],
            "critical_links": [],
            "status": "No value-added machine flow links defined.",
        }

    normalized_penalty = min(total_penalty / max(active_flow_count, 1), FLOW_EFFICIENCY_MAX_SCORE)
    score = max(0.0, round(FLOW_EFFICIENCY_MAX_SCORE - normalized_penalty, 1))

    return {
        "score": score,
        "findings": findings,
        "critical_links": critical_links,
        "status": "ok",
    }

def score_bottleneck_support(machine_flows, machine_index, bottleneck_id):
    """
    Score whether upstream/downstream support to bottleneck machine is spatially reasonable.
    """
    if not bottleneck_id:
        return {
            "score": BOTTLENECK_SUPPORT_MAX_SCORE,
            "findings": [],
            "status": "No bottleneck machine available.",
        }

    related_flows = []
    for flow in machine_flows:
        from_id = str(flow.get("from_machine_id", "")).strip()
        to_id = str(flow.get("to_machine_id", "")).strip()
        if from_id == bottleneck_id or to_id == bottleneck_id:
            related_flows.append(flow)

    if not related_flows:
        return {
            "score": 12.0,
            "findings": [{
                "type": "bottleneck_unmodeled",
                "machine_id": bottleneck_id,
                "message": "Bottleneck machine has no defined machine flow links.",
            }],
            "status": "partial",
        }

    penalty = 0.0
    findings = []

    for flow in related_flows:
        flow_id = str(flow.get("id", ""))
        from_id = str(flow.get("from_machine_id", "")).strip()
        to_id = str(flow.get("to_machine_id", "")).strip()

        if from_id not in machine_index or to_id not in machine_index:
            continue

        m1 = machine_index[from_id]
        m2 = machine_index[to_id]
        dist_ft = machine_center_distance_ft(m1, m2)

        # Default support threshold for bottleneck-facing links
        threshold_ft = 30.0
        if dist_ft > threshold_ft:
            local_penalty = min((dist_ft - threshold_ft) / 4.0, 6.0)
            penalty += local_penalty

            findings.append({
                "type": "bottleneck_support_distance",
                "flow_id": flow_id,
                "machine_id": bottleneck_id,
                "from_machine_id": from_id,
                "to_machine_id": to_id,
                "distance_ft": round(dist_ft, 2),
                "threshold_ft": threshold_ft,
                "message": (
                    f"Bottleneck-related link {flow_id} is spatially long "
                    f"({dist_ft} ft > {threshold_ft} ft)."
                ),
            })

    score = max(0.0, round(BOTTLENECK_SUPPORT_MAX_SCORE - min(penalty, BOTTLENECK_SUPPORT_MAX_SCORE), 1))

    return {
        "score": score,
        "findings": findings,
        "status": "ok",
    }

def score_wip_risk(machine_flows, machine_index):
    """
    Heuristic WIP risk score based on upstream/downstream imbalance + distance + transfer mode.
    """
    if not machine_flows:
        return {
            "score": HANDLING_WIP_MAX_SCORE,
            "findings": [],
            "status": "No machine flow links defined.",
        }

    penalty = 0.0
    findings = []

    for flow in machine_flows:
        from_id = str(flow.get("from_machine_id", "")).strip()
        to_id = str(flow.get("to_machine_id", "")).strip()
        flow_id = str(flow.get("id", "")).strip()

        if from_id not in machine_index or to_id not in machine_index:
            continue

        upstream = machine_index[from_id]
        downstream = machine_index[to_id]

        upstream_rate = safe_machine_effective_rate(upstream)
        downstream_rate = safe_machine_effective_rate(downstream)
        dist_ft = machine_center_distance_ft(upstream, downstream)

        mode = str(flow.get("transfer_mode", "human") or "human")
        value_added = bool(flow.get("value_added_step", True))

        # Focus on operationally relevant links
        if not value_added:
            continue

        if upstream_rate > downstream_rate and dist_ft > 25.0 and mode in {"human", "forklift"}:
            diff_ratio = min((upstream_rate - downstream_rate) / max(downstream_rate, 1.0), 2.0)
            local_penalty = 2.0 + diff_ratio + min((dist_ft - 25.0) / 10.0, 3.0)
            penalty += local_penalty

            findings.append({
                "type": "wip_risk",
                "flow_id": flow_id,
                "from_machine_id": from_id,
                "to_machine_id": to_id,
                "upstream_rate": round(upstream_rate, 2),
                "downstream_rate": round(downstream_rate, 2),
                "distance_ft": round(dist_ft, 2),
                "transfer_mode": mode,
                "message": (
                    f"Potential WIP accumulation risk on {flow_id}: upstream rate "
                    f"exceeds downstream rate over a long {mode} transfer."
                ),
            })

    score = max(0.0, round(HANDLING_WIP_MAX_SCORE - min(penalty, HANDLING_WIP_MAX_SCORE), 1))

    return {
        "score": score,
        "findings": findings,
        "status": "ok",
    }

def score_safety_penalties(placed_machines, placed_conduits, placed_cranes=None, workflow_paths=None):
    """
    Convert existing layout warnings into a bounded safety score.
    """
    warnings = run_layout_analysis(
        placed_machines,
        placed_conduits,
        placed_cranes or [],
        workflow_paths or [],
    )

    findings = []
    for w in warnings:
        findings.append({
            "type": "layout_warning",
            "message": str(w),
        })

    # Simple first-pass heuristic: each warning costs 2 points, capped.
    penalty = min(len(warnings) * 2.0, SAFETY_COMPLIANCE_MAX_SCORE)
    score = max(0.0, round(SAFETY_COMPLIANCE_MAX_SCORE - penalty, 1))

    return {
        "score": score,
        "findings": findings,
        "status": "ok",
    }

def score_utility_serviceability(placed_machines, placed_conduits):
    """
    Heuristic utility score based on rough proximity of utility-dependent machines
    to utility runs of matching type.
    """
    if not placed_machines:
        return {
            "score": UTILITY_SERVICEABILITY_MAX_SCORE,
            "findings": [],
            "status": "No machines placed.",
        }

    findings = []
    penalty = 0.0
    
    for idx, machine in enumerate(placed_machines):
        mid = str(machine.get("id", f"M-{idx+1:03d}"))

        needs_water = bool(machine.get("WaterHookup", False))
        vapor_port = str(machine.get("VaporPort", "VP-NONE"))
        try:
            wattage = float(machine.get("Wattage", 0.0))
        except Exception:
            wattage = 0.0

        preferred_utility_zone = str(machine.get("PreferredUtilityZone", "") or "")
        value_added_primary = bool(machine.get("ValueAddedPrimary", True))

        # Very simple checks for first release
        has_water_route = any(c.get("utility_type", "") == "water" for c in placed_conduits)
        has_hvac_route = any(c.get("utility_type", "") == "hvac" for c in placed_conduits)
        has_electrical_route = any(c.get("utility_type", "") == "electrical" for c in placed_conduits)

        weight = 1.5 if value_added_primary else 1.0

        if needs_water and not has_water_route:
            penalty += 2.0 * weight
            findings.append({
                "type": "missing_water_support",
                "machine_id": mid,
                "preferred_utility_zone": preferred_utility_zone,
                "message": f"Machine {mid} requires water hookup but no water route is defined.",
            })

        if vapor_port and vapor_port != "VP-NONE" and not has_hvac_route:
            penalty += 2.0 * weight
            findings.append({
                "type": "missing_hvac_support",
                "machine_id": mid,
                "preferred_utility_zone": preferred_utility_zone,
                "message": f"Machine {mid} has vapor port {vapor_port} but no HVAC route is defined.",
            })

        if wattage > 0 and not has_electrical_route:
            penalty += 1.0 * weight
            findings.append({
                "type": "missing_electrical_support",
                "machine_id": mid,
                "preferred_utility_zone": preferred_utility_zone,
                "message": f"Machine {mid} has electrical load but no electrical route is defined.",
            })

    score = max(0.0, round(UTILITY_SERVICEABILITY_MAX_SCORE - min(penalty, UTILITY_SERVICEABILITY_MAX_SCORE), 1))

    return {
        "score": score,
        "findings": findings,
        "status": "ok",
    }

def generate_layout_recommendations(
    machine_flows,
    machine_index,
    bottleneck_id,
    flow_findings,
    bottleneck_findings,
    wip_findings,
    safety_findings,
    utility_findings,
):
    """
    Build a ranked recommendation list from optimization findings.
    """
    recommendations = []

    # Priority 1: safety/compliance
    for item in safety_findings:
        recommendations.append({
            "priority": 1,
            "category": "safety",
            "message": str(item.get("message", "Resolve layout safety/compliance warning.")),
            "related_ids": [],
        })

    # Priority 2: bottleneck support
    for item in bottleneck_findings:
        msg = item.get("message", "")
        if item.get("type") == "bottleneck_unmodeled":
            msg = (
                f"Define machine flow links for bottleneck machine {item.get('machine_id')} "
                "to support placement optimization."
            )
        recommendations.append({
            "priority": 2,
            "category": "bottleneck",
            "message": msg,
            "related_ids": [
                item.get("machine_id"),
                item.get("from_machine_id"),
                item.get("to_machine_id"),
            ],
        })

    # Priority 3: long value-added links
    for item in flow_findings:
        if item.get("type") == "long_value_added_link":
            from_id = item.get("from_machine_id")
            to_id = item.get("to_machine_id")
            recommendations.append({
                "priority": 3,
                "category": "flow_distance",
                "message": (
                    f"Move {to_id} closer to {from_id} or reduce transfer distance on "
                    f"flow {item.get('flow_id')}."
                ),
                "related_ids": [item.get("flow_id"), from_id, to_id],
            })

    # Priority 4: WIP risk
    for item in wip_findings:
        recommendations.append({
            "priority": 4,
            "category": "wip",
            "message": (
                f"Reduce transfer distance or rebalance rates between "
                f"{item.get('from_machine_id')} and {item.get('to_machine_id')} "
                f"to reduce WIP risk."
            ),
            "related_ids": [
                item.get("flow_id"),
                item.get("from_machine_id"),
                item.get("to_machine_id"),
            ],
        })

    # Priority 5: utility support
    for item in utility_findings:
        preferred_zone = str(item.get("preferred_utility_zone", "") or "")
        base_message = str(item.get("message", "Improve utility support to machine."))

        if preferred_zone:
            base_message = f"{base_message} Preferred utility zone: {preferred_zone}."

        recommendations.append({
            "priority": 5,
            "category": "utility",
            "message": base_message,
            "related_ids": [item.get("machine_id")],
        })

    # De-duplicate basic repeats by message
    deduped = []
    seen = set()
    for rec in recommendations:
        key = (rec.get("priority"), rec.get("category"), rec.get("message"))
        if key not in seen:
            seen.add(key)
            deduped.append(rec)

    deduped.sort(key=lambda r: (r.get("priority", 99), str(r.get("message", ""))))
    return deduped[:20]

def build_optimization_report(session_state, workflow_paths=None):
    """
    Build composite optimization report for value-added placement analysis.
    """
    workflow_paths = workflow_paths or []

    placed_machines = session_state.get("placed_machines", [])
    placed_conduits = session_state.get("placed_conduits", [])
    placed_cranes = session_state.get("placed_cranes", [])
    machine_flows = session_state.get("machine_flows", [])

    if not placed_machines:
        report = empty_optimization_report()
        report["status"] = "No machines placed. Optimization report not generated."
        return report

    machine_index = index_machines_by_id(placed_machines)
    bottleneck_id, bottleneck_rate = find_bottleneck_machine(placed_machines)

    flow_score_data = score_all_flow_links(machine_flows, machine_index)
    bottleneck_score_data = score_bottleneck_support(machine_flows, machine_index, bottleneck_id)
    wip_score_data = score_wip_risk(machine_flows, machine_index)
    safety_score_data = score_safety_penalties(
        placed_machines,
        placed_conduits,
        placed_cranes,
        workflow_paths,
    )
    utility_score_data = score_utility_serviceability(
        placed_machines,
        placed_conduits,
    )

    overall_score = round(
        float(flow_score_data["score"])
        + float(bottleneck_score_data["score"])
        + float(safety_score_data["score"])
        + float(utility_score_data["score"])
        + float(wip_score_data["score"]),
        1,
    )

    recommendations = generate_layout_recommendations(
        machine_flows=machine_flows,
        machine_index=machine_index,
        bottleneck_id=bottleneck_id,
        flow_findings=flow_score_data["findings"],
        bottleneck_findings=bottleneck_score_data["findings"],
        wip_findings=wip_score_data["findings"],
        safety_findings=safety_score_data["findings"],
        utility_findings=utility_score_data["findings"],
    )

    return {
        "report_type": "optimization_report",
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "overall_score": overall_score,
        "subscores": {
            "flow_efficiency": flow_score_data["score"],
            "bottleneck_support": bottleneck_score_data["score"],
            "safety_compliance": safety_score_data["score"],
            "utility_serviceability": utility_score_data["score"],
            "handling_wip": wip_score_data["score"],
        },
        "bottleneck_machine": bottleneck_id,
        "bottleneck_effective_rate": round(bottleneck_rate, 2),
        "critical_links": flow_score_data["critical_links"],
        "recommendations": recommendations,
        "findings": {
            "flow": flow_score_data["findings"],
            "bottleneck": bottleneck_score_data["findings"],
            "wip": wip_score_data["findings"],
            "safety": safety_score_data["findings"],
            "utility": utility_score_data["findings"],
        },
        "status": "ok",
    }



