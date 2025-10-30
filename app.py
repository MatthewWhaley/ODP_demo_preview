import streamlit as st
import pandas as pd
import pydeck as pdk

# ---- CONFIG ----
DATASET_UUID = "2b69f875-cc3d-4dad-b816-8a64d41c6932"

# ---- DATA LOADING ----
@st.cache_data(show_spinner=True)
def load_data(limit_rows=None):
    # If your package import differs, adjust here:
    from odp.client import Client
    cli = Client()
    # Pull as a DataFrame; if the table is large, consider sampling or a where-clause
    df = next(cli.dataset(DATASET_UUID).table.select().dataframes())
    # Ensure columns exist as expected
    exp = ["structure_id","label","lat","lon","year","month","latest_flag"]
    missing = [c for c in exp if c not in df.columns]
    if missing:
        st.warning(f"Missing expected columns: {missing}")
    if limit_rows:
        df = df.head(limit_rows)
    return df

st.set_page_config(page_title="ODP Quick Map", layout="wide")
st.title("ODP Quick Map — Streamlit Prototype")

with st.sidebar:
    st.header("Filters")
    limit_rows = st.number_input("Row cap (quick dev)", min_value=1000, max_value=200000, value=50000, step=1000)
    df = load_data(limit_rows=limit_rows)

    labels = sorted(df["label"].dropna().unique().tolist())
    sel_labels = st.multiselect("Label", options=labels, default=labels[: min(5, len(labels))])

    years = sorted(df["year"].dropna().unique().tolist())
    if years:
        yr_min, yr_max = min(years), max(years)
        sel_year_range = st.slider("Year range", min_value=int(yr_min), max_value=int(yr_max),
                                   value=(int(yr_min), int(yr_max)))
    else:
        sel_year_range = (2000, 2100)

    months = list(range(1,13))
    sel_months = st.multiselect("Months", options=months, default=months)

    latest_only = st.checkbox("Latest only (latest_flag == 'Y')", value=False)

    structure_search = st.text_input("Structure ID contains (optional)")

# ---- FILTERING ----
q = df.copy()
if sel_labels:
    q = q[q["label"].isin(sel_labels)]
if sel_year_range:
    q = q[(q["year"] >= sel_year_range[0]) & (q["year"] <= sel_year_range[1])]
if sel_months:
    q = q[q["month"].isin(sel_months)]
if latest_only and "latest_flag" in q.columns:
    q = q[q["latest_flag"].astype(str).str.upper().eq("Y")]
if structure_search:
    q = q[q["structure_id"].astype(str).str.contains(structure_search, case=False, na=False)]

# ---- SUMMARY ----
c1, c2, c3, c4 = st.columns(4)
c1.metric("Rows", f"{len(q):,}")
c2.metric("Structures", f"{q['structure_id'].nunique():,}" if "structure_id" in q.columns else "—")
c3.metric("Labels", f"{q['label'].nunique():,}" if "label" in q.columns else "—")
c4.metric("Years", f"{q['year'].nunique():,}" if "year" in q.columns else "—")

# ---- MAP ----
st.subheader("Map")
if {"lat","lon"}.issubset(q.columns) and not q.empty:
    view_state = pdk.ViewState(latitude=float(q["lat"].median()),
                               longitude=float(q["lon"].median()),
                               zoom=3)
    layer = pdk.Layer(
        "ScatterplotLayer",
        data=q,
        get_position="[lon, lat]",
        get_radius=15000,
        pickable=True,
        radius_min_pixels=2,
        radius_max_pixels=30,
    )
    tooltip = {
        "html": "<b>Structure:</b> {structure_id}<br/>"
                "<b>Label:</b> {label}<br/>"
                "<b>Date:</b> {year}-{month}",
        "style": {"backgroundColor": "white", "color": "black"}
    }
    st.pydeck_chart(pdk.Deck(layers=[layer], initial_view_state=view_state, tooltip=tooltip))
else:
    st.info("No points to show. Try relaxing filters.")

# ---- TABLE ----
with st.expander("Preview filtered rows"):
    st.dataframe(q.head(1000), use_container_width=True)
