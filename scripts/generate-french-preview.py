#!/usr/bin/env python3
"""Build complete per-page French translation dictionaries for Canadian Editorial PREVIEWS.

Google Cloud Translation Advanced v3 is called at build time, not from browsers.
Do not edit published portfolio pages. Generated dictionaries are reviewed before
any main-site publication.
"""
import argparse
import json
import re
from pathlib import Path
from bs4 import BeautifulSoup
from google.cloud import translate_v3 as translate

PREVIEW = Path("previews/canadian")
PAGES = (
    "index.html",
    "projects/index.html",
    "certifications/index.html",
    "contact/index.html",
    "projects/enterprise-it-support/index.html",
    "projects/client-placement-optimization/index.html",
    "projects/invoicing-automation/index.html",
)
SKIP_TAGS = {"script", "style", "noscript", "svg", "code", "pre"}
PROTECTED_EXACT = {
    "Salesforce", "Sales Cloud", "Service Cloud", "Experience Cloud", "Apex",
    "GitHub", "Google", "Zoom", "LinkedIn", "Scrum.org", "CBAP®",
    "Professional Scrum Master I (PSM I)", "NOC", "IIBA",
}
MAX_CHARS = 11000
MAX_ITEMS = 90

def normalize(value):
    return " ".join(value.split())

def slug(page):
    return "home" if page == "index.html" else page.removesuffix("/index.html").replace("/", "--")

def page_strings(file):
    soup = BeautifulSoup(file.read_text(encoding="utf-8"), "html.parser")
    found = []
    for string in soup.find_all(string=True):
        if string.parent and string.parent.name in SKIP_TAGS:
            continue
        if string.find_parent(attrs={"data-no-translate": True}):
            continue
        text = normalize(str(string))
        if not text or not any(c.isalpha() for c in text):
            continue
        if text in PROTECTED_EXACT or text.startswith(("data:", "https://", "mailto:")):
            continue
        if text not in found:
            found.append(text)
    return found

def translate_all(client, parent, texts):
    translated = {}
    remaining = list(texts)
    while remaining:
        batch, total = [], 0
        while remaining and len(batch) < MAX_ITEMS:
            next_text = remaining[0]
            length = len(next_text)
            if length > MAX_CHARS:
                raise ValueError(f"One text node is too long to translate ({length} chars): {next_text[:100]}")
            if batch and total + length > MAX_CHARS:
                break
            batch.append(remaining.pop(0))
            total += length
        response = client.translate_text(
            request={
                "parent": parent,
                "contents": batch,
                "mime_type": "text/plain",
                "source_language_code": "en",
                "target_language_code": "fr",
            }
        )
        if len(response.translations) != len(batch):
            raise RuntimeError("Translation API response length does not match request")
        for original, item in zip(batch, response.translations):
            translated[original] = item.translated_text
        print(f"Translated {len(translated)}/{len(texts)} distinct strings")
    return translated

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-id", required=True)
    parser.add_argument("--dry-run", action="store_true", help="Count content without API calls")
    args = parser.parse_args()
    pages = {page: page_strings(PREVIEW / page) for page in PAGES}
    unique = list(dict.fromkeys(text for group in pages.values() for text in group))
    print(json.dumps({"pages": {p: len(v) for p, v in pages.items()},
                      "unique_strings": len(unique), "characters": sum(map(len, unique))},
                     indent=2))
    if args.dry_run:
        return
    client = translate.TranslationServiceClient()
    all_translations = translate_all(client, f"projects/{args.project_id}/locations/global", unique)
    destination = PREVIEW / "assets" / "translations"
    destination.mkdir(parents=True, exist_ok=True)
    for page, source_text in pages.items():
        mapping = {english: all_translations[english] for english in source_text}
        target = destination / (slug(page) + ".json")
        target.write_text(json.dumps({"source": "Google Cloud Translation Advanced v3",
                                      "source_language": "en", "target_language": "fr",
                                      "page": page, "translations": mapping},
                                     indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"Wrote {target}: {len(mapping)} strings")

if __name__ == "__main__":
    main()
