# ui_components/lighting.py
import streamlit as st


def render_lighting_tab(lighting_lib):
    l_col1, l_col2 = st.columns(2)

    with l_col1:
        st.subheader("💡 Place Light from Library")
        light_options = [
            f"{l['Make']} {l['Brand']} ({l['Type']})" for l in lighting_lib
        ]
        selected_l_idx = st.selectbox(
            "Choose Lighting Fixture",
            range(len(light_options)),
            format_func=lambda x: light_options[x],
            key="l_sel_tab",
        )

        lx = st.number_input(
            "Target Placement X (ft)",
            min_value=0.0,
            max_value=float(st.session_state.floor_w),
            value=50.0,
            key="lx_tab",
        )
        ly = st.number_input(
            "Target Placement Y (ft)",
            min_value=0.0,
            max_value=float(st.session_state.floor_h),
            value=80.0,
            key="ly_tab",
        )

        if st.button("Add Lighting Fixture", type="primary", key="add_light_btn"):
            spec = dict(lighting_lib[selected_l_idx])
            spec["id"] = generate_next_id("L", st.session_state.placed_lighting)
            spec["x"] = float(lx)
            spec["y"] = float(ly)

            if not (0 <= spec["x"] <= st.session_state.floor_w and 0 <= spec["y"] <= st.session_state.floor_h):
                st.error("Lighting placement must be inside the factory floor.")
            else:
                st.session_state.placed_lighting.append(spec)
                st.success(f"Added lighting fixture {spec['id']}.")
                st.rerun() if hasattr(st, "rerun") else st.experimental_rerun()

    with l_col2:
        st.subheader("Edit Existing Lighting")
        if st.session_state.placed_lighting:
            labels = [
                f"{l.get('id', f'L-{i+1:03d}')} | {l.get('Make', '')} {l.get('Brand', '')}"
                for i, l in enumerate(st.session_state.placed_lighting)
            ]
            selected_placed_l_idx = st.selectbox(
                "Select placed light to edit",
                range(len(labels)),
                format_func=lambda x: labels[x],
                key="edit_light_select",
            )

            light = st.session_state.placed_lighting[selected_placed_l_idx]

            edit_lx = st.number_input(
                "Edit X (ft)",
                min_value=0.0,
                max_value=float(st.session_state.floor_w),
                value=float(light["x"]),
                key=f"edit_lx_{selected_placed_l_idx}",
            )
            edit_ly = st.number_input(
                "Edit Y (ft)",
                min_value=0.0,
                max_value=float(st.session_state.floor_h),
                value=float(light["y"]),
                key=f"edit_ly_{selected_placed_l_idx}",
            )
            edit_wattage = st.number_input(
                "Edit Wattage",
                min_value=0.0,
                max_value=10000.0,
                value=float(light.get("Wattage", 0.0)),
                key=f"edit_lw_{selected_placed_l_idx}",
            )
            edit_kelvin = st.number_input(
                "Edit Kelvin",
                min_value=1000,
                max_value=10000,
                value=int(light.get("Kelvin", 5000)),
                key=f"edit_lk_{selected_placed_l_idx}",
            )
            edit_lumens = st.number_input(
                "Edit Lumens",
                min_value=0,
                max_value=500000,
                value=int(light.get("Lumens", 10000)),
                key=f"edit_llm_{selected_placed_l_idx}",
            )
            edit_dimmable = st.checkbox(
                "Dimmable",
                value=bool(light.get("Dimmable", True)),
                key=f"edit_ld_{selected_placed_l_idx}",
            )

            l_btn_col1, l_btn_col2 = st.columns(2)
            with l_btn_col1:
                if st.button("Update Light", key=f"upd_l_btn_{selected_placed_l_idx}"):
                    if not (
                        0 <= edit_lx <= st.session_state.floor_w
                        and 0 <= edit_ly <= st.session_state.floor_h
                    ):
                        st.error("Lighting placement must be inside the floor.")
                    else:
                        updated = dict(light)
                        updated["x"] = float(edit_lx)
                        updated["y"] = float(edit_ly)
                        updated["Wattage"] = float(edit_wattage)
                        updated["Kelvin"] = int(edit_kelvin)
                        updated["Lumens"] = int(edit_lumens)
                        updated["Dimmable"] = bool(edit_dimmable)
                        st.session_state.placed_lighting[selected_placed_l_idx] = updated
                        st.success(f"Updated lighting fixture {updated.get('id', 'unknown')}.")
                        st.rerun() if hasattr(st, "rerun") else st.experimental_rerun()

            with l_btn_col2:
                if st.button("Delete Light", key=f"del_l_btn_{selected_placed_l_idx}"):
                    removed_light = st.session_state.placed_lighting.pop(selected_placed_l_idx)
                    st.warning(
                        f"Removed {removed_light.get('id', 'light')} "
                        f"({removed_light.get('Make', '')} {removed_light.get('Brand', '')})."
                    )
                    st.rerun() if hasattr(st, "rerun") else st.experimental_rerun()
        else:
            st.info("No lighting fixtures currently placed.")