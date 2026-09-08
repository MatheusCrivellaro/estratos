// Estratos — renderiza data/articles.json como um feed agrupado por dia.

const TOPIC_NAMES = {
  arqueologia: "Arqueologia",
  manuscritos: "Manuscritos",
  historia: "História",
  teologia: "Teologia",
  ciencia: "Ciência",
};
const PAGE = 60;

const $feed = document.getElementById("feed");
const $status = document.getElementById("status");
const $more = document.getElementById("more");
const $search = document.getElementById("search");
const $peer = document.getElementById("peer");
const $topics = document.getElementById("topics");

let articles = [];
let shown = PAGE;
let topic = decodeURIComponent(location.hash.slice(1)) || "";

const dayFmt = new Intl.DateTimeFormat("pt-BR", { day: "numeric" });
const monthFmt = new Intl.DateTimeFormat("pt-BR", { month: "short", year: "numeric" });
const updatedFmt = new Intl.DateTimeFormat("pt-BR", { dateStyle: "long", timeStyle: "short" });

function esc(s) {
  return String(s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
}

function normalize(s) {
  return s.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();
}

function filtered() {
  const q = normalize($search.value.trim());
  return articles.filter((a) =>
    (!topic || a.category === topic) &&
    (!$peer.checked || a.peer) &&
    (!q || normalize(`${a.title} ${a.summary} ${a.source} ${a.authors || ""}`).includes(q))
  );
}

function entry(a) {
  return `<li><article class="entry">
    <h3><a href="${esc(a.url)}" target="_blank" rel="noopener">${esc(a.title)}</a></h3>
    <p class="meta"><span class="src">${esc(a.source)}</span>${a.peer ? '<span class="peer">revisado por pares</span>' : ""}${a.authors ? `<span class="authors">${esc(a.authors)}</span>` : ""}${topic ? "" : `<span class="topic">${TOPIC_NAMES[a.category] || ""}</span>`}</p>
    ${a.summary ? `<p class="summary">${esc(a.summary)}</p>` : ""}
  </article></li>`;
}

function render() {
  const list = filtered();
  const visible = list.slice(0, shown);
  $more.hidden = shown >= list.length;

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
    const d = new Date(date + "T12:00:00");
    return `<section class="day">
      <h2 class="day-label">${dayFmt.format(d)}<small>${monthFmt.format(d).replace(". de ", " ")}</small></h2>
      <ol>${items.map(entry).join("")}</ol>
    </section>`;
  }).join("");
}

function setTopic(t) {
  topic = t;
  shown = PAGE;
  for (const b of $topics.querySelectorAll("button")) {
    b.setAttribute("aria-selected", b.dataset.topic === t ? "true" : "false");
  }
  history.replaceState(null, "", t ? `#${t}` : location.pathname);
  render();
}

$topics.addEventListener("click", (e) => {
  const b = e.target.closest("button[data-topic]");
  if (b) setTopic(b.dataset.topic);
});
$search.addEventListener("input", () => { shown = PAGE; render(); });
$peer.addEventListener("change", () => { shown = PAGE; render(); });
$more.addEventListener("click", () => { shown += PAGE; render(); });

fetch("data/articles.json")
  .then((r) => r.json())
  .then((data) => {
    articles = data.articles;
    const peers = articles.filter((a) => a.peer).length;
    $status.textContent =
      `${articles.length} artigos de ${data.sources.length} fontes, ${peers} deles revisados por pares. ` +
      `Atualizado em ${updatedFmt.format(new Date(data.updated))}.`;
    document.getElementById("sources").textContent = data.sources.join("; ");
    setTopic(TOPIC_NAMES[topic] ? topic : "");
  })
  .catch(() => {
    $status.textContent = "Não foi possível carregar o feed. Rode “python fetch.py” para gerar os dados e sirva a pasta por HTTP.";
  });
