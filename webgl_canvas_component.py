# webgl_canvas_component.py
import json
import streamlit as st


def _build_default_component_result():
    """
    Standard return shape for the future Three.js component bridge.
    """
    return {
        "component_ready": False,
        "event_available": False,
        "event_payload": None,
        "status": "placeholder",
    }


def render_webgl_canvas_component(
    scene_payload,
    component_key="threejs_canvas",
    height_px=700,
    show_debug=False,
):
    """
    Placeholder Python-side wrapper for the future browser-native Three.js canvas.

    Current behavior:
    - Renders an informational placeholder panel in Streamlit
    - Displays selected scene metadata
    - Returns a stable result dict matching the future component contract

    Future behavior:
    - This function will call an actual Streamlit custom component
      and return browser-generated interaction events.
    """
    result = _build_default_component_result()

    if not isinstance(scene_payload, dict):
        st.error("WebGL canvas component received invalid scene payload.")
        result["status"] = "invalid_scene_payload"
        return result

    project = scene_payload.get("project", {})
    floor = scene_payload.get("floor", {})
    display = scene_payload.get("display", {})
    counts = scene_payload.get("counts", {})
    selection = scene_payload.get("selection", {})

    with st.container(border=True):
        st.subheader("Three.js Interactive Canvas Placeholder")
        st.caption(
            "Branch 4.7 integration stub: this placeholder preserves the future "
            "component interface until the browser-side Three.js frontend is connected."
        )

        info_col1, info_col2, info_col3 = st.columns(3)

        with info_col1:
            st.metric("View Mode", display.get("view_mode", "unknown"))
            st.metric("Scene Revision", scene_payload.get("scene_revision", 0))

        with info_col2:
            st.metric("Machines", counts.get("machines", 0))
            st.metric("Conduits", counts.get("conduits", 0))

        with info_col3:
            st.metric("Cranes", counts.get("cranes", 0))
            st.metric("Machine Flows", counts.get("machine_flows", 0))

        st.markdown(
            f"**Project:** {project.get('dwg_num', '')} — {project.get('dwg_title', '')}"
        )
        st.markdown(
            f"**Floor:** {floor.get('width_ft', 0.0)} ft × {floor.get('height_ft', 0.0)} ft"
        )

        selected_object_type = selection.get("selected_object_type", "")
        selected_object_id = selection.get("selected_object_id", "")
        if selected_object_type or selected_object_id:
            st.info(
                f"Current frontend selection mirror: "
                f"{selected_object_type or 'object'} {selected_object_id or ''}".strip()
            )
        else:
            st.info("No frontend selection is currently mirrored.")

        st.write(
            f"Reserved canvas display area: approximately {int(height_px)} px tall."
        )

        if show_debug:
            with st.expander("Scene Payload Debug", expanded=False):
                st.json(scene_payload, expanded=False)

            with st.expander("Placeholder Return Contract", expanded=False):
                st.code(
                    json.dumps(result, indent=2),
                    language="json",
                )

    return result


def render_webgl_canvas_status_banner():
    """
    Optional helper for app-level status messaging.
    """
    st.warning(
        "The browser-native Three.js canvas is not connected yet. "
        "The application is currently using a placeholder integration wrapper."
    )
