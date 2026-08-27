    # interactive_canvas.py
import math
import pandas as pd
import plotly.graph_objects as go
import streamlit as st


def _object_center_machine(m):
    return float(m.get("x", 0.0)), float(m.get("y", 0.0))


def _object_center_light(l):
    return float(l.get("x", 0.0)), float(l.get("y", 0.0))


def _object_center_conduit(c):
    xs = [float(v) for v in c.get("x", [])]
    ys = [float(v) for v in c.get("y", [])]
    if xs and ys and len(xs) == len(ys):
        return sum(xs) / len(xs), sum(ys) / len(ys)
    return 0.0, 0.0


def _object_center_workflow():
    if "path_points" not in st.session_state or len(st.session_state.path_points) == 0:
        return 0.0, 0.0
    wdf = st.session_state.path_points
    xs = [float(v) for v in wdf["X Coordinate"].tolist()]
    ys = [float(v) for v in wdf["Y Coordinate"].tolist()]
    return sum(xs) / len(xs), sum(ys) / len(ys)


def _dist(x1, y1, x2, y2):
    return math.sqrt((float(x2) - float(x1)) ** 2 + (float(y2) - float(y1)) ** 2)

def _machine_dimension_geometry(m):
    mx = float(m.get("x", 0.0))
    my = float(m.get("y", 0.0))
    mw = float(m.get("Width", 0.0))
    mh = float(m.get("Height", 0.0))
    so = float(m.get("Standoff", 0.0))

    half_w = mw / 2.0
    half_h = mh / 2.0
    clear_pad = max(1.0, 0.6 * so, 0.12 * max(mw, mh))
    ext_gap = 0.4

    dim_x_line_offset_ft = float(m.get("dim_x_line_offset_ft", 0.0))
    dim_y_line_offset_ft = float(m.get("dim_y_line_offset_ft", 0.0))
    dim_x_text_offset_ft = float(m.get("dim_x_text_offset_ft", 0.0))
    dim_y_text_offset_ft = float(m.get("dim_y_text_offset_ft", 0.0))
    dim_x_text_anchor_ft = float(m.get("dim_x_text_anchor_ft", 0.0))
    dim_y_text_anchor_ft = float(m.get("dim_y_text_anchor_ft", 0.0))
    dim_x_side = str(m.get("dim_x_side", "below"))
    dim_y_side = str(m.get("dim_y_side", "left"))

    x_text_gap = 1.4
    y_text_gap = 7.0

    if dim_x_side == "above":
        x_dim_y = my + half_h + so + clear_pad + dim_x_line_offset_ft
        x_text_y = x_dim_y + x_text_gap + dim_x_text_offset_ft
        x_ext_obj_y = my + half_h + so + ext_gap
    else:
        x_dim_y = my - half_h - so - clear_pad - dim_x_line_offset_ft
        x_text_y = x_dim_y - x_text_gap - dim_x_text_offset_ft
        x_ext_obj_y = my - half_h - so - ext_gap

    if dim_y_side == "right":
        y_dim_x = mx + half_w + so + clear_pad + dim_y_line_offset_ft
        y_text_x = y_dim_x + y_text_gap + dim_y_text_offset_ft
        y_ext_obj_x = mx + half_w + so + ext_gap
    else:
        y_dim_x = mx - half_w - so - clear_pad - dim_y_line_offset_ft
        y_text_x = y_dim_x - y_text_gap - dim_y_text_offset_ft
        y_ext_obj_x = mx - half_w - so - ext_gap

    x_text_x = ((0.0 + mx) / 2.0) + dim_x_text_anchor_ft
    y_text_y = ((0.0 + my) / 2.0) + dim_y_text_anchor_ft

    return {
        "mx": mx,
        "my": my,
        "x_dim_y": x_dim_y,
        "x_text_x": x_text_x,
        "x_text_y": x_text_y,
        "x_ext_obj_y": x_ext_obj_y,
        "y_dim_x": y_dim_x,
        "y_text_x": y_text_x,
        "y_text_y": y_text_y,
        "y_ext_obj_x": y_ext_obj_x,
    }

def _lighting_dimension_geometry(l):
    lx = float(l.get("x", 0.0))
    ly = float(l.get("y", 0.0))

    clear_pad = 1.0
    ext_gap = 0.4

    dim_x_line_offset_ft = float(l.get("dim_x_line_offset_ft", 0.0))
    dim_y_line_offset_ft = float(l.get("dim_y_line_offset_ft", 0.0))
    dim_x_text_offset_ft = float(l.get("dim_x_text_offset_ft", 0.0))
    dim_y_text_offset_ft = float(l.get("dim_y_text_offset_ft", 0.0))
    dim_x_text_anchor_ft = float(l.get("dim_x_text_anchor_ft", 0.0))
    dim_y_text_anchor_ft = float(l.get("dim_y_text_anchor_ft", 0.0))
    dim_x_side = str(l.get("dim_x_side", "below"))
    dim_y_side = str(l.get("dim_y_side", "left"))

    x_text_gap = 1.4
    y_text_gap = 8.0

    if dim_x_side == "above":
        x_dim_y = ly + clear_pad + dim_x_line_offset_ft
        x_text_y = x_dim_y + x_text_gap + dim_x_text_offset_ft
        x_ext_obj_y = ly + ext_gap
    else:
        x_dim_y = ly - clear_pad - dim_x_line_offset_ft
        x_text_y = x_dim_y - x_text_gap - dim_x_text_offset_ft
        x_ext_obj_y = ly - ext_gap

    if dim_y_side == "right":
        y_dim_x = lx + clear_pad + dim_y_line_offset_ft
        y_text_x = y_dim_x + y_text_gap + dim_y_text_offset_ft
        y_ext_obj_x = lx + ext_gap
    else:
        y_dim_x = lx - clear_pad - dim_y_line_offset_ft
        y_text_x = y_dim_x - y_text_gap - dim_y_text_offset_ft
        y_ext_obj_x = lx - ext_gap

    x_text_x = ((0.0 + lx) / 2.0) + dim_x_text_anchor_ft
    y_text_y = ((0.0 + ly) / 2.0) + dim_y_text_anchor_ft

    return {
        "lx": lx,
        "ly": ly,
        "x_dim_y": x_dim_y,
        "x_text_x": x_text_x,
        "x_text_y": x_text_y,
        "x_ext_obj_y": x_ext_obj_y,
        "y_dim_x": y_dim_x,
        "y_text_x": y_text_x,
        "y_text_y": y_text_y,
        "y_ext_obj_x": y_ext_obj_x,
    }


