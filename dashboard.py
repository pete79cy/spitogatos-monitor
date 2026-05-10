"""Generate the Spitogatos dashboard HTML from a list of apartments.

Public API: render_dashboard(apartments, web_dir) → writes index.html + YYYY-MM-DD.html.

Each apartment dict needs the standard keys (id, title, price, location, size,
description, floor, bedrooms, bathrooms, image, link) plus an optional
`is_new` boolean.
"""
import json
import re
from datetime import datetime
from pathlib import Path

# ────────────────────────────────────────────────────────────────────────────
# Numeric extraction helpers
# ────────────────────────────────────────────────────────────────────────────


def _price_num(price: str) -> int:
    if not price:
        return 0
    digits = re.sub(r"[^\d]", "", price.split("/")[0])
    return int(digits) if digits else 0


def _sqm_num(s: str) -> int:
    if not s:
        return 0
    m = re.search(r"(\d+)\s*(?:τ\.?μ\.?|m²)", s)
    return int(m.group(1)) if m else 0


def _short_neighborhood(loc: str) -> str:
    """Trim the trailing '(Ηράκλειο Κρήτης)' so the neighborhood reads cleanly."""
    if not loc:
        return ""
    return re.sub(r"\s*\([^)]+\)\s*$", "", loc).strip()


def _enrich(apt: dict) -> dict:
    p = _price_num(apt.get("price", ""))
    s = _sqm_num(apt.get("size", "") or apt.get("title", ""))
    return {
        "id": apt.get("id", ""),
        "title": apt.get("title", "") or "",
        "price": apt.get("price", "") or "",
        "price_num": p,
        "sqm": s,
        "ppsqm": round(p / s, 1) if (p and s) else 0.0,
        "location": apt.get("location", "") or "",
        "neighborhood": _short_neighborhood(apt.get("location", "")),
        "bedrooms": apt.get("bedrooms", "") or "",
        "bathrooms": apt.get("bathrooms", "") or "",
        "floor": apt.get("floor", "") or "",
        "description": apt.get("description", "") or "",
        "image": apt.get("image", "") or "",
        "link": apt.get("link", "") or "",
        "is_new": bool(apt.get("is_new", False)),
        "is_missing": bool(apt.get("is_missing", False)),
        "found_at": apt.get("found_at", "") or "",
        "price_changed": bool(apt.get("price_changed", False)),
        "price_history": apt.get("price_history", []) or [],
    }


# ────────────────────────────────────────────────────────────────────────────
# Aggregate stats
# ────────────────────────────────────────────────────────────────────────────


def _summary(items):
    prices = [a["price_num"] for a in items if a["price_num"]]
    if not prices:
        return {"count": len(items), "min": 0, "max": 0, "avg": 0, "new_count": 0}
    return {
        "count": len(items),
        "min": min(prices),
        "max": max(prices),
        "avg": round(sum(prices) / len(prices)),
        "new_count": sum(1 for a in items if a["is_new"]),
    }


# (daily snapshot links removed — single rolling view replaces them)


# ────────────────────────────────────────────────────────────────────────────
# HTML template (placeholders __XXX__ replaced via str.replace)
# ────────────────────────────────────────────────────────────────────────────

