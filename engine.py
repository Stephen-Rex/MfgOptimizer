# engine.py
import numpy as np

def run_layout_analysis(placed_machines, placed_conduits):
    """
    Performs comprehensive spatial and regulatory checks on layout components.
    """
    warnings = []
    
    # 1. NJ-UCC Depth and Warning Tape Checks
    for cond in placed_conduits:
        depth = cond.get("depth_in", 36)
        has_tape = cond.get("warning_tape", True)
        label = cond.get("label", "Main Run")
        
        if depth < 36:
            warnings.append(f"NJ-UCC Viol: Conduit '{label}' depth of {depth} in is less than the required 36 in.")
        if not has_tape:
            warnings.append(f"NJ-UCC Viol: Conduit '{label}' must have standard orange 4 mil warning tape.")
            
    # 2. Safety Overlap Check (Standoff intersects with other machines)
    for i, m1 in enumerate(placed_machines):
        x1, y1 = m1["x"], m1["y"]
        r1 = (max(m1["Width"], m1["Height"]) / 2.0) + m1["Standoff"]
        
        for j, m2 in enumerate(placed_machines):
            if i >= j:
                continue
            x2, y2 = m2["x"], m2["y"]
            r2 = (max(m2["Width"], m2["Height"]) / 2.0) + m2["Standoff"]
            
            dist = np.sqrt((x1 - x2)**2 + (y1 - y2)**2)
            if dist < (r1 + r2):
                warnings.append(f"OSHA Safety Viol: Standoff overlap detected between '{m1['Make']}' and '{m2['Make']}'.")
                
    return warnings

def calculate_production_metrics(placed_machines, m_workers=3, cv_task=0.5):
    """
    Implements MPDI Switch-Off Energy Optimization & Bucket Brigade models.
    """
    if not placed_machines:
        return {}
        
    # Standard values
    volumes = [m["Volume"] for m in placed_machines]
    yields = [m["Yield"] / 100.0 for m in placed_machines]
    eff_vols = [v * y for v, y in zip(volumes, yields)]
    
    # Bottleneck is minimum throughput
    bn_idx = np.argmin(eff_vols)
    bottleneck_machine = placed_machines[bn_idx]
    
    # 1. MPDI Switch-Off Energy Model (UDP Sleep Cycle Savings)
    always_on_p = sum(12.0 * 6.4 + 5.35 * 1.6 for m in placed_machines) # kW hours/shift
    switch_off_p = sum(12.0 * 6.4 + 0.52 * 1.28 + 6.0 * 0.32 for m in placed_machines)
    energy_savings_pct = (1.0 - (switch_off_p / always_on_p)) * 100.0 if always_on_p > 0 else 0.0
    
    # 2. MPDI Bucket Brigades Assembly Simulator (Eq 3 & 4)
    total_time_min = sum(1.0 / (v * y) for v, y in zip(volumes, yields) if (v * y) > 0) * 60.0
    n_tasks = len(placed_machines)
    
    # Hand-off loss (h)
    h = (m_workers - 1) * ((cv_task**2 + 1) * total_time_min) / (2 * n_tasks) if n_tasks > 0 else 0.0
    E0 = total_time_min / (total_time_min + h) if (total_time_min + h) > 0 else 0.0
    
    # Estimated monthly throughput (9600 minutes steady state)
    throughput_month = int(E0 * m_workers / total_time_min * 9600) if total_time_min > 0 else 0
    
    return {
        "Bottleneck Machine": f"{bottleneck_machine['Make']} {bottleneck_machine['Model']}",
        "Line Balance Efficiency": f"{E0:.2%}",
        "Bucket Brigade Throughput": f"{throughput_month} assemblies/month",
        "UDP Switch-Off Savings": f"{energy_savings_pct:.1f}% idle power reduction"
    }

