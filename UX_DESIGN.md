# CAT-NIP UX Design Document

## 1. Product Vision

CAT-NIP transforms catastrophe portfolio analysis from a form-heavy technical workflow into an AI-first conversational experience. The analyst describes a catastrophe scenario in natural language, and CAT-NIP interprets, recommends filters, finds matching historical/modeled events, and produces an executive-quality portfolio impact dashboard — all in a single progressive flow.

**Design philosophy:** Bloomberg Terminal credibility, ChatGPT simplicity, Palantir Foundry density.

---

## 2. Information Architecture

```
CAT-NIP
├── Scenario Builder (default)     ← AI-first event analysis
│   ├── Prompt
│   ├── Parsed Filters
│   ├── Candidate Events
│   ├── Scenario Assignment
│   └── Portfolio Impact Dashboard
├── Classic View                    ← Legacy form-based workflow
└── (Sidebar)
    ├── Logo + branding
    ├── Connection info (server, database)
    ├── Next Quarter rotation
    └── Advanced server override
```

**Navigation:** Two-page architecture. Scenario Builder is the default and recommended experience. Classic View preserves the legacy form-based flow for power users who prefer explicit control. Sidebar holds connection configuration — always accessible, never in the way.

**Future pages:** Saved Analyses, Administration (stubbed in roadmap).

---

## 3. End-to-End User Flow

```
[Analyst opens CAT-NIP]
        │
        ▼
[Hero prompt: "What catastrophe event would you like to analyze?"]
        │
        │  Types: "Category 5 hurricane near Miami, $5-15B industry loss"
        ▼
[Parsed Event Card]
  ├─ Peril: Wind       ● HIGH CONFIDENCE
  ├─ Region: FL        ● HIGH CONFIDENCE
  └─ Loss: $5-15B      ● HIGH CONFIDENCE
        │
        │  (Optional) Expand "Refine Filters" to adjust
        ▼
[Click "Find Matching Events"]
        │
        ▼
[Candidate Events Table]
  ├─ Checkboxes to shortlist
  └─ Auto-sorted by industry loss
        │
        │  System pre-assigns Low / Med / High from ranked events
        ▼
[Scenario Assignment]
  ├─ Low:  EventID 12345   ← lowest industry loss
  ├─ Med:  EventID 23456   ← median
  └─ High: EventID 34567   ← highest
        │
        │  (Optional) Override any assignment
        ▼
[Click "Analyze Portfolio Impact"]
        │
        ▼
[Portfolio Impact Dashboard]
  ├─ 3x Scenario Summary Cards (Low / Med / High)
  │   └─ Gross Loss, Contracts, Market Share, Industry Loss
  ├─ Scenario Comparison Bar Chart
  ├─ Loss by Contract Table (pivot: Low/Med/High columns)
  └─ Full Output Detail (expandable)
```

---

## 4. Screen-by-Screen Design

### 4.1 Prompt Screen

**Layout:** Full-width hero gradient banner (dark blue → mid blue) with large heading and subtitle. Below it, a full-width text area with a compact "Analyze" button right-aligned.

**Rationale:** The prompt is the #1 entry point. Making it visually dominant signals "start here" without instructions. The gradient banner differentiates it from the rest of the page and creates visual hierarchy. The conversational framing ("What catastrophe event would you like to analyze?") is modeled on ChatGPT's approachability while maintaining professional tone.

### 4.2 Parsed Event Card

**Layout:** Card with left blue accent border. Header row: "Parsed Event" title left-aligned, confidence badge right-aligned. Below: quoted query in italic gray. Below: filter pills (peril, region, loss range, keyword, magnitude, model).

**Pills:** Blue background for detected values, gray background for "Not detected."

**Confidence logic:** HIGH (green badge) when 2+ of 3 core fields parsed. PARTIAL (amber) for 1. NEEDS REFINEMENT (red) for 0.

**Rationale:** This replaces the old "Filters updated from scenario query" toast with persistent, scannable feedback. The analyst can immediately see what CAT-NIP understood and what needs refinement. Confidence badges set expectations before the SQL query runs. This pattern is borrowed from Bloomberg's entity recognition displays.

### 4.3 Refinement Panel

**Layout:** Collapsed `st.expander`. Three columns: Peril dropdown, Zone text input, Industry Loss slider. Filter mode radio buttons below. Conditional display of Event Characteristics controls (keyword, magnitude, AIR table selection).