def _conduit_note_geometry(c):
    xs = [float(v) for v in c.get("x", [])]
    ys = [float(v) for v in c.get("y", [])]
    if not xs or not ys or len(xs) != len(ys):
        return {"cx": 0.0, "cy": 0.0, "tx": 0.0, "ty": 0.0}

    cx = sum(xs) / len(xs)
    cy = sum(ys) / len(ys)
    tx = cx + float(c.get("dim_label_x_offset_ft", 0.0))
    ty = cy + float(c.get("dim_label_y_offset_ft", 0.0))
    return {"cx": cx, "cy": cy, "tx": tx, "ty": ty}


def _workflow_note_geometry():
    if "path_points" not in st.session_state or len(st.session_state.path_points) == 0:
        return {"cx": 0.0, "cy": 0.0, "tx": 0.0, "ty": 0.0}

    wdf = st.session_state.path_points
    xs = [float(v) for v in wdf["X Coordinate"].tolist()]
    ys = [float(v) for v in wdf["Y Coordinate"].tolist()]
    cx = sum(xs) / len(xs)
    cy = sum(ys) / len(ys)
    tx = cx + float(st.session_state.get("workflow_dim_label_x_offset_ft", 0.0))
    ty = cy + float(st.session_state.get("workflow_dim_label_y_offset_ft", 0.0))
    return {"cx": cx, "cy": cy, "tx": tx, "ty": ty}


def _crane_note_geometry(cr):
    ll_x = float(cr.get("ll_x", 0.0))
    ll_y = float(cr.get("ll_y", 0.0))
    ur_x = float(cr.get("ur_x", 0.0))
    ur_y = float(cr.get("ur_y", 0.0))
    cx = (ll_x + ur_x) / 2.0
    cy = (ll_y + ur_y) / 2.0
    tx = cx + float(cr.get("dim_label_x_offset_ft", 0.0))
    ty = cy + float(cr.get("dim_label_y_offset_ft", 0.0))
    return {"cx": cx, "cy": cy, "tx": tx, "ty": ty}

def _point_dimension_geometry(
    px,
    py,
    idx,
    base_x_offset=2.5,
    base_y_offset=2.5,
    stack_pitch=1.0,
    x_text_dx_ft=0.0,
    x_text_dy_ft=0.0,
    y_text_dx_ft=0.0,
    y_text_dy_ft=0.0,
):
    x_dim_y = 0.0 - base_x_offset - (idx * stack_pitch)
    y_dim_x = 0.0 - base_y_offset - (idx * stack_pitch)

    x_text_x = ((0.0 + float(px)) / 2.0) + float(x_text_dx_ft)
    x_text_y = (x_dim_y - 0.8) + float(x_text_dy_ft)

    y_text_x = (y_dim_x - 0.8) + float(y_text_dx_ft)
    y_text_y = ((0.0 + float(py)) / 2.0) + float(y_text_dy_ft)

    return {
        "px": float(px),
        "py": float(py),
        "x_dim_y": x_dim_y,
        "x_text_x": x_text_x,
        "x_text_y": x_text_y,
        "y_dim_x": y_dim_x,
        "y_text_x": y_text_x,
        "y_text_y": y_text_y,
    }

