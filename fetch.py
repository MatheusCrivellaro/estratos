"""Coleta artigos acadêmicos sobre Bíblia e cristianismo, traduz as chamadas e grava data/articles.json.

Uso: python fetch.py
"""
import html
import json
import re
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path

import feedparser
import requests
from deep_translator import GoogleTranslator

OUT = Path(__file__).parent / "data" / "articles.json"
MAX_AGE_DAYS = 180
CONTACT = "estratos-feed@example.com"  # usado no "polite pool" da CrossRef

# Fontes RSS/Atom.
#   category: arqueologia | manuscritos | historia | teologia | ciencia
#   kind:     revista | instituicao | blog | noticia  (periódicos revisados por pares recebem "periodico")
#   filter:   True exige palavra-chave bíblica no texto (para feeds gerais de ciência)
FEEDS = [
    {"name": "Biblical Archaeology Society", "url": "https://www.biblicalarchaeology.org/feed/", "category": "arqueologia", "kind": "revista"},
    {"name": "ASOR", "url": "https://www.asor.org/feed/", "category": "arqueologia", "kind": "instituicao"},
    {"name": "Israel Hayom - Arqueologia", "url": "https://www.israelhayom.com/tag/archaeology/feed/", "category": "arqueologia", "kind": "noticia"},
    {"name": "Archaeology Magazine", "url": "https://archaeology.org/feed/", "category": "ciencia", "kind": "revista", "filter": True},
    {"name": "ScienceDaily - Arqueologia", "url": "https://www.sciencedaily.com/rss/fossils_ruins/archaeology.xml", "category": "ciencia", "kind": "noticia", "filter": True},
    {"name": "Phys.org - Arqueologia", "url": "https://phys.org/rss-feed/science-news/archaeology-fossils/", "category": "ciencia", "kind": "noticia", "filter": True},
    {"name": "Live Science", "url": "https://www.livescience.com/feeds/all", "category": "ciencia", "kind": "noticia", "filter": True},
    {"name": "Evangelical Textual Criticism", "url": "https://evangelicaltextualcriticism.blogspot.com/feeds/posts/default", "category": "manuscritos", "kind": "blog"},
    {"name": "Text & Canon Institute", "url": "https://textandcanon.org/feed/", "category": "manuscritos", "kind": "instituicao"},
    {"name": "PaleoJudaica", "url": "https://paleojudaica.blogspot.com/feeds/posts/default", "category": "manuscritos", "kind": "blog"},
    {"name": "Tyndale House", "url": "https://tyndalehouse.com/feed/", "category": "manuscritos", "kind": "instituicao"},
    {"name": "Ancient Jew Review", "url": "https://www.ancientjewreview.com/read?format=rss", "category": "historia", "kind": "revista"},
    {"name": "Bible & Interpretation", "url": "https://bibleinterp.arizona.edu/rss.xml", "category": "historia", "kind": "revista"},
    {"name": "TheTorah.com", "url": "https://www.thetorah.com/rss", "category": "historia", "kind": "revista"},
    {"name": "The Bart Ehrman Blog", "url": "https://www.ehrmanblog.org/feed/", "category": "historia", "kind": "blog"},
    {"name": "Reading Acts", "url": "https://readingacts.com/feed/", "category": "teologia", "kind": "blog"},
    {"name": "Larry Hurtado's Blog", "url": "https://larryhurtado.wordpress.com/feed/", "category": "historia", "kind": "blog"},
]

# Consultas na CrossRef (artigos revisados por pares de qualquer editora).
CROSSREF_QUERIES = [
    ("Dead Sea Scrolls", "manuscritos"),
    ("Qumran", "manuscritos"),
    ("New Testament textual criticism", "manuscritos"),
    ("Septuagint", "manuscritos"),
    ("biblical archaeology", "arqueologia"),
    ("Iron Age Israel archaeology", "arqueologia"),
    ("Jerusalem excavation", "arqueologia"),
    ("Hebrew Bible", "teologia"),
    ("early Christianity", "historia"),
    ("Second Temple Judaism", "historia"),
    ("historical Jesus", "historia"),
    ("Pauline epistles", "teologia"),
]

