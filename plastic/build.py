#!/usr/bin/env python3
"""
build.py — Static article generator for EIT website.

Usage:
    python build.py                            # build every file in articles/src/
    python build.py articles/src/my-post.html  # build a single file

Reads:   articles/_template.html      (the shared skeleton)
Reads:   articles/src/*.html          (minimal content files)
Writes:  articles/<same-filename>.html (final static HTML)

Content file format
-------------------
Each file in articles/src/ must contain:

  1. A front-matter HTML comment at the very top with key: value pairs:

       <!--
       category: Innovation
       headline: My Article Title
       author:   Jane Doe
       date:     March 4, 2026
       -->

  2. Section blocks using HTML comment markers:

       <!-- body -->
       <p>Article paragraphs, <h2> subheadings, <blockquote>s, etc.</p>
       <!-- /body -->

       <!-- sources -->
       <li>Source one.</li>
       <li>Source two.</li>
       <!-- /sources -->

       <!-- copyright -->
       &copy; 2026 EIT &mdash; All rights reserved.
       <!-- /copyright -->
"""

import re
import sys
from datetime import datetime
from pathlib import Path

TEMPLATE_PATH = Path("articles/_template.html")
SRC_DIR       = Path("articles/src")
OUT_DIR       = Path("articles")
INDEX_PATH    = Path("index.html")


def wrap_paragraphs(body: str) -> str:
    """Wrap plain-text lines in <p> tags; leave lines already starting with '<' alone."""
    lines = body.splitlines()
    result = []
    for line in lines:
        stripped = line.strip()
        if stripped and not stripped.startswith("<"):
            result.append(f"<p>{stripped}</p>")
        else:
            result.append(line)
    return "\n".join(result)

def wrap_sources(sources: str) -> str:
    """Wrap plain-text lines in <li> tags; leave lines already starting with '<' alone."""
    lines = sources.splitlines()
    result = []
    for line in lines:
        stripped = line.strip()
        if stripped and not stripped.startswith("<"):
            result.append(f"<li>{stripped}</li>")
        else:
            result.append(line)
    return "\n".join(result)


def parse(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")

    # Front-matter: first HTML comment block
    meta = {}
    fm = re.match(r"^\s*<!--\n(.*?)-->", text, re.DOTALL)
    if fm:
        for line in fm.group(1).splitlines():
            if ":" in line:
                key, _, val = line.partition(":")
                meta[key.strip().lower()] = val.strip()

    # Named section blocks: <!-- tag --> ... <!-- /tag -->
    def section(tag):
        m = re.search(
            rf"<!--\s*{tag}\s*-->(.*?)<!--\s*/{tag}\s*-->",
            text, re.DOTALL | re.IGNORECASE
        )
        return m.group(1).strip() if m else ""

    return {
        "headline":  meta.get("headline",  ""),
        "category":  meta.get("category",  ""),
        "author":    meta.get("author",    ""),
        "date":      meta.get("date",      ""),
        "body":      wrap_paragraphs(section("body")),
        "sources_section": (
            '<section class="article-sources">\n'
            '      <h3 class="article-sources__title">Sources</h3>\n'
            '      <ol>\n        ' + wrap_sources(section("sources")) + '\n      </ol>\n    </section>'
            if section("sources").strip() else ""
        ),
        "copyright":     section("copyright"),
    }


def build(src_path: Path):
    data     = parse(src_path)
    template = TEMPLATE_PATH.read_text(encoding="utf-8")

    result = template
    for key, value in data.items():
        result = result.replace(f"{{{{{key}}}}}", value)

    out_path = OUT_DIR / src_path.name
    out_path.write_text(result, encoding="utf-8")
    print(f"  built  {out_path}")


def make_excerpt(body: str, max_chars: int = 220) -> str:
    """Return plain text of the first paragraph, truncated to max_chars."""
    for line in body.splitlines():
        stripped = line.strip()
        if stripped:
            text = re.sub(r"<[^>]+>", "", stripped)  # strip HTML tags
            text = text.strip()
            if not text:
                continue
            if len(text) > max_chars:
                text = text[:max_chars].rsplit(" ", 1)[0] + "\u2026"
            return text
    return ""


def build_index():
    """Regenerate the article cards inside index.html from all source files."""
    index_text = INDEX_PATH.read_text(encoding="utf-8")

    def parse_date(d: str) -> datetime:
        for fmt in ("%B %d, %Y", "%B %Y"):
            try:
                return datetime.strptime(d, fmt)
            except ValueError:
                pass
        return datetime.min

    articles = []
    for src in sorted(SRC_DIR.glob("*.html")):
        data = parse(src)
        articles.append((src.name, data))

    articles.sort(key=lambda x: parse_date(x[1]["date"]), reverse=True)

    cards = []
    for filename, data in articles:
        excerpt = make_excerpt(data["body"])
        card = (
            f'        <a href="articles/{filename}" class="tile">\n'
            f'            <span class="tile__category">{data["category"]}</span>\n'
            f'            <h2 class="tile__headline">{data["headline"]}</h2>\n'
            f'            <p class="tile__excerpt">{excerpt}</p>\n'
            f'            <div class="tile__meta">\n'
            f'                <span class="tile__date">{data["date"]}</span>\n'
            f'                <span class="tile__read-more">Read \u2192</span>\n'
            f'            </div>\n'
            f'        </a>'
        )
        cards.append(card)

    cards_block = "\n\n".join(cards)
    new_text = re.sub(
        r"(<!--\s*article-cards\s*-->).*?(<!--\s*/article-cards\s*-->)",
        f"<!-- article-cards -->\n{cards_block}\n        <!-- /article-cards -->",
        index_text,
        flags=re.DOTALL,
    )
    INDEX_PATH.write_text(new_text, encoding="utf-8")
    print(f"  updated  {INDEX_PATH}")


def main():
    if len(sys.argv) > 1:
        targets = [Path(p) for p in sys.argv[1:]]
    else:
        targets = sorted(SRC_DIR.glob("*.html"))

    if not targets:
        print("No source files found in articles/src/")
        return

    print(f"Building {len(targets)} article(s)…")
    for t in targets:
        build(t)
    build_index()
    print("Done.")


if __name__ == "__main__":
    main()
