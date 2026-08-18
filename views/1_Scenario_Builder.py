"""
CAT-NIP Scenario Builder — AI-first event analysis workflow.
Progressive disclosure: Prompt → Parsed Filters → Candidate Events → Scenario Assignment → Results Dashboard.
"""
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from _db import init_db_state, run_sql
from components import (
    step_indicator, section_header, prompt_hero, parsed_event_card,
    scenario_summary_card, copy_button, plain_int_str, format_pct_series,
)
from event_logic import (
    parse_scenario_query, PERIL_OPTIONS,
    discover_air_event_tables, prefilter_air_profiles_by_peril,
    infer_model_from_industry, match_table_by_model,
    infer_table_by_keyword_match, fetch_air_event_details,
    fetch_air_descriptions_for_peril,
    build_event_search_sql, build_output_sql,
)
from theme import (
    DARK_BLUE, MID_GRAY, EVEREST_BLUE,
    SCENARIO_COLOR_MAP, SCENARIO_LOW, SCENARIO_MED, SCENARIO_HIGH,
)

init_db_state()
DB = st.session_state.sql_database
SRV = st.session_state.sql_server

# ── Determine current step for the indicator ──────────────────────────────────
STEPS = ["Describe Event", "Refine Filters", "Select Events", "Assign Scenarios", "View Results"]


def _current_step():
    if "sb_waterfall" in st.session_state:
        return 4
    if "sb_candidates" in st.session_state:
        if any(st.session_state.get(f"sb_{s}_id") for s in ("low", "med", "high")):
            return 3
        return 2
    if st.session_state.get("sb_parsed"):
        return 1
    return 0


step_indicator(STEPS, _current_step())

# ── Step 1: Prompt ─────────────────────────────────────────────────────────────
prompt_hero()

col_prompt, col_btn = st.columns([5, 1])
with col_prompt:
    query = st.text_area(
        "Describe the event",
        key="sb_query",
        height=80,
        placeholder='e.g. "Category 5 hurricane makes landfall near Miami, $5-15B industry loss"',
        label_visibility="collapsed",
    )
with col_btn:
    st.markdown("<div style='height:22px'></div>", unsafe_allow_html=True)
    analyze_clicked = st.button("Analyze", type="primary", use_container_width=True)

if analyze_clicked and query.strip():
    parsed = parse_scenario_query(query)
    st.session_state["sb_parsed"] = parsed
    st.session_state["sb_raw_query"] = query.strip()
    if parsed["peril"]:
        st.session_state["sb_peril"] = parsed["peril"]
    if parsed["zone"]:
        st.session_state["sb_zone"] = parsed["zone"]
    if parsed["loss_lo"] is not None and parsed["loss_hi"] is not None:
        st.session_state["sb_loss_range"] = (parsed["loss_lo"], parsed["loss_hi"])
    if parsed["event_keyword"]:
        st.session_state["sb_event_keyword"] = parsed["event_keyword"]
    if parsed["mag_lo"] is not None and parsed["mag_hi"] is not None:
        st.session_state["sb_mag_range"] = (parsed["mag_lo"], parsed["mag_hi"])
    st.session_state.pop("sb_candidates", None)
    st.session_state.pop("sb_waterfall", None)
    st.rerun()

# ── Step 2: Parsed filters + refinement ────────────────────────────────────────
parsed = st.session_state.get("sb_parsed")
if not parsed:
    st.stop()

parsed_event_card(parsed, st.session_state.get("sb_raw_query", ""))

