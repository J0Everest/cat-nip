import os
import streamlit as st
from _db import init_db_state, next_quarter

st.set_page_config(
    page_title="Everest Cat Tools",
    layout="wide",
    initial_sidebar_state="expanded",
)

# shared SQL settings across all pages
init_db_state()

with st.sidebar:
    _logo_path = os.path.join(
        os.path.dirname(__file__),
        "assets", "Logo suite", "Logo Digital",
        "Logo - BlueBlack Everest (R) (Digital - PNG).png",
    )
    if os.path.exists(_logo_path):
        with open(_logo_path, "rb") as _f:
            st.image(_f.read(), width=180)

    st.caption("Everest Cat Tools")
    st.markdown("<div style='height:45vh'></div>", unsafe_allow_html=True)
    st.markdown("---")
    st.markdown("##### Connection")
    st.text_input("SQL Server", value=st.session_state.sql_server, disabled=True)
    st.text_input("Database", key="sql_database")
    if st.button("Next Quarter", use_container_width=True):
        st.session_state.sql_database = next_quarter(st.session_state.sql_database)
        st.rerun()
    with st.expander("Advanced"):
        _override = st.text_input("Override SQL Server", value=st.session_state.sql_server)
        if _override and _override != st.session_state.sql_server:
            st.session_state.sql_server = _override
            st.rerun()

pg = st.navigation(
    [
        st.Page("views/2_Event_Response_v2.py", title="Event Response", icon="📋"),
    ],
    position="sidebar",
)
pg.run()
