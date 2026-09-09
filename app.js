// Estratos — renderiza data/articles.json como um feed agrupado por dia.

const TOPIC_NAMES = {
  arqueologia: "Arqueologia",
  manuscritos: "Manuscritos",
  historia: "História",
  teologia: "Teologia",
  ciencia: "Ciência",
};
const PAGE = 50;

const $ = (id) => document.getElementById(id);
const $feed = $("feed"), $lead = $("lead"), $status = $("status"), $more = $("more");
const $search = $("search"), $peer = $("peer"), $topics = $("topics"), $theme = $("theme");

let articles = [];
let shown = PAGE;
let topic = decodeURIComponent(location.hash.slice(1)) || "";

const dayFmt = new Intl.DateTimeFormat("pt-BR", { day: "numeric" });
const monthFmt = new Intl.DateTimeFormat("pt-BR", { month: "short", year: "numeric" });
const longFmt = new Intl.DateTimeFormat("pt-BR", { day: "numeric", month: "long" });
const updatedFmt = new Intl.DateTimeFormat("pt-BR", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" });

const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
const normalize = (s) => s.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();
const localDate = (iso) => new Date(iso + "T12:00:00");

function relativeDay(iso) {
  const today = new Date(); today.setHours(12, 0, 0, 0);
  const diff = Math.round((today - localDate(iso)) / 86400000);
  if (diff === 0) return "hoje";
  if (diff === 1) return "ontem";
  if (diff < 7) return `há ${diff} dias`;
  return "";
}

function filtered() {
  const q = normalize($search.value.trim());
  return articles.filter((a) =>
    (!topic || a.category === topic) &&
    (!$peer.checked || a.peer) &&
    (!q || normalize(`${a.title} ${a.summary} ${a.source} ${a.authors || ""}`).includes(q))
  );
}

function meta(a) {
  return `<p class="meta">
    <i class="dot ${esc(a.category)}" title="${TOPIC_NAMES[a.category] || ""}"></i><span class="src">${esc(a.source)}</span>${a.peer ? '<span class="peer">revisado por pares</span>' : ""}${a.authors ? `<span class="authors">${esc(a.authors)}</span>` : ""}
  </p>`;
}

function entry(a) {
  return `<li><article class="entry">
    <h3><a href="${esc(a.url)}" target="_blank" rel="noopener">${esc(a.title)}</a></h3>
    ${meta(a)}
    ${a.summary ? `<p class="summary" title="Clique para ler o resumo completo">${esc(a.summary)}</p>` : ""}
  </article></li>`;
}

function renderLead(list) {
  // Destaque: a descoberta mais recente com resumo, preferindo arqueologia e manuscritos.
  const top = list.slice(0, 40);
  const pick = top.find((a) => a.summary.length > 120 && ["arqueologia", "manuscritos"].includes(a.category))
    || top.find((a) => a.summary.length > 120);
  if (!pick || $search.value.trim()) { $lead.hidden = true; return null; }
  const d = localDate(pick.date);
  const rel = relativeDay(pick.date);
  $lead.hidden = false;
  $lead.innerHTML = `
    <p class="kicker"><b>Em destaque</b>, ${longFmt.format(d)}${rel ? `, ${rel}` : ""}</p>
    <h2><a href="${esc(pick.url)}" target="_blank" rel="noopener">${esc(pick.title)}</a></h2>
    <p class="summary">${esc(pick.summary)}</p>
    ${meta(pick)}`;
  return pick;
}

function render() {
  const list = filtered();
  const lead = renderLead(list);
  const rest = lead ? list.filter((a) => a !== lead) : list;
  const visible = rest.slice(0, shown);
  $more.hidden = shown >= rest.length;

  if (!list.length) {
    $feed.innerHTML = `<p class="empty">Nenhum artigo corresponde a essa busca. Tente outra palavra ou volte para “Tudo”.</p>`;
    return;
  }

  const days = new Map();
  for (const a of visible) {
    if (!days.has(a.date)) days.set(a.date, []);
    days.get(a.date).push(a);
  }

  $feed.innerHTML = [...days].map(([date, items]) => {
    const d = localDate(date);
    const rel = relativeDay(date);
    return `<section class="day">
      <h2 class="day-label">${dayFmt.format(d)}<small>${monthFmt.format(d).replace(". de ", " ")}${rel ? `<br>${rel}` : ""}</small></h2>
      <ol>${items.map(entry).join("")}</ol>
    </section>`;
  }).join("");
}

function updateCounts() {
  const base = articles.filter((a) => !$peer.checked || a.peer);
  for (const el of $topics.querySelectorAll("[data-count]")) {
    const t = el.dataset.count;
    el.textContent = t ? base.filter((a) => a.category === t).length : base.length;
  }
}

function setTopic(t) {
  topic = t;
  shown = PAGE;
  for (const b of $topics.querySelectorAll("button")) {
    if (b.dataset.topic === t) b.setAttribute("aria-current", "true");
    else b.removeAttribute("aria-current");
  }
  history.replaceState(null, "", t ? `#${t}` : location.pathname);
  render();
}

function setTheme(mode) {
  if (mode) document.documentElement.dataset.theme = mode;
  else delete document.documentElement.dataset.theme;
  try { mode ? localStorage.setItem("theme", mode) : localStorage.removeItem("theme"); } catch (e) {}
  const dark = mode ? mode === "dark" : matchMedia("(prefers-color-scheme: dark)").matches;
  $theme.textContent = dark ? "Tema claro" : "Tema escuro";
}

$topics.addEventListener("click", (e) => {
  const b = e.target.closest("button[data-topic]");
  if (b) setTopic(b.dataset.topic);
});
$search.addEventListener("input", () => { shown = PAGE; render(); });
$peer.addEventListener("change", () => { shown = PAGE; updateCounts(); render(); });
$more.addEventListener("click", () => { shown += PAGE; render(); });
$feed.addEventListener("click", (e) => {
  const s = e.target.closest(".summary");
  if (s) s.classList.toggle("open");
});
$theme.addEventListener("click", () => {
  const dark = document.documentElement.dataset.theme
    ? document.documentElement.dataset.theme === "dark"
    : matchMedia("(prefers-color-scheme: dark)").matches;
  setTheme(dark ? "light" : "dark");
});
setTheme(document.documentElement.dataset.theme || "");

fetch("data/articles.json")
  .then((r) => r.json())
  .then((data) => {
    articles = data.articles;
    const peers = articles.filter((a) => a.peer).length;
    $status.textContent = `${articles.length} artigos de ${data.sources.length} fontes, ${peers} revisados por pares. Atualizado em ${updatedFmt.format(new Date(data.updated))}.`;
    $("sources").textContent = data.sources.join("; ");
    updateCounts();
    setTopic(TOPIC_NAMES[topic] ? topic : "");
  })
  .catch(() => {
    $status.textContent = "Não foi possível carregar o feed. Rode “python fetch.py” para gerar os dados e sirva a pasta por HTTP.";
  });