with st.expander("Refine filters", expanded=False):
    f1, f2, f3 = st.columns(3)
    with f1:
        peril = st.selectbox("Peril", PERIL_OPTIONS, key="sb_peril")
    with f2:
        zone_filter = st.text_input("Zone (partial match)", key="sb_zone", placeholder="e.g. FL, Zone 03, Caribbean")
    with f3:
        default_range = st.session_state.get("sb_loss_range", (0.0, 300.0))
        ind_lo, ind_hi = st.slider("Industry Loss ($B)", 0.0, 300.0, value=default_range, step=0.5, key="sb_loss_range")

    filter_mode = st.radio("Filter mode", ["Industry Loss", "Event Characteristics", "Both"], horizontal=True, key="sb_filter_mode")

    event_keyword = st.session_state.get("sb_event_keyword", "")
    use_air_events = False
    air_table_profiles = []
    air_table_label = None
    mag_lo, mag_hi = st.session_state.get("sb_mag_range", (0.0, 12.0))

    if filter_mode in ("Event Characteristics", "Both"):
        c1, c2 = st.columns(2)
        with c1:
            event_keyword = st.text_input("Event description keyword", key="sb_event_keyword")
        with c2:
            mag_lo, mag_hi = st.slider("Magnitude range", 0.0, 12.0, value=(mag_lo, mag_hi), step=0.1, key="sb_mag_range")
            use_air_events = st.checkbox(f"Enrich from {st.session_state.get('AIR_EVENTS_DB', 'AIREvents')}", value=True, key="sb_use_air")

        if use_air_events:
            all_profiles = discover_air_event_tables(SRV, DB)
            air_table_profiles, was_prefiltered = prefilter_air_profiles_by_peril(all_profiles, peril)
            if air_table_profiles:
                if was_prefiltered:
                    st.caption(f"Tables prefiltered for peril: {peril}")
                labels = [f"{p['schema']}.{p['table']}" for p in air_table_profiles]
                auto_label = infer_table_by_keyword_match(SRV, DB, air_table_profiles, peril, zone_filter, st.session_state.get("sb_raw_query", ""))
                if not auto_label:
                    model_hint = infer_model_from_industry(SRV, DB, peril, zone_filter)
                    if model_hint:
                        auto_label = match_table_by_model(labels, model_hint)
                if auto_label and auto_label in labels:
                    st.session_state["sb_air_table"] = auto_label
                elif st.session_state.get("sb_air_table") not in labels:
                    st.session_state["sb_air_table"] = labels[0]
                air_table_label = st.selectbox("AIR Events table", labels, key="sb_air_table")

                profile = next((p for p in air_table_profiles if f"{p['schema']}.{p['table']}" == air_table_label), None)
                if profile and profile.get("desc_col"):
                    desc_options = fetch_air_descriptions_for_peril(SRV, DB, profile, peril, zone_filter, "", 500)
                    if desc_options:
                        picked = st.selectbox("Event description", ["(any)"] + desc_options, key="sb_desc_pick")
                        if picked != "(any)":
                            event_keyword = picked
                            st.session_state["sb_event_keyword"] = picked

# ── Step 3: Find candidate events ─────────────────────────────────────────────
section_header("Candidate Events")

if st.button("Find Matching Events", type="primary", use_container_width=True):
    with st.spinner("Searching CatAccum..."):
        try:
            sql = build_event_search_sql(DB, zone_filter, ind_lo, ind_hi, peril, filter_mode, "" if use_air_events else event_keyword)
            df_raw = run_sql(SRV, DB, sql)

            if filter_mode in ("Event Characteristics", "Both") and use_air_events and air_table_profiles and air_table_label and df_raw is not None and not df_raw.empty:
                profile = next((p for p in air_table_profiles if f"{p['schema']}.{p['table']}" == air_table_label), None)
                if profile:
                    air_df = fetch_air_event_details(SRV, DB, [int(v) for v in df_raw["EventID"].dropna().tolist()], profile)
                    if air_df is not None and not air_df.empty:
                        df_raw = df_raw.merge(air_df, on="EventID", how="left")
                        if event_keyword and "AIR_Description" in df_raw.columns:
                            df_raw = df_raw[df_raw["AIR_Description"].astype(str).str.contains(event_keyword, case=False, na=False)]
                        mag_filter_is_set = not (float(mag_lo) <= 0.0 and float(mag_hi) >= 12.0)
                        if "AIR_Magnitude" in df_raw.columns and mag_filter_is_set:
                            mag_vals = pd.to_numeric(df_raw["AIR_Magnitude"], errors="coerce")
                            df_raw = df_raw[(mag_vals >= float(mag_lo)) & (mag_vals <= float(mag_hi))]

            if df_raw is not None and not df_raw.empty:
                df_raw.insert(0, "\u2713", False)
                st.session_state["sb_candidates"] = df_raw
                st.session_state.pop("sb_waterfall", None)
            else:
                st.warning("No events matched. Try broadening your filters.")
                st.session_state.pop("sb_candidates", None)
        except Exception as exc:
            st.error(f"Query failed: {exc}")
            st.session_state.pop("sb_candidates", None)

if "sb_candidates" not in st.session_state:
    st.info("Describe an event above and click **Find Matching Events** to begin.")
    st.stop()

# ── Display candidate table ───────────────────────────────────────────────────
cand = st.session_state["sb_candidates"].copy()
if "EventID" in cand.columns:
    cand["EventID"] = cand["EventID"].map(plain_int_str)
