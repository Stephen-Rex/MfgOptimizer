# visualization.py
import matplotlib.pyplot as plt
import numpy as np

def draw_asme_drawing(size_char="B", scale_factor=10.0, machines=[], conduits=[], show_safety=False, show_contour=False):
    """
    Renders factory layout inside standardized ASME Y14.1 margins and title block.
    """
    # 1. Standard boundaries (ASME Y14.1 Table 4-1)
    sizes = {"A": (8.5, 11.0), "B": (11.0, 17.0), "C": (17.0, 22.0), "D": (22.0, 34.0)}
    width_in, height_in = sizes.get(size_char.upper(), (11.0, 17.0))
    width_ft, height_ft = width_in * scale_factor, height_in * scale_factor
    
    fig, ax = plt.subplots(figsize=(10, 6.5))
    
    # 2. Draw border & format margin
    margin_ft = 0.50 * scale_factor
    ax.plot([0, width_ft, width_ft, 0, 0], [0, 0, height_ft, height_ft, 0], 'k-', lw=2)
    ax.plot([margin_ft, width_ft - margin_ft, width_ft - margin_ft, margin_ft, margin_ft],
            [margin_ft, margin_ft, height_ft - margin_ft, height_ft - margin_ft, margin_ft], 'k--', lw=1)
            
    # 3. Draw ASME Title Block (lower right)
    tb_w, tb_h = 6.25 * scale_factor, 2.0 * scale_factor
    tb_x, tb_y = width_ft - margin_ft - tb_w, margin_ft
    ax.plot([tb_x, tb_x, width_ft - margin_ft, width_ft - margin_ft, tb_x], [tb_y, tb_y + tb_h, tb_y + tb_h, tb_y, tb_y], 'r-', lw=1.5)
    
    ax.text(tb_x + 2, tb_y + tb_h - 4, "FACILITY ARCHITECTS INC.", fontsize=7, weight='bold')
    ax.text(tb_x + 2, tb_y + tb_h - 9, "TITLE: Factory Layout Blueprint", fontsize=7)
    ax.text(tb_x + 2, tb_y + tb_h - 14, f"DWG NO: FFO-001  SIZE: {size_char}", fontsize=7)
    
    # 4. Underlays: Contour or Safety Heatmap
    if (show_safety or show_contour) and len(machines) > 0:
        grid_x = np.linspace(0, width_ft, 100)
        grid_y = np.linspace(0, height_ft, 100)
        X, Y = np.meshgrid(grid_x, grid_y)
        
        if show_safety:
            Z_safety = np.zeros_like(X)
            for m in machines:
                dist = np.sqrt((X - m["x"])**2 + (Y - m["y"])**2)
                r = (max(m["Width"], m["Height"]) / 2.0) + m["Standoff"]
                Z_safety += np.exp(-dist / r)
            ax.imshow(Z_safety, extent=[0, width_ft, 0, height_ft], origin='lower', cmap='RdYlGn_r', alpha=0.5)
            
        elif show_contour:
            Z_vol = np.zeros_like(X)
            for m in machines:
                dist_sq = (X - m["x"])**2 + (Y - m["y"])**2
                Z_vol += m["Volume"] * np.exp(-dist_sq / 1200)
            ax.contourf(X, Y, Z_vol, cmap='viridis', alpha=0.5)
            
    # 5. Overlay machines and conduits
    for m in machines:
        mx, my = m["x"], m["y"]
        mw, mh = m["Width"], m["Height"]
        rect = plt.Rectangle((mx - mw/2, my - mh/2), mw, mh, fill=True, color='skyblue', alpha=0.8, edgecolor='blue', lw=1.5)
        ax.add_patch(rect)
        ax.text(mx, my, f"{m['Make']}\\n{m['Model']}", fontsize=6, ha='center', va='center')
        
        # Red standoff circle
        so = m["Standoff"]
        so_circ = plt.Circle((mx, my), (max(mw, mh)/2.0) + so, fill=False, color='red', linestyle=':', lw=1)
        ax.add_patch(so_circ)
        
    for cond in conduits:
        cx, cy = cond["x"], cond["y"]
        ax.plot(cx, cy, color='orange', linestyle='-', lw=2, label="Conduit Routing")
        
    ax.set_xlim(-5, width_ft + 5)
    ax.set_ylim(-5, height_ft + 5)
    ax.set_aspect('equal')
    ax.axis('off')
    return fig
