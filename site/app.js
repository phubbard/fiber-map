(function () {
  "use strict";

  // Fixed categorical slots: a company keeps its colour whatever else is on screen.
  // Everything past slot 7 folds into slot 8 ("other") and relies on the code letters.
  const COMPANIES = {
    "AT&T": { slot: 1, code: "AT" },
    "Spectrum": { slot: 2, code: "SP" },
    "Cox": { slot: 3, code: "CX" },
    "Wyyerd": { slot: 4, code: "WY", darkInk: true },
    "Verizon": { slot: 5, code: "VZ" },
    "Zayo": { slot: 6, code: "ZY" },
    "Crown Castle": { slot: 7, code: "CC" },
  };
  const OTHER_CODES = {
    "Google Fiber": "GF", "T-Mobile": "TM", "Lumen": "LU", "Frontier": "FR", "Sonic": "SO",
    "Ting": "TI", "Astound": "AS", "GeoLinks": "GL", "Fiber (other)": "F?",
  };
  const KIND_LABEL = { row: "Right-of-way", traffic: "Traffic control", encroachment: "Encroachment" };
  const DAY = 864e5;

  const $ = (sel) => document.querySelector(sel);
  const meta = (company) => COMPANIES[company] || { slot: 8, code: OTHER_CODES[company] || "··", other: true };
  const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const cssVar = (name) => getComputedStyle(document.documentElement).getPropertyValue(name).trim();
  const sum = (obj, key) => Object.values(obj || {}).reduce((a, c) => a + (c[key] || 0), 0);

  function daysSince(iso) {
    if (!iso) return Infinity;
    const t = Date.parse(iso.length === 10 ? iso + "T12:00:00" : iso);
    return Number.isNaN(t) ? Infinity : (Date.now() - t) / DAY;
  }
  function fmtDate(iso) {
    if (!iso) return "—";
    const d = new Date(iso.length === 10 ? iso + "T12:00:00" : iso);
    return Number.isNaN(d.getTime()) ? iso : d.toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" });
  }
  function relTime(iso) {
    const d = daysSince(iso);
    if (!Number.isFinite(d)) return "";
    if (d < 1 / 24) return "just now";
    if (d < 1) return Math.round(d * 24) + "h ago";
    if (d < 14) return Math.round(d) + "d ago";
    const dt = new Date(iso);
    const sameYear = dt.getFullYear() === new Date().getFullYear();
    return dt.toLocaleDateString(undefined, sameYear ? { month: "short", day: "numeric" } : { month: "short", day: "numeric", year: "numeric" });
  }
  function dot(company, extraClass) {
    const m = meta(company);
    return `<span class="chip-dot ${m.darkInk ? "dark-ink" : ""} ${extraClass || ""}" style="--c: var(--series-${m.slot})" aria-hidden="true">${esc(m.code)}</span>`;
  }

  // ---- header ---------------------------------------------------------------
  function renderHeader(data) {
    document.title = `Fiber map · ${data.area.label}`;
    $("#title").textContent = data.area.label;
    const km = (data.area.radius_km * 2).toFixed(1);
    $("#subtitle").textContent = `Updated ${relTime(data.generated_at)} · ${data.permits.length} telecom permits in a ${km} km box · ${data.news.length} headlines`;
    $("#links").innerHTML = data.links.map((l) => `<a href="${esc(l.url)}" target="_blank" rel="noopener">${esc(l.label)}</a>`).join("");
  }

  // ---- KPI tiles -------------------------------------------------------------
  function tile(label, value, delta, deltaLabel, sub) {
    let deltaHtml = "";
    if (delta !== null && delta !== undefined) {
      const cls = delta > 0 ? "up" : delta < 0 ? "down" : "flat";
      const sign = delta > 0 ? "+" : "";
      deltaHtml = `<div class="tile-delta ${cls}">${sign}${delta} ${esc(deltaLabel)}</div>`;
    }
    return `<div class="tile"><div class="tile-label">${esc(label)}</div><div class="tile-value">${esc(value)}</div>${deltaHtml}${sub ? `<div class="tile-sub">${esc(sub)}</div>` : ""}</div>`;
  }
  function renderKpis(data) {
    const P = data.permits;
    const isJob = (p) => p.kind !== "traffic";
    const fiberNow = P.filter((p) => p.fiber && isJob(p) && daysSince(p.created) <= 365).length;
    const fiberPrev = P.filter((p) => p.fiber && isJob(p) && daysSince(p.created) > 365 && daysSince(p.created) <= 730).length;
    const fiberDrops = P.filter((p) => p.fiber && isJob(p) && p.drop && daysSince(p.created) <= 365).length;
    const active = P.filter((p) => isJob(p) && (p.phase === "active" || p.phase === "planned"));
    const activeFiber = active.filter((p) => p.fiber).length;
    const newP = P.filter((p) => daysSince(p.first_seen) <= data.new_window_days).length;
    const newN = data.news.filter((n) => daysSince(n.first_seen) <= data.new_window_days).length;
    const tiles = [
      tile("Fiber permits here, last 12 months", fiberNow, fiberNow - fiberPrev, "vs prior 12 months", fiberDrops ? `${fiberDrops} of them single-property drops` : ""),
      tile("Open right-of-way permits here", active.length, null, "", `${activeFiber} of them fiber jobs`),
      tile(`New in the last ${data.new_window_days} days`, newP, null, "", `${newN} new headline${newN === 1 ? "" : "s"}`),
    ];
    const S = data.stats.source;
    if (data.source && data.source.source !== "none") {
      const now = sum(S.trailing12, "fiber");
      const prev = sum(S.prior12, "fiber");
      const top = Object.entries(S.trailing12 || {})
        .map(([co, c]) => [co, c.fiber || 0]).filter(([, n]) => n > 0)
        .sort((a, b) => b[1] - a[1]).slice(0, 3).map(([co, n]) => `${co} ${n}`).join(" · ");
      tiles.push(tile(`${data.source.label}: fiber permits, last 12 months`, now, now - prev, "vs prior 12 months", top));
    }
    $("#kpis").innerHTML = tiles.join("");
  }

  // ---- map -------------------------------------------------------------------
  function renderMap(data) {
    const [s, w, n, e] = data.area.bbox;
    const map = L.map("map", { scrollWheelZoom: false });
    map.fitBounds([[s, w], [n, e]]);
    // fitBounds shows the whole box with margin; zoom_offset (config, default 1) tightens it to the ZIP.
    const offset = Number(data.area.zoom_offset || 0);
    if (offset) map.setZoom(map.getZoom() + offset);
    const t = data.tiles || { mode: "remote" };
    if (t.mode === "local" && t.zooms && t.zooms.length) {
      const minZ = Math.min(...t.zooms), maxZ = Math.max(...t.zooms);
      L.tileLayer("tiles/{z}/{x}/{y}.png", {
        minZoom: minZ, maxZoom: 19, minNativeZoom: minZ, maxNativeZoom: maxZ,
        bounds: [[s - 0.03, w - 0.04], [n + 0.03, e + 0.04]],
        attribution: t.attribution || "&copy; OpenStreetMap contributors",
      }).addTo(map);
    } else {
      L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", { maxZoom: 19, attribution: "&copy; OpenStreetMap contributors" }).addTo(map);
    }
    L.rectangle([[s, w], [n, e]], { color: cssVar("--text-secondary") || "#52514e", weight: 1, dashArray: "4 4", fill: false, interactive: false }).addTo(map);

    const groups = new Map();   // company -> layerGroup
    const markers = new Map();  // permit id -> marker
    const state = { traffic: false, done: false, off: new Set() };

    function visible(p) {
      if (!state.traffic && p.kind === "traffic") return false;
      if (!state.done && (p.phase === "done" || p.phase === "cancelled")) return false;
      if (state.off.has(p.company)) return false;
      return true;
    }
    function popup(p) {
      return `<strong>${esc(p.company)}</strong> ${p.fiber ? '<span class="chip fiber">fiber</span>' : ""}${p.drop ? ' <span class="chip">single drop</span>' : ""}<br>` +
        `${esc(KIND_LABEL[p.kind] || p.kind)} · ${esc(p.status || p.phase)} · created ${fmtDate(p.created)}` +
        `${p.issued ? " · issued " + fmtDate(p.issued) : ""}${p.closed ? " · closed " + fmtDate(p.closed) : ""}<br>` +
        `${esc(p.address || "(no address)")}${p.job ? ` · job ${esc(p.job)}` : ""}<br><small>${esc(p.scope)}</small>`;
    }
    function build() {
      groups.forEach((g) => map.removeLayer(g));
      groups.clear(); markers.clear();
      for (const p of data.permits) {
        if (p.lat == null || p.lng == null || !visible(p)) continue;
        const m = meta(p.company);
        const size = p.kind !== "row" ? 13 : p.fiber ? 24 : 18;
        const icon = L.divIcon({
          className: "",
          html: `<div class="pin ${p.phase} ${p.kind} ${p.fiber ? "fiber" : ""} ${m.darkInk ? "dark-ink" : ""}" style="--c: var(--series-${m.slot})" title="${esc(p.company)}">${esc(m.code)}</div>`,
          iconSize: [size, size], iconAnchor: [size / 2, size / 2], popupAnchor: [0, -size / 2],
        });
        const marker = L.marker([p.lat, p.lng], { icon, zIndexOffset: p.fiber ? 1000 : 0 }).bindPopup(popup(p));
        markers.set(p.id, marker);
        if (!groups.has(p.company)) groups.set(p.company, L.layerGroup().addTo(map));
        groups.get(p.company).addLayer(marker);
      }
      renderTable(data, map, visible, markers);
    }
    function renderLegend() {
      const counts = {};
      for (const p of data.permits) counts[p.company] = (counts[p.company] || 0) + 1;
      const companies = Object.keys(counts).sort((a, b) => meta(a).slot - meta(b).slot || a.localeCompare(b));
      $("#legend").innerHTML = companies.map((co) =>
        `<button type="button" class="legend-item ${state.off.has(co) ? "off" : ""}" data-company="${esc(co)}" aria-pressed="${!state.off.has(co)}">${dot(co)}<span>${esc(co)}</span><span class="tile-sub">${counts[co]}</span></button>`
      ).join("") || '<span class="empty">No telecom permits in this area yet.</span>';
      $("#legend").querySelectorAll(".legend-item").forEach((btn) => btn.addEventListener("click", () => {
        const co = btn.dataset.company;
        if (state.off.has(co)) state.off.delete(co); else state.off.add(co);
        renderLegend(); build();
      }));
    }
    $("#toggle-traffic").addEventListener("change", (ev) => { state.traffic = ev.target.checked; build(); });
    $("#toggle-done").addEventListener("change", (ev) => { state.done = ev.target.checked; build(); });
    renderLegend();
    build();
    function focus(id) {
      const m = markers.get(id);
      const p = data.permits.find((x) => x.id === id);
      if (!m && !(p && p.lat != null)) return;
      map.setView(m ? m.getLatLng() : [p.lat, p.lng], Math.max(map.getZoom(), 16));
      if (m) m.openPopup();
      $("#map").scrollIntoView({ behavior: "smooth", block: "center" });
    }
    return { map, focus };
  }

  // ---- permit table ------------------------------------------------------------
  function renderTable(data, map, visible, markers) {
    const rows = data.permits.filter(visible);
    $("#permits-heading").textContent = `Permits in area (${rows.length} shown of ${data.permits.length})`;
    const tbody = $("#permits tbody");
    if (!rows.length) {
      tbody.innerHTML = '<tr><td colspan="6" class="empty">Nothing to show with the current filters.</td></tr>';
      return;
    }
    tbody.innerHTML = rows.map((p) => {
      const isNew = daysSince(p.first_seen) <= data.new_window_days;
      return `<tr class="${p.phase}" data-id="${esc(p.id)}">` +
        `<td class="num">${fmtDate(p.created)}${isNew ? ' <span class="new">new</span>' : ""}</td>` +
        `<td><span class="co">${dot(p.company)}${esc(p.company)}</span>${p.fiber ? ' <span class="chip fiber">fiber</span>' : ""}${p.drop ? ' <span class="chip">drop</span>' : ""}</td>` +
        `<td>${esc(KIND_LABEL[p.kind] || p.kind)}</td><td>${esc(p.status || p.phase)}</td>` +
        `<td>${esc(p.address || "—")}</td><td class="scope">${esc(p.scope.slice(0, 140))}${p.scope.length > 140 ? "…" : ""}</td></tr>`;
    }).join("");
    tbody.querySelectorAll("tr[data-id]").forEach((tr) => tr.addEventListener("click", () => {
      const m = markers.get(tr.dataset.id);
      if (!m) return;
      map.setView(m.getLatLng(), Math.max(map.getZoom(), 16));
      m.openPopup();
      $("#map").scrollIntoView({ behavior: "smooth", block: "center" });
    }));
  }

  // ---- banner: what changed, and is the build still running ---------------------
  function renderBanner(data, focus) {
    const el = $("#banner");
    const alerts = data.alerts || [];
    let prev = null;
    const nowIso = new Date().toISOString();
    try { prev = localStorage.getItem("fibermap.lastVisit"); localStorage.setItem("fibermap.lastVisit", nowIso); } catch (e) { /* private window etc. */ }
    const unseen = (a) => !prev || a.date > prev;
    const parts = [];
    if (daysSince(data.generated_at) > 2) {
      parts.push(`<div class="alert warn">This page was last built ${relTime(data.generated_at)}. The nightly job may have stopped; check ~/logs/fiber-map.log on the server.</div>`);
    }
    const nUnseen = alerts.filter(unseen).length;
    const since = prev ? `${nUnseen} since your last visit ${relTime(prev)}` : "first visit on this browser";
    parts.push(`<div class="banner-head"><strong>Last ${data.new_window_days} days</strong><span class="muted">${alerts.length} item${alerts.length === 1 ? "" : "s"} · ${since}</span></div>`);
    if (!alerts.length) {
      parts.push(`<div class="alert">Nothing new: no company pulled its first permit here or city-wide, and no new right-of-way permit landed in the box.</div>`);
    } else {
      parts.push(`<ul class="alerts">` + alerts.map((a) =>
        `<li class="${a.kind} ${unseen(a) ? "unseen" : ""}" ${a.permit_id ? `data-id="${esc(a.permit_id)}"` : ""}>${dot(a.company)}<span class="when">${fmtDate(a.date)}</span><span>${esc(a.text)}</span></li>`
      ).join("") + `</ul>`);
    }
    el.innerHTML = parts.join("");
    el.querySelectorAll("li[data-id]").forEach((li) => li.addEventListener("click", () => focus(li.dataset.id)));
  }

  // ---- watchlist of unmatched holders --------------------------------------------
  function renderWatchlist(data) {
    const w = data.watchlist;
    const details = $("#watchlist");
    if (!w || !w.unmatched_holders || !w.unmatched_holders.length) { details.hidden = true; return; }
    $("#holders tbody").innerHTML = w.unmatched_holders.map((h) => {
      const isNew = daysSince(h.first_created) <= data.new_window_days;
      return `<tr><td>${esc(h.holder)}${isNew ? ' <span class="new">new</span>' : ""}</td><td class="num">${h.count}</td>` +
        `<td class="num">${h.telecomish || 0}</td><td class="num">${fmtDate(h.first_created)}</td></tr>`;
    }).join("");
  }

  // ---- news ---------------------------------------------------------------------
  function renderNews(data) {
    const ol = $("#news");
    if (!data.news.length) { ol.innerHTML = '<li class="empty">No headlines fetched.</li>'; return; }
    ol.innerHTML = data.news.slice(0, 80).map((n) => {
      const isNew = daysSince(n.first_seen) <= data.new_window_days;
      return `<li><a href="${esc(n.link)}" target="_blank" rel="noopener">${esc(n.title)}</a>` +
        `<div class="meta"><span class="chip">${esc(n.query)}</span><span>${esc(n.source || "")}</span><span>${relTime(n.published)}</span>${isNew ? '<span class="new">new</span>' : ""}</div></li>`;
    }).join("");
  }

  // ---- footer -------------------------------------------------------------------
  function renderFooter(data) {
    const src = data.source && data.source.url
      ? `Permits: <a href="${esc(data.source.url)}" target="_blank" rel="noopener">${esc(data.source.label)}</a>`
      : "Permits: no source configured";
    $("#footer").innerHTML = [
      `Generated ${esc(data.generated_at)}`,
      src,
      "News: Google News RSS",
      `Map tiles: &copy; <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener">OpenStreetMap</a> contributors${data.tiles && data.tiles.mode === "local" ? ", cached at build time" : ""}`,
      '<a href="https://github.com/phubbard/fiber-map" target="_blank" rel="noopener">fiber-map</a> · no third-party requests at runtime',
    ].join(" · ");
  }

  async function main() {
    // data.js (written by the build) works from disk; data.json needs a web server.
    let data = window.FIBERMAP_DATA || null;
    if (!data) {
      try {
        const r = await fetch("data.json", { cache: "no-store" });
        if (!r.ok) throw new Error("HTTP " + r.status);
        data = await r.json();
      } catch (err) {
        $("#subtitle").textContent = location.protocol === "file:"
          ? "Opened from disk but site/data.js is missing. Run: python3 -m fibermap build, then reload."
          : "No data yet. Run: python3 -m fibermap build";
        return;
      }
    }
    renderHeader(data);
    renderKpis(data);
    const mapApi = renderMap(data);
    renderBanner(data, mapApi.focus);
    renderWatchlist(data);
    renderNews(data);
    renderFooter(data);
  }
  main();
})();
