# visualization.py
import matplotlib.patches as patches
import matplotlib.pyplot as plt
import numpy as np
import plotly.graph_objects as go
import streamlit as st

def _draw_dim_line(ax, x1, y1, x2, y2, color='#00E5FF', lw=1.0, z=7):
  ax.plot([x1, x2], [y1, y2], color=color, lw=lw, zorder=z)

def _draw_ext_line(ax, x1, y1, x2, y2, color='#AAAAAA', lw=0.8, z=6):
  ax.plot([x1, x2], [y1, y2], color=color, lw=lw, zorder=z)

def _draw_tick(ax, x, y, dx, dy, color='#00E5FF', lw=1.0, z=7):
  ax.plot([x - dx, x + dx], [y - dy, y + dy], color=color, lw=lw, zorder=z)

def _machine_occ_box(m, O_x, O_y, S, include_standoff=True):
  mx_in = O_x + float(m['x']) * S
  my_in = O_y + float(m['y']) * S
  mw_in = float(m['Width']) * S
  mh_in = float(m['Height']) * S
  so_in = float(m.get('Standoff', 0.0)) * S if include_standoff else 0.0

  x_min = mx_in - mw_in / 2.0 - so_in
  x_max = mx_in + mw_in / 2.0 + so_in
  y_min = my_in - mh_in / 2.0 - so_in
  y_max = my_in + mh_in / 2.0 + so_in
  return x_min, x_max, y_min, y_max


def _hline_hits_any_machine(y_line, x0, x1, machines, self_idx, O_x, O_y, S, pad=0.04):
  xa = min(x0, x1)
  xb = max(x0, x1)

  for j, other in enumerate(machines):
    if j == self_idx:
      continue

    ox0, ox1, oy0, oy1 = _machine_occ_box(
        other, O_x, O_y, S, include_standoff=True
    )

    y_hits = (y_line >= oy0 - pad) and (y_line <= oy1 + pad)
    x_hits = not (xb < ox0 - pad or xa > ox1 + pad)

    if y_hits and x_hits:
      return True

  return False


def _vline_hits_any_machine(x_line, y0, y1, machines, self_idx, O_x, O_y, S, pad=0.04):
  ya = min(y0, y1)
  yb = max(y0, y1)

  for j, other in enumerate(machines):
    if j == self_idx:
      continue

    ox0, ox1, oy0, oy1 = _machine_occ_box(
        other, O_x, O_y, S, include_standoff=True
    )

    x_hits = (x_line >= ox0 - pad) and (x_line <= ox1 + pad)
    y_hits = not (yb < oy0 - pad or ya > oy1 + pad)

    if x_hits and y_hits:
      return True

  return False

