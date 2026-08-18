"""
CAT-NIP reusable UI components.
All functions return HTML strings via st.markdown or render inline.
"""
import json
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from theme import (
    DARK_BLUE, MID_GRAY, EVEREST_BLUE, BORDER_GRAY, WHITE,
    SCENARIO_LOW, SCENARIO_MED, SCENARIO_HIGH,
    COLOR_SUCCESS, COLOR_WARNING, COLOR_DANGER,
)


# ── Step indicator ─────────────────────────────────────────────────────────────
def step_indicator(steps: list[str], current_idx: int):
    items = []
    for i, label in enumerate(steps):
        cls = "step-item"
        if i < current_idx:
            cls += " done"
        elif i == current_idx:
            cls += " active"
        items.append(f'<div class="{cls}">{label}</div>')
    st.markdown(f'<div class="step-bar">{"".join(items)}</div>', unsafe_allow_html=True)


# ── Section header ─────────────────────────────────────────────────────────────
def section_header(title: str, subtitle: str = ""):
    sub = f'<span style="font-weight:400;color:{MID_GRAY};font-size:0.85rem;margin-left:12px;">{subtitle}</span>' if subtitle else ""
    st.markdown(f'<div class="catnip-section-title">{title}{sub}</div>', unsafe_allow_html=True)


# ── Prompt hero ────────────────────────────────────────────────────────────────
def prompt_hero():
    st.markdown(
        '<div class="prompt-hero">'
        "<h2>What catastrophe event would you like to analyze?</h2>"
        "<p>Describe a natural disaster scenario and CAT-NIP will find matching events and estimate portfolio impact.</p>"
        "</div>",
        unsafe_allow_html=True,
    )


# ── Confidence badge ───────────────────────────────────────────────────────────
def _badge_html(level: str, text: str) -> str:
    cls_map = {"high": "catnip-badge-high", "med": "catnip-badge-med", "low": "catnip-badge-low"}
    cls = cls_map.get(level, "catnip-badge-med")
    return f'<span class="catnip-badge {cls}">{text}</span>'


# ── Filter pills ───────────────────────────────────────────────────────────────
def _pill_html(label: str, value: str, muted: bool = False) -> str:
    cls = "catnip-pill-muted" if muted else "catnip-pill"
    return f'<span class="{cls}"><strong>{label}:</strong> {value}</span>'


# ── Parsed event card ──────────────────────────────────────────────────────────
def parsed_event_card(parsed: dict, raw_query: str):
    pills = []
    confidence_parts = 0
    total_parts = 3  # peril, zone, loss range

    if parsed.get("peril"):
        pills.append(_pill_html("Peril", parsed["peril"]))
        confidence_parts += 1
    else:
        pills.append(_pill_html("Peril", "Not detected", muted=True))

    if parsed.get("zone"):
        pills.append(_pill_html("Region", parsed["zone"]))
        confidence_parts += 1
    else:
        pills.append(_pill_html("Region", "Not detected", muted=True))

    if parsed.get("loss_lo") is not None and parsed.get("loss_hi") is not None:
        pills.append(_pill_html("Industry Loss", f"${parsed['loss_lo']:.1f}B \u2013 ${parsed['loss_hi']:.1f}B"))
        confidence_parts += 1
    else:
        pills.append(_pill_html("Industry Loss", "Full range", muted=True))

    if parsed.get("event_keyword"):
        pills.append(_pill_html("Keyword", parsed["event_keyword"]))

    if parsed.get("mag_lo") is not None and parsed.get("mag_hi") is not None:
        pills.append(_pill_html("Magnitude", f"{parsed['mag_lo']:.1f} \u2013 {parsed['mag_hi']:.1f}"))

    if parsed.get("model_no"):
        pills.append(_pill_html("Model #", str(parsed["model_no"])))

    conf_ratio = confidence_parts / total_parts
    if conf_ratio >= 0.66:
        badge = _badge_html("high", "HIGH CONFIDENCE")
    elif conf_ratio >= 0.33:
        badge = _badge_html("med", "PARTIAL MATCH")
    else:
        badge = _badge_html("low", "NEEDS REFINEMENT")

    pills_html = " ".join(pills)

    st.markdown(
        f"""<div class="catnip-card catnip-card-accent">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;">
            <span style="font-weight:700;color:{DARK_BLUE};font-size:0.95rem;">Parsed Event</span>
            {badge}
        </div>
        <div style="margin-bottom:8px;color:{MID_GRAY};font-size:0.82rem;font-style:italic;">
            &ldquo;{raw_query}&rdquo;
        </div>
        <div>{pills_html}</div>
        </div>""",
        unsafe_allow_html=True,
    )