TEMPLATE = r"""<!doctype html>
<html lang="el">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Spitogatos Ηράκλειο · __DATE__</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<style>
  :root { --bg:#0f172a; --panel:#1e293b; --text:#e2e8f0; --muted:#94a3b8;
          --accent:#38bdf8; --new:#22c55e; --border:#334155; }
  * { box-sizing: border-box; }
  body { margin:0; font-family: -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;
         background:var(--bg); color:var(--text); padding:16px; }
  h1 { margin:0 0 4px 0; font-size:20px; }
  .muted { color: var(--muted); font-size: 13px; }
  .row { display:flex; flex-wrap:wrap; gap:12px; margin:12px 0; }
  .panel { background:var(--panel); border-radius:8px; padding:16px;
           border:1px solid var(--border); }
  .stat { flex:1 1 140px; min-width: 140px; }
  .stat .v { font-size:22px; font-weight:600; }
  .stat .l { color:var(--muted); font-size:12px; }
  .filters { display:flex; flex-wrap:wrap; gap:8px; align-items:center; }
  .filters select, .filters input {
    background:var(--bg); color:var(--text); border:1px solid var(--border);
    border-radius:6px; padding:6px 8px; font-size:14px;
  }
  .filters label { font-size:13px; color:var(--muted); }
  table { width:100%; border-collapse:collapse; font-size:14px; }
  th, td { text-align:left; padding:8px 10px; border-bottom:1px solid var(--border);
           vertical-align: middle; }
  th { cursor:pointer; user-select:none; color:var(--muted); font-weight:500;
       white-space: nowrap; }
  th.sorted::after { content: " ▾"; color: var(--accent); }
  th.sorted.asc::after { content: " ▴"; }
  tbody tr:hover { background: rgba(255,255,255,0.03); }
  .thumb { width:60px; height:45px; object-fit:cover; border-radius:4px; }
  .badge { display:inline-block; padding:2px 6px; border-radius:4px;
           background:var(--new); color:#022c22; font-size:11px;
           font-weight:600; margin-left:4px; }
  .badge.drop { background:#f59e0b; color:#3a2406; }
  .badge.miss { background:#475569; color:#cbd5e1; }
  tr.missing td { opacity:.55; }
  .age { color: var(--muted); font-size:11px; }
  .price { font-weight:600; }
  .ppsqm { color: var(--accent); font-weight:500; }
  .star { background:none; border:0; cursor:pointer; font-size:18px; padding:2px 6px;
          color:#475569; transition:color .1s; }
  .star.on { color:#fbbf24; }
  .star:hover { color:#fbbf24; }
  a { color: var(--accent); text-decoration: none; }
  a:hover { text-decoration: underline; }
  .charts { display:grid; grid-template-columns: 1fr 1fr; gap:12px; }
  @media (max-width: 800px) {
    .charts { grid-template-columns: 1fr; }
    .thumb { width:48px; height:36px; }
    th, td { padding:6px; font-size:13px; }
    .hide-mobile { display:none; }
  }
  .new-card { display:inline-block; width:200px; margin-right:8px; vertical-align:top;
              background: var(--bg); border:1px solid var(--border); border-radius:6px;
              padding:8px; }
  .new-card img { width:100%; height:120px; object-fit:cover; border-radius:4px; }
  .new-card .t { font-weight:600; margin-top:4px; font-size:13px; }
  .new-card .p { color: var(--accent); font-size:13px; }
  .new-row { overflow-x:auto; white-space: nowrap; padding-bottom:4px; }
  .history a { margin-right: 8px; font-size: 12px; }
</style>
</head>
<body>

<h1>🏠 Spitogatos · Φοιτητικά Ηράκλειο
  <a href="/favorites" style="font-size:14px;margin-left:12px;color:var(--accent);text-decoration:none">⭐ Favorites Room →</a>
</h1>
<div class="muted">Τελευταία ενημέρωση: <strong>__DATE__</strong> · __NEW_COUNT__ νέες σήμερα</div>

<div class="row">
  <div class="panel stat"><div class="l">Σύνολο</div><div class="v">__COUNT__</div></div>
  <div class="panel stat"><div class="l">Ελάχιστη τιμή</div><div class="v">€__MIN__</div></div>
  <div class="panel stat"><div class="l">Μέγιστη τιμή</div><div class="v">€__MAX__</div></div>
  <div class="panel stat"><div class="l">Μέσος όρος</div><div class="v">€__AVG__</div></div>
  <div class="panel stat"><div class="l">Νέες σήμερα</div><div class="v" style="color:var(--new)">__NEW_COUNT__</div></div>
</div>

<div class="panel" id="newSection" style="display:__NEW_DISPLAY__">
  <h3 style="margin-top:0">🆕 Νέες αγγελίες σήμερα</h3>
  <div class="new-row" id="newRow"></div>
</div>

<div class="panel">
  <div class="filters">
    <label>Συνοικία:
      <select id="fNeigh"><option value="">— Όλες —</option></select>
    </label>
    <label>Τύπος:
      <select id="fType"><option value="">— Όλοι —</option></select>
    </label>
    <label>Τιμή έως:
      <input type="number" id="fMaxPrice" placeholder="€" style="width:80px">
    </label>
    <label>τμ από:
      <input type="number" id="fMinSqm" placeholder="τ.μ." style="width:70px">
    </label>
    <label><input type="checkbox" id="fOnlyNew"> Μόνο νέες</label>
    <label><input type="checkbox" id="fHideMissing"> Απόκρυψη όσων λείπουν</label>
    <span class="muted" id="resultCount"></span>
  </div>
</div>

<div class="panel">
  <table id="tbl">
    <thead>
      <tr>
        <th></th>
        <th></th>
        <th data-key="title">Τύπος</th>
        <th data-key="price_num" class="sorted asc">Τιμή</th>
        <th data-key="sqm">τ.μ.</th>
        <th data-key="ppsqm">€/τμ</th>
        <th data-key="neighborhood">Συνοικία</th>
        <th data-key="bedrooms" class="hide-mobile">Υ/Δ</th>
        <th data-key="floor" class="hide-mobile">Όροφος</th>
        <th></th>
      </tr>
    </thead>
    <tbody></tbody>
  </table>
</div>

<div class="row charts">
  <div class="panel"><h3 style="margin-top:0">Κατανομή τιμών</h3>
    <canvas id="cPrice" height="180"></canvas></div>
  <div class="panel"><h3 style="margin-top:0">Μέση τιμή ανά συνοικία</h3>
    <canvas id="cNeigh" height="180"></canvas></div>
</div>

<script>
const APARTMENTS = __APARTMENTS_JSON__;
const APT_BY_ID = Object.fromEntries(APARTMENTS.map(a => [a.id, a]));
let FAVS = new Set();

// Google Maps transit directions: neighborhood → Ιατρική Σχολή Βούτες
const TRANSIT_DEST = 'Ιατρική Σχολή Πανεπιστημίου Κρήτης, Βούτες, Ηράκλειο';
function transitUrl(neighborhood) {
  const origin = (neighborhood && neighborhood.trim()) ? `${neighborhood}, Ηράκλειο` : 'Ηράκλειο Κρήτης';
  return `https://www.google.com/maps/dir/?api=1&origin=${encodeURIComponent(origin)}&destination=${encodeURIComponent(TRANSIT_DEST)}&travelmode=transit`;
}

function relAge(iso) {
  if (!iso) return '';
  const then = new Date(iso); if (isNaN(then)) return '';
  const days = Math.floor((Date.now() - then.getTime()) / 86400000);
  if (days <= 0) return 'σήμερα';
  if (days === 1) return 'χθες';
  if (days < 7) return `πριν ${days} μέρες`;
  if (days < 30) return `πριν ${Math.floor(days/7)} εβδ.`;
  return `πριν ${Math.floor(days/30)} μήνες`;
}

async function loadFavs() {
  try {
    const r = await fetch('/api/favorites/ids');
    if (r.ok) FAVS = new Set(await r.json());
  } catch (e) { console.error(e); }
}

async function toggleFav(btn) {
  const id = btn.dataset.id;
  const isOn = FAVS.has(id);
  btn.disabled = true;
  try {
    if (isOn) {
      const r = await fetch('/api/favorites/' + id, { method: 'DELETE' });
      if (r.ok) FAVS.delete(id);
    } else {
      const apt = APT_BY_ID[id];
      const r = await fetch('/api/favorites/' + id, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(apt),
      });
      if (r.ok) FAVS.add(id);
    }
    btn.classList.toggle('on', FAVS.has(id));
    btn.textContent = FAVS.has(id) ? '★' : '☆';
  } finally {
    btn.disabled = false;
  }
}

// History links
document.getElementById('historyLinks').innerHTML =
  HISTORY.map(f => `<a href="${f}">${f.replace('.html','')}</a>`).join(' · ') ||
  '<span class="muted">καμία προηγούμενη μέρα</span>';

// Populate filter options
const neighborhoods = [...new Set(APARTMENTS.map(a => a.neighborhood).filter(Boolean))].sort();
const types = [...new Set(APARTMENTS.map(a => (a.title.split(',')[0] || '').trim()).filter(Boolean))].sort();
const fNeigh = document.getElementById('fNeigh');
const fType = document.getElementById('fType');
neighborhoods.forEach(n => { const o=document.createElement('option'); o.value=n; o.textContent=n; fNeigh.appendChild(o); });
types.forEach(t => { const o=document.createElement('option'); o.value=t; o.textContent=t; fType.appendChild(o); });

// New today highlights
const newOnes = APARTMENTS.filter(a => a.is_new);
const newRow = document.getElementById('newRow');
newOnes.forEach(a => {
  const card = document.createElement('a');
  card.href = a.link; card.target = '_blank'; card.className = 'new-card';
  card.innerHTML = `${a.image ? `<img src="${a.image}" alt="">` : ''}
    <div class="t">${a.title}</div>
    <div class="p">${a.price} · ${a.neighborhood}</div>`;
  newRow.appendChild(card);
});

// Sort + render table
let sortKey = 'price_num';
let sortAsc = true;

function getFiltered() {
  const fn = fNeigh.value, ft = fType.value;
  const mp = parseInt(document.getElementById('fMaxPrice').value || '999999');
  const ms = parseInt(document.getElementById('fMinSqm').value || '0');
  const onlyNew = document.getElementById('fOnlyNew').checked;
  const hideMissing = document.getElementById('fHideMissing').checked;
  return APARTMENTS.filter(a => {
    if (fn && a.neighborhood !== fn) return false;
    if (ft && !a.title.startsWith(ft)) return false;
    if (a.price_num > mp) return false;
    if (a.sqm < ms) return false;
    if (onlyNew && !a.is_new) return false;
    if (hideMissing && a.is_missing) return false;
    return true;
  });
}

function render() {
  const items = getFiltered().slice().sort((a,b) => {
    const va = a[sortKey], vb = b[sortKey];
    if (typeof va === 'number') return sortAsc ? va-vb : vb-va;
    return sortAsc ? String(va).localeCompare(String(vb)) : String(vb).localeCompare(String(va));
  });
  document.getElementById('resultCount').textContent = `(${items.length} αποτελέσματα)`;
  const tbody = document.querySelector('#tbl tbody');
  tbody.innerHTML = items.map(a => `
    <tr class="${a.is_missing ? 'missing' : ''}">
      <td><button class="star ${FAVS.has(a.id) ? 'on' : ''}" data-id="${a.id}" title="Αγαπημένο">${FAVS.has(a.id) ? '★' : '☆'}</button></td>
      <td>${a.image ? `<img src="${a.image}" class="thumb" alt="">` : ''}</td>
      <td>${a.title}${a.is_new ? '<span class="badge">🆕 ΝΕΟ</span>' : ''}${a.price_changed ? '<span class="badge drop">⬇️ ΑΛΛΑΓΗ ΤΙΜΗΣ</span>' : ''}${a.is_missing ? '<span class="badge miss">λείπει</span>' : ''}<div class="age">${relAge(a.found_at)}</div></td>
      <td class="price">${a.price}</td>
      <td>${a.sqm || '—'}</td>
      <td class="ppsqm">${a.ppsqm ? '€' + a.ppsqm : '—'}</td>
      <td>${a.neighborhood}</td>
      <td class="hide-mobile">${a.bedrooms}</td>
      <td class="hide-mobile">${a.floor}</td>
      <td><a href="${a.link}" target="_blank" title="Σπιτογάτος">↗</a> <a href="${transitUrl(a.neighborhood)}" target="_blank" title="Συγκοινωνία προς Ιατρική Σχολή Βούτες">🚌</a></td>
    </tr>`).join('');
  // Wire up star buttons
  tbody.querySelectorAll('button.star').forEach(btn => {
    btn.addEventListener('click', () => toggleFav(btn));
  });
  // Update sort indicator
  document.querySelectorAll('th[data-key]').forEach(th => {
    th.classList.toggle('sorted', th.dataset.key === sortKey);
    th.classList.toggle('asc', th.dataset.key === sortKey && sortAsc);
  });
}

document.querySelectorAll('th[data-key]').forEach(th => {
  th.addEventListener('click', () => {
    if (sortKey === th.dataset.key) sortAsc = !sortAsc;
    else { sortKey = th.dataset.key; sortAsc = true; }
    render();
  });
});

['fNeigh','fType','fMaxPrice','fMinSqm','fOnlyNew','fHideMissing'].forEach(id => {
  document.getElementById(id).addEventListener('input', render);
});

// Load favorites first, then render so stars reflect server state
loadFavs().then(render);

// Charts
const allPrices = APARTMENTS.map(a => a.price_num).filter(p => p > 0);
const buckets = [0, 250, 350, 450, 600, 800, 1000, 1500, 99999];
const labels = ['<€250','€250-349','€350-449','€450-599','€600-799','€800-999','€1000-1499','€1500+'];
const counts = new Array(labels.length).fill(0);
allPrices.forEach(p => {
  for (let i = 0; i < buckets.length - 1; i++) {
    if (p >= buckets[i] && p < buckets[i+1]) { counts[i]++; break; }
  }
});
new Chart(document.getElementById('cPrice'), {
  type: 'bar',
  data: { labels, datasets: [{ data: counts, backgroundColor: '#38bdf8' }] },
  options: { plugins:{legend:{display:false}}, scales:{y:{ticks:{color:'#94a3b8'}},x:{ticks:{color:'#94a3b8'}}} }
});

// Avg price per neighborhood
const byN = {};
APARTMENTS.forEach(a => {
  if (!a.neighborhood || !a.price_num) return;
  if (!byN[a.neighborhood]) byN[a.neighborhood] = [];
  byN[a.neighborhood].push(a.price_num);
});
const nLabels = Object.keys(byN).sort((a,b) =>
  (byN[a].reduce((x,y)=>x+y,0)/byN[a].length) - (byN[b].reduce((x,y)=>x+y,0)/byN[b].length));
const nValues = nLabels.map(n => Math.round(byN[n].reduce((x,y)=>x+y,0) / byN[n].length));
new Chart(document.getElementById('cNeigh'), {
  type: 'bar',
  data: { labels: nLabels, datasets: [{ data: nValues, backgroundColor:'#22c55e' }] },
  options: {
    indexAxis:'y',
    plugins:{legend:{display:false}, tooltip:{callbacks:{label:c=>'€'+c.parsed.x}}},
    scales:{x:{ticks:{color:'#94a3b8',callback:v=>'€'+v}},y:{ticks:{color:'#94a3b8'}}}
  }
});
</script>
</body>
</html>
"""


def render_dashboard(apartments_raw: list, web_dir: str) -> str:
    """Render the dashboard. Returns relative URL of the generated index."""
    web = Path(web_dir)
    web.mkdir(parents=True, exist_ok=True)

    enriched = [_enrich(a) for a in apartments_raw]
    summary = _summary(enriched)
    today = datetime.now().strftime("%Y-%m-%d")
    new_display = "block" if summary["new_count"] > 0 else "none"

    html = (
        TEMPLATE
        .replace("__DATE__", today)
        .replace("__COUNT__", str(summary["count"]))
        .replace("__MIN__", f"{summary['min']:,}".replace(",", "."))
        .replace("__MAX__", f"{summary['max']:,}".replace(",", "."))
        .replace("__AVG__", f"{summary['avg']:,}".replace(",", "."))
        .replace("__NEW_COUNT__", str(summary["new_count"]))
        .replace("__NEW_DISPLAY__", new_display)
        .replace("__APARTMENTS_JSON__", json.dumps(enriched, ensure_ascii=False))
    )

    (web / "index.html").write_text(html, encoding="utf-8")
    print(f"📄 Dashboard written: index.html ({summary['count']} listings, "
          f"{summary['new_count']} new)")
    return "/index.html"
