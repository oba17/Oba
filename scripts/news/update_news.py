#!/usr/bin/env python3
"""Collect public RSS/Atom headlines for the Canadian Editorial preview.
Requires only Python stdlib; deliberately stores titles, short summaries and source links.
Never copy full publisher articles. One failed source does not break the others.
"""
import datetime as dt
import email.utils
from concurrent.futures import ThreadPoolExecutor, as_completed
from html.parser import HTMLParser
import html
import hashlib
import io
import json
import logging
import pathlib
import re
import urllib.request
import xml.etree.ElementTree as ET
from urllib.parse import urlsplit, quote, urlparse, parse_qs
from PIL import Image, UnidentifiedImageError

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

MEDIA = "{http://search.yahoo.com/mrss/}"
IMAGE_TAG = re.compile(r"""<img[^>]+src=["']([^"']+)""", re.I)

def image_url(url):
    url = html.unescape(url or "").strip()
    parts = urlsplit(url)
    if parts.scheme == "https" and parts.netloc and not parts.username and not parts.password:
        return url
    return ""

def extract_media(item, raw_description, article_link):
    """Use publisher-provided media only; never fabricate thumbnails."""
    image, video = "", ""
    for node in item.iter():
        tag = node.tag.rsplit("}", 1)[-1].lower()
        medium = (node.attrib.get("medium", "") or node.attrib.get("type", "")).lower()
        link = image_url(node.attrib.get("url", "") or node.attrib.get("href", ""))
        if tag in ("thumbnail", "image") and link and not image:
            image = link
        elif tag in ("content", "enclosure") and link:
            if medium.startswith("image/") or medium == "image":
                image = image or link
            elif medium.startswith("video/") or medium == "video":
                video = video or link
    if not image and raw_description:
        match = IMAGE_TAG.search(raw_description)
        if match:
            image = image_url(match.group(1))
    # Public video share links may provide thumbnails without an embed.
    youtube = urlparse(article_link)
    if not image and youtube.hostname in ("www.youtube.com", "youtube.com", "youtu.be"):
        video_id = (parse_qs(youtube.query).get("v") or [""])[0] if youtube.hostname != "youtu.be" else youtube.path.strip("/")
        if re.fullmatch(r"[A-Za-z0-9_-]{11}", video_id):
            image = f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg"
            video = article_link
    return image, video

def normalize_headline(title):
    """Match a Google News headline with the corresponding official publisher item."""
    title = (title or "").lower()
    title = re.sub(r"\\s+[-|–]\\s+(?:openai|salesforce|microsoft|zoom|ars technica|iiba)(?:\\s+.*)?$", "", title)
    return re.sub(r"[^a-z0-9]+", " ", title).strip()

def prefer_publisher_links(items):
    """Replace Google News relay links only if the same story exists on a direct
    publisher feed. This makes metadata/lead images retrievable.
    """
    direct = {}
    for item in items:
        host = (urlsplit(item.get("url", "")).hostname or "").lower()
        if host not in ("news.google.com", "www.news.google.com"):
            key = (item.get("category"), normalize_headline(item.get("title")))
            direct[key] = item
    for item in items:
        host = (urlsplit(item.get("url", "")).hostname or "").lower()
        if host not in ("news.google.com", "www.news.google.com"):
            continue
        key = (item.get("category"), normalize_headline(item.get("title")))
        real = direct.get(key)
        if real:
            item["url"] = real["url"]
            item["source"] = real["source"]
            item["image_url"] = item.get("image_url") or real.get("image_url", "")
            item["video_url"] = item.get("video_url") or real.get("video_url", "")
    return items

class MetaImages(HTMLParser):
    """Read publisher-owned OpenGraph/Twitter image and video metadata."""
    def __init__(self):
        super().__init__()
        self.image = ""
        self.video = ""
    def handle_starttag(self, tag, attrs):
        if tag.lower() != "meta":
            return
        a = dict(attrs)
        key = (a.get("property") or a.get("name") or "").lower()
        content = image_url(a.get("content", ""))
        if key in ("og:image", "og:image:secure_url", "twitter:image", "twitter:image:src") and content:
            self.image = self.image or content
        if key in ("og:video", "og:video:url", "og:video:secure_url", "twitter:player") and content:
            self.video = self.video or content

def publisher_preview(item):
    """Read a public article page only when the feed lacks a useful image.
    Does not download photos, bypass access controls, or copy video contents.
    """
    link = item.get("url", "")
    domain = urlsplit(link).hostname or ""
    if domain == "news.google.com" or not link.startswith("https://"):
        return ("", "")
    try:
        req = urllib.request.Request(link, headers={"User-Agent": UA, "Accept": "text/html"})
        with urllib.request.urlopen(req, timeout=7) as response:
            final = urlsplit(response.geturl())
            if final.scheme != "https" or not final.hostname:
                return ("", "")
            mime = response.headers.get("Content-Type", "")
            if "text/html" not in mime:
                return ("", "")
            sample = response.read(350_000).decode("utf-8", "replace")
        parser = MetaImages()
        parser.feed(sample)
        return (parser.image or "", parser.video or "")
    except (OSError, UnicodeError, ValueError, Exception) as exc:
        logging.debug("Preview unavailable for %s: %s", link[:80], exc)
        return ("", "")

