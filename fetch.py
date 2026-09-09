"""Coleta artigos de fontes acadêmicas sobre Bíblia e cristianismo e grava data/articles.json.

Uso: python fetch.py
"""
import html
import json
import re
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import feedparser
import requests

OUT = Path(__file__).parent / "data" / "articles.json"
MAX_AGE_DAYS = 180
CONTACT = "estratos-feed@example.com"  # usado no "polite pool" da CrossRef

# Fontes RSS/Atom. category: arqueologia | manuscritos | historia | teologia | ciencia
# peer: True para periódicos revisados por pares. filter: True exige palavra-chave bíblica.
FEEDS = [
    # Arqueologia
    {"name": "Biblical Archaeology Society", "url": "https://www.biblicalarchaeology.org/feed/", "category": "arqueologia"},
    {"name": "ASOR", "url": "https://www.asor.org/feed/", "category": "arqueologia"},
    {"name": "Israel Hayom - Arqueologia", "url": "https://www.israelhayom.com/tag/archaeology/feed/", "category": "arqueologia"},
    {"name": "Archaeology Magazine", "url": "https://archaeology.org/feed/", "category": "ciencia", "filter": True},
    {"name": "ScienceDaily - Arqueologia", "url": "https://www.sciencedaily.com/rss/fossils_ruins/archaeology.xml", "category": "ciencia", "filter": True},
    {"name": "Phys.org - Arqueologia", "url": "https://phys.org/rss-feed/science-news/archaeology-fossils/", "category": "ciencia", "filter": True},
    {"name": "Live Science", "url": "https://www.livescience.com/feeds/all", "category": "ciencia", "filter": True},
    # Manuscritos e crítica textual
    {"name": "Evangelical Textual Criticism", "url": "https://evangelicaltextualcriticism.blogspot.com/feeds/posts/default", "category": "manuscritos"},
    {"name": "Text & Canon Institute", "url": "https://textandcanon.org/feed/", "category": "manuscritos"},
    {"name": "PaleoJudaica", "url": "https://paleojudaica.blogspot.com/feeds/posts/default", "category": "manuscritos"},
    {"name": "Tyndale House", "url": "https://tyndalehouse.com/feed/", "category": "manuscritos"},
    # História e estudos bíblicos
    {"name": "Ancient Jew Review", "url": "https://www.ancientjewreview.com/read?format=rss", "category": "historia"},
    {"name": "Bible & Interpretation", "url": "https://bibleinterp.arizona.edu/rss.xml", "category": "historia"},
    {"name": "TheTorah.com", "url": "https://www.thetorah.com/rss", "category": "historia"},
    {"name": "The Bart Ehrman Blog", "url": "https://www.ehrmanblog.org/feed/", "category": "historia"},
    {"name": "Reading Acts", "url": "https://readingacts.com/feed/", "category": "teologia"},
    {"name": "Larry Hurtado's Blog", "url": "https://larryhurtado.wordpress.com/feed/", "category": "historia"},
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
            "source": src["name"], "category": src["category"], "peer": bool(src.get("peer")),
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
            "source": journal, "authors": authors, "category": category, "peer": True,
        })
    print(f"  CrossRef '{query}': {len(items)}")
    return items


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

    merged = {}
    for a in old + new:  # itens novos sobrescrevem os antigos com o mesmo título
        if since <= a["date"] <= today:
            merged[norm_key(a["title"])] = a
    articles = sorted(merged.values(), key=lambda a: a["date"], reverse=True)

    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps({
        "updated": datetime.now(timezone.utc).isoformat(timespec="minutes"),
        "sources": sorted({a["source"] for a in articles}),
        "articles": articles,
    }, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n{len(articles)} artigos gravados em {OUT}")


if __name__ == "__main__":
    main()
