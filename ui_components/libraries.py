# ui_components/libraries.py
import pandas as pd
import streamlit as st


def render_libraries_tab(machinery_lib, lighting_lib, crane_lib):
    st.header("📚 Default Machinery, Lighting & Crane Libraries")
    st.markdown("Reference specification tables loaded from default library configurations.")

    search_term = st.text_input("Library Search", value="", key="lib_search")
    search_term_lower = search_term.strip().lower()

    df_machinery = pd.DataFrame(machinery_lib)

    preferred_machine_cols = [
        "Make",
        "Model",
        "Type",
        "Width",
        "Height",
        "Standoff",
        "VaporPort",
        "WaterHookup",
        "Amperage",
        "Wattage",
        "ToolHeads",
        "Volume",
        "Yield",
        "CraneRequired",
        "Decibel",
        "HumanInterventionRequired",
        "PreferredUtilityZone",
        "ProcessFamily",
        "ValueAddedPrimary",
    ]
    existing_machine_cols = [c for c in preferred_machine_cols if c in df_machinery.columns]
    remaining_machine_cols = [c for c in df_machinery.columns if c not in existing_machine_cols]
    df_machinery = df_machinery[existing_machine_cols + remaining_machine_cols]
    df_lighting = pd.DataFrame(lighting_lib)
    df_cranes = pd.DataFrame(crane_lib)

    def filter_df(df):
        if not search_term_lower:
            return df
        mask = df.astype(str).apply(
            lambda col: col.str.lower().str.contains(search_term_lower, na=False)
        ).any(axis=1)
        return df[mask]

    lib_col1, lib_col2, lib_col3 = st.columns(3)

    with lib_col1:
        st.subheader("🏭 Default Machinery Library")
        st.dataframe(filter_df(df_machinery), use_container_width=True)

    with lib_col2:
        st.subheader("💡 Default Lighting Library")
        st.dataframe(filter_df(df_lighting), use_container_width=True)

    with lib_col3:
        st.subheader("🏗 Default Overhead Crane Library")
        st.dataframe(filter_df(df_cranes), use_container_width=True)