**Rationale:** Progressive disclosure. Most queries produce good parses — 80% of users never open this. The 20% who need manual control find everything in one place. Moving from "always visible" to "expandable" reduces visual noise significantly.

### 4.4 Candidate Events

**Layout:** Section header with blue underline. "Find Matching Events" primary button (full width). Caption showing count. Interactive data_editor with checkbox column and number-formatted Industry Loss.

**Rationale:** The data_editor is retained because analysts need precise row-level selection and the ability to scan many events (sometimes 50+). Cards don't scale for this. The improvement is contextual: section headers, event counts, and better column formatting reduce cognitive load.

### 4.5 Scenario Assignment

**Layout:** Three equal columns. Each has a colored label (green/amber/red) + dropdown + optional manual ID input. Colors match the scenario semantics used throughout the results dashboard.

**Rationale:** Side-by-side layout enables instant comparison. Color-coding (Low=green, Med=amber, High=red) creates a visual language that carries through to the results. Auto-assignment from ranked candidates means most analysts can skip manual selection entirely.

### 4.6 Portfolio Impact Dashboard

**Layout:**

Row 1: Three scenario summary cards (Low | Med | High)
- Each card: colored top border, large gross loss value, sub-metrics (contracts, market share, industry loss)

Row 2: Scenario comparison bar chart (Plotly)
- Three bars, color-matched, with value labels outside

Row 3: Loss by contract table
- Pivoted: one row per contract, columns for Low/Med/High gross loss
- Copy button above

Row 4: Full output (expandable)
- Raw detail table with all columns

**Rationale:** The "cards first, chart second, table third" hierarchy serves three audiences in order:
1. **Executives** read the cards (5 seconds)
2. **Managers** read the chart (15 seconds)
3. **Analysts** read the tables (unlimited)

This is the core progressive disclosure principle applied to output rather than input.

---

## 5. Design System

### Colors

| Token | Hex | Usage |
|---|---|---|
| `EVEREST_BLUE` | #235CF4 | Primary actions, accents, links |
| `MID_BLUE` | #0A3699 | Hover states, secondary emphasis |
| `DARK_BLUE` | #061C49 | Text, headings, sidebar background |
| `MID_GRAY` | #A4ABC8 | Captions, secondary text |
| `LIGHT_GRAY` | #F5F5F5 | Backgrounds, subtle fills |
| `BORDER_GRAY` | #E2E8F0 | Card borders, dividers |
| `SCENARIO_LOW` | #198038 | Low scenario (green) |
| `SCENARIO_MED` | #E67E22 | Medium scenario (amber) |
| `SCENARIO_HIGH` | #DA1E28 | High scenario (red) |

### Typography

- **Font:** Inter (Google Fonts), fallback to Segoe UI, system sans-serif
- **Headings:** 700 weight, DARK_BLUE
- **Body:** 400 weight, 0.88rem
- **Captions:** 0.78rem, MID_GRAY
- **Labels:** 0.72rem, uppercase, 0.04em letter-spacing

### Component Library

| Component | File | Purpose |
|---|---|---|
| `step_indicator()` | components.py | 5-step progress bar |
| `prompt_hero()` | components.py | Gradient hero prompt area |
| `parsed_event_card()` | components.py | AI interpretation display |
| `scenario_summary_card()` | components.py | Scenario result card |
| `section_header()` | components.py | Blue-underlined section title |
| `copy_button()` | components.py | Clipboard copy for tables |
| `inject_global_css()` | theme.py | Global style injection |

---

## 6. UX Rationale

### Why AI-first prompt instead of form fields?

The current form requires analysts to know the exact filter names and valid values before they start. The prompt inverts this: the analyst describes intent, and CAT-NIP infers structure. This reduces the learning curve for new analysts from hours to minutes.

### Why progressive disclosure instead of tabs?

Tabs hide information. Progressive disclosure reveals it in sequence. For a workflow that is inherently sequential (describe → filter → select → analyze), progressive disclosure matches the mental model. Each step's output is visible context for the next step.

### Why keep the data_editor for candidate events?

Cards are better for 3-8 items. Candidate events can be 50+. A searchable, sortable, selectable table is the right primitive for large collections. The data_editor adds inline checkboxes without leaving the context.

### Why scenario cards instead of a table?

The scenario summary has exactly 3 items (Low/Med/High) with 4 metrics each. This is the sweet spot for card layout: scannable, comparable, visually distinct. A table would bury the scenario comparison in undifferentiated rows.