def build_interactive_canvas_figure():
    floor_w = float(st.session_state.floor_w)
    floor_h = float(st.session_state.floor_h)

    fig = go.Figure()

    canvas_mode = st.session_state.get("editor_canvas_mode", "select")
    show_dim_traces = canvas_mode == "dim"    

    # Trace map for Phase 3 click resolution via curveNumber
    st.session_state.editor_trace_map = []

    def _register_trace(entity_type, obj_index, sub_index=-1, obj_id=""):
        st.session_state.editor_trace_map.append(
            {
                "entity_type": str(entity_type),
                "obj_index": int(obj_index),
                "sub_index": int(sub_index),
                "id": str(obj_id),
            }
        )

    # Floor boundary
    fig.add_shape(
        type="rect",
        x0=0,
        y0=0,
        x1=floor_w,
        y1=floor_h,
        line=dict(color="#39FF14", width=3),
        fillcolor="rgba(0,0,0,0)",
        layer="below",
    )

   
    # Grid
    if st.session_state.get("editor_show_grid", True):
        grid_step = float(st.session_state.get("editor_snap_ft", 10.0))
        grid_step = max(grid_step, 1.0)

        x = 0.0
        while x <= floor_w:
            fig.add_shape(
                type="line",
                x0=x, y0=0, x1=x, y1=floor_h,
                line=dict(color="#1F3B4D", width=1),
                layer="below",
            )
            x += grid_step

        y = 0.0
        while y <= floor_h:
            fig.add_shape(
                type="line",
                x0=0, y0=y, x1=floor_w, y1=y,
                line=dict(color="#1F3B4D", width=1),
                layer="below",
            )
            y += grid_step

    # Machines
    for idx, m in enumerate(st.session_state.placed_machines):
        mx = float(m["x"])
        my = float(m["y"])
        mw = float(m["Width"])
        mh = float(m["Height"])
        so = float(m.get("Standoff", 0.0))
        mid = str(m.get("id", f"M-{idx+1:03d}"))

        is_selected = (
            st.session_state.editor_selected_type == "machine"
            and int(st.session_state.editor_selected_index) == idx
        )
        is_move_armed = (
            st.session_state.get("editor_move_awaiting_target", False)
            and st.session_state.get("editor_move_selected_type", "") == "machine"
            and int(st.session_state.get("editor_move_selected_index", -1)) == idx
        )

        x0 = mx - mw / 2.0
        x1 = mx + mw / 2.0
        y0 = my - mh / 2.0
        y1 = my + mh / 2.0

        fig.add_shape(
            type="rect",
            x0=x0,
            y0=y0,
            x1=x1,
            y1=y1,
            line=dict(
                color="#FFD700" if is_move_armed else ("#00E5FF" if is_selected else "#87CEEB"),
                width=4 if is_move_armed else (3 if is_selected else 2),
            ),
            fillcolor=(
                "rgba(255,215,0,0.25)" if is_move_armed
                else ("rgba(0,229,255,0.22)" if is_selected else "rgba(135,206,235,0.18)")
            ),
            layer="below",
        )

        if so > 0:
            fig.add_shape(
                type="rect",
                x0=x0 - so,
                y0=y0 - so,
                x1=x1 + so,
                y1=y1 + so,
                line=dict(
                    color="rgba(255,255,255,0.35)" if not is_selected else "rgba(255,215,0,0.65)",
                    width=1,
                    dash="dot",
                ),
                fillcolor="rgba(0,0,0,0)",
                layer="below",
            )

        fig.add_trace(
            go.Scatter(
                x=[x0, x1, x1, x0, x0],
                y=[y0, y0, y1, y1, y0],
                mode="lines",
                fill="toself",
                fillcolor="rgba(0,0,0,0.001)",
                line=dict(color="rgba(0,0,0,0)", width=0),
                showlegend=False,
                hoverinfo="skip",
                customdata=[["machine", idx, mid, -1]] * 5,
            )
        )
        _register_trace("machine", idx, -1, mid)

        fig.add_trace(
            go.Scatter(
                x=[mx],
                y=[my],
                mode="markers+text",
                marker=dict(
                    size=16 if is_move_armed else (14 if is_selected else 10),
                    color="#FFD700" if is_move_armed else ("#00E5FF" if is_selected else "#87CEEB"),
                    line=dict(color="white", width=2 if is_move_armed else 1),
                ),
                text=[mid],
                textposition="top center",
                name=mid,
                showlegend=False,
                customdata=[["machine", idx, mid, -1]],
                hovertemplate=f"{mid}<br>X={mx:.2f}<br>Y={my:.2f}<extra></extra>",
            )
        )
        _register_trace("machine", idx, -1, mid)

        # Machine dimension traces for moveable dimensions on plotly
        if show_dim_traces and bool(m.get("dim_visible", True)):
            g = _machine_dimension_geometry(m)

            is_x_armed = (
                st.session_state.get("editor_dim_move_awaiting_target", False)
                and st.session_state.get("editor_dim_selected_owner_type", "") == "machine"
                and int(st.session_state.get("editor_dim_selected_owner_index", -1)) == idx
                and st.session_state.get("editor_dim_selected_axis", "") == "x"
            )
            is_y_armed = (
                st.session_state.get("editor_dim_move_awaiting_target", False)
                and st.session_state.get("editor_dim_selected_owner_type", "") == "machine"
                and int(st.session_state.get("editor_dim_selected_owner_index", -1)) == idx
                and st.session_state.get("editor_dim_selected_axis", "") == "y"
            )

            x_color = "#FFD700" if is_x_armed else "#66FFFF"
            y_color = "#FFD700" if is_y_armed else "#66FFFF"
            ext_color = "#AAAAAA"

            # X dimension line
            fig.add_trace(
                go.Scatter(
                    x=[0.0, g["mx"]],
                    y=[g["x_dim_y"], g["x_dim_y"]],
                    mode="lines",
                    line=dict(color=x_color, width=2),
                    showlegend=False,
                    hoverinfo="skip",
                    customdata=[["dimension_machine_x_line", idx, mid, -1]] * 2,
                )
            )
            _register_trace("dimension_machine_x_line", idx, -1, mid)

            # X extension lines
            fig.add_trace(
                go.Scatter(
                    x=[0.0, 0.0, None, g["mx"], g["mx"]],
                    y=[0.0, g["x_dim_y"], None, g["x_ext_obj_y"], g["x_dim_y"]],
                    mode="lines",
                    line=dict(color=ext_color, width=1),
                    showlegend=False,
                    hoverinfo="skip",
                    customdata=[["dimension_machine_x_ext", idx, mid, -1]] * 5,
                )
            )
            _register_trace("dimension_machine_x_ext", idx, -1, mid)

            # X dimension visible text
            fig.add_trace(
                go.Scatter(
                    x=[g["x_text_x"]],
                    y=[g["x_text_y"]],
                    mode="text",
                    text=[f"X = {g['mx']:.1f} ft"],
                    textposition="middle center",
                    textfont=dict(color=x_color, size=12),
                    showlegend=False,
                    hoverinfo="skip",
                    #hovertemplate=f"{mid} X dimension<extra></extra>",
                )
            )
            _register_trace("dimension_machine_x_text_visual", idx, -1, mid)

            # X dimension click hitbox
            fig.add_trace(
                go.Scatter(
                    x=[g["x_text_x"]],
                    y=[g["x_text_y"]],
                    mode="markers",
                    marker=dict(
                        size=44,
                        color="rgba(255,215,0,0.22)" if is_x_armed else "rgba(0,255,255,0.10)",
                        line=dict(width=1, color="rgba(255,255,255,0.20)")
                    ),
                    showlegend=False,
                    customdata=[["dimension_machine_x_text", idx, mid, -1]],
                    hovertemplate=f"{mid} X dimension<extra></extra>",
                )
            )
            _register_trace("dimension_machine_x_text", idx, -1, mid)
            

            # Y dimension line
            fig.add_trace(
                go.Scatter(
                    x=[g["y_dim_x"], g["y_dim_x"]],
                    y=[0.0, g["my"]],
                    mode="lines",
                    line=dict(color=y_color, width=2),
                    showlegend=False,
                    hoverinfo="skip",
                    customdata=[["dimension_machine_y_line", idx, mid, -1]] * 2,
                )
            )
            _register_trace("dimension_machine_y_line", idx, -1, mid)

            # Y extension lines
            fig.add_trace(
                go.Scatter(
                    x=[0.0, g["y_dim_x"], None, g["y_ext_obj_x"], g["y_dim_x"]],
                    y=[0.0, 0.0, None, g["my"], g["my"]],
                    mode="lines",
                    line=dict(color=ext_color, width=1),
                    showlegend=False,
                    hoverinfo="skip",
                    customdata=[["dimension_machine_y_ext", idx, mid, -1]] * 5,
                )
            )
            _register_trace("dimension_machine_y_ext", idx, -1, mid)

            # Y dimension visible text
            fig.add_trace(
                go.Scatter(
                    x=[g["y_text_x"]],
                    y=[g["y_text_y"]],
                    mode="text",
                    text=[f"Y = {g['my']:.1f} ft"],
                    textposition="middle center",
                    textfont=dict(color=y_color, size=12),
                    showlegend=False,
                    hoverinfo="skip",
                )
            )
            _register_trace("dimension_machine_y_text_visual", idx, -1, mid)

            # Y dimension click hitbox
            fig.add_trace(
                go.Scatter(
                    x=[g["y_text_x"]],
                    y=[g["y_text_y"]],
                    mode="markers",
                    marker=dict(
                        size=44,
                        color="rgba(255,215,0,0.22)" if is_y_armed else "rgba(0,255,255,0.10)",
                        line=dict(width=1, color="rgba(255,255,255,0.20)")
                    ),
                    showlegend=False,
                    customdata=[["dimension_machine_y_text", idx, mid, -1]],
                    hovertemplate=f"{mid} Y dimension<extra></extra>",
                )
            )
            _register_trace("dimension_machine_y_text", idx, -1, mid)


    
    # Lighting
    for idx, l in enumerate(st.session_state.placed_lighting):
        lx = float(l["x"])
        ly = float(l["y"])
        lid = str(l.get("id", f"L-{idx+1:03d}"))

        is_selected = (
            st.session_state.editor_selected_type == "lighting"
            and int(st.session_state.editor_selected_index) == idx
        )

        is_move_armed = (
            st.session_state.get("editor_move_awaiting_target", False)
            and st.session_state.get("editor_move_selected_type", "") == "lighting"
            and int(st.session_state.get("editor_move_selected_index", -1)) == idx
        )

        fig.add_trace(
            go.Scatter(
                x=[lx],
                y=[ly],
                mode="markers+text",
                marker=dict(
                    size=18 if is_move_armed else (16 if is_selected else 12),
                    color="#FF00FF" if is_move_armed else "#FFD700",
                    symbol="diamond",
                    line=dict(color="#FFFFFF", width=3 if is_move_armed else (2 if is_selected else 1)),
                ),
                text=[lid],
                textposition="top center",
                name=lid,
                showlegend=False,
                customdata=[["lighting", idx, lid, -1]],
                hovertemplate=f"{lid}<br>X={lx:.2f}<br>Y={ly:.2f}<extra></extra>",
            )
        )
        _register_trace("lighting", idx, -1, lid)

        if show_dim_traces and bool(l.get("dim_visible", True)):
            g = _lighting_dimension_geometry(l)

            is_x_armed = (
                st.session_state.get("editor_dim_move_awaiting_target", False)
                and st.session_state.get("editor_dim_selected_owner_type", "") == "lighting"
                and int(st.session_state.get("editor_dim_selected_owner_index", -1)) == idx
                and st.session_state.get("editor_dim_selected_axis", "") == "x"
            )
            is_y_armed = (
                st.session_state.get("editor_dim_move_awaiting_target", False)
                and st.session_state.get("editor_dim_selected_owner_type", "") == "lighting"
                and int(st.session_state.get("editor_dim_selected_owner_index", -1)) == idx
                and st.session_state.get("editor_dim_selected_axis", "") == "y"
            )

            x_color = "#FFD700" if is_x_armed else "#66FFFF"
            y_color = "#FFD700" if is_y_armed else "#66FFFF"
            ext_color = "#AAAAAA"

            fig.add_trace(go.Scatter(
                x=[0.0, g["lx"]],
                y=[g["x_dim_y"], g["x_dim_y"]],
                mode="lines",
                line=dict(color=x_color, width=2),
                showlegend=False,
                hoverinfo="skip",
                customdata=[["dimension_lighting_x_line", idx, lid, -1]] * 2,
            ))
            _register_trace("dimension_lighting_x_line", idx, -1, lid)

            fig.add_trace(go.Scatter(
                x=[0.0, 0.0, None, g["lx"], g["lx"]],
                y=[0.0, g["x_dim_y"], None, g["x_ext_obj_y"], g["x_dim_y"]],
                mode="lines",
                line=dict(color=ext_color, width=1),
                showlegend=False,
                hoverinfo="skip",
                customdata=[["dimension_lighting_x_ext", idx, lid, -1]] * 5,
            ))
            _register_trace("dimension_lighting_x_ext", idx, -1, lid)

            fig.add_trace(go.Scatter(
                x=[g["x_text_x"]],
                y=[g["x_text_y"]],
                mode="text",
                text=[f"X = {g['lx']:.1f} ft"],
                textposition="middle center",
                textfont=dict(color=x_color, size=12),
                showlegend=False,
                hoverinfo="skip",
            ))
            _register_trace("dimension_lighting_x_text_visual", idx, -1, lid)

            fig.add_trace(go.Scatter(
                x=[g["x_text_x"]],
                y=[g["x_text_y"]],
                mode="markers",
                marker=dict(
                    size=44,
                    color="rgba(255,215,0,0.22)" if is_x_armed else "rgba(0,255,255,0.10)",
                    line=dict(width=1, color="rgba(255,255,255,0.20)")
                ),
                showlegend=False,
                customdata=[["dimension_lighting_x_text", idx, lid, -1]],
                hovertemplate=f"{lid} X dimension<extra></extra>",
            ))
            _register_trace("dimension_lighting_x_text", idx, -1, lid)

            fig.add_trace(go.Scatter(
                x=[g["y_dim_x"], g["y_dim_x"]],
                y=[0.0, g["ly"]],
                mode="lines",
                line=dict(color=y_color, width=2),
                showlegend=False,
                hoverinfo="skip",
                customdata=[["dimension_lighting_y_line", idx, lid, -1]] * 2,
            ))
            _register_trace("dimension_lighting_y_line", idx, -1, lid)

            fig.add_trace(go.Scatter(
                x=[0.0, g["y_dim_x"], None, g["y_ext_obj_x"], g["y_dim_x"]],
                y=[0.0, 0.0, None, g["ly"], g["ly"]],
                mode="lines",
                line=dict(color=ext_color, width=1),
                showlegend=False,
                hoverinfo="skip",
                customdata=[["dimension_lighting_y_ext", idx, lid, -1]] * 5,
            ))
            _register_trace("dimension_lighting_y_ext", idx, -1, lid)

            fig.add_trace(go.Scatter(
                x=[g["y_text_x"]],
                y=[g["y_text_y"]],
                mode="text",
                text=[f"Y = {g['ly']:.1f} ft"],
                textposition="middle center",
                textfont=dict(color=y_color, size=12),
                showlegend=False,
                hoverinfo="skip",
            ))
            _register_trace("dimension_lighting_y_text_visual", idx, -1, lid)

            fig.add_trace(go.Scatter(
                x=[g["y_text_x"]],
                y=[g["y_text_y"]],
                mode="markers",
                marker=dict(
                    size=44,
                    color="rgba(255,215,0,0.22)" if is_y_armed else "rgba(0,255,255,0.10)",
                    line=dict(width=1, color="rgba(255,255,255,0.20)")
                ),
                showlegend=False,
                customdata=[["dimension_lighting_y_text", idx, lid, -1]],
                hovertemplate=f"{lid} Y dimension<extra></extra>",
            ))
            _register_trace("dimension_lighting_y_text", idx, -1, lid)

    # Conduits
    for idx, c in enumerate(st.session_state.placed_conduits):
        xs = [float(v) for v in c.get("x", [])]
        ys = [float(v) for v in c.get("y", [])]
        cid = str(c.get("id", f"C-{idx+1:03d}"))

        is_selected = (
            st.session_state.editor_selected_type == "conduit"
            and int(st.session_state.editor_selected_index) == idx
        )

        is_move_armed_line = (
            st.session_state.get("editor_move_awaiting_target", False)
            and st.session_state.get("editor_move_selected_type", "") == "conduit"
            and int(st.session_state.get("editor_move_selected_index", -1)) == idx
        )

        if len(xs) >= 2 and len(xs) == len(ys):
            fig.add_trace(
                go.Scatter(
                    x=xs,
                    y=ys,
                    mode="lines",
                    line=dict(
                        color="#FFD700" if is_move_armed_line else "#FFA500",
                        width=5 if is_move_armed_line else (4 if is_selected else 3),
                    ),
                    name=cid,
                    showlegend=False,
                    customdata=[["conduit", idx, cid, -1]] * len(xs),
                    hovertemplate=f"{cid}<extra></extra>",
                )
            )
            _register_trace("conduit", idx, -1, cid)

            for p_idx, (px, py) in enumerate(zip(xs, ys)):
                v_selected = (
                    is_selected
                    and int(st.session_state.get("editor_selected_vertex_index", 0)) == p_idx
                )

                v_move_armed = (
                    st.session_state.get("editor_move_awaiting_target", False)
                    and st.session_state.get("editor_move_selected_type", "") == "conduit_vertex"
                    and int(st.session_state.get("editor_move_selected_index", -1)) == idx
                    and int(st.session_state.get("editor_move_selected_vertex_index", -1)) == p_idx
                )
                fig.add_trace(
                    go.Scatter(
                        x=[px],
                        y=[py],
                        mode="markers+text",
                        marker=dict(
                            size=16 if v_move_armed else (14 if v_selected else 10),
                            color="#FFD700" if v_move_armed else ("#FF00FF" if v_selected else "#FFD700"),
                            line=dict(color="black", width=2 if v_move_armed else 1),
                        ),
                        text=[f"CV{p_idx+1}"],
                        textposition="top center",
                        showlegend=False,
                        customdata=[["conduit_vertex", idx, cid, p_idx]],
                        hovertemplate=f"{cid} V{p_idx+1}<br>X={px:.2f}<br>Y={py:.2f}<extra></extra>",
                    )
                )
                _register_trace("conduit_vertex", idx, p_idx, cid)

                if show_dim_traces and bool(c.get("dim_visible", True)):
                    vertex_dim_offsets = c.get("vertex_dim_offsets", {})
                    v_off = vertex_dim_offsets.get(str(p_idx), {})
                    g = _point_dimension_geometry(
                        px,
                        py,
                        p_idx,
                        base_x_offset=2.5,
                        base_y_offset=2.5,
                        stack_pitch=1.0,
                        x_text_dx_ft=float(v_off.get("x_text_dx_ft", 0.0)),
                        x_text_dy_ft=float(v_off.get("x_text_dy_ft", 0.0)),
                        y_text_dx_ft=float(v_off.get("y_text_dx_ft", 0.0)),
                        y_text_dy_ft=float(v_off.get("y_text_dy_ft", 0.0)),
                    )
                    dim_color = "#FFD700" if v_selected else "#66FFFF"
                    ext_color = "#AAAAAA"

                    # X dim line
                    fig.add_trace(go.Scatter(
                        x=[0.0, g["px"]],
                        y=[g["x_dim_y"], g["x_dim_y"]],
                        mode="lines",
                        line=dict(color=dim_color, width=1.5),
                        showlegend=False,
                        hoverinfo="skip",
                        customdata=[[f"dimension_conduit_vertex_x_line", idx, cid, p_idx]] * 2,
                    ))
                    _register_trace("dimension_conduit_vertex_x_line", idx, p_idx, cid)

                    # X ext lines
                    fig.add_trace(go.Scatter(
                        x=[0.0, 0.0, None, g["px"], g["px"]],
                        y=[0.0, g["x_dim_y"], None, g["py"], g["x_dim_y"]],
                        mode="lines",
                        line=dict(color=ext_color, width=1),
                        showlegend=False,
                        hoverinfo="skip",
                        customdata=[[f"dimension_conduit_vertex_x_ext", idx, cid, p_idx]] * 5,
                    ))
                    _register_trace("dimension_conduit_vertex_x_ext", idx, p_idx, cid)

                    # X text
                    fig.add_trace(go.Scatter(
                        x=[g["x_text_x"]],
                        y=[g["x_text_y"]],
                        mode="text",
                        text=[f"X = {g['px']:.1f} ft"],
                        textposition="middle center",
                        textfont=dict(color=dim_color, size=11),
                        showlegend=False,
                        hoverinfo="skip",
                    ))
                    _register_trace("dimension_conduit_vertex_x_text_visual", idx, p_idx, cid)

                    # X hitbox
                    fig.add_trace(go.Scatter(
                        x=[g["x_text_x"]],
                        y=[g["x_text_y"]],
                        mode="markers",
                        marker=dict(
                            size=36,
                            color="rgba(0,255,255,0.08)",
                            line=dict(width=1, color="rgba(255,255,255,0.15)")
                        ),
                        showlegend=False,
                        customdata=[["dimension_conduit_vertex_x_text", idx, cid, p_idx]],
                        hovertemplate=f"{cid} vertex {p_idx+1} X dimension<extra></extra>",
                    ))
                    _register_trace("dimension_conduit_vertex_x_text", idx, p_idx, cid)

                    # Y dim line
                    fig.add_trace(go.Scatter(
                        x=[g["y_dim_x"], g["y_dim_x"]],
                        y=[0.0, g["py"]],
                        mode="lines",
                        line=dict(color=dim_color, width=1.5),
                        showlegend=False,
                        hoverinfo="skip",
                        customdata=[[f"dimension_conduit_vertex_y_line", idx, cid, p_idx]] * 2,
                    ))
                    _register_trace("dimension_conduit_vertex_y_line", idx, p_idx, cid)

                    # Y ext lines
                    fig.add_trace(go.Scatter(
                        x=[0.0, g["y_dim_x"], None, g["px"], g["y_dim_x"]],
                        y=[0.0, 0.0, None, g["py"], g["py"]],
                        mode="lines",
                        line=dict(color=ext_color, width=1),
                        showlegend=False,
                        hoverinfo="skip",
                        customdata=[[f"dimension_conduit_vertex_y_ext", idx, cid, p_idx]] * 5,
                    ))
                    _register_trace("dimension_conduit_vertex_y_ext", idx, p_idx, cid)

                    # Y text
                    fig.add_trace(go.Scatter(
                        x=[g["y_text_x"]],
                        y=[g["y_text_y"]],
                        mode="text",
                        text=[f"Y = {g['py']:.1f} ft"],
                        textposition="middle center",
                        textfont=dict(color=dim_color, size=11),
                        showlegend=False,
                        hoverinfo="skip",
                    ))
                    _register_trace("dimension_conduit_vertex_y_text_visual", idx, p_idx, cid)

                    # Y hitbox
                    fig.add_trace(go.Scatter(
                        x=[g["y_text_x"]],
                        y=[g["y_text_y"]],
                        mode="markers",
                        marker=dict(
                            size=36,
                            color="rgba(0,255,255,0.08)",
                            line=dict(width=1, color="rgba(255,255,255,0.15)")
                        ),
                        showlegend=False,
                        customdata=[["dimension_conduit_vertex_y_text", idx, cid, p_idx]],
                        hovertemplate=f"{cid} vertex {p_idx+1} Y dimension<extra></extra>",
                    ))
                    _register_trace("dimension_conduit_vertex_y_text", idx, p_idx, cid)


            
            if show_dim_traces and bool(c.get("dim_visible", True)):
                g = _conduit_note_geometry(c)
                is_note_armed = (
                    st.session_state.get("editor_dim_move_awaiting_target", False)
                    and st.session_state.get("editor_dim_selected_owner_type", "") == "conduit"
                    and int(st.session_state.get("editor_dim_selected_owner_index", -1)) == idx
                    and st.session_state.get("editor_dim_selected_axis", "") == "note"
                )

                note_color = "#FFD700" if is_note_armed else "#FFFFFF"

                fig.add_trace(go.Scatter(
                    x=[g["tx"]],
                    y=[g["ty"]],
                    mode="text",
                    text=[str(c.get("label", cid))],
                    textposition="middle center",
                    textfont=dict(color=note_color, size=12),
                    showlegend=False,
                    hoverinfo="skip",
                ))
                _register_trace("dimension_conduit_note_visual", idx, -1, cid)

                fig.add_trace(go.Scatter(
                    x=[g["tx"]],
                    y=[g["ty"]],
                    mode="markers",
                    marker=dict(
                        size=48,
                        color="rgba(255,215,0,0.20)" if is_note_armed else "rgba(255,255,255,0.08)",
                        line=dict(width=1, color="rgba(255,255,255,0.20)")
                    ),
                    showlegend=False,
                    customdata=[["dimension_conduit_note", idx, cid, -1]],
                    hovertemplate=f"{cid} note<extra></extra>",
                ))
                _register_trace("dimension_conduit_note", idx, -1, cid)

    # Workflow
    if "path_points" in st.session_state and len(st.session_state.path_points) >= 2:
        wdf = st.session_state.path_points
        xs = [float(v) for v in wdf["X Coordinate"].tolist()]
        ys = [float(v) for v in wdf["Y Coordinate"].tolist()]

        is_selected = st.session_state.editor_selected_type == "workflow"

        is_move_armed_line = (
            st.session_state.get("editor_move_awaiting_target", False)
            and st.session_state.get("editor_move_selected_type", "") == "workflow_point"
        )

        fig.add_trace(
            go.Scatter(
                x=xs,
                y=ys,
                mode="lines",
                line=dict(
                    color="#FFD700" if is_move_armed_line else "#808080",
                    width=6 if is_move_armed_line else (5 if is_selected else 4),
                ),
                name="WF-001",
                showlegend=False,
                customdata=[["workflow", 0, "WF-001", -1]] * len(xs),
                hovertemplate="WF-001<extra></extra>",
            )
        )
        _register_trace("workflow", 0, -1, "WF-001")

        selected_wpt = int(st.session_state.get("editor_workflow_selected_point_index", 0))
        selected_wpt = max(0, min(selected_wpt, len(xs) - 1)) if len(xs) > 0 else 0

        for p_idx, (px, py) in enumerate(zip(xs, ys)):
            p_selected = is_selected and selected_wpt == p_idx

            p_move_armed = (
                st.session_state.get("editor_move_awaiting_target", False)
                and st.session_state.get("editor_move_selected_type", "") == "workflow_point"
                and int(st.session_state.get("editor_move_selected_workflow_point_index", -1)) == p_idx
            )            
            fig.add_trace(
                go.Scatter(
                    x=[px],
                    y=[py],
                    mode="markers+text",
                    marker=dict(
                        size=16 if p_move_armed else (14 if p_selected else 10),
                        color="#FFD700" if p_move_armed else ("#FF00FF" if p_selected else "#FFD700"),
                        line=dict(color="black", width=2 if p_move_armed else 1),
                    ),
                    text=[f"WP{p_idx+1}"],
                    textposition="top center",
                    showlegend=False,
                    customdata=[["workflow_point", 0, "WF-001", p_idx]],
                    hovertemplate=f"WF-001 P{p_idx+1}<br>X={px:.2f}<br>Y={py:.2f}<extra></extra>",
                )
            )
            _register_trace("workflow_point", 0, p_idx, "WF-001")

            if show_dim_traces and bool(st.session_state.get("workflow_dim_visible", True)):
                x_dx = 0.0
                x_dy = 0.0
                y_dx = 0.0
                y_dy = 0.0

                if "dim_x_text_dx_ft" in wdf.columns:
                    x_dx = float(wdf.iloc[p_idx].get("dim_x_text_dx_ft", 0.0))
                if "dim_x_text_dy_ft" in wdf.columns:
                    x_dy = float(wdf.iloc[p_idx].get("dim_x_text_dy_ft", 0.0))
                if "dim_y_text_dx_ft" in wdf.columns:
                    y_dx = float(wdf.iloc[p_idx].get("dim_y_text_dx_ft", 0.0))
                if "dim_y_text_dy_ft" in wdf.columns:
                    y_dy = float(wdf.iloc[p_idx].get("dim_y_text_dy_ft", 0.0))

                g = _point_dimension_geometry(
                    px,
                    py,
                    p_idx,
                    base_x_offset=3.0,
                    base_y_offset=3.0,
                    stack_pitch=1.0,
                    x_text_dx_ft=x_dx,
                    x_text_dy_ft=x_dy,
                    y_text_dx_ft=y_dx,
                    y_text_dy_ft=y_dy,
                )
                dim_color = "#FFD700" if p_selected else "#66FFFF"
                ext_color = "#AAAAAA"

                # X dim line
                fig.add_trace(go.Scatter(
                    x=[0.0, g["px"]],
                    y=[g["x_dim_y"], g["x_dim_y"]],
                    mode="lines",
                    line=dict(color=dim_color, width=1.5),
                    showlegend=False,
                    hoverinfo="skip",
                    customdata=[["dimension_workflow_point_x_line", 0, "WF-001", p_idx]] * 2,
                ))
                _register_trace("dimension_workflow_point_x_line", 0, p_idx, "WF-001")

                # X ext lines
                fig.add_trace(go.Scatter(
                    x=[0.0, 0.0, None, g["px"], g["px"]],
                    y=[0.0, g["x_dim_y"], None, g["py"], g["x_dim_y"]],
                    mode="lines",
                    line=dict(color=ext_color, width=1),
                    showlegend=False,
                    hoverinfo="skip",
                    customdata=[["dimension_workflow_point_x_ext", 0, "WF-001", p_idx]] * 5,
                ))
                _register_trace("dimension_workflow_point_x_ext", 0, p_idx, "WF-001")

                # X text
                fig.add_trace(go.Scatter(
                    x=[g["x_text_x"]],
                    y=[g["x_text_y"]],
                    mode="text",
                    text=[f"X = {g['px']:.1f} ft"],
                    textposition="middle center",
                    textfont=dict(color=dim_color, size=11),
                    showlegend=False,
                    hoverinfo="skip",
                ))
                _register_trace("dimension_workflow_point_x_text_visual", 0, p_idx, "WF-001")

                # X hitbox
                fig.add_trace(go.Scatter(
                    x=[g["x_text_x"]],
                    y=[g["x_text_y"]],
                    mode="markers",
                    marker=dict(
                        size=36,
                        color="rgba(0,255,255,0.08)",
                        line=dict(width=1, color="rgba(255,255,255,0.15)")
                    ),
                    showlegend=False,
                    customdata=[["dimension_workflow_point_x_text", 0, "WF-001", p_idx]],
                    hovertemplate=f"Workflow point {p_idx+1} X dimension<extra></extra>",
                ))
                _register_trace("dimension_workflow_point_x_text", 0, p_idx, "WF-001")

                # Y dim line
                fig.add_trace(go.Scatter(
                    x=[g["y_dim_x"], g["y_dim_x"]],
                    y=[0.0, g["py"]],
                    mode="lines",
                    line=dict(color=dim_color, width=1.5),
                    showlegend=False,
                    hoverinfo="skip",
                    customdata=[["dimension_workflow_point_y_line", 0, "WF-001", p_idx]] * 2,
                ))
                _register_trace("dimension_workflow_point_y_line", 0, p_idx, "WF-001")

                # Y ext lines
                fig.add_trace(go.Scatter(
                    x=[0.0, g["y_dim_x"], None, g["px"], g["y_dim_x"]],
                    y=[0.0, 0.0, None, g["py"], g["py"]],
                    mode="lines",
                    line=dict(color=ext_color, width=1),
                    showlegend=False,
                    hoverinfo="skip",
                    customdata=[["dimension_workflow_point_y_ext", 0, "WF-001", p_idx]] * 5,
                ))
                _register_trace("dimension_workflow_point_y_ext", 0, p_idx, "WF-001")

                # Y text
                fig.add_trace(go.Scatter(
                    x=[g["y_text_x"]],
                    y=[g["y_text_y"]],
                    mode="text",
                    text=[f"Y = {g['py']:.1f} ft"],
                    textposition="middle center",
                    textfont=dict(color=dim_color, size=11),
                    showlegend=False,
                    hoverinfo="skip",
                ))
                _register_trace("dimension_workflow_point_y_text_visual", 0, p_idx, "WF-001")

                # Y hitbox
                fig.add_trace(go.Scatter(
                    x=[g["y_text_x"]],
                    y=[g["y_text_y"]],
                    mode="markers",
                    marker=dict(
                        size=36,
                        color="rgba(0,255,255,0.08)",
                        line=dict(width=1, color="rgba(255,255,255,0.15)")
                    ),
                    showlegend=False,
                    customdata=[["dimension_workflow_point_y_text", 0, "WF-001", p_idx]],
                    hovertemplate=f"Workflow point {p_idx+1} Y dimension<extra></extra>",
                ))
                _register_trace("dimension_workflow_point_y_text", 0, p_idx, "WF-001")

        if show_dim_traces and bool(st.session_state.get("workflow_dim_visible", True)):
            g = _workflow_note_geometry()
            is_note_armed = (
                st.session_state.get("editor_dim_move_awaiting_target", False)
                and st.session_state.get("editor_dim_selected_owner_type", "") == "workflow"
                and st.session_state.get("editor_dim_selected_axis", "") == "note"
            )

            note_color = "#FFD700" if is_note_armed else "#FFFFFF"

            fig.add_trace(go.Scatter(
                x=[g["tx"]],
                y=[g["ty"]],
                mode="text",
                text=["Workflow Path"],
                textposition="middle center",
                textfont=dict(color=note_color, size=12),
                showlegend=False,
                hoverinfo="skip",
            ))
            _register_trace("dimension_workflow_note_visual", 0, -1, "WF-001")

            fig.add_trace(go.Scatter(
                x=[g["tx"]],
                y=[g["ty"]],
                mode="markers",
                marker=dict(
                    size=52,
                    color="rgba(255,215,0,0.20)" if is_note_armed else "rgba(255,255,255,0.08)",
                    line=dict(width=1, color="rgba(255,255,255,0.20)")
                ),
                showlegend=False,
                customdata=[["dimension_workflow_note", 0, "WF-001", -1]],
                hovertemplate="Workflow note<extra></extra>",
            ))
            _register_trace("dimension_workflow_note", 0, -1, "WF-001")

    # Cranes
    for idx, cr in enumerate(st.session_state.placed_cranes):
        ll_x = float(cr.get("ll_x", 0.0))
        ll_y = float(cr.get("ll_y", 0.0))
        ur_x = float(cr.get("ur_x", 0.0))
        ur_y = float(cr.get("ur_y", 0.0))
        crid = str(cr.get("id", f"CR-{idx+1:03d}"))

        is_selected = (
            st.session_state.editor_selected_type == "crane"
            and int(st.session_state.editor_selected_index) == idx
        )

        is_move_armed = (
            st.session_state.get("editor_move_awaiting_target", False)
            and st.session_state.get("editor_move_selected_type", "") == "crane"
            and int(st.session_state.get("editor_move_selected_index", -1)) == idx
        )

        fig.add_shape(
            type="rect",
            x0=ll_x,
            y0=ll_y,
            x1=ur_x,
            y1=ur_y,
            line=dict(
                color="#FFD700" if is_move_armed else ("#00E5FF" if is_selected else "#BBBBBB"),
                width=4 if is_move_armed else (3 if is_selected else 2),
                dash="dash",
            ),
            fillcolor="rgba(255,215,0,0.22)" if is_move_armed else "rgba(160,160,160,0.18)",
        )

        cx = (ll_x + ur_x) / 2.0
        cy = (ll_y + ur_y) / 2.0

        fig.add_trace(
            go.Scatter(
                x=[cx],
                y=[cy],
                mode="markers+text",
                marker=dict(
                    size=18 if is_move_armed else (16 if is_selected else 12),
                    color="#FFD700" if is_move_armed else ("#00E5FF" if is_selected else "#BBBBBB"),
                    symbol="square",
                    line=dict(
                        color="#FF00FF" if is_move_armed else "white",
                        width=2 if is_move_armed else 1.5,
                    ),
                ),
                text=[crid],
                textposition="top center",
                name=crid,
                customdata=[["crane", idx, crid, -1]],
                hovertemplate=f"{crid}<br>X={cx:.2f}<br>Y={cy:.2f}<extra></extra>",
                showlegend=False,
            )
        )
        _register_trace("crane", idx, -1, crid)

        if show_dim_traces and bool(cr.get("dim_visible", True)):
            g = _crane_note_geometry(cr)

            is_note_armed = (
                st.session_state.get("editor_dim_move_awaiting_target", False)
                and st.session_state.get("editor_dim_selected_owner_type", "") == "crane"
                and int(st.session_state.get("editor_dim_selected_owner_index", -1)) == idx
                and st.session_state.get("editor_dim_selected_axis", "") == "note"
            )

            note_color = "#FFD700" if is_note_armed else "#FFFFFF"

            fig.add_trace(go.Scatter(
                x=[g["tx"]],
                y=[g["ty"]],
                mode="text",
                text=[crid],
                textposition="middle center",
                textfont=dict(color=note_color, size=12),
                showlegend=False,
                hoverinfo="skip",
            ))
            _register_trace("dimension_crane_note_visual", idx, -1, crid)

            fig.add_trace(go.Scatter(
                x=[g["tx"]],
                y=[g["ty"]],
                mode="markers",
                marker=dict(
                    size=48,
                    color="rgba(255,215,0,0.20)" if is_note_armed else "rgba(255,255,255,0.08)",
                    line=dict(width=1, color="rgba(255,255,255,0.20)")
                ),
                showlegend=False,
                customdata=[["dimension_crane_note", idx, crid, -1]],
                hovertemplate=f"{crid} note<extra></extra>",
            ))
            _register_trace("dimension_crane_note", idx, -1, crid)

    # Floor click target grid
    # Add this late so object traces win clicks when overlapping.
    floor_click_step = float(st.session_state.get("editor_snap_ft", 10.0))
    floor_click_step = max(floor_click_step, 1.0)

    floor_x = []
    floor_y = []

    x = 0.0
    while x <= floor_w:
        y = 0.0
        while y <= floor_h:
            floor_x.append(float(x))
            floor_y.append(float(y))
            y += floor_click_step
        x += floor_click_step

    fig.add_trace(
        go.Scatter(
            x=floor_x,
            y=floor_y,
            mode="markers",
            marker=dict(
                size=6,
                color="rgba(0,0,0,0.001)",
            ),
            showlegend=False,
            hovertemplate="Floor<br>X=%{x:.2f}<br>Y=%{y:.2f}<extra></extra>",
            customdata=[["floor", -1, "FLOOR", -1]] * len(floor_x),
            name="floor_click_grid",
        )
    )
    _register_trace("floor", -1, -1, "FLOOR")

    # Click marker
    last_x = st.session_state.get("editor_last_mouse_x", None)
    last_y = st.session_state.get("editor_last_mouse_y", None)
    if last_x is not None and last_y is not None:
        fig.add_trace(
            go.Scatter(
                x=[float(last_x)],
                y=[float(last_y)],
                mode="markers+text",
                marker=dict(size=12, color="#FF00FF", symbol="x"),
                text=["Pick"],
                textposition="top right",
                showlegend=False,
                hoverinfo="skip",
            )
        )
        _register_trace("pick_marker", -1, -1, "PICK")

    
    fig.update_layout(
        height=650,
        paper_bgcolor="#0B1E2D",
        plot_bgcolor="#0B1E2D",
        font=dict(color="white"),
        margin=dict(l=30, r=30, t=40, b=30),
        title="Interactive 2D Layout Editor",
        xaxis=dict(
            title="X (ft)",
            range=[0, floor_w],
            showgrid=False,
            zeroline=False,
            scaleanchor="y",
            scaleratio=1,
        ),
        yaxis=dict(
            title="Y (ft)",
            range=[0, floor_h],
            showgrid=False,
            zeroline=False,
        ),
        dragmode=False,
    )

    return fig