KEYWORDS = re.compile(
    r"\b(bible|biblical|old testament|new testament|hebrew|israel|israelite|judah|judea|judaea|jerusalem|"
    r"jesus|christ|christian|gospel|apostle|paul\b|dead sea|qumran|scroll|septuagint|torah|canaan|philistine|"
    r"galilee|nazareth|bethlehem|temple mount|solomon|david\b|jericho|megiddo|lachish|samaria|jordan|sinai|"
    r"levant|near east|mesopotamia|assyria|babylon|persia|phoenician|aramaic|papyrus|codex|manuscript|"
    r"moses|exodus|pharaoh|egypt|nineveh|hittite|moab|edom|ugarit)",
    re.I,
)

# Filtro mais rígido para a CrossRef, que devolve muito ruído em consultas amplas.
STRICT_RE = re.compile(
    r"\b(bible|biblical|old testament|new testament|hebrew bible|septuagint|qumran|dead sea scrolls|torah|"
    r"gospel|jesus|christ|christian|apostle|pauline|paul's|israelite|ancient israel|judah|judea|judaea|jerusalem|"
    r"second temple|canaan|philistine|galilee|masoretic|targum|papyr|codex|manuscript|patristic|"
    r"church father|syriac|coptic|aramaic|levant|near east|synagogue|rabbinic|mishna|talmud)",
    re.I,
)
JOURNAL_RE = re.compile(
    r"bible|biblical|theolog|testament|judai|jewish|christian|near east|levant|israel|atiqot|qadum|dead sea|"
    r"qumran|septuagint|patristic|scripture|vetus|novum|hebrew|semit|religio|church",
    re.I,
)

# Índice de assuntos: cada artigo recebe as etiquetas cujo padrão aparece no título ou no resumo.
TAGS = [
    ("Manuscritos do Mar Morto", r"dead sea scroll|qumran|\b[14]q\d|\b11q"),
    ("Jerusalém", r"jerusalem|temple mount|city of david|siloam|ophel|kidron"),
    ("Antigo Testamento", r"old testament|hebrew bible|pentateuch|torah|genesis|exodus|leviticus|deuteronomy|isaiah|jeremiah|ezekiel|psalm|proverbs|\bjob\b|daniel|kings\b|samuel|chronicles|prophet"),
    ("Novo Testamento", r"new testament|gospel|synoptic|\bmatthew\b|\bmark\b|\bluke\b|\bjohn\b|acts of the apostles|epistle|apocalypse|revelation"),
    ("Jesus histórico", r"historical jesus|\bjesus\b|nazareth|galilee|capernaum"),
    ("Paulo e as epístolas", r"\bpaul\b|pauline|romans|corinthians|galatians|thessalonians|philippians|ephesians|colossians"),
    ("Crítica textual", r"textual criticism|textual variant|\bvariant|codex|codices|papyr|scribe|scribal|critical edition|nestle|byzantine text|masoretic|manuscript"),
    ("Septuaginta", r"septuagint|\blxx\b|greek bible|old greek"),
    ("Judaísmo do Segundo Templo", r"second temple|hasmonean|maccabe|josephus|philo|essene|pharisee|sadducee|jubilees|enoch"),
    ("Cristianismo primitivo", r"early christian|early church|patristic|church father|origen|augustine|irenaeus|tertullian|apostolic father|gnostic|nag hammadi|apocryph|syriac|coptic"),
    ("Epigrafia e inscrições", r"inscription|epigraph|ostrac|\bseal|bulla|stele|stela|graffit|\bcoin|numismat"),
    ("Escavações", r"excavat|dig season|\btel\b|\btell\b|stratum|strata|survey|unearth"),
    ("Israel antigo", r"iron age|israelite|judah|kingdom of|davidic|solomon|omri|hezekiah|lachish|megiddo|hazor|samaria|philistine|canaan"),
    ("Egito e Mesopotâmia", r"egypt|pharaoh|mesopotam|babylon|assyria|sumer|akkad|persia|ugarit|hittite|cuneiform|hieroglyph"),
    ("Línguas antigas", r"\bhebrew\b|aramaic|\bgreek\b|\blatin\b|akkadian|philolog|lexic|grammar|semitic|linguistic"),
    ("Liturgia e cânon", r"\bcanon|liturg|lectionar|synagogue|worship|prayer|psalter|hymn"),
    ("Interpretação e teologia", r"theolog|christolog|soteriolog|eschatolog|doctrine|exeges|hermeneut|reception"),
    ("Livros e eventos", r"book review|review of|new book|forthcoming|published by|mohr siebeck|eerdmans|\bsbl\b|conference|call for papers|lecture|podcast|interview"),
]
TAGS = [(name, re.compile(pat, re.I)) for name, pat in TAGS]

