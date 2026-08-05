# visualization.py
import matplotlib.pyplot as plt
import numpy as np


def draw_asme_drawing(
    size_char='B',
    floor_width_ft=200.0,
    floor_height_ft=100.0,
    machines=[],
    conduits=[],
    lighting=[],
    workflow_paths=[],
    show_safety=False,
    show_contour=False,
    show_decibel=False,
    designer_name='Facility Architects Inc.',
    dwg_title='Factory Layout Blueprint',
    dwg_num='FFO-001',
):
  """Renders factory layout inside standardized ASME Y14.1 margins and title block.

  Renders workflow paths as a solid grey bar (1ft thick) with dotted yellow
  lines representing the safety standoff envelope (5ft normal offset). Labels
  machines as M1, M2... and lights as L1, L2... Adds 20ft dotted grey grid lines
  inside the factory floor boundary. Allows editing title block metadata
  (Designer, Title, Drawing Number). Includes Machine Decibel Acoustic Contour
  Plot using Inverse Square Law.
  """
  sizes = {
      'A': (8.5, 11.0),
      'B': (11.0, 17.0),
      'C': (17.0, 22.0),
      'D': (22.0, 34.0),
  }
  height_in, width_in = sizes.get(size_char.upper(), (11.0, 17.0))

  margin = 0.50
  tb_w, tb_h = 6.25, 2.0

  W1 = width_in - 2 * margin - tb_w
  H1 = height_in - 2 * margin
  S1 = min(W1 / floor_width_ft, H1 / floor_height_ft) if W1 > 0 else 0

  W2 = width_in - 2 * margin
  H2 = height_in - 2 * margin - tb_h
  S2 = min(W2 / floor_width_ft, H2 / floor_height_ft) if H2 > 0 else 0

  if S1 >= S2 and S1 > 0:
    S = S1
    W_drawn = floor_width_ft * S
    H_drawn = floor_height_ft * S
    O_x = margin + (W1 - W_drawn) / 2
    O_y = margin + (H1 - H_drawn) / 2
  elif S2 > S1 and S2 > 0:
    S = S2
    W_drawn = floor_width_ft * S
    H_drawn = floor_height_ft * S
    O_x = margin + (W2 - W_drawn) / 2
    O_y = margin + tb_h + (H2 - H_drawn) / 2
  else:
    S = min(
        (width_in - 2 * margin) / floor_width_ft,
        (height_in - 2 * margin) / floor_height_ft,
    )
    W_drawn = floor_width_ft * S
    H_drawn = floor_height_ft * S
    O_x = margin + (width_in - 2 * margin - W_drawn) / 2
    O_y = margin + (height_in - 2 * margin - H_drawn) / 2

  fig_w, fig_h = 10.0, 6.5
  fig, ax = plt.subplots(figsize=(fig_w, fig_h))

  blueprint_blue = '#002B49'
  fig.patch.set_facecolor(blueprint_blue)
  ax.set_facecolor(blueprint_blue)

  yellow_color = '#FFD700'
  ax.plot(
      [0, width_in, width_in, 0, 0],
      [0, 0, height_in, height_in, 0],
      color=yellow_color,
      lw=2,
  )
  ax.plot(
      [margin, width_in - margin, width_in - margin, margin, margin],
      [margin, margin, height_in - margin, height_in - margin, margin],
      color=yellow_color,
      linestyle='--',
      lw=1,
  )

  tb_x, tb_y = width_in - margin - tb_w, margin
  ax.plot(
      [tb_x, tb_x, width_in - margin, width_in - margin, tb_x],
      [tb_y, tb_y + tb_h, tb_y + tb_h, tb_y, tb_y],
      color=yellow_color,
      lw=1.5,
  )

  text_color = '#FFFFFF'
  ax.text(
      tb_x + 0.2,
      tb_y + tb_h - 0.4,
      str(designer_name).upper(),
      fontsize=7,
      weight='bold',
      color=text_color,
  )
  ax.text(
      tb_x + 0.2,
      tb_y + tb_h - 0.8,
      f'TITLE: {dwg_title}',
      fontsize=7,
      color=text_color,
  )
  ax.text(
      tb_x + 0.2,
      tb_y + tb_h - 1.2,
      f'DWG NO: {dwg_num}  SIZE: {size_char}',
      fontsize=7,
      color=text_color,
  )
  ax.text(
      tb_x + 0.2,
      tb_y + tb_h - 1.6,
      f'Floor Scale: 1 in = {1.0/S:.1f} ft',
      fontsize=6,
      color='#A0A0A0',
  )

  floor_green = '#39FF14'
  ax.plot(
      [O_x, O_x + W_drawn, O_x + W_drawn, O_x, O_x],
      [O_y, O_y, O_y + H_drawn, O_y + H_drawn, O_y],
      color=floor_green,
      lw=2,
      label='Factory Floor Boundary',
  )

  # --- Dotted Grey Grid Lines Every 20 ft Inside Factory Floor Boundary ---
  grid_color = '#808080'
  x_ticks = np.arange(20.0, floor_width_ft, 20.0)
  for x_ft in x_ticks:
    gx_in = O_x + x_ft * S
    ax.plot(
        [gx_in, gx_in],
        [O_y, O_y + H_drawn],
        color=grid_color,
        linestyle=':',
        lw=0.8,
        zorder=1,
        alpha=0.6,
    )

  y_ticks = np.arange(20.0, floor_height_ft, 20.0)
  for y_ft in y_ticks:
    gy_in = O_y + y_ft * S
    ax.plot(
        [O_x, O_x + W_drawn],
        [gy_in, gy_in],
        color=grid_color,
        linestyle=':',
        lw=0.8,
        zorder=1,
        alpha=0.6,
    )

  # --- Draw Heatmaps, Volume Contours, or Decibel Contour Plot ---
  if (show_safety or show_contour or show_decibel) and len(machines) > 0:
    grid_x = np.linspace(0, floor_width_ft, 100)
    grid_y = np.linspace(0, floor_height_ft, 100)
    X, Y = np.meshgrid(grid_x, grid_y)

    if show_decibel:
      # Sound Pressure Level (SPL) Inverse Square Law: L_p(r) = L_p0 - 20 * log10(r / r0)
      r0 = 3.0
      sum_intensity = np.zeros_like(X)

      for m in machines:
        db_0 = m.get('Decibel', 75.0)
        dist = np.sqrt((X - m['x']) ** 2 + (Y - m['y']) ** 2)
        r_eff = np.maximum(dist, r0)
        spl_i = db_0 - 20.0 * np.log10(r_eff / r0)
        sum_intensity += 10.0 ** (spl_i / 10.0)

      Z_db = 10.0 * np.log10(np.maximum(sum_intensity, 1e-12))

      X_plot = O_x + X * S
      Y_plot = O_y + Y * S

      z_min = np.min(Z_db)
      z_max = np.max(Z_db)
      levels = np.linspace(max(30.0, z_min), max(35.0, z_max), 12)

      ax.contourf(
          X_plot,
          Y_plot,
          Z_db,
          levels=levels,
          cmap='plasma',
          alpha=0.5,
          zorder=1,
      )
      ax.contour(
          X_plot,
          Y_plot,
          Z_db,
          levels=levels[::2],
          colors='white',
          linewidths=0.5,
          alpha=0.7,
          zorder=1,
      )

    elif show_safety:
      Z_safety = np.zeros_like(X)
      for m in machines:
        dist = np.sqrt((X - m['x']) ** 2 + (Y - m['y']) ** 2)
        r = (max(m['Width'], m['Height']) / 2.0) + m['Standoff']
        Z_safety += np.exp(-dist / r)

      z_min = np.min(Z_safety)
      z_max = np.max(Z_safety)
      vmin, vmax = 0.0, max(1.0, z_max) if z_min != z_max else 1.0
      ax.imshow(
          Z_safety,
          extent=[O_x, O_x + W_drawn, O_y, O_y + H_drawn],
          origin='lower',
          cmap='RdYlGn_r',
          alpha=0.4,
          vmin=vmin,
          vmax=vmax,
          zorder=1,
      )

    elif show_contour:
      Z_vol = np.zeros_like(X)
      for m in machines:
        dist_sq = (X - m['x']) ** 2 + (Y - m['y']) ** 2
        Z_vol += m['Volume'] * np.exp(-dist_sq / 1200)

      X_plot = O_x + X * S
      Y_plot = O_y + Y * S
      z_max = np.max(Z_vol)
      levels = np.linspace(0.0, z_max, 10) if z_max > 0 else [0.0, 1.0]
      ax.contourf(
          X_plot,
          Y_plot,
          Z_vol,
          levels=levels,
          cmap='viridis',
          alpha=0.4,
          zorder=1,
      )

  # --- Draw Workflow Paths ---
  data_width = width_in + 2.0
  points_per_data_inch = (fig_w / data_width) * 72.0

  for path in workflow_paths:
    x_pts = np.array(path['x'])
    y_pts = np.array(path['y'])
    standoffs = path.get('standoffs', [5.0] * len(x_pts))

    if len(x_pts) >= 2:
      x_in = O_x + x_pts * S
      y_in = O_y + y_pts * S

      bar_width_ft = path.get('width_ft', 1.0)
      bar_lw_pts = bar_width_ft * S * points_per_data_inch

      ax.plot(
          x_in,
          y_in,
          color='#808080',
          lw=max(1.5, bar_lw_pts),
          alpha=0.85,
          solid_capstyle='round',
          solid_joinstyle='round',
          zorder=2,
          label='Workflow Path',
      )

      dx = np.diff(x_pts)
      dy = np.diff(y_pts)
      lengths = np.sqrt(dx**2 + dy**2)
      lengths[lengths == 0] = 1e-6

      nx = -dy / lengths
      ny = dx / lengths

      vx_n = np.zeros(len(x_pts))
      vy_n = np.zeros(len(y_pts))
      vx_n[0], vy_n[0] = nx[0], ny[0]
      vx_n[-1], vy_n[-1] = nx[-1], ny[-1]

      for i in range(1, len(x_pts) - 1):
        vx_n[i] = (nx[i - 1] + nx[i]) / 2.0
        vy_n[i] = (ny[i - 1] + ny[i]) / 2.0
        v_len = np.sqrt(vx_n[i] ** 2 + vy_n[i] ** 2)
        if v_len > 0:
          vx_n[i] /= v_len
          vy_n[i] /= v_len

      st_in = np.array(standoffs) * S
      left_x = x_in + vx_n * st_in
      left_y = y_in + vy_n * st_in
      right_x = x_in - vx_n * st_in
      right_y = y_in - vy_n * st_in

      ax.plot(
          left_x,
          left_y,
          color='#FFD700',
          linestyle=':',
          lw=1.5,
          zorder=3,
          label='Safety Standoff Envelope',
      )
      ax.plot(
          right_x,
          right_y,
          color='#FFD700',
          linestyle=':',
          lw=1.5,
          zorder=3,
      )

      ax.scatter(
          x_in, y_in, color='#FFD700', s=25, zorder=4, edgecolor='black'
      )
      for idx, (px, py) in enumerate(zip(x_in, y_in)):
        ax.text(
            px,
            py + 0.12,
            f'P{idx+1}',
            color='#FFFFFF',
            fontsize=6,
            weight='bold',
            ha='center',
            zorder=5,
        )

  # Draw conduits
  for cond in conduits:
    cx_in = [O_x + val * S for val in cond['x']]
    cy_in = [O_y + val * S for val in cond['y']]
    ax.plot(cx_in, cy_in, color='#FFA500', linestyle='-', lw=2, zorder=3)

  # Draw machines with M1, M2...
  for idx, m in enumerate(machines):
    mx_in = O_x + m['x'] * S
    my_in = O_y + m['y'] * S
    mw_in = m['Width'] * S
    mh_in = m['Height'] * S

    rect = plt.Rectangle(
        (mx_in - mw_in / 2, my_in - mh_in / 2),
        mw_in,
        mh_in,
        fill=True,
        color='skyblue',
        alpha=0.85,
        edgecolor='white',
        lw=1.5,
        zorder=4,
    )
    ax.add_patch(rect)
    m_label = f'M{idx+1}'
    ax.text(
        mx_in,
        my_in,
        m_label,
        fontsize=7,
        weight='bold',
        ha='center',
        va='center',
        color='#FFFFFF',
        zorder=5,
    )

    so_in = m['Standoff'] * S
    so_circ = plt.Circle(
        (mx_in, my_in),
        (max(mw_in, mh_in) / 2.0) + so_in,
        fill=False,
        color='#FF3333',
        linestyle=':',
        lw=1,
        zorder=4,
    )
    ax.add_patch(so_circ)

  # Draw lighting with L1, L2...
  for idx, l in enumerate(lighting):
    lx_in = O_x + l['x'] * S
    ly_in = O_y + l['y'] * S
    ax.plot(
        lx_in,
        ly_in,
        marker='o',
        color='gold',
        markersize=8,
        markeredgecolor='black',
        markeredgewidth=1,
        zorder=5,
    )
    ax.plot(lx_in, ly_in, marker='*', color='white', markersize=4, zorder=6)
    l_label = f'L{idx+1}'
    ax.text(
        lx_in + 0.1,
        ly_in + 0.1,
        l_label,
        fontsize=6.5,
        weight='bold',
        color='#FFD700',
        zorder=7,
    )

  ax.set_xlim(-1, width_in + 1)
  ax.set_ylim(-1, height_in + 1)
  ax.set_aspect('equal')
  ax.axis('off')
  return fig
