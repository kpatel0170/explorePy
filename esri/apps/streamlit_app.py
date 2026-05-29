"""Quick Streamlit UI for exploring an ArcGIS Enterprise feature layer.

Run:
    streamlit run esri/apps/streamlit_app.py

Connects to Portal (env vars / profile), lets you query a layer by URL or
item id, preview the table, and render a choropleth — all without writing code.
"""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

# Make esri_utils importable when run from repo root.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from esri_utils import analysis, cleaning, layers, viz  # noqa: E402
from esri_utils.config import PortalConfig  # noqa: E402
from esri_utils.portal import connect  # noqa: E402

st.set_page_config(page_title="ArcGIS Enterprise Explorer", layout="wide")
st.title("🌎 ArcGIS Enterprise Explorer")


@st.cache_resource(show_spinner="Connecting to Portal…")
def _gis():
    return connect(PortalConfig.from_env())


with st.sidebar:
    st.header("Connection")
    use_env = st.checkbox("Use env-var connection", value=True)
    gis = None
    if use_env:
        try:
            gis = _gis()
            st.success(f"Connected: {gis.properties.user.username}")
        except Exception as exc:  # noqa: BLE001
            st.error(f"Connect failed: {exc}")

    st.header("Layer source")
    mode = st.radio("Reference layer by", ["REST URL", "Item ID"])
    ref = st.text_input("URL or Item ID")
    layer_idx = st.number_input("Layer index", min_value=0, value=0, step=1)
    where = st.text_input("WHERE clause", value="1=1")
    load = st.button("Load layer", type="primary")


if load and ref:
    try:
        if mode == "REST URL":
            layer = layers.layer_from_url(ref, gis=gis)
        else:
            layer = layers.get_feature_layer(gis, ref, int(layer_idx))
        sdf = layers.query_to_sdf(layer, where=where)
        sdf = cleaning.trim_strings(cleaning.standardize_columns(sdf))
        st.session_state["sdf"] = sdf
        st.success(f"Loaded {len(sdf):,} features.")
    except Exception as exc:  # noqa: BLE001
        st.error(f"Load failed: {exc}")


sdf = st.session_state.get("sdf")
if sdf is not None:
    tab_table, tab_quality, tab_map = st.tabs(["Table", "Data quality", "Map"])

    with tab_table:
        st.dataframe(sdf.drop(columns=["SHAPE"], errors="ignore"), use_container_width=True)

    with tab_quality:
        st.dataframe(cleaning.null_report(sdf), use_container_width=True)

    with tab_map:
        numeric = sdf.select_dtypes("number").columns.tolist()
        if numeric:
            col = st.selectbox("Color by", numeric)
            try:
                gdf = analysis.to_geodataframe(sdf)
                ax = viz.choropleth(gdf, col, title=col)
                st.pyplot(ax.get_figure())
            except Exception as exc:  # noqa: BLE001
                st.warning(f"Map render failed: {exc}")
        else:
            st.info("No numeric columns to map.")
else:
    st.info("Configure a connection and load a layer from the sidebar.")
