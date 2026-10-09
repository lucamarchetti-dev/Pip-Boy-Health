(() => {
  "use strict";
  const B = document.body, ROOT = document.documentElement;
  const TH = { cpu: +B.dataset.cpuTh, ram: +B.dataset.ramTh, disk: +B.dataset.diskTh };
  const NAMES = { cpu: "CPU", ram: "RAM", disk: "disco" };
  const SERIES = [["cpu", "cpu_percent"], ["ram", "ram_percent"], ["disk", "disk_percent"]];
  const INTERVAL = 15000;
  const REDUCE = matchMedia("(prefers-reduced-motion: reduce)").matches;
  const $ = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => [...r.querySelectorAll(s)];

  const st = {
    rows: [], total: 0, paused: false, timer: null, first: true,
    known: new Set($$("#rows tr[data-id]").map(tr => tr.dataset.id)),
    filter: "all", hidden: new Set(), geo: null,
  };

  const fmt = v => v.toFixed(1).replace(".", ",");
  const fmtTime = iso => new Date(iso).toLocaleTimeString("it-IT");
  const fmtDT = iso => new Date(iso).toLocaleString("it-IT", { day: "2-digit", month: "2-digit", year: "numeric", hour: "2-digit", minute: "2-digit", second: "2-digit" });
  const esc = s => String(s).replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const level = (v, th) => (v > th ? "crit" : v > th - 10 ? "near" : "ok");

  /* ---------- numeri animati ---------- */
  function countTo(el, to, dec = 1, suffix = "") {
    const from = parseFloat(el.dataset.v || "0");
    el.dataset.v = to;
    const write = v => { el.textContent = (dec ? v.toFixed(dec).replace(".", ",") : Math.round(v)) + suffix; };
    if (REDUCE) return write(to);
    const t0 = performance.now(), dur = 1000;
    const step = now => {
      const p = Math.min(1, (now - t0) / dur), e = 1 - Math.pow(1 - p, 3);
      write(from + (to - from) * e);
      if (p < 1) requestAnimationFrame(step);
    };
    requestAnimationFrame(step);
  }

  /* ---------- anelli ---------- */
  const C = 326.73;
  $$(".gauge").forEach(g => {
    const key = g.dataset.key, svg = $(".ring", g);
    const tick = document.createElementNS("http://www.w3.org/2000/svg", "line");
    tick.setAttribute("class", "tick");
    Object.entries({ x1: 70, y1: 5, x2: 70, y2: 19, transform: `rotate(${TH[key] * 3.6} 70 70)` }).forEach(([k, v]) => tick.setAttribute(k, v));
    svg.appendChild(tick);
  });

  function renderGauges(rows) {
    const cur = rows[0], prev = rows[1];
    $$(".gauge").forEach(g => {
      const key = g.dataset.key, f = key + "_percent";
      if (!cur) return;
      const v = cur[f];
      g.classList.remove("is-ok", "is-near", "is-crit");
      g.classList.add("is-" + level(v, TH[key]));
      $(".fg", g).style.strokeDashoffset = C * (1 - Math.min(100, v) / 100);
      countTo($('[data-role="val"]', g), v);
      const d = $('[data-role="delta"]', g);
      if (!prev) d.textContent = "Prima rilevazione";
      else {
        const diff = v - prev[f];
        d.textContent = Math.abs(diff) < 0.05 ? "Stabile rispetto alla precedente"
          : (diff > 0 ? "In aumento di " : "In calo di ") + fmt(Math.abs(diff)) + " punti";
      }
    });
  }

  /* ---------- tracciato ECG: unico gesto "decorativo", ma cambia con lo stato ---------- */
  function ecgPath(crit) {
    const gap = crit ? 75 : 150, n = 600 / gap, mid = 30;
    let d = `M0 ${mid}`;
    for (let i = 0; i < n; i++) {
      const amp = crit ? 16 + ((i * 7) % 5) * 3 : 22;
      d += ` h${gap - 54} q6 -7 12 0 h6 l4 6 l6 ${-(amp + 6)} l6 ${amp + 14} l4 -14 q8 -10 16 0`;
    }
    return d;
  }
  let ecgMode = null;
  function renderHero(rows) {
    const cur = rows[0], hero = $(".hero");
    const bad = cur ? SERIES.filter(([k]) => cur[k + "_critical"]).map(([k]) => NAMES[k]) : [];
    const crit = bad.length > 0;
    hero.dataset.s = !cur ? "none" : crit ? "crit" : "ok";
    $("#headline").textContent = !cur ? "Nessuna rilevazione ancora."
      : crit ? `Serve attenzione: ${bad.join(" e ")} ${bad.length > 1 ? "sono" : "è"} oltre soglia.`
      : "Tutto regolare.";
    $("#sub").textContent = cur ? `Ultima rilevazione alle ${fmtTime(cur.created_at)} su ${cur.hostname}.`
      : "Premi «Rileva ora» per salvare la prima misura.";
    if (ecgMode !== crit) {
      ecgMode = crit;
      const d = ecgPath(crit);
      $("#ecg-a").setAttribute("d", d); $("#ecg-b").setAttribute("d", d);
      $("#ecg-g").style.setProperty("--ecg-t", crit ? "3.2s" : "6.5s");
    }
  }

  /* ---------- cifre di sintesi ---------- */
  function renderFigures(rows) {
    const avg = f => rows.length ? rows.reduce((s, r) => s + r[f], 0) / rows.length : 0;
    const nCrit = rows.filter(r => r.critical).length;
    countTo($("#f-total"), st.total, 0);
    const fc = $("#f-crit"); countTo(fc, nCrit, 0); fc.classList.toggle("bad", nCrit > 0);
    countTo($("#f-cpu"), avg("cpu_percent"), 1, "%");
    countTo($("#f-disk"), avg("disk_percent"), 1, "%");
  }

  /* ---------- grafico ---------- */
  let W = 800;
  const H = 260, L = 4, R = 8, T = 14, Bt = 26;
  function renderChart(rows) {
    const svg = $("#chart"), plot = $("#plot");
    // il viewBox segue la larghezza reale: testo e tratti non vengono mai deformati
    W = Math.max(320, Math.round(svg.getBoundingClientRect().width) || 800);
    svg.setAttribute("viewBox", `0 0 ${W} ${H}`);
    const pts = rows.slice().reverse(), n = pts.length;
    if (n < 2) {
      plot.innerHTML = `<text x="${W / 2}" y="${H / 2}" text-anchor="middle" fill="currentColor" opacity=".5" font-size="15">Servono almeno 2 rilevazioni per il grafico</text>`;
      st.geo = null; return;
    }
    const x = i => L + (W - L - R) * i / (n - 1);
    const y = v => T + (H - T - Bt) * (1 - v / 100);
    let g = "";
    for (const t of [0, 25, 50, 75, 100])
      g += `<line class="grid" x1="${L}" x2="${W - R}" y1="${y(t)}" y2="${y(t)}"/><text x="${L + 2}" y="${y(t) - 4}" font-size="11" fill="currentColor" opacity=".45">${t}%</text>`;
    g += `<line class="th" x1="${L}" x2="${W - R}" y1="${y(TH.disk)}" y2="${y(TH.disk)}"/>`;
    g += `<text x="${W - R - 4}" y="${y(TH.disk) - 5}" text-anchor="end" font-size="11" fill="var(--crit)">soglia disco ${TH.disk}%</text>`;
    for (const [k, f] of SERIES) {
      if (st.hidden.has(k)) continue;
      const d = pts.map((p, i) => `${i ? "L" : "M"}${x(i).toFixed(1)} ${y(p[f]).toFixed(1)}`).join("");
      g += `<path class="area s-${k}" d="${d} L${x(n - 1)} ${y(0)} L${x(0)} ${y(0)}Z"/>`;
      g += `<path class="line s-${k}" pathLength="1" d="${d}"/>`;
    }
    g += `<text x="${L}" y="${H - 6}" font-size="11" fill="currentColor" opacity=".55">${fmtTime(pts[0].created_at)}</text>`;
    g += `<text x="${W - R}" y="${H - 6}" text-anchor="end" font-size="11" fill="currentColor" opacity=".55">${fmtTime(pts[n - 1].created_at)}</text>`;
    plot.innerHTML = g;
    if (st.first && !REDUCE) svg.classList.add("draw"); else svg.classList.remove("draw");
    st.geo = { pts, n, x };
  }

  const wrap = $("#chart-wrap"), tip = $("#tip"), cursor = $("#cursor");
  wrap.addEventListener("mousemove", e => {
    if (!st.geo) return;
    const { pts, n, x } = st.geo, r = $("#chart").getBoundingClientRect();
    const px = (e.clientX - r.left) / r.width * W;
    const i = Math.max(0, Math.min(n - 1, Math.round((px - L) / (W - L - R) * (n - 1))));
    const p = pts[i], xs = x(i);
    cursor.setAttribute("x1", xs); cursor.setAttribute("x2", xs);
    wrap.classList.add("hover");
    const wr = wrap.getBoundingClientRect();
    const left = Math.max(80, Math.min(wr.width - 80, r.left - wr.left + xs / W * r.width));
    tip.style.left = left + "px"; tip.hidden = false;
    tip.innerHTML = `<b>${esc(fmtTime(p.created_at))}</b>` + SERIES.filter(([k]) => !st.hidden.has(k))
      .map(([k, f]) => `<span style="--sc:var(--c-${k})"><i>${k === "disk" ? "Disco" : k.toUpperCase()}</i>${fmt(p[f])}%</span>`).join("");
  });
  wrap.addEventListener("mouseleave", () => { wrap.classList.remove("hover"); tip.hidden = true; });

  $$(".lg").forEach(b => b.addEventListener("click", () => {
    const k = b.dataset.s, off = !st.hidden.has(k);
    off ? st.hidden.add(k) : st.hidden.delete(k);
    b.setAttribute("aria-pressed", String(!off));
    renderChart(st.rows);
  }));

  /* ---------- tabella ---------- */
  const cell = (m, k) => {
    const v = m[k + "_percent"];
    return `<td${m[k + "_critical"] ? ' class="crit"' : ""}><span class="v">${fmt(v)}%</span><span class="bar"><i style="width:${Math.min(100, v)}%"></i></span></td>`;
  };
  function renderTable(rows) {
    const list = st.filter === "crit" ? rows.filter(r => r.critical) : rows;
    $("#rows").innerHTML = list.length ? list.map(m => {
      const fresh = !st.first && !st.known.has(String(m.id));
      return `<tr data-id="${m.id}" class="${m.critical ? "row-crit" : ""}${fresh ? " is-new" : ""}">
        <td>${fmtDT(m.created_at)}${m.simulated ? ' <span class="tag">simulata</span>' : ""}</td>
        <td>${esc(m.hostname)}</td>${cell(m, "cpu")}${cell(m, "ram")}${cell(m, "disk")}
        <td>${m.log_tail ? `<details><summary>Apri</summary><pre>${esc(m.log_tail)}</pre></details>` : "–"}</td></tr>`;
    }).join("") : `<tr><td colspan="6" class="empty">${st.filter === "crit" ? "Nessuna rilevazione critica tra le ultime: ottimo segno." : "Nessuna rilevazione. Premi «Rileva ora»."}</td></tr>`;
  }
  $$(".chip").forEach(c => c.addEventListener("click", () => {
    st.filter = c.dataset.filter;
    $$(".chip").forEach(o => o.setAttribute("aria-pressed", String(o === c)));
    renderTable(st.rows);
  }));

  /* ---------- notifiche ---------- */
  function toast(msg, kind = "ok") {
    const t = document.createElement("div");
    t.className = "toast " + (kind === "ok" ? "" : kind);
    t.textContent = msg;
    $("#toasts").appendChild(t);
    setTimeout(() => { t.classList.add("out"); setTimeout(() => t.remove(), 350); }, 5000);
  }

  /* ---------- aggiornamento ---------- */
  function setPill(s) {
    const p = $("#pill"); p.dataset.s = s;
    $("b", p).textContent = { live: "In diretta", paused: "In pausa", offline: "Non raggiungibile" }[s];
  }
  function restartTick() {
    const t = $("#tick");
    t.style.animation = "none"; void t.offsetWidth;
    if (!st.paused && !REDUCE) t.style.animation = `tick ${INTERVAL}ms linear forwards`;
    else t.style.width = "0";
  }
  function schedule() {
    clearTimeout(st.timer);
    restartTick();
    if (!st.paused) st.timer = setTimeout(refresh, INTERVAL);
  }

  function apply(data) {
    const rows = data.results;
    const newest = rows[0];
    if (!st.first && newest && !st.known.has(String(newest.id)) && newest.critical)
      toast(`Nuova rilevazione critica: ${SERIES.filter(([k]) => newest[k + "_critical"]).map(([k]) => NAMES[k]).join(", ")}.`, "crit");
    st.rows = rows; st.total = data.total;
    renderHero(rows); renderGauges(rows); renderFigures(rows); renderChart(rows); renderTable(rows);
    rows.forEach(r => st.known.add(String(r.id)));
    st.first = false;
  }

  async function refresh() {
    try {
      const res = await fetch(B.dataset.api, { cache: "no-store", headers: { "X-Requested-With": "XMLHttpRequest" } });
      if (!res.ok) throw new Error(res.status);
      apply(await res.json());
      setPill(st.paused ? "paused" : "live");
    } catch (e) {
      setPill("offline");
    }
    schedule();
  }

  /* ---------- azioni ---------- */
  $("#collect-form").addEventListener("submit", async e => {
    e.preventDefault();
    const form = e.currentTarget, btn = e.submitter, all = $$("button", form);
    const fd = new FormData(form); if (btn) fd.set("mode", btn.value);
    all.forEach(b => (b.disabled = true)); btn && btn.classList.add("loading");
    try {
      const res = await fetch(B.dataset.collect, { method: "POST", body: fd, headers: { "X-Requested-With": "XMLHttpRequest" } });
      if (!res.ok) throw new Error(res.status);
      const j = await res.json();
      j.critical ? toast(`Rilevazione salvata, ma ci sono valori critici (disco al ${fmt(j.disk_percent)}%).`, "crit")
                 : toast("Rilevazione salvata.");
      await refresh();
    } catch (err) {
      const code = /^\d+$/.test(err.message) ? `errore del server (${err.message}): guarda il terminale dove gira runserver` : "server non raggiungibile: controlla che runserver sia attivo";
      toast(`Impossibile salvare la rilevazione: ${code}.`, "crit");
    } finally {
      all.forEach(b => (b.disabled = false)); btn && btn.classList.remove("loading");
    }
  });

  $("#pause").addEventListener("click", e => {
    st.paused = !st.paused;
    e.currentTarget.classList.toggle("on", st.paused);
    e.currentTarget.setAttribute("aria-label", st.paused ? "Riprendi gli aggiornamenti" : "Metti in pausa gli aggiornamenti");
    setPill(st.paused ? "paused" : "live");
    st.paused ? (clearTimeout(st.timer), restartTick()) : refresh();
  });

  $("#theme").addEventListener("click", () => {
    const t = ROOT.dataset.theme === "dark" ? "light" : "dark";
    ROOT.dataset.theme = t;
    try { localStorage.setItem("hm-theme", t); } catch (e) { /* ignora */ }
  });

  let rz; window.addEventListener("resize", () => { clearTimeout(rz); rz = setTimeout(() => renderChart(st.rows), 150); });

  document.addEventListener("visibilitychange", () => { if (!document.hidden && !st.paused) refresh(); });

  refresh();
})();