def apply_canvas_pick(x_ft, y_ft):
    """
    Internal fallback selection helper for Phase 3 canvas clicks when
    direct trace metadata is unavailable.
    """
    x_ft = float(x_ft)
    y_ft = float(y_ft)

    st.session_state.editor_last_mouse_x = x_ft
    st.session_state.editor_last_mouse_y = y_ft

    obj_type = st.session_state.get("editor_selected_type", "machine")

    if obj_type == "machine":
        best_idx = None
        best_d = 1e18
        for idx, m in enumerate(st.session_state.placed_machines):
            cx, cy = _object_center_machine(m)
            d = _dist(x_ft, y_ft, cx, cy)
            if d < best_d:
                best_d = d
                best_idx = idx
        if best_idx is not None:
            st.session_state.editor_selected_index = best_idx
            st.session_state.editor_prime_inputs = True
            st.session_state.editor_phase3_status = f"Selected machine index {best_idx}."

    elif obj_type == "lighting":
        best_idx = None
        best_d = 1e18
        for idx, l in enumerate(st.session_state.placed_lighting):
            cx, cy = _object_center_light(l)
            d = _dist(x_ft, y_ft, cx, cy)
            if d < best_d:
                best_d = d
                best_idx = idx
        if best_idx is not None:
            st.session_state.editor_selected_index = best_idx
            st.session_state.editor_prime_inputs = True
            st.session_state.editor_phase3_status = f"Selected lighting index {best_idx}."

    elif obj_type == "conduit":
        best_obj = None
        best_vertex = None
        best_d = 1e18
        for idx, c in enumerate(st.session_state.placed_conduits):
            xs = [float(v) for v in c.get("x", [])]
            ys = [float(v) for v in c.get("y", [])]
            for p_idx, (px, py) in enumerate(zip(xs, ys)):
                d = _dist(x_ft, y_ft, px, py)
                if d < best_d:
                    best_d = d
                    best_obj = idx
                    best_vertex = p_idx
        if best_obj is not None:
            st.session_state.editor_selected_index = best_obj
            st.session_state.editor_pending_vertex_index = best_vertex
            st.session_state.editor_prime_inputs = True
            st.session_state.editor_phase3_status = (
                f"Selected conduit {best_obj}, vertex {best_vertex}."
            )

    elif obj_type == "workflow":
        if "path_points" in st.session_state and len(st.session_state.path_points) > 0:
            wdf = st.session_state.path_points
            best_idx = None
            best_d = 1e18
            for p_idx in range(len(wdf)):
                px = float(wdf.iloc[p_idx]["X Coordinate"])
                py = float(wdf.iloc[p_idx]["Y Coordinate"])
                d = _dist(x_ft, y_ft, px, py)
                if d < best_d:
                    best_d = d
                    best_idx = p_idx
            if best_idx is not None:
                st.session_state.editor_pending_workflow_point_index = best_idx
                st.session_state.editor_prime_inputs = True
                st.session_state.editor_phase3_status = (
                    f"Selected workflow point {best_idx}."
                )

    elif obj_type == "crane":
        best_idx = None
        best_d = 1e18
        for idx, cr in enumerate(st.session_state.placed_cranes):
            cx = (float(cr.get("ll_x", 0.0)) + float(cr.get("ur_x", 0.0))) / 2.0
            cy = (float(cr.get("ll_y", 0.0)) + float(cr.get("ur_y", 0.0))) / 2.0
            d = _dist(x_ft, y_ft, cx, cy)
            if d < best_d:
                best_d = d
                best_idx = idx
        if best_idx is not None:
            st.session_state.editor_selected_index = best_idx
            st.session_state.editor_prime_inputs = True
            st.session_state.editor_phase3_status = f"Selected crane index {best_idx}."

    st.session_state.editor_canvas_refresh_token += 1