col_cfg = {"\u2713": st.column_config.CheckboxColumn("Select")}
if "Industry Loss ($B)" in cand.columns:
    col_cfg["Industry Loss ($B)"] = st.column_config.NumberColumn(format="$%.2fB")

n_events = len(cand)
st.caption(f"{n_events} candidate event{'s' if n_events != 1 else ''} found")
edited = st.data_editor(cand, use_container_width=True, hide_index=True, num_rows="fixed", column_config=col_cfg)
st.session_state["sb_candidates"] = edited

# ── Step 4: Scenario assignment ────────────────────────────────────────────────
section_header("Assign Scenarios", "Select Low, Medium, and High severity events")

shortlist = edited[edited["\u2713"]] if edited["\u2713"].any() else edited
selected_ids = ["(none)"] + [str(int(v)) for v in shortlist["EventID"].tolist()]
ranked = shortlist.sort_values("Industry Loss ($B)", ascending=True) if "Industry Loss ($B)" in shortlist.columns else shortlist
ranked_ids = [str(int(v)) for v in ranked["EventID"].tolist()] if len(ranked) else []

for key, default_idx in [("sb_low_pick", 0), ("sb_med_pick", None), ("sb_high_pick", -1)]:
    if st.session_state.get(key) not in selected_ids:
        if default_idx is None:
            default_idx = len(ranked_ids) // 2
        st.session_state[key] = ranked_ids[default_idx] if ranked_ids else "(none)"

s1, s2, s3 = st.columns(3)
with s1:
    st.markdown(f'<div class="scenario-label" style="color:{SCENARIO_LOW};">LOW SCENARIO</div>', unsafe_allow_html=True)
    low_pick = st.selectbox("Event ID", selected_ids, key="sb_low_pick", label_visibility="collapsed")
    low_id = int(low_pick) if low_pick != "(none)" else int(st.number_input("Low EventID", min_value=0, value=0, step=1, key="sb_low_manual"))
with s2:
    st.markdown(f'<div class="scenario-label" style="color:{SCENARIO_MED};">MEDIUM SCENARIO</div>', unsafe_allow_html=True)
    med_pick = st.selectbox("Event ID", selected_ids, key="sb_med_pick", label_visibility="collapsed")
    med_id = int(med_pick) if med_pick != "(none)" else int(st.number_input("Med EventID", min_value=0, value=0, step=1, key="sb_med_manual"))
with s3:
    st.markdown(f'<div class="scenario-label" style="color:{SCENARIO_HIGH};">HIGH SCENARIO</div>', unsafe_allow_html=True)
    high_pick = st.selectbox("Event ID", selected_ids, key="sb_high_pick", label_visibility="collapsed")
    high_id = int(high_pick) if high_pick != "(none)" else int(st.number_input("High EventID", min_value=0, value=0, step=1, key="sb_high_manual"))

with st.expander("View generated SQL"):
    st.code(build_output_sql(DB, low_id, med_id, high_id), language="sql")

# ── Step 5: Run analysis ──────────────────────────────────────────────────────
if st.button("Analyze Portfolio Impact", type="primary", use_container_width=True):
    with st.spinner("Running waterfall analysis..."):
        try:
            df_out = run_sql(SRV, DB, build_output_sql(DB, low_id, med_id, high_id))
            if df_out is not None and not df_out.empty:
                st.session_state["sb_waterfall"] = df_out
            else:
                st.warning("No rows returned for these event IDs.")
        except Exception as exc:
            st.error(f"Analysis failed: {exc}")

if "sb_waterfall" not in st.session_state:
    st.stop()

# ═══════════════════════════════════════════════════════════════════════════════
# RESULTS DASHBOARD
# ═══════════════════════════════════════════════════════════════════════════════
df_out = st.session_state["sb_waterfall"]
st.divider()
section_header("Portfolio Impact Dashboard")

# ── Summary by scenario ───────────────────────────────────────────────────────
summary = (
    df_out.groupby("Scenario", dropna=False)
    .agg(
        contracts=("Contract #", "nunique"),
        industry_b=("Industry Loss ($B)", "max"),
        gross_m=("Gross Loss $M", "sum"),
    )
    .reset_index()
)
summary["mkt_share"] = (summary["gross_m"] / (summary["industry_b"] * 1000.0) * 100.0).where(summary["industry_b"] > 0, 0.0)
summary["mkt_share_fmt"] = summary["mkt_share"].map(lambda x: f"{x:.2f}%")

