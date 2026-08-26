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


def build_interactive_canvas_figure():
    floor_w = float(st.session_state.floor_w)
    floor_h = float(st.session_state.floor_h)

    fig = go.Figure()

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
        grid_step = float(st.session_state.get("editor_snap_ft", 1.0))
        if grid_step <= 0:
            grid_step = 1.0

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
                color="#87CEEB" if not is_selected else "#00E5FF",
                width=2 if not is_selected else 3,
            ),
            fillcolor="rgba(135,206,235,0.18)" if not is_selected else "rgba(0,229,255,0.22)",
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
                    size=14 if is_selected else 10,
                    color="#00E5FF" if is_selected else "#87CEEB",
                    line=dict(color="white", width=1),
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

    # Lighting
    for idx, l in enumerate(st.session_state.placed_lighting):
        lx = float(l["x"])
        ly = float(l["y"])
        lid = str(l.get("id", f"L-{idx+1:03d}"))

        is_selected = (
            st.session_state.editor_selected_type == "lighting"
            and int(st.session_state.editor_selected_index) == idx
        )

        fig.add_trace(
            go.Scatter(
                x=[lx],
                y=[ly],
                mode="markers+text",
                marker=dict(
                    size=16 if is_selected else 12,
                    color="#FFD700",
                    symbol="diamond",
                    line=dict(color="#FFFFFF", width=2 if is_selected else 1),
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

    # Conduits
    for idx, c in enumerate(st.session_state.placed_conduits):
        xs = [float(v) for v in c.get("x", [])]
        ys = [float(v) for v in c.get("y", [])]
        cid = str(c.get("id", f"C-{idx+1:03d}"))

        is_selected = (
            st.session_state.editor_selected_type == "conduit"
            and int(st.session_state.editor_selected_index) == idx
        )

        if len(xs) >= 2 and len(xs) == len(ys):
            fig.add_trace(
                go.Scatter(
                    x=xs,
                    y=ys,
                    mode="lines+markers",
                    line=dict(color="#FFA500", width=4 if is_selected else 3),
                    marker=dict(size=8, color="#FFD700"),
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
                fig.add_trace(
                    go.Scatter(
                        x=[px],
                        y=[py],
                        mode="markers+text",
                        marker=dict(
                            size=14 if v_selected else 10,
                            color="#FF00FF" if v_selected else "#FFD700",
                            line=dict(color="black", width=1),
                        ),
                        text=[f"CV{p_idx+1}"],
                        textposition="top center",
                        showlegend=False,
                        customdata=[["conduit_vertex", idx, cid, p_idx]],
                        hovertemplate=f"{cid} V{p_idx+1}<br>X={px:.2f}<br>Y={py:.2f}<extra></extra>",
                    )
                )
                _register_trace("conduit_vertex", idx, p_idx, cid)

    # Workflow
    if "path_points" in st.session_state and len(st.session_state.path_points) >= 2:
        wdf = st.session_state.path_points
        xs = [float(v) for v in wdf["X Coordinate"].tolist()]
        ys = [float(v) for v in wdf["Y Coordinate"].tolist()]

        is_selected = st.session_state.editor_selected_type == "workflow"

        fig.add_trace(
            go.Scatter(
                x=xs,
                y=ys,
                mode="lines+markers",
                line=dict(color="#808080", width=5 if is_selected else 4),
                marker=dict(size=8, color="#00E5FF"),
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
            fig.add_trace(
                go.Scatter(
                    x=[px],
                    y=[py],
                    mode="markers+text",
                    marker=dict(
                        size=14 if p_selected else 10,
                        color="#FF00FF" if p_selected else "#FFD700",
                        line=dict(color="black", width=1),
                    ),
                    text=[f"WP{p_idx+1}"],
                    textposition="top center",
                    showlegend=False,
                    customdata=[["workflow_point", 0, "WF-001", p_idx]],
                    hovertemplate=f"WF-001 P{p_idx+1}<br>X={px:.2f}<br>Y={py:.2f}<extra></extra>",
                )
            )
            _register_trace("workflow_point", 0, p_idx, "WF-001")

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

        fig.add_shape(
            type="rect",
            x0=ll_x,
            y0=ll_y,
            x1=ur_x,
            y1=ur_y,
            line=dict(
                color="#BBBBBB" if not is_selected else "#00E5FF",
                width=2 if not is_selected else 3,
                dash="dash",
            ),
            fillcolor="rgba(160,160,160,0.18)",
        )

        cx = (ll_x + ur_x) / 2.0
        cy = (ll_y + ur_y) / 2.0

        fig.add_trace(
            go.Scatter(
                x=[cx],
                y=[cy],
                mode="markers+text",
                marker=dict(
                    size=16 if is_selected else 12,
                    color="#BBBBBB" if not is_selected else "#00E5FF",
                    symbol="square",
                    line=dict(
                        color="white" if not is_selected else "#FFD700",
                        width=1.5,
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

    # Floor click target grid
    # Add this late so object traces win clicks when overlapping.
    floor_click_step = float(st.session_state.get("editor_snap_ft", 1.0))
    if floor_click_step <= 0:
        floor_click_step = 1.0

    # Keep density and interference reasonable
    floor_click_step = max(floor_click_step, 2.0)

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
                size=4,
                color="rgba(0,0,0,0.001)",
            ),
            showlegend=False,
            hoverinfo="skip",
            customdata=[["floor", -1, "FLOOR", -1]] * len(floor_x),
            name="floor_click_grid",
        )
    )
    _register_trace("floor", -1, -1, "FLOOR")

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
