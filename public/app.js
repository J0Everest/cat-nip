let rows = [];

const headerFilters = Array.from(document.querySelectorAll("[data-filter]"));
const body = document.getElementById("tableBody");
const totalsBody = document.getElementById("totalsBody");
const meta = document.getElementById("tableMeta");
const errorEl = document.getElementById("error");
const copilotForm = document.getElementById("copilotForm");
const copilotQuestion = document.getElementById("copilotQuestion");
const copilotAskBtn = document.getElementById("copilotAskBtn");
const copilotResponse = document.getElementById("copilotResponse");
const STATUS_ORDER = ["Quoted", "Authorized", "Bound"];

function toNumber(raw) {
  return Number(String(raw ?? "").replace(/,/g, "").replace(/%/g, "")) || 0;
}

function formatPercent(num) {
  return `${num.toFixed(2)}%`;
}

function formatWholeNumber(num) {
  return num.toLocaleString(undefined, { maximumFractionDigits: 0 });
}

function render() {
  const activeFilters = Object.fromEntries(
    headerFilters
      .map((el) => [el.dataset.filter, String(el.value || "").trim().toLowerCase()])
      .filter(([, value]) => value)
  );

  const filtered = rows.filter((r) =>
    Object.entries(activeFilters).every(([key, value]) =>
      String(r[key] ?? "").toLowerCase().includes(value)
    )
  );

  body.innerHTML = "";
  const groups = [...new Set(filtered.map((r) => r.group))];

  groups.forEach((group, groupIndex) => {
    const inGroup = filtered.filter((r) => r.group === group);
    inGroup.forEach((r, index) => {
      const tr = document.createElement("tr");
      tr.className = groupIndex % 2 === 0 ? "group-a" : "group-b";

      if (index === 0) {
        const tdGroup = document.createElement("td");
        tdGroup.rowSpan = inGroup.length;
        tdGroup.className = "center bold";
        tdGroup.textContent = String(group);
        tr.appendChild(tdGroup);
      }

      const cells = [
        { value: r.asOfDate },
        { value: r.status, className: `status ${r.status}` },
        { value: r.layerDesc },
        { value: r.terms },
        { value: r.curr },
        { value: r.reinst },
        { value: r.rol, className: "right" },
        { value: r.cr, className: "right" },
        { value: r.sdf, className: "right" },
        { value: r.roe, className: "right" },
        { value: r.finalShare, className: "right" },
        { value: r.ourLimit, className: "right" },
        { value: r.ourPremium, className: "right" },
        { value: r.finalRate, className: "right" },
        { value: r.subjectBase, className: "right" },
        { value: r.contract },
        { value: r.user }
      ];

      cells.forEach((c) => {
        const td = document.createElement("td");
        td.textContent = c.value;
        if (c.className) td.className = c.className;
        tr.appendChild(td);
      });

      body.appendChild(tr);
    });
  });

  meta.textContent = `Showing ${filtered.length} row${filtered.length === 1 ? "" : "s"}`;

  const totalsByStatus = STATUS_ORDER.map((status) => {
    const set = filtered.filter((r) => r.status === status);
    const limitTotal = set.reduce((sum, r) => sum + toNumber(r.ourLimit), 0);
    const premiumTotal = set.reduce((sum, r) => sum + toNumber(r.ourPremium), 0);
    const rolAvg = set.length ? set.reduce((sum, r) => sum + toNumber(r.rol), 0) / set.length : null;
    const crAvg = set.length ? set.reduce((sum, r) => sum + toNumber(r.cr), 0) / set.length : null;

    return { status, rowCount: set.length, limitTotal, premiumTotal, rolAvg, crAvg };
  });

  totalsBody.innerHTML = totalsByStatus.map((item) => `
    <tr class="status-total">
      <td colspan="7">Totals - ${item.status}</td>
      <td class="right">${item.rolAvg == null ? "N/A" : formatPercent(item.rolAvg)}</td>
      <td class="right">${item.crAvg == null ? "N/A" : formatPercent(item.crAvg)}</td>
      <td></td>
      <td></td>
      <td></td>
      <td class="right">${formatWholeNumber(item.limitTotal)}</td>
      <td class="right">${formatWholeNumber(item.premiumTotal)}</td>
      <td></td>
      <td></td>
      <td></td>
      <td class="right">Rows: ${item.rowCount}</td>
    </tr>
  `).join("");
}

async function loadRows() {
  try {
    const res = await fetch("/api/placements");
    if (!res.ok) throw new Error(`API error ${res.status}`);
    rows = await res.json();
    errorEl.textContent = "";
    render();
  } catch (error) {
    errorEl.textContent = `Could not load SQL data: ${error.message}`;
    rows = [];
    render();
  }
}

function renderCopilotResponse(payload) {
  if (!payload) {
    copilotResponse.textContent = "No response received.";
    return;
  }

  if (payload.error) {
    copilotResponse.textContent = `Could not answer from CatAccum: ${payload.error}`;
    return;
  }

  const lines = [];

  if (payload.summary) lines.push(payload.summary);

  if (payload.detected) {
    const peril = payload.detected.peril || "not detected";
    const region = payload.detected.region || "not detected";
    lines.push(`Detected filters → peril: ${peril}, region: ${region}`);
  }

  if (Array.isArray(payload.items) && payload.items.length) {
    lines.push("Top impacts:");
    payload.items.forEach((item, idx) => {
      const peril = item.peril || "N/A";
      const region = item.region || "N/A";
      const impact = Number(item.totalImpact || 0).toLocaleString(undefined, {
        maximumFractionDigits: 0
      });
      lines.push(`${idx + 1}. ${peril} in ${region} | exposures: ${item.exposureCount ?? 0} | impact: ${impact}`);
    });
  }

  copilotResponse.textContent = lines.join("\n");
}

async function askCopilot(question) {
  copilotAskBtn.disabled = true;
  copilotResponse.textContent = "Analyzing CatAccum scenario...";

  try {
    const res = await fetch("/api/copilot/ask", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question })
    });

    const payload = await res.json();
    if (!res.ok) {
      throw new Error(payload.error || `API error ${res.status}`);
    }

    renderCopilotResponse(payload);
  } catch (error) {
    copilotResponse.textContent = `Could not answer from CatAccum: ${error.message}`;
  } finally {
    copilotAskBtn.disabled = false;
  }
}

headerFilters.forEach((el) => {
  el.addEventListener("input", render);
  el.addEventListener("change", render);
});

if (copilotForm) {
  copilotForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const question = String(copilotQuestion.value || "").trim();
    if (!question) return;
    await askCopilot(question);
  });
}

loadRows();