_order = pd.CategoricalDtype(categories=["Low", "Med", "High"], ordered=True)
summary["Scenario"] = summary["Scenario"].astype(_order)
summary = summary.sort_values("Scenario").reset_index(drop=True)

# ── Scenario cards row ────────────────────────────────────────────────────────
cols = st.columns(3)
for i, row in summary.iterrows():
    with cols[i % 3]:
        scenario_summary_card(
            scenario=row["Scenario"],
            gross_loss_m=row["gross_m"],
            contracts=int(row["contracts"]),
            market_share=row["mkt_share_fmt"],
            industry_loss_b=row["industry_b"],
        )

# ── Summary table (copy-friendly) ─────────────────────────────────────────────
summary_display = summary.rename(columns={
    "contracts": "Impacted Contracts",
    "industry_b": "Industry Loss ($B)",
    "gross_m": "Gross Loss $M",
    "mkt_share_fmt": "Market Share %",
})[["Scenario", "Impacted Contracts", "Industry Loss ($B)", "Gross Loss $M", "Market Share %"]]
copy_button(summary_display, "Copy Summary", "sb_summary")
st.dataframe(summary_display, use_container_width=True, hide_index=True)

# ── Scenario comparison chart ─────────────────────────────────────────────────
section_header("Scenario Comparison")

fig = go.Figure()
for _, row in summary.iterrows():
    sc = row["Scenario"]
    fig.add_trace(go.Bar(
        x=[sc],
        y=[row["gross_m"]],
        name=sc,
        marker_color=SCENARIO_COLOR_MAP.get(sc, EVEREST_BLUE),
        text=[f"${row['gross_m']:,.1f}M"],
        textposition="outside",
        hovertemplate=f"<b>{sc} Scenario</b><br>Gross Loss: $%{{y:,.1f}}M<br>Contracts: {int(row['contracts'])}<br>Market Share: {row['mkt_share_fmt']}<extra></extra>",
    ))

fig.update_layout(
    yaxis_title="Gross Loss ($M)",
    showlegend=False,
    height=350,
    margin=dict(t=30, b=40, l=60, r=20),
    plot_bgcolor="rgba(0,0,0,0)",
    yaxis=dict(gridcolor="#E2E8F0"),
    font=dict(family="Inter, Segoe UI, sans-serif", color=DARK_BLUE),
)
st.plotly_chart(fig, use_container_width=True)

# ── Loss by contract ──────────────────────────────────────────────────────────
section_header("Loss by Contract", "Low / Med / High")

loss_pivot = (
    df_out.pivot_table(
        index=["layerkey", "Department", "Company", "SubType", "Contract #", "Terms", "100% Limit ($)", "ROL", "Share"],
        columns="Scenario",
        values="Gross Loss $M",
        aggfunc="sum",
        fill_value=0.0,
    )
    .reset_index()
)

for sc in ["Low", "Med", "High"]:
    if sc not in loss_pivot.columns:
        loss_pivot[sc] = 0.0

loss_pivot = loss_pivot.rename(columns={
    "layerkey": "Layerkey", "SubType": "Subtype", "Contract #": "Contract",
    "100% Limit ($)": "Everest Limit",
    "Low": "Low $M", "Med": "Med $M", "High": "High $M",
})

ordered_cols = ["Layerkey", "Department", "Company", "Subtype", "Contract", "Terms", "Everest Limit", "ROL", "Share", "Low $M", "Med $M", "High $M"]
loss_pivot = loss_pivot[[c for c in ordered_cols if c in loss_pivot.columns]]

if "Layerkey" in loss_pivot.columns:
    loss_pivot["Layerkey"] = loss_pivot["Layerkey"].map(plain_int_str)
if "Share" in loss_pivot.columns:
    loss_pivot["Share"] = format_pct_series(loss_pivot["Share"])

copy_button(loss_pivot, "Copy Loss by Contract", "sb_contracts")
st.dataframe(loss_pivot, use_container_width=True, hide_index=True)

# ── Full output ───────────────────────────────────────────────────────────────
with st.expander("Full output detail"):
    df_fmt = df_out.copy()
    if "layerkey" in df_fmt.columns:
        df_fmt["layerkey"] = df_fmt["layerkey"].map(plain_int_str)
    if "Share" in df_fmt.columns:
        df_fmt["Share"] = format_pct_series(df_fmt["Share"])
    copy_button(df_fmt, "Copy Full Output", "sb_full")
    st.dataframe(df_fmt, use_container_width=True, hide_index=True)