# ── Scenario summary card ─────────────────────────────────────────────────────
def scenario_summary_card(scenario: str, gross_loss_m: float, contracts: int, market_share: str, industry_loss_b: float):
    color_map = {"Low": SCENARIO_LOW, "Med": SCENARIO_MED, "High": SCENARIO_HIGH}
    color = color_map.get(scenario, EVEREST_BLUE)
    css_class = f"scenario-card scenario-card-{scenario.lower()}"

    st.markdown(
        f"""<div class="{css_class}">
        <div class="scenario-label" style="color:{color};">{scenario} Scenario</div>
        <div class="scenario-value">${gross_loss_m:,.1f}M</div>
        <div class="scenario-detail">Gross Loss</div>
        <hr style="margin:8px 0;border-color:{BORDER_GRAY};">
        <div style="display:flex;justify-content:space-around;font-size:0.78rem;">
            <div><strong>{contracts}</strong><br><span style="color:{MID_GRAY};">Contracts</span></div>
            <div><strong>{market_share}</strong><br><span style="color:{MID_GRAY};">Mkt Share</span></div>
            <div><strong>${industry_loss_b:.1f}B</strong><br><span style="color:{MID_GRAY};">Industry</span></div>
        </div>
        </div>""",
        unsafe_allow_html=True,
    )


# ── Copy-to-clipboard button ──────────────────────────────────────────────────
def copy_button(df: pd.DataFrame, label: str, key: str):
    if df is None or df.empty:
        return
    payload = df.to_csv(index=False, sep="\t")
    js_text = json.dumps(payload)
    btn_id = f"copy_btn_{key}"
    html = f"""
<div style="margin: 0.15rem 0 0.5rem 0;">
    <button id="{btn_id}" style="
            background:{EVEREST_BLUE};color:#fff;border:none;border-radius:6px;
            padding:6px 10px;cursor:pointer;font-size:12px;">
        {label}
    </button>
    <span id="{btn_id}_msg" style="margin-left:8px;color:#2e7d32;font-size:12px;"></span>
</div>
<script>
    const btn = document.getElementById('{btn_id}');
    const msg = document.getElementById('{btn_id}_msg');
    if (btn) {{
        btn.addEventListener('click', async () => {{
            try {{
                await navigator.clipboard.writeText({js_text});
                if (msg) msg.textContent = 'Copied';
                setTimeout(() => {{ if (msg) msg.textContent = ''; }}, 1500);
            }} catch (e) {{
                if (msg) msg.textContent = 'Clipboard blocked';
            }}
        }});
    }}
</script>
"""
    components.html(html, height=38)


# ── Formatting helpers ─────────────────────────────────────────────────────────
def plain_int_str(v) -> str:
    if pd.isna(v):
        return ""
    try:
        return str(int(float(v)))
    except Exception:
        return str(v).replace(",", "")


def format_pct_series(values: pd.Series) -> pd.Series:
    vals = pd.to_numeric(values, errors="coerce")
    non_na = vals.dropna()
    if not non_na.empty and (non_na.abs() <= 1.0).all():
        vals = vals * 100.0
    return vals.map(lambda x: "" if pd.isna(x) else f"{x:.1f}%")