def enrich_previews(articles, old_items):
    # Preserve working media from earlier runs so network failures don't remove pictures.
    past = {x.get("url"): x for x in old_items}
    for article in articles:
        old = past.get(article.get("url"), {})
        for field in ("image_url", "video_url"):
            article[field] = article.get(field) or old.get(field, "")
    # Prioritize images for the first few stories in all six subjects.
    candidates = []
    per_topic = {}
    for article in articles:
        category = article.get("category", "")
        if article.get("image_url") or per_topic.get(category, 0) >= 5:
            continue
        if (urlsplit(article.get("url", "")).hostname or "") == "news.google.com":
            continue
        per_topic[category] = per_topic.get(category, 0) + 1
        candidates.append(article)
    with ThreadPoolExecutor(max_workers=5) as pool:
        pending = {pool.submit(publisher_preview, item): item for item in candidates[:24]}
        for future in as_completed(pending):
            image, video = future.result()
            if image:
                pending[future]["image_url"] = image
            if video:
                pending[future]["video_url"] = video

IMAGE_DIR = ROOT / "previews/canadian/assets/news-images"
LOCAL_PREFIX = "/Oba/previews/canadian/assets/news-images/"
MAX_IMAGE_BYTES = 2_000_000

def cache_thumbnail(item):
    """Store a resized, source-attributed article thumbnail on this GitHub Pages site.
    Prevents publisher hotlink blocking; skips files that cannot be downloaded.
    """
    url = image_url(item.get("image_url", ""))
    if not url:
        return ""
    key = hashlib.sha256(url.encode("utf-8")).hexdigest()[:16]
    name = f"{key}.jpg"
    target = IMAGE_DIR / name
    if target.is_file() and target.stat().st_size > 200:
        return LOCAL_PREFIX + name
    try:
        req = urllib.request.Request(url, headers={
            "User-Agent": UA,
            "Accept": "image/avif,image/webp,image/jpeg,image/png,image/*;q=0.8",
            "Referer": item.get("url", "")
        })
        with urllib.request.urlopen(req, timeout=9) as res:
            mime = res.headers.get("Content-Type", "").lower()
            if not mime.startswith("image/"):
                return ""
            data = res.read(MAX_IMAGE_BYTES + 1)
        if len(data) > MAX_IMAGE_BYTES:
            return ""
        with Image.open(io.BytesIO(data)) as im:
            im.load()
            if im.width < 120 or im.height < 80:
                return ""
            im.thumbnail((700, 450), Image.Resampling.LANCZOS)
            if im.mode != "RGB":
                im = im.convert("RGB")
            IMAGE_DIR.mkdir(parents=True, exist_ok=True)
            im.save(target, format="JPEG", quality=75, optimize=True)
        return LOCAL_PREFIX + name
    except (OSError, ValueError, UnidentifiedImageError, Image.DecompressionBombError) as exc:
        logging.debug("Image not accessible from source: %s (%s)", url[:120], exc)
        return ""

def cache_publisher_media(articles):
    # Cache a manageable number per topic, prioritizing the newest available photos.
    selected = []
    per_category = {}
    for item in articles:
        category = item["category"]
        if not item.get("image_url") or per_category.get(category, 0) >= 8:
            continue
        per_category[category] = per_category.get(category, 0) + 1
        selected.append(item)
    with ThreadPoolExecutor(max_workers=5) as pool:
        futures = {pool.submit(cache_thumbnail, item): item for item in selected}
        for future in as_completed(futures):
            path = future.result()
            if path:
                futures[future]["local_image_url"] = path
    # Also keep previously saved thumbnails when the image was already present.
    for item in articles:
        link = item.get("local_image_url", "")
        if link.startswith(LOCAL_PREFIX) and re.fullmatch(r"[a-f0-9]{16}\\.jpg", link.split("/")[-1]):
            if not (IMAGE_DIR / link.split("/")[-1]).is_file():
                item.pop("local_image_url", None)
    logging.info("Cached %d verified publisher thumbnails",
                 sum(bool(item.get("local_image_url")) for item in articles))

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
        raw_description = get_text(item, "description", ATOM + "summary", ATOM + "content")
        description = clean(raw_description, 210)
        image, video = extract_media(item, raw_description, link)
        date = date_iso(get_text(item, "pubDate", DC + "date", ATOM + "published", ATOM + "updated"))
        parsed = urlsplit(link)
        if not title or parsed.scheme != "https" or not parsed.netloc or not date:
            continue
        results.append({"category":category, "source":publisher, "title":title,
                        "url":link, "summary":description, "published_at":date,
                        "image_url":image, "video_url":video})
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

    all_items = prefer_publisher_links(all_items)
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
    enrich_previews(articles, old.get("articles", []))
    cache_publisher_media(articles)
    output = {"updated_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds").replace("+00:00","Z"),
              "articles": articles, "sources_ok":successful}
    DEST.parent.mkdir(parents=True, exist_ok=True)
    DEST.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    logging.info("Stored %d articles from %d categories", len(articles),len(grouped))

if __name__ == "__main__":
    main()