---

## 7. AI Interaction Patterns

### Natural Language Parsing

The current `parse_scenario_query()` uses regex patterns to extract:
- Peril (from PERIL_ALIASES dictionary)
- Zone (from ZONE_TOKEN_MAP + regex patterns)
- Industry loss range (regex for "$X-Y billion")
- Magnitude range (regex for "magnitude X-Y")
- Model number (regex for "model #N")
- Event keywords (from "description:" prefix)

**Future enhancement:** Replace regex parsing with an LLM call for more robust extraction:
```python
# Future: replace parse_scenario_query with LLM extraction
prompt = f"Extract peril, region, loss range from: {user_query}"
response = llm.extract_structured(prompt, schema=EventFilters)
```

### Confidence Display

The parsed event card shows confidence as a ratio of successfully extracted fields. This sets user expectations: "HIGH CONFIDENCE" means CAT-NIP understood the query well; "NEEDS REFINEMENT" means the user should check the filter panel.

### Auto-Selection

Multiple layers of auto-selection reduce manual work:
1. **Peril → AIR table prefiltering** (keyword scoring against table names)
2. **Model inference** from Industry database (highest-loss model for peril/zone)
3. **Keyword matching** against AIR event descriptions
4. **Scenario pre-assignment** from ranked candidate events (lowest → Low, median → Med, highest → High)

---

## 8. Dashboard Layout

The results dashboard follows the "inverted pyramid" pattern:

```
┌─────────────────────────────────────────────────────┐
│  [Low Card]      [Med Card]      [High Card]        │  ← Executive summary (5 sec)
│  $2.3M gross     $8.7M gross     $24.1M gross       │
│  12 contracts    23 contracts    41 contracts        │
├─────────────────────────────────────────────────────┤
│  ┌───────────────────────────────────────────────┐  │
│  │  Bar Chart: Scenario Comparison               │  │  ← Visual comparison (15 sec)
│  │  [Low]    [Med]         [High]                │  │
│  └───────────────────────────────────────────────┘  │
├─────────────────────────────────────────────────────┤
│  Loss by Contract Table                             │  ← Analyst detail (unlimited)
│  Layerkey | Dept | Company | Low $M | Med $M | Hi  │
│  123456   | RE   | ACME    | 0.12   | 0.45   | 1.2 │
│  ...                                                │
├─────────────────────────────────────────────────────┤
│  ▶ Full Output Detail (expandable)                  │  ← Raw data (on demand)
└─────────────────────────────────────────────────────┘
```

---

## 9. Mobile and Tablet Considerations

Streamlit's responsive layout handles mobile/tablet automatically via its CSS grid. Specific considerations:

- **Columns collapse:** 3-column layouts (scenario cards, filter controls) stack vertically on narrow screens.
- **Hero prompt:** Full-width on all devices; text area height is fixed at 80px (sufficient on mobile).
- **Data tables:** Horizontal scroll on narrow screens; Streamlit data_editor handles this natively.
- **Copy buttons:** Clipboard API works on mobile browsers but may require HTTPS.
- **Sidebar:** Collapsible on mobile (Streamlit default behavior).

**Recommendation:** Primary deployment is desktop (analyst workstations). Mobile is view-only for executives reviewing shared results. No mobile-specific features needed in Phase 1.

---

## 10. Future Enhancements and Roadmap

### Phase 1 (Current) — Foundation
- [x] AI-first prompt with NLP parsing
- [x] Progressive disclosure workflow
- [x] Scenario comparison cards and chart
- [x] Executive-quality dashboard
- [x] Design system and component library

### Phase 2 — Intelligence
- [ ] LLM-powered query parsing (replace regex)
- [ ] Saved analyses / bookmarks
- [ ] PDF/PPTX export for executive presentations
- [ ] Geographic impact map (Plotly scatter_mapbox on waterfall results)

### Phase 3 — Collaboration
- [ ] Shared analysis links
- [ ] Annotation and commentary on scenarios
- [ ] Audit trail / version history
- [ ] User authentication and role-based access

### Phase 4 — Advanced Analytics
- [ ] EP curve visualization per scenario
- [ ] Tail risk metrics (VaR, TVaR)
- [ ] Multi-event / aggregate scenario analysis
- [ ] What-if modeling (adjust terms, limits, shares)
- [ ] Integration with Databricks notebooks for custom analysis