TAG_RE = re.compile(r"<[^>]+>")
WS_RE = re.compile(r"\s+")
TRAILER_RE = re.compile(r"(\[…\]|\[\.\.\.\]|The post .*? appeared first on .*$|Continue reading.*$|Read more.*$)", re.I)
UA = {"User-Agent": "Mozilla/5.0 (compatible; Estratos feed reader)"}


def clean(text, limit=700):
    text = html.unescape(TAG_RE.sub(" ", text or ""))
    text = WS_RE.sub(" ", text).strip()
    text = TRAILER_RE.sub("", text).strip()
    text = re.sub(r"^(Abstract|Summary|Resumo)[:.]?\s+", "", text)
    if len(text) > limit:
        text = text[: limit - 1].rsplit(" ", 1)[0] + "…"
    return text


def norm_key(title):
    return re.sub(r"[^a-z0-9]+", "", title.lower())[:80]


def tags_for(text):
    return [name for name, rx in TAGS if rx.search(text)][:4]


def parse_feed(src):
    items = []
    try:
        r = requests.get(src["url"], timeout=25, headers=UA)
        r.raise_for_status()
        parsed = feedparser.parse(r.content)
    except Exception as e:
        print(f"  ! {src['name']}: {e}")
        return items
    for e in parsed.entries:
        title = clean(e.get("title", ""), 240)
        link = e.get("link", "")
        if not title or not link:
            continue
        summary = clean(e.get("summary") or (e.get("content") or [{}])[0].get("value", ""))
        dt = e.get("published_parsed") or e.get("updated_parsed")
        if not dt:
            continue
        date = datetime(*dt[:6], tzinfo=timezone.utc).date().isoformat()
        if src.get("filter") and not (KEYWORDS.search(title) or KEYWORDS.search(summary)):
            continue
        items.append({
            "title": title, "url": link, "summary": summary, "date": date,
            "source": src["name"], "category": src["category"], "kind": src["kind"], "peer": False,
            "tags": tags_for(f"{title} {summary}"),
        })
    print(f"  {src['name']}: {len(items)}")
    return items


