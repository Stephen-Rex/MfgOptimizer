# visualization.py
import matplotlib.pyplot as plt
import numpy as np

def draw_asme_drawing(size_char='B', floor_width_ft=200.0, floor_height_ft=100.0, machines=[], conduits=[], lighting=[], show_safety=False, show_contour=False):
    """
    Renders factory layout inside standardized ASME Y14.1 margins, title block,
    scaling the custom-sized factory floor to fit inside the drawing sheet.
    """
    # Standard sheet sizes in inches (ASME Y14.1 Table 4-1)
    sizes = {'A': (8.5, 11.0), 'B': (11.0, 17.0), 'C': (17.0, 22.0), 'D': (22.0, 34.0)}
    height_in, width_in = sizes.get(size_char.upper(), (11.0, 17.0))
    
    # 1. Compute dynamic scale factor (inches per foot) to fit within margins (0.50 in all around)
    margin = 0.50
    W_avail = width_in - 2 * margin
    H_avail = height_in - 2 * margin
    
    S = min(W_avail / floor_width_ft, H_avail / floor_height_ft)
    
    W_drawn = floor_width_ft * S
    H_drawn = floor_height_ft * S
    
    # Offsets to center the floor inside margins
    O_x = margin + (W_avail - W_drawn) / 2
    O_y = margin + (H_avail - H_drawn) / 2
    
    fig, ax = plt.subplots(figsize=(10, 6.5))
    
    # Draw physical sheet border & format margin (in inches)
    ax.plot([0, width_in, width_in, 0, 0], [0, 0, height_in, height_in, 0], 'k-', lw=2)
    ax.plot([margin, width_in - margin, width_in - margin, margin, margin],
            [margin, margin, height_in - margin, height_in - margin, margin], 'k--', lw=1)
            
    # Draw standard ASME Title Block (lower right of sheet)
    tb_w, tb_h = 6.25, 2.0
    tb_x, tb_y = width_in - margin - tb_w, margin
    ax.plot([tb_x, tb_x, width_in - margin, width_in - margin, tb_x], [tb_y, tb_y + tb_h, tb_y + tb_h, tb_y, tb_y], 'r-', lw=1.5)
    
    ax.text(tb_x + 0.2, tb_y + tb_h - 0.4, 'FACILITY ARCHITECTS INC.', fontsize=7, weight='bold')
    ax.text(tb_x + 0.2, tb_y + tb_h - 0.8, 'TITLE: Factory Layout Blueprint', fontsize=7)
    ax.text(tb_x + 0.2, tb_y + tb_h - 1.2, f'DWG NO: FFO-001  SIZE: {size_char}', fontsize=7)
    ax.text(tb_x + 0.2, tb_y + tb_h - 1.6, f'Floor Scale: 1 in = {1.0/S:.1f} ft', fontsize=6, color='gray')
    
    # Draw green Factory Floor Boundary box (in inches)
    ax.plot([O_x, O_x + W_drawn, O_x + W_drawn, O_x, O_x], [O_y, O_y, O_y + H_drawn, O_y + H_drawn, O_y], 'g-', lw=2, label='Factory Floor Boundary')
    
    # Draw heatmaps or contour underlays (in plot inches)
    if (show_safety or show_contour) and len(machines) > 0:
        grid_x = np.linspace(0, floor_width_ft, 100)
        grid_y = np.linspace(0, floor_height_ft, 100)
        X, Y = np.meshgrid(grid_x, grid_y)
        
        if show_safety:
            Z_safety = np.zeros_like(X)
            for m in machines:
                dist = np.sqrt((X - m['x'])**2 + (Y - m['y'])**2)
                r = (max(m['Width'], m['Height']) / 2.0) + m['Standoff']
                Z_safety += np.exp(-dist / r)
                
            # Safe Normalization
            z_min = np.min(Z_safety)
            z_max = np.max(Z_safety)
            if z_min == z_max:
                vmin, vmax = 0.0, 1.0
            else:
                vmin, vmax = 0.0, max(1.0, z_max)
            ax.imshow(Z_safety, extent=[O_x, O_x + W_drawn, O_y, O_y + H_drawn], origin='lower', cmap='RdYlGn_r', alpha=0.5, vmin=vmin, vmax=vmax)
            
        elif show_contour:
            Z_vol = np.zeros_like(X)
            for m in machines:
                dist_sq = (X - m['x'])**2 + (Y - m['y'])**2
                Z_vol += m['Volume'] * np.exp(-dist_sq / 1200)
                
            X_plot = O_x + X * S
            Y_plot = O_y + Y * S
            
            z_max = np.max(Z_vol)
            if z_max == 0:
                levels = [0.0, 1.0]
                Z_vol = np.zeros_like(X)
            else:
                levels = np.linspace(0.0, z_max, 10)
            ax.contourf(X_plot, Y_plot, Z_vol, levels=levels, cmap='viridis', alpha=0.5)
            
    # Draw machines (mapped from feet to inches)
    for m in machines:
        mx_in = O_x + m['x'] * S
        my_in = O_y + m['y'] * S
        mw_in = m['Width'] * S
        mh_in = m['Height'] * S
        
        rect = plt.Rectangle((mx_in - mw_in/2, my_in - mh_in/2), mw_in, mh_in, fill=True, color='skyblue', alpha=0.8, edgecolor='blue', lw=1.5)
        ax.add_patch(rect)
        ax.text(mx_in, my_in, f'{m["Make"]}\n{m["Model"]}', fontsize=5, ha='center', va='center')
        
        # Red standoff circle
        so_in = m['Standoff'] * S
        so_circ = plt.Circle((mx_in, my_in), (max(mw_in, mh_in)/2.0) + so_in, fill=False, color='red', linestyle=':', lw=1)
        ax.add_patch(so_circ)
        
    # Draw conduits (mapped from feet to inches)
    for cond in conduits:
        cx_in = [O_x + val * S for val in cond['x']]
        cy_in = [O_y + val * S for val in cond['y']]
        ax.plot(cx_in, cy_in, color='orange', linestyle='-', lw=2)
        
    # Draw lighting fixtures (mapped from feet to inches)
    for l in lighting:
        lx_in = O_x + l['x'] * S
        ly_in = O_y + l['y'] * S
        ax.plot(lx_in, ly_in, marker='o', color='gold', markersize=10, markeredgecolor='black', markeredgewidth=1)
        ax.plot(lx_in, ly_in, marker='*', color='white', markersize=5)
        ax.text(lx_in + 0.1, ly_in + 0.1, f'{l["Make"]}\n{l["Brand"]}', fontsize=5, color='darkgoldenrod', weight='bold')
        
    ax.set_xlim(-1, width_in + 1)
    ax.set_ylim(-1, height_in + 1)
    ax.set_aspect('equal')
    ax.axis('off')
    return fig
