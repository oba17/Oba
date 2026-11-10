#!/usr/bin/env python3
"""Collect public RSS/Atom headlines for the Canadian Editorial preview.
Requires only Python stdlib; deliberately stores titles, short summaries and source links.
Never copy full publisher articles. One failed source does not break the others.
"""
import datetime as dt
import email.utils
import html
import json
import logging
import pathlib
import re
import urllib.request
import xml.etree.ElementTree as ET
from urllib.parse import urlsplit, quote

ROOT = pathlib.Path(__file__).resolve().parents[2]
DEST = ROOT / "previews/canadian/data/news.json"
UA = "ObaPortfolioIndustryFeed/1.0 (+https://github.com/oba17/Oba)"
SOURCES = [
    ("Salesforce", "Salesforce Developers", "https://developer.salesforce.com/blogs/feed"),
    ("Microsoft", "Microsoft Tech Community", "https://techcommunity.microsoft.com/t5/s/gxcuf89792/rss/board?board.id=microsoft_365blog"),
    ("AI", "OpenAI News", "https://openai.com/news/rss.xml"),
    ("Zoom", "Zoom Blog", "https://www.zoom.com/en/blog/feed/"),
    ("Tech", "Ars Technica", "https://feeds.arstechnica.com/arstechnica/index"),
    ("Business Analysis", "Bridging the Gap", "https://www.bridging-the-gap.com/feed/"),
    ("Business Analysis", "Adaptive US", "https://adaptiveus.com/blog/rss.xml"),
    ("Business Analysis", "Modern Analyst", "https://modernanalyst.substack.com/feed"),
]
# Backup news-search feeds for sources without a public or stable RSS endpoint.
# Queries restrict coverage to the publishers' own domains.
for _category, _domain in [
    ("Salesforce", "developer.salesforce.com"),
    ("Microsoft", "techcommunity.microsoft.com"),
    ("AI", "openai.com"),
    ("Zoom", "zoom.com"),
    ("Tech", "arstechnica.com"),
    ("Business Analysis", "iiba.org"),
]:
    _query = quote(f"site:{_domain} when:60d")
    SOURCES.append((_category, f"Google News · {_domain}",
                    f"https://news.google.com/rss/search?q={_query}&hl=en-CA&gl=CA&ceid=CA%3Aen"))

ATOM = "{http://www.w3.org/2005/Atom}"
DC = "{http://purl.org/dc/elements/1.1/}"
HTML_TAG = re.compile(r"<[^>]*>")
SPACE = re.compile(r"\s+")

def clean(value, limit=190):
    value = html.unescape(HTML_TAG.sub(" ", value or ""))
    value = SPACE.sub(" ", value).strip()
    return value[:limit].rstrip() + ("…" if len(value) > limit else "")

def date_iso(value):
    if not value:
        return ""
    try:
        parsed = email.utils.parsedate_to_datetime(value)
        if parsed:
            return parsed.astimezone(dt.timezone.utc).isoformat().replace("+00:00", "Z")
    except (TypeError, ValueError):
        pass
    try:
        return dt.datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(dt.timezone.utc).isoformat().replace("+00:00", "Z")
    except ValueError:
        return ""

def get_text(item, *names):
    for name in names:
        node = item.find(name)
        if node is not None and node.text:
            return node.text
    return ""

def fetch(category, publisher, url):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept":"application/rss+xml, application/atom+xml, application/xml, text/xml, */*"})
    with urllib.request.urlopen(req, timeout=18) as response:
        raw = response.read(2_500_000)
    feed = ET.fromstring(raw)
    entries = feed.findall("./channel/item") if feed.tag.lower() == "rss" else feed.findall(f"./{ATOM}entry")
    if not entries:
        entries = feed.findall(f".//{ATOM}entry")
    results = []
    for item in entries[:20]:
        title = clean(get_text(item, "title", ATOM + "title"), 135)
        link = get_text(item, "link").strip()
        if not link:
            for node in item.findall(ATOM + "link"):
                if node.attrib.get("rel", "alternate") == "alternate":
                    link = node.attrib.get("href", "")
                    break
        description = clean(get_text(item, "description", ATOM + "summary", ATOM + "content"), 210)
        date = date_iso(get_text(item, "pubDate", DC + "date", ATOM + "published", ATOM + "updated"))
        parsed = urlsplit(link)
        if not title or parsed.scheme != "https" or not parsed.netloc or not date:
            continue
        results.append({"category":category, "source":publisher, "title":title,
                        "url":link, "summary":description, "published_at":date})
    return results

def main():
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    all_items = []
    successful = []
    for category, publisher, url in SOURCES:
        try:
            items = fetch(category, publisher, url)
            logging.info("%s: %d items", publisher, len(items))
            if items:
                successful.append(category)
                all_items.extend(items)
        except Exception as exc:
            logging.warning("%s failed: %s", publisher, exc)

    old = {}
    if DEST.is_file():
        try:
            old = json.loads(DEST.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            pass

    # Preserve previously collected items for sources temporarily unavailable.
    for item in old.get("articles", []):
        if item.get("category") not in successful and item.get("category") in {c for c, _, _ in SOURCES}:
            all_items.append(item)

    dedup = {}
    for item in all_items:
        dedup[item["url"].split("?")[0].rstrip("/")] = item
    grouped = {}
    for item in sorted(dedup.values(), key=lambda x: x.get("published_at", ""), reverse=True):
        group = grouped.setdefault(item["category"], [])
        if len(group) < 12:
            group.append(item)
    articles = sorted((x for group in grouped.values() for x in group),
                      key=lambda x: x.get("published_at", ""), reverse=True)[:72]
    if not articles:
        raise SystemExit("No live feeds and no cached articles; not overwriting JSON")
    output = {"updated_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds").replace("+00:00","Z"),
              "articles": articles, "sources_ok":successful}
    DEST.parent.mkdir(parents=True, exist_ok=True)
    DEST.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    logging.info("Stored %d articles from %d categories", len(articles),len(grouped))

if __name__ == "__main__":
    main()
