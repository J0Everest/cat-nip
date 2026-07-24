import streamlit as st
import pandas as pd

st.set_page_config(page_title="Event Response Mockup", layout="wide")

st.title("Event Response – UI Mockup")
st.caption("Simple prototype for event selection and response package flow")

st.markdown("### 1) Event Filters")
c1, c2, c3 = st.columns(3)
with c1:
    peril = st.selectbox("Peril", ["EQ", "Wind", "Flood", "Wildfire", "MPCI", "CROP"])
with c2:
    geo_mode = st.radio("Location Mode", ["Zone", "Radius"], horizontal=True)
with c3:
    severity_mode = st.radio("Severity", ["Peril Metric", "Industry Loss"], horizontal=True)

if geo_mode == "Zone":
    zone = st.selectbox("Zone", [
        "South America  Venezuela", "US  Zone 03 FL", "Caribbean  Puerto Rico", "Europe  Italy"
    ])
else:
    r1, r2, r3 = st.columns(3)
    with r1:
        lat = st.number_input("Center Lat", value=10.48)
    with r2:
        lon = st.number_input("Center Lon", value=-66.90)
    with r3:
        radius_km = st.slider("Radius (km)", 25, 2000, 300)

if severity_mode == "Peril Metric":
    if peril == "EQ":
        st.slider("EQ Magnitude (Mw)", 4.0, 9.5, (6.5, 8.0))
    elif peril == "Wind":
        st.slider("HU Category", 1, 5, (3, 5))
    else:
        st.slider("Peril Intensity", 0, 100, (30, 80))
else:
    st.slider("Industry Loss ($B)", 0.0, 250.0, (5.0, 50.0), 0.5)

st.markdown("### 2) Candidate Events")
if st.button("Find Events"):
    st.session_state["events"] = pd.DataFrame([
        {"Select": False, "eventid": 101001, "peril": peril, "location": "Venezuela", "industry_loss_b": 12.4},
        {"Select": False, "eventid": 101018, "peril": peril, "location": "Caribbean", "industry_loss_b": 8.1},
        {"Select": False, "eventid": 101045, "peril": peril, "location": "US Gulf", "industry_loss_b": 22.7},
    ])

if "events" in st.session_state:
    edited = st.data_editor(
        st.session_state["events"],
        use_container_width=True,
        hide_index=True,
        num_rows="fixed",
        column_config={"Select": st.column_config.CheckboxColumn(required=False)},
    )
    st.session_state["events"] = edited

    st.markdown("### 3) Response Package")
    selected = edited[edited["Select"] == True]
    st.write(f"Selected Events: {len(selected)}")
    if len(selected) > 0:
        st.dataframe(selected, use_container_width=True, hide_index=True)

    c1, c2 = st.columns(2)
    with c1:
        st.button("Populate Input Template", use_container_width=True)
    with c2:
        st.button("Export Workbook (.xlsm)", use_container_width=True)
else:
    st.info("Set filters and click Find Events.")