def draw_asme_drawing(
    size_char='B',
    floor_width_ft=200.0,
    floor_height_ft=100.0,
    machines=[],
    conduits=[],
    lighting=[],
    workflow_paths=[],
    cranes=[],
    show_machines=True,
    show_lighting=True,
    show_cranes=True,
    show_workflow=True,
    show_electrical=True,
    show_safety=False,
    show_contour=False,
    show_decibel=False,
    show_locator_dims=False,
    locator_dim_mode='stacked',
    designer_name='FACILITY ARCHITECTS INC.',
    dwg_title='Factory Layout Blueprint',
    dwg_num='FFO-001',
):
  """Generates a standardized 2D ASME Y14.1 blueprint drawing."""
  sizes = {
      'A': (8.5, 11.0),
      'B': (11.0, 17.0),
      'C': (17.0, 22.0),
      'D': (22.0, 34.0),
  }
  height_in, width_in = sizes.get(size_char.upper(), (11.0, 17.0))

  margin = 0.50
  tb_w, tb_h = 6.25, 2.0

  # Scale factor calculation
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

  # Title Block Box
  tb_x, tb_y = width_in - margin - tb_w, margin
  ax.plot(
      [tb_x, tb_x, width_in - margin, width_in - margin, tb_x],
      [tb_y, tb_y + tb_h, tb_y + tb_h, tb_y, tb_y],
      color=yellow_color,
      lw=1.5,
  )

  # Dynamic Title Block Text
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
      f'Floor Scale: 1 in = {1.0/S:.1f} ft' if S > 0 else 'Floor Scale: N/A',
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

  # Dotted Grey Grid Lines Every 20 ft Inside Factory Floor Boundary
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

  # --- Draw Overhead Crane Coverage Areas ---
  if show_cranes:
    for idx, crane in enumerate(cranes):
      if 'll_x' in crane:
        x_min, y_min = crane['ll_x'], crane['ll_y']
        x_max, y_max = crane['ur_x'], crane['ur_y']
      elif 'x1' in crane:
        xs = [crane['x1'], crane['x2'], crane['x3'], crane['x4']]
        ys = [crane['y1'], crane['y2'], crane['y3'], crane['y4']]
        x_min, x_max = min(xs), max(xs)
        y_min, y_max = min(ys), max(ys)
      else:
        x_min, y_min, x_max, y_max = 0, 0, 10, 10

      c_x = [x_min, x_max, x_max, x_min]
      c_y = [y_min, y_min, y_max, y_max]

      c_x_in = [O_x + x * S for x in c_x]
      c_y_in = [O_y + y * S for y in c_y]

      poly_pts = list(zip(c_x_in, c_y_in))
      polygon = patches.Polygon(
          poly_pts,
          closed=True,
          facecolor='grey',
          edgecolor='#D3D3D3',
          alpha=0.35,
          linestyle='--',
          linewidth=1.5,
          zorder=2,
          label='Crane Coverage' if idx == 0 else '',
      )
      ax.add_patch(polygon)

      center_x = np.mean(c_x_in)
      center_y = np.mean(c_y_in)
      crane_label = f'C{idx+1}'
      ax.text(
          center_x,
          center_y,
          crane_label,
          fontsize=7,
          weight='bold',
          ha='center',
          va='center',
          color='#FFFFFF',
          bbox=dict(
              boxstyle='round,pad=0.2',
              facecolor='#222222',
              alpha=0.6,
              edgecolor='gray',
          ),
          zorder=3,
      )

  # --- Draw Heatmaps, Volume Contours, or Decibel Contour Plot ---
  if (
      (show_safety or show_contour or show_decibel)
      and len(machines) > 0
      and show_machines
  ):
    grid_x = np.linspace(0, floor_width_ft, 100)
    grid_y = np.linspace(0, floor_height_ft, 100)
    X, Y = np.meshgrid(grid_x, grid_y)

    if show_decibel:
      r0 = 3.0
      sum_intensity = np.zeros_like(X)

      for m in machines:
        db_0 = m.get('Decibel', 75.0)
        dist = np.sqrt((X - m['x']) ** 2 + (Y - m['y']) ** 2)
        r_eff = np.maximum(dist, r0)
        spl_i = db_0 - 20.0 * np.log10(r_eff / r0)
        sum_intensity += 10.0 ** (spl_i / 10.0)

      Z_db = 10.0 * np.log10(np.maximum(sum_intensity, 1e-12))
      Z_db = np.maximum(0.0, Z_db)

      X_plot = O_x + X * S
      Y_plot = O_y + Y * S

      z_max = np.max(Z_db)
      levels = np.linspace(0.0, max(10.0, z_max), 12)

      cf = ax.contourf(
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

      cbar = fig.colorbar(cf, ax=ax, fraction=0.025, pad=0.02)
      cbar.set_label(
          'Noise Level (dBA)', color='white', fontsize=8, weight='bold'
      )
      cbar.ax.yaxis.set_tick_params(
          color='white', labelcolor='white', labelsize=7
      )
      cbar.outline.set_edgecolor('gold')

    elif show_safety:
      Z_safety = np.zeros_like(X)
      for m in machines:
        dist = np.sqrt((X - m['x']) ** 2 + (Y - m['y']) ** 2)
        r = (max(m['Width'], m['Height']) / 2.0) + m['Standoff']
        Z_safety += np.exp(-dist / r)

      z_min = np.min(Z_safety)
      z_max = np.max(Z_safety)
      vmin, vmax = 0.0, max(1.0, z_max) if z_min != z_max else 1.0
      im = ax.imshow(
          Z_safety,
          extent=[O_x, O_x + W_drawn, O_y, O_y + H_drawn],
          origin='lower',
          cmap='RdYlGn_r',
          alpha=0.4,
          vmin=vmin,
          vmax=vmax,
          zorder=1,
      )

      cbar = fig.colorbar(im, ax=ax, fraction=0.025, pad=0.02)
      cbar.set_label(
          'Safety Overlap Risk Index', color='white', fontsize=8, weight='bold'
      )
      cbar.ax.yaxis.set_tick_params(
          color='white', labelcolor='white', labelsize=7
      )
      cbar.outline.set_edgecolor('gold')

    elif show_contour:
      Z_vol = np.zeros_like(X)
      for m in machines:
        dist_sq = (X - m['x']) ** 2 + (Y - m['y']) ** 2
        Z_vol += m['Volume'] * np.exp(-dist_sq / 1200)

      X_plot = O_x + X * S
      Y_plot = O_y + Y * S
      z_max = np.max(Z_vol)
      levels = np.linspace(0.0, z_max, 10) if z_max > 0 else [0.0, 1.0]
      cf = ax.contourf(
          X_plot,
          Y_plot,
          Z_vol,
          levels=levels,
          cmap='viridis',
          alpha=0.4,
          zorder=1,
      )

      cbar = fig.colorbar(cf, ax=ax, fraction=0.025, pad=0.02)
      cbar.set_label(
          'Part Volume Density (parts/hr)',
          color='white',
          fontsize=8,
          weight='bold',
      )
      cbar.ax.yaxis.set_tick_params(
          color='white', labelcolor='white', labelsize=7
      )
      cbar.outline.set_edgecolor('gold')

  # --- Draw Workflow Paths ---
  if show_workflow:
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

        if show_locator_dims and bool(st.session_state.get("workflow_dim_visible", True)):
          cx_ft = float(np.mean(x_pts))
          cy_ft = float(np.mean(y_pts))
          cx_in = O_x + cx_ft * S
          cy_in = O_y + cy_ft * S

          label_x_offset_in = float(
              st.session_state.get("workflow_dim_label_x_offset_ft", 0.0)
          ) * S
          label_y_offset_in = float(
              st.session_state.get("workflow_dim_label_y_offset_ft", 0.0)
          ) * S
          show_length = bool(st.session_state.get("workflow_dim_show_length", True))
          show_metadata = bool(st.session_state.get("workflow_dim_show_metadata", True))

          note_lines = ["Workflow Path"]

          if show_length:
            total_len = 0.0
            for i in range(1, len(x_pts)):
              dx = float(x_pts[i]) - float(x_pts[i - 1])
              dy = float(y_pts[i]) - float(y_pts[i - 1])
              total_len += np.sqrt(dx**2 + dy**2)
            note_lines.append(f"Len: {total_len:.1f} ft")

          if show_metadata:
            mode = path.get("movement_mode", "human")
            speed = path.get("speed_fpm", None)
            width = path.get("width_ft", None)
            meta = [str(mode)]
            if speed is not None:
              meta.append(f"{float(speed):.1f} spd")
            if width is not None:
              meta.append(f"{float(width):.1f} ft wide")
            note_lines.append(" / ".join(meta))

          ax.text(
              cx_in + label_x_offset_in,
              cy_in + label_y_offset_in,
              "\n".join(note_lines),
              fontsize=5.5,
              color='#FFFFFF',
              ha='center',
              va='center',
              zorder=8,
              bbox=dict(facecolor='#222222', edgecolor='gold', alpha=0.55, pad=1.0),
          )




  
  # Draw conduits
  if show_electrical:
    for cond in conduits:
      cx_in = [O_x + val * S for val in cond['x']]
      cy_in = [O_y + val * S for val in cond['y']]
      ax.plot(cx_in, cy_in, color='#FFA500', linestyle='-', lw=2, zorder=3)

  # Draw machines with M1, M2...
  if show_machines:
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

      if show_locator_dims:
        x_ft = float(m['x'])
        y_ft = float(m['y'])
        w_ft = float(m.get('Width', 0.0))
        h_ft = float(m.get('Height', 0.0))
        so_ft = float(m.get('Standoff', 0.0))

        half_w_in = mw_in / 2.0
        half_h_in = mh_in / 2.0
        so_in = so_ft * S

        clear_pad_in = max(0.18, 0.6 * so_in, 0.12 * max(mw_in, mh_in))
        ext_gap_in = 0.08
        tick_half = 0.04

        dim_color = '#00E5FF'
        ext_color = '#AAAAAA'
        txt_color = '#FFFFFF'

        stack_pitch = 0.28
        max_pushes = 20

        # Initial candidate locations:
        # - X dimension below this machine envelope
        # - Y dimension left of this machine envelope
        x_dim_y = my_in - half_h_in - so_in - clear_pad_in
        y_dim_x = mx_in - half_w_in - so_in - clear_pad_in

        # Push the X dimension down until it clears all other machines
        pushes = 0
        while _hline_hits_any_machine(
            x_dim_y, O_x, mx_in, machines, idx, O_x, O_y, S
        ) and pushes < max_pushes:
          x_dim_y -= stack_pitch
          pushes += 1

        # Small final stagger to reduce identical-line coincidence
        x_dim_y -= idx * 0.04

        # Push the Y dimension left until it clears all other machines
        pushes = 0
        while _vline_hits_any_machine(
            y_dim_x, O_y, my_in, machines, idx, O_x, O_y, S
        ) and pushes < max_pushes:
          y_dim_x -= stack_pitch
          pushes += 1

        # Small final stagger to reduce identical-line coincidence
        y_dim_x -= idx * 0.04

        # Keep dimensions from being pushed excessively outside the sheet
        x_dim_y = max(-0.5, x_dim_y)
        y_dim_x = max(-0.5, y_dim_x)

        # Editable per-machine dimension overrides are stored in feet and converted
        # into drawing-space units using scale factor S.
        dim_visible = bool(m.get("dim_visible", True))
        dim_x_line_offset_in = float(m.get("dim_x_line_offset_ft", 0.0)) * S
        dim_y_line_offset_in = float(m.get("dim_y_line_offset_ft", 0.0)) * S
        dim_x_text_offset_in = float(m.get("dim_x_text_offset_ft", 0.0)) * S
        dim_y_text_offset_in = float(m.get("dim_y_text_offset_ft", 0.0)) * S
        dim_show_footprint = bool(m.get("dim_show_footprint", True))

        if not dim_visible:
            continue

        x_dim_y -= dim_x_line_offset_in
        y_dim_x -= dim_y_line_offset_in
        
        # ----- X locator dimension -----
        _draw_dim_line(
            ax,
            O_x,
            x_dim_y,
            mx_in,
            x_dim_y,
            color=dim_color,
            lw=1.0,
            z=7,
        )

        _draw_ext_line(
            ax,
            O_x,
            O_y,
            O_x,
            x_dim_y + ext_gap_in,
            color=ext_color,
            lw=0.8,
            z=6,
        )

        x_ext_top = my_in - half_h_in - so_in - ext_gap_in
        _draw_ext_line(
            ax,
            mx_in,
            x_ext_top,
            mx_in,
            x_dim_y + ext_gap_in,
            color=ext_color,
            lw=0.8,
            z=6,
        )

        _draw_tick(
            ax, O_x, x_dim_y, tick_half, tick_half,
            color=dim_color, lw=1.0, z=7
        )
        _draw_tick(
            ax, mx_in, x_dim_y, tick_half, tick_half,
            color=dim_color, lw=1.0, z=7
        )

        ax.text(
            (O_x + mx_in) / 2.0,
            x_dim_y - 0.08 - dim_x_text_offset_in,
            f"X = {x_ft:.1f} ft",
            fontsize=6,
            color=txt_color,
            ha='center',
            va='top',
            zorder=8,
            bbox=dict(
                facecolor='#222222',
                edgecolor='none',
                alpha=0.55,
                pad=1.2,
            ),
        )

        # ----- Y locator dimension -----
        _draw_dim_line(
            ax,
            y_dim_x,
            O_y,
            y_dim_x,
            my_in,
            color=dim_color,
            lw=1.0,
            z=7,
        )

        _draw_ext_line(
            ax,
            O_x,
            O_y,
            y_dim_x + ext_gap_in,
            O_y,
            color=ext_color,
            lw=0.8,
            z=6,
        )

        y_ext_right = mx_in - half_w_in - so_in - ext_gap_in
        _draw_ext_line(
            ax,
            y_ext_right,
            my_in,
            y_dim_x + ext_gap_in,
            my_in,
            color=ext_color,
            lw=0.8,
            z=6,
        )

        _draw_tick(
            ax, y_dim_x, O_y, tick_half, tick_half,
            color=dim_color, lw=1.0, z=7
        )
        _draw_tick(
            ax, y_dim_x, my_in, tick_half, tick_half,
            color=dim_color, lw=1.0, z=7
        )

        ax.text(
            y_dim_x - 0.08 - dim_y_text_offset_in,
            (O_y + my_in) / 2.0,
            f"Y = {y_ft:.1f} ft",
            fontsize=6,
            color=txt_color,
            ha='right',
            va='center',
            rotation=90,
            zorder=8,
            bbox=dict(
                facecolor='#222222',
                edgecolor='none',
                alpha=0.55,
                pad=1.2,
            ),
        )

        # Optional footprint callout above machine
        if dim_show_footprint:
            ax.text(
                mx_in,
                my_in + half_h_in + so_in + 0.12,
                f"{w_ft:.1f}' x {h_ft:.1f}'",
                fontsize=6,
                color='#FFD700',
                ha='center',
                va='bottom',
                zorder=8,
                bbox=dict(
                    facecolor='#111111',
                    edgecolor='none',
                    alpha=0.45,
                    pad=1.0,
                ),
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
  if show_lighting:
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
        if show_locator_dims and bool(l.get("dim_visible", True)):
            lx_ft = float(l["x"])
            ly_ft = float(l["y"])

            dim_x_line_offset_in = float(l.get("dim_x_line_offset_ft", 0.0)) * S
            dim_y_line_offset_in = float(l.get("dim_y_line_offset_ft", 0.0)) * S
            dim_x_text_offset_in = float(l.get("dim_x_text_offset_ft", 0.0)) * S
            dim_y_text_offset_in = float(l.get("dim_y_text_offset_ft", 0.0)) * S
            dim_show_fixture_note = bool(l.get("dim_show_fixture_note", True))

            dim_color = '#66FFFF'
            ext_color = '#AAAAAA'
            txt_color = '#FFFFFF'

            x_dim_y = O_y - 0.45 - dim_x_line_offset_in
            y_dim_x = O_x - 0.45 - dim_y_line_offset_in

            _draw_dim_line(ax, O_x, x_dim_y, lx_in, x_dim_y, color=dim_color, lw=0.8, z=7)
            _draw_ext_line(ax, O_x, O_y, O_x, x_dim_y + 0.05, color=ext_color, lw=0.7, z=6)
            _draw_ext_line(ax, lx_in, ly_in, lx_in, x_dim_y + 0.05, color=ext_color, lw=0.7, z=6)
            _draw_tick(ax, O_x, x_dim_y, 0.03, 0.03, color=dim_color, lw=0.8, z=7)
            _draw_tick(ax, lx_in, x_dim_y, 0.03, 0.03, color=dim_color, lw=0.8, z=7)

            ax.text(
                (O_x + lx_in) / 2.0,
                x_dim_y - 0.05 - dim_x_text_offset_in,
                f"X = {lx_ft:.1f} ft",
                fontsize=5.5,
                color=txt_color,
                ha='center',
                va='top',
                zorder=8,
                bbox=dict(facecolor='#222222', edgecolor='none', alpha=0.5, pad=1.0),
            )

            _draw_dim_line(ax, y_dim_x, O_y, y_dim_x, ly_in, color=dim_color, lw=0.8, z=7)
            _draw_ext_line(ax, O_x, O_y, y_dim_x + 0.05, O_y, color=ext_color, lw=0.7, z=6)
            _draw_ext_line(ax, lx_in, ly_in, y_dim_x + 0.05, ly_in, color=ext_color, lw=0.7, z=6)
            _draw_tick(ax, y_dim_x, O_y, 0.03, 0.03, color=dim_color, lw=0.8, z=7)
            _draw_tick(ax, y_dim_x, ly_in, 0.03, 0.03, color=dim_color, lw=0.8, z=7)

            ax.text(
                y_dim_x - 0.05 - dim_y_text_offset_in,
                (O_y + ly_in) / 2.0,
                f"Y = {ly_ft:.1f} ft",
                fontsize=5.5,
                color=txt_color,
                ha='right',
                va='center',
                rotation=90,
                zorder=8,
                bbox=dict(facecolor='#222222', edgecolor='none', alpha=0.5, pad=1.0),
            )

            if dim_show_fixture_note:
              fixture_note = f"{l.get('Type', 'Light')} / {float(l.get('Wattage', 0.0)):.0f}W"
              ax.text(
                  lx_in + 0.12,
                  ly_in - 0.12,
                  fixture_note,
                  fontsize=5.5,
                  color='#FFD700',
                  ha='left',
                  va='top',
                  zorder=8,
                  bbox=dict(facecolor='#111111', edgecolor='none', alpha=0.4, pad=0.8),
              )

  ax.set_xlim(-1, width_in + 1)
  ax.set_ylim(-1, height_in + 1)
  ax.set_aspect('equal')
  ax.axis('off')
  return fig


def draw_3d_asme_factory_viewport(
    floor_w=200.0,
    floor_h=100.0,
    ceiling_h=25.0,
    machines=[],
    lighting=[],
    cranes=[],
    conduits=[],
    workflow_paths=[],
    show_machines=True,
    show_lighting=True,
    show_cranes=True,
    show_workflow=True,
    show_electrical=True,
):
  """Generates an interactive Plotly 3D WebGL viewport for plant floor walkthrough."""
  fig = go.Figure()

  # 1. Floor Plane (Z = 0)
  fig.add_trace(
      go.Mesh3d(
          x=[0, floor_w, floor_w, 0],
          y=[0, 0, floor_h, floor_h],
          z=[0, 0, 0, 0],
          i=[0, 0],
          j=[1, 2],
          k=[2, 3],
          color='#002B49',
          opacity=0.95,
          name='Factory Floor',
          showscale=False,
      )
  )

  # Grid lines on floor
  for x_grid in np.arange(0, floor_w + 20, 20):
    fig.add_trace(
        go.Scatter3d(
            x=[x_grid, x_grid],
            y=[0, floor_h],
            z=[0.1, 0.1],
            mode='lines',
            line=dict(color='#39FF14', width=1.5),
            showlegend=False,
            hoverinfo='none',
        )
    )
  for y_grid in np.arange(0, floor_h + 20, 20):
    fig.add_trace(
        go.Scatter3d(
            x=[0, floor_w],
            y=[y_grid, y_grid],
            z=[0.1, 0.1],
            mode='lines',
            line=dict(color='#39FF14', width=1.5),
            showlegend=False,
            hoverinfo='none',
        )
    )

  # 2. Machines 3D Cuboids
  if show_machines:
    for idx, m in enumerate(machines):
      mx, my = m['x'], m['y']
      mw, mh = m['Width'], m['Height']
      mz = m.get('Height3D', 8.0)

      x0, x1 = mx - mw / 2, mx + mw / 2
      y0, y1 = my - mh / 2, my + mh / 2
      z0, z1 = 0.0, mz

      vx = [x0, x1, x1, x0, x0, x1, x1, x0]
      vy = [y0, y0, y1, y1, y0, y0, y1, y1]
      vz = [z0, z0, z0, z0, z1, z1, z1, z1]

      i_idx = [7, 0, 0, 0, 4, 4, 2, 6, 4, 0, 3, 7]
      j_idx = [0, 1, 2, 3, 5, 1, 3, 7, 0, 1, 2, 6]
      k_idx = [4, 5, 6, 7, 1, 5, 7, 5, 1, 2, 6, 2]

      fig.add_trace(
          go.Mesh3d(
              x=vx,
              y=vy,
              z=vz,
              i=i_idx,
              j=j_idx,
              k=k_idx,
              color='#00A8E8',
              opacity=0.85,
              name=(
                  f"Machine M{idx+1} ({m.get('Make','')} {m.get('Model','')})"
              ),
              flatshading=True,
          )
      )

      fig.add_trace(
          go.Scatter3d(
              x=[mx],
              y=[my],
              z=[z1 + 2.0],
              mode='text',
              text=[f'M{idx+1}'],
              textposition='top center',
              textfont=dict(color='white', size=11, family='Arial Black'),
              showlegend=False,
          )
      )

  # 3. Overhead Cranes 3D Coverage Volumes & Bridge Girders
  if show_cranes:
    for idx, crane in enumerate(cranes):
      if 'll_x' in crane:
        x_min, y_min = crane['ll_x'], crane['ll_y']
        x_max, y_max = crane['ur_x'], crane['ur_y']
      elif 'x1' in crane:
        xs = [crane['x1'], crane['x2'], crane['x3'], crane['x4']]
        ys = [crane['y1'], crane['y2'], crane['y3'], crane['y4']]
        x_min, x_max = min(xs), max(xs)
        y_min, y_max = min(ys), max(ys)
      else:
        x_min, y_min, x_max, y_max = 20, 20, 180, 80

      z_crane_beam = ceiling_h - 2.0

      # 3D Transparent Grey Box Volume
      vx = [x_min, x_max, x_max, x_min, x_min, x_max, x_max, x_min]
      vy = [y_min, y_min, y_max, y_max, y_min, y_min, y_max, y_max]
      vz = [0, 0, 0, 0, z_crane_beam, z_crane_beam, z_crane_beam, z_crane_beam]

      i_idx = [7, 0, 0, 0, 4, 4, 2, 6, 4, 0, 3, 7]
      j_idx = [0, 1, 2, 3, 5, 1, 3, 7, 0, 1, 2, 6]
      k_idx = [4, 5, 6, 7, 1, 5, 7, 5, 1, 2, 6, 2]

      fig.add_trace(
          go.Mesh3d(
              x=vx,
              y=vy,
              z=vz,
              i=i_idx,
              j=j_idx,
              k=k_idx,
              color='#A0A0A0',
              opacity=0.25,
              name=f'Crane C{idx+1} Coverage Zone',
              flatshading=True,
          )
      )

      cx_mid = (x_min + x_max) / 2
      fig.add_trace(
          go.Scatter3d(
              x=[cx_mid, cx_mid],
              y=[y_min, y_max],
              z=[z_crane_beam, z_crane_beam],
              mode='lines+markers',
              line=dict(color='#FF6B00', width=8),
              marker=dict(size=6, color='yellow'),
              name=f'Crane C{idx+1} Bridge Girder',
          )
      )

      fig.add_trace(
          go.Scatter3d(
              x=[cx_mid],
              y=[(y_min + y_max) / 2],
              z=[z_crane_beam + 2.0],
              mode='text',
              text=[f'C{idx+1}'],
              textfont=dict(color='#FFD700', size=12, family='Arial Black'),
              showlegend=False,
          )
      )

  # 4. Lighting Fixtures at Ceiling Height
  if show_lighting:
    for idx, l in enumerate(lighting):
      lx, ly = l['x'], l['y']
      lz = ceiling_h - 1.0
      fig.add_trace(
          go.Scatter3d(
              x=[lx],
              y=[ly],
              z=[lz],
              mode='markers+text',
              marker=dict(size=8, color='gold', symbol='diamond'),
              text=[f'L{idx+1}'],
              textposition='top center',
              textfont=dict(color='gold', size=10),
              name=f'Lighting L{idx+1}',
          )
      )

  # 5. Workflow Paths in 3D
  if show_workflow:
    for path in workflow_paths:
      x_pts, y_pts = path.get('x', []), path.get('y', [])
      z_pts = [1.5] * len(x_pts)
      if len(x_pts) >= 2:
        fig.add_trace(
            go.Scatter3d(
                x=x_pts,
                y=y_pts,
                z=z_pts,
                mode='lines+markers',
                line=dict(color='#808080', width=6),
                marker=dict(size=5, color='#FFD700'),
                name='Workflow Path 3D',
            )
        )

  # 6. Electrical Underground Conduits (Z < 0)
  if show_electrical:
    for cond in conduits:
      cx_pts, cy_pts = cond.get('x', []), cond.get('y', [])
      cz_pts = [-2.0] * len(cx_pts)  # 2ft trench depth
      if len(cx_pts) >= 2:
        fig.add_trace(
            go.Scatter3d(
                x=cx_pts,
                y=cy_pts,
                z=cz_pts,
                mode='lines',
                line=dict(color='#FFA500', width=6),
                name=f"Conduit: {cond.get('label', 'Run')}",
            )
        )

  if show_locator_dims and bool(cond.get("dim_visible", True)):
        xs_ft = [float(v) for v in cond['x']]
        ys_ft = [float(v) for v in cond['y']]
        if len(xs_ft) >= 2 and len(xs_ft) == len(ys_ft):
          cx_ft = sum(xs_ft) / len(xs_ft)
          cy_ft = sum(ys_ft) / len(ys_ft)
          cx_in = O_x + cx_ft * S
          cy_in = O_y + cy_ft * S

          label_x_offset_in = float(cond.get("dim_label_x_offset_ft", 0.0)) * S
          label_y_offset_in = float(cond.get("dim_label_y_offset_ft", 0.0)) * S
          show_length = bool(cond.get("dim_show_length", True))
          show_metadata = bool(cond.get("dim_show_metadata", True))

          note_lines = [str(cond.get("label", cond.get("id", "Conduit")))]
          if show_length:
            total_len = 0.0
            for i in range(1, len(xs_ft)):
              dx = xs_ft[i] - xs_ft[i - 1]
              dy = ys_ft[i] - ys_ft[i - 1]
              total_len += np.sqrt(dx**2 + dy**2)
            note_lines.append(f"Len: {total_len:.1f} ft")

          if show_metadata:
            utility_type = cond.get("utility_type", "electrical")
            depth = cond.get("depth_in", None)
            if depth is not None:
              note_lines.append(f"{utility_type} / {depth} in")
            else:
              note_lines.append(f"{utility_type}")

          ax.text(
              cx_in + label_x_offset_in,
              cy_in + label_y_offset_in,
              "\n".join(note_lines),
              fontsize=5.5,
              color='#FFFFFF',
              ha='center',
              va='center',
              zorder=8,
              bbox=dict(facecolor='#222222', edgecolor='orange', alpha=0.55, pad=1.0),
          )  
  

  fig.update_layout(
      scene=dict(
          xaxis=dict(
              title='Floor Width X (ft)',
              range=[0, floor_w],
              backgroundcolor='#001F3F',
          ),
          yaxis=dict(
              title='Floor Height Y (ft)',
              range=[0, floor_h],
              backgroundcolor='#001F3F',
          ),
          zaxis=dict(
              title='Height Z (ft)',
              range=[-5, ceiling_h + 5],
              backgroundcolor='#001F3F',
          ),
          aspectmode='manual',
          aspectratio=dict(x=floor_w / 100, y=floor_h / 100, z=ceiling_h / 100),
          camera=dict(eye=dict(x=1.5, y=-1.5, z=1.2)),
      ),
      paper_bgcolor='#001529',
      margin=dict(l=0, r=0, b=0, t=30),
      title=dict(
          text=(
              '🕶️ Interactive 3D Factory Floor Viewport (Orbit / Zoom /'
              ' Walkthrough)'
          ),
          font=dict(color='white', size=14),
      ),
  )
  return fig
