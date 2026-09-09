// Estratos — renderiza data/articles.json como um corte estratigráfico com índice de filtros.

const PAGE = 50;
const KIND_NAMES = {
  periodico: "periódico acadêmico",
  revista: "revista especializada",
  instituicao: "instituição de pesquisa",
  blog: "blog acadêmico",
  noticia: "notícia de ciência",
};

const $ = (id) => document.getElementById(id);
const el = {
  feed: $("feed"), lead: $("lead"), more: $("more"), search: $("search"), peer: $("peer"),
  period: $("period"), topic: $("topic"), kind: $("kind"), tag: $("tag"), source: $("source"),
  clear: $("clear"), activeCount: $("active-count"), editionDate: $("edition-date"),
  editionMeta: $("edition-meta"), theme: $("theme"), indexBox: $("index-box"),
};

// Estado dos filtros, espelhado na URL para que qualquer combinação seja compartilhável.
const state = { q: "", periodo: "", tema: "", tipo: "", assunto: "", fonte: "", pares: "" };
let articles = [];
let shown = PAGE;

const fmt = {
  day: new Intl.DateTimeFormat("pt-BR", { day: "numeric" }),
  month: new Intl.DateTimeFormat("pt-BR", { month: "short", year: "numeric" }),
  long: new Intl.DateTimeFormat("pt-BR", { day: "numeric", month: "long" }),
  edition: new Intl.DateTimeFormat("pt-BR", { weekday: "long", day: "numeric", month: "long", year: "numeric" }),
  updated: new Intl.DateTimeFormat("pt-BR", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" }),
};

const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
const normalize = (s) => s.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();
const localDate = (iso) => new Date(iso + "T12:00:00");
const cap = (s) => s.charAt(0).toUpperCase() + s.slice(1);
const domain = (url) => { try { return new URL(url).hostname.replace(/^www\./, ""); } catch { return ""; } };

function daysAgo(iso) {
  const today = new Date(); today.setHours(12, 0, 0, 0);
  return Math.round((today - localDate(iso)) / 86400000);
}
function relative(iso) {
  const d = daysAgo(iso);
  if (d === 0) return "hoje";
  if (d === 1) return "ontem";
  if (d < 7) return `há ${d} dias`;
  return "";
}

// Filtragem com facetas: `skip` ignora um filtro para calcular as contagens daquela faceta.
function matches(a, skip) {
  const s = (k) => (k === skip ? "" : state[k]);
  if (s("tema") && a.category !== s("tema")) return false;
  if (s("tipo") && a.kind !== s("tipo")) return false;
  if (s("assunto") && !(a.tags || []).includes(s("assunto"))) return false;
  if (s("fonte") && a.source !== s("fonte")) return false;
  if (s("pares") && !a.peer) return false;
  if (s("periodo") && daysAgo(a.date) >= Number(s("periodo"))) return false;
  if (s("q")) {
    const hay = normalize([a.title, a.title_pt, a.summary, a.summary_pt, a.source, a.authors, (a.tags || []).join(" ")].filter(Boolean).join(" "));
    if (!hay.includes(normalize(s("q")))) return false;
  }
  return true;
}
const filtered = (skip) => articles.filter((a) => matches(a, skip));
const countBy = (list, key) => list.reduce((m, a) => (m[key(a)] = (m[key(a)] || 0) + 1, m), {});

/* Renderização */

function meta(a) {
  return `<p class="meta"><span class="src">${esc(a.source)}</span><span>${KIND_NAMES[a.kind] || ""}</span>${a.peer ? '<span class="peer">revisado por pares</span>' : ""}${a.authors ? `<span class="authors">${esc(a.authors)}</span>` : ""}</p>`;
}
function tags(a) {
  if (!a.tags || !a.tags.length) return "";
  return `<p class="tags">${a.tags.map((t) => `<button data-tag="${esc(t)}">${esc(t)}</button>`).join("")}</p>`;
}
function entry(a) {
  const title = a.title_pt || a.title;
  const summary = a.summary_pt || a.summary;
  return `<li><article class="entry">
    <h3><a href="${esc(a.url)}" target="_blank" rel="noopener">${esc(title)}</a></h3>
    ${meta(a)}
    ${summary ? `<p class="summary">${esc(summary)}</p>` : ""}
    <div class="detail">
      ${a.title_pt && a.title_pt !== a.title ? `<p class="original">${esc(a.title)}</p>` : ""}
      <p><a href="${esc(a.url)}" target="_blank" rel="noopener">Ler na fonte</a> ${esc(domain(a.url))}</p>
    </div>
    ${tags(a)}
  </article></li>`;
}

function renderLead(list) {
  const top = list.slice(0, 40);
  const pick = top.find((a) => a.summary.length > 120 && ["arqueologia", "manuscritos"].includes(a.category))
    || top.find((a) => a.summary.length > 120);
  const anyFilter = Object.values(state).some(Boolean);
  if (!pick || anyFilter) { el.lead.hidden = true; return null; }
  const rel = relative(pick.date);
  el.lead.hidden = false;
  el.lead.innerHTML = `
    <p class="kicker"><b>Em destaque</b>, ${fmt.long.format(localDate(pick.date))}${rel ? `, ${rel}` : ""}</p>
    <h2><a href="${esc(pick.url)}" target="_blank" rel="noopener">${esc(pick.title_pt || pick.title)}</a></h2>
    <p class="summary">${esc(pick.summary_pt || pick.summary)}</p>
    ${pick.title_pt && pick.title_pt !== pick.title ? `<p class="original">${esc(pick.title)}</p>` : ""}
    ${meta(pick)}
    ${tags(pick)}`;
  return pick;
}

function renderFeed() {
  const list = filtered();
  const lead = renderLead(list);
  const rest = lead ? list.filter((a) => a !== lead) : list;
  const visible = rest.slice(0, shown);
  el.more.hidden = shown >= rest.length;
  el.more.textContent = `Mostrar mais ${Math.min(PAGE, rest.length - shown)} artigos`;

  if (!list.length) {
    el.feed.innerHTML = `<p class="empty">Nenhum artigo corresponde a esses filtros. <button data-clear>Limpar filtros</button></p>`;
    return;
  }
  const days = new Map();
  for (const a of visible) {
    if (!days.has(a.date)) days.set(a.date, []);
    days.get(a.date).push(a);
  }
  el.feed.innerHTML = [...days].map(([date, items]) => {
    const d = localDate(date);
    const rel = relative(date);
    return `<section class="day">
      <h2 class="day-label">${fmt.day.format(d)}<small>${fmt.month.format(d).replace(". de ", " ")}${rel ? `<br>${rel}` : ""}</small></h2>
      <ol>${items.map(entry).join("")}</ol>
    </section>`;
  }).join("");
}

function renderIndex() {
  // Cada faceta conta sobre a lista filtrada por todas as outras facetas.
  const setRows = (container, key, listKey) => {
    const counts = countBy(filtered(key), listKey);
    const total = filtered(key).length;
    for (const b of container.querySelectorAll("button")) {
      const v = b.dataset.v;
      const n = v ? counts[v] || 0 : total;
      b.querySelector(".n").textContent = n;
      b.disabled = !!v && n === 0;
      b.setAttribute("aria-pressed", state[key] === v ? "true" : "false");
    }
  };
  setRows(el.topic, "tema", (a) => a.category);
  setRows(el.kind, "tipo", (a) => a.kind);

  for (const b of el.period.querySelectorAll("button")) {
    b.setAttribute("aria-pressed", state.periodo === b.dataset.v ? "true" : "false");
  }

  const tagCounts = countBy(filtered("assunto").flatMap((a) => a.tags || []), (t) => t);
  const tagList = Object.entries(tagCounts).sort((x, y) => y[1] - x[1]);
  if (state.assunto && !tagCounts[state.assunto]) tagList.push([state.assunto, 0]);
  el.tag.innerHTML = tagList.map(([t, n]) =>
    `<button data-v="${esc(t)}" aria-pressed="${state.assunto === t}">${esc(t)}<span class="n">${n}</span></button>`
  ).join("") || `<span class="n">Nenhum assunto com esses filtros.</span>`;

  const srcCounts = countBy(filtered("fonte"), (a) => a.source);
  const sources = Object.keys(srcCounts).sort((x, y) => x.localeCompare(y, "pt"));
  if (state.fonte && !srcCounts[state.fonte]) sources.push(state.fonte);
  el.source.innerHTML = `<option value="">Todas as fontes (${sources.length})</option>` +
    sources.map((s) => `<option value="${esc(s)}"${state.fonte === s ? " selected" : ""}>${esc(s)} (${srcCounts[s] || 0})</option>`).join("");

  el.peer.checked = !!state.pares;
  if (el.search.value !== state.q) el.search.value = state.q;

  const active = Object.values(state).filter(Boolean).length;
  el.clear.hidden = !active;
  el.activeCount.textContent = active ? `${active} ${active === 1 ? "filtro ativo" : "filtros ativos"}` : "";
}

function render() {
  renderIndex();
  renderFeed();
  const params = new URLSearchParams();
  for (const [k, v] of Object.entries(state)) if (v) params.set(k, v);
  const qs = params.toString();
  history.replaceState(null, "", qs ? `?${qs}` : location.pathname);
}

function set(key, value) {
  state[key] = state[key] === value && key !== "q" ? "" : value;
  shown = PAGE;
  render();
  if (key !== "q" && narrow.matches) el.indexBox.open = false;
}

/* Eventos */

const pressHandler = (key) => (e) => {
  const b = e.target.closest("button[data-v]");
  if (b) set(key, b.dataset.v);
};
el.topic.addEventListener("click", pressHandler("tema"));
el.kind.addEventListener("click", pressHandler("tipo"));
el.period.addEventListener("click", pressHandler("periodo"));
el.tag.addEventListener("click", pressHandler("assunto"));
el.source.addEventListener("change", () => { state.fonte = el.source.value; shown = PAGE; render(); });
el.peer.addEventListener("change", () => { state.pares = el.peer.checked ? "1" : ""; shown = PAGE; render(); });

let searchTimer;
el.search.addEventListener("input", () => {
  clearTimeout(searchTimer);
  searchTimer = setTimeout(() => { state.q = el.search.value.trim(); shown = PAGE; render(); }, 150);
});

function clearAll() {
  for (const k of Object.keys(state)) state[k] = "";
  shown = PAGE;
  render();
}
el.clear.addEventListener("click", clearAll);
el.more.addEventListener("click", () => { shown += PAGE; renderFeed(); });

el.feed.addEventListener("click", (e) => {
  if (e.target.closest("[data-clear]")) return clearAll();
  const tag = e.target.closest("button[data-tag]");
  if (tag) { set("assunto", tag.dataset.tag); window.scrollTo({ top: 0 }); return; }
  const summary = e.target.closest(".summary");
  if (summary) summary.closest(".entry").classList.toggle("open");
});
el.lead.addEventListener("click", (e) => {
  const tag = e.target.closest("button[data-tag]");
  if (tag) set("assunto", tag.dataset.tag);
});

/* Tema claro e escuro */

function isDark() {
  const t = document.documentElement.dataset.theme;
  return t ? t === "dark" : matchMedia("(prefers-color-scheme: dark)").matches;
}
function setTheme(mode) {
  if (mode) document.documentElement.dataset.theme = mode;
  else delete document.documentElement.dataset.theme;
  try { mode ? localStorage.setItem("theme", mode) : localStorage.removeItem("theme"); } catch (e) {}
  el.theme.textContent = isDark() ? "Tema claro" : "Tema escuro";
}
el.theme.addEventListener("click", () => setTheme(isDark() ? "light" : "dark"));
setTheme(document.documentElement.dataset.theme || "");

/* Carga */

const narrow = matchMedia("(max-width: 900px)");
el.indexBox.open = !narrow.matches;
narrow.addEventListener("change", (e) => { el.indexBox.open = !e.matches; });
el.editionDate.textContent = cap(fmt.edition.format(new Date()));

const params = new URLSearchParams(location.search);
for (const k of Object.keys(state)) state[k] = params.get(k) || "";

fetch("data/articles.json")
  .then((r) => r.json())
  .then((data) => {
    articles = data.articles;
    const peers = articles.filter((a) => a.peer).length;
    el.editionMeta.textContent = `${articles.length} artigos de ${data.sources.length} fontes, ${peers} revisados por pares. Atualizado em ${fmt.updated.format(new Date(data.updated))}.`;
    render();
  })
  .catch(() => {
    el.editionMeta.textContent = "Não foi possível carregar o feed. Rode “python fetch.py” e sirva a pasta por HTTP.";
  });