def crossref(query, category, since):
    items = []
    try:
        r = requests.get(
            "https://api.crossref.org/works",
            params={
                "query.bibliographic": query, "rows": 25,
                "filter": f"from-pub-date:{since},type:journal-article",
                "select": "title,container-title,author,abstract,URL,issued,DOI",
                "mailto": CONTACT,
            },
            timeout=40, headers={"User-Agent": f"Estratos/1.0 (mailto:{CONTACT})"},
        )
        r.raise_for_status()
        works = r.json()["message"]["items"]
    except Exception as e:
        print(f"  ! CrossRef '{query}': {e}")
        return items
    for w in works:
        title = clean(" ".join(w.get("title") or []), 240)
        parts = (w.get("issued") or {}).get("date-parts", [[None]])[0]
        if not title or not parts or not parts[0]:
            continue
        y, m, d = (list(parts) + [1, 1])[:3]
        date = f"{y:04d}-{m or 1:02d}-{d or 1:02d}"
        authors = ", ".join(
            " ".join(filter(None, [a.get("given"), a.get("family")])) for a in (w.get("author") or [])[:3]
        )
        journal = html.unescape((w.get("container-title") or ["Periódico"])[0])
        summary = clean(w.get("abstract", ""))
        if not (STRICT_RE.search(f"{title} {summary}") or JOURNAL_RE.search(journal)):
            continue
        items.append({
            "title": title, "url": w.get("URL") or f"https://doi.org/{w.get('DOI')}",
            "summary": summary, "date": date,
            "source": journal, "authors": authors, "category": category, "kind": "periodico", "peer": True,
            "tags": tags_for(f"{title} {summary}"),
        })
    print(f"  CrossRef '{query}': {len(items)}")
    return items


def translate_missing(articles):
    """Traduz título e resumo dos artigos que ainda não têm versão em português."""
    todo = [a for a in articles if "title_pt" not in a or ("summary_pt" not in a and a["summary"])]
    if not todo:
        print("Tradução: nada novo.")
        return
    print(f"Tradução: {len(todo)} artigos…")
    def tr(text):
        # Uma instância por chamada: o GoogleTranslator guarda estado interno e não é seguro entre threads.
        for attempt in range(3):
            try:
                return GoogleTranslator(source="auto", target="pt").translate(text) or text
            except Exception:
                time.sleep(2 * (attempt + 1))
        return None

    def work(a):
        if "title_pt" not in a:
            t = tr(a["title"])
            if t:
                a["title_pt"] = t
        if "summary_pt" not in a and a["summary"]:
            s = tr(a["summary"])
            if s:
                a["summary_pt"] = s

    with ThreadPoolExecutor(max_workers=4) as pool:
        list(pool.map(work, todo))
    missing = sum(1 for a in todo if "title_pt" not in a)
    print(f"Tradução concluída ({missing} sem tradução).")


def main():
    today = datetime.now(timezone.utc).date().isoformat()
    since = (datetime.now(timezone.utc) - timedelta(days=MAX_AGE_DAYS)).date().isoformat()

    old = []
    if OUT.exists():
        old = json.loads(OUT.read_text(encoding="utf-8")).get("articles", [])

    print("Feeds:")
    new = []
    for src in FEEDS:
        new += parse_feed(src)
    print("CrossRef:")
    for q, cat in CROSSREF_QUERIES:
        new += crossref(q, cat, since)
        time.sleep(0.5)

    # Itens novos sobrescrevem os antigos, mas herdam as traduções já feitas.
    merged = {}
    for a in old:
        if since <= a["date"] <= today:
            merged[norm_key(a["title"])] = a
    for a in new:
        if not (since <= a["date"] <= today):
            continue
        key = norm_key(a["title"])
        prev = merged.get(key, {})
        keep = {k: prev[k] for k in ("title_pt", "summary_pt") if k in prev}
        if prev.get("summary") != a["summary"]:
            keep.pop("summary_pt", None)
        merged[key] = {**keep, **a}

    # Remove repetições pelo link (o mesmo texto republicado com título ligeiramente diferente).
    seen, articles = set(), []
    for a in sorted(merged.values(), key=lambda a: (a["date"], a["title"]), reverse=True):
        if a["url"] in seen:
            continue
        seen.add(a["url"])
        articles.append(a)
    translate_missing(articles)

    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps({
        "updated": datetime.now(timezone.utc).isoformat(timespec="minutes"),
        "sources": sorted({a["source"] for a in articles}),
        "articles": articles,
    }, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n{len(articles)} artigos gravados em {OUT}")


if __name__ == "__main__":
    main()
