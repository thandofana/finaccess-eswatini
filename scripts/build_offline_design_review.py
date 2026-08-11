"""Create a self-contained, server-free visual review of the three concepts."""

from __future__ import annotations

import re
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urljoin, urlparse
from urllib.request import urlopen


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT_ROOT / "design_review"
BASE_URL = "http://127.0.0.1:3011/"
PAGES = {
    "index.html": "",
    "ledger.html": "concepts/ledger",
    "open-field.html": "concepts/open-field",
    "signal.html": "concepts/signal",
}

OFFLINE_STYLE = """
<style>
.offline-review-note{position:relative;z-index:9999;display:flex;justify-content:center;padding:10px 16px;border-bottom:1px solid #d7dfd9;background:#fffdf8;color:#53675d;font:600 12px/1.4 "Segoe UI",Arial,sans-serif;letter-spacing:.02em;text-align:center}
</style>
"""


def fetch(url: str) -> str:
    with urlopen(url, timeout=30) as response:  # noqa: S310 - fixed localhost source
        return response.read().decode("utf-8")


def fetch_stylesheet(href: str) -> str:
    try:
        return fetch(urljoin(BASE_URL, href))
    except HTTPError:
        filename = Path(urlparse(href).path).name
        built_asset = PROJECT_ROOT / "frontend" / "dist" / "client" / "assets" / filename
        return built_asset.read_text(encoding="utf-8")


def make_offline(html: str, page_name: str) -> str:
    stylesheet_urls = re.findall(
        r'<link[^>]+rel="stylesheet"[^>]+href="([^"]+)"[^>]*>', html
    )
    css = "\n".join(fetch_stylesheet(href) for href in stylesheet_urls)
    html = re.sub(r'<link[^>]+rel="stylesheet"[^>]*>', f"<style>{css}</style>", html)
    html = re.sub(r'<link[^>]+rel="(?:modulepreload|preload)"[^>]*>', "", html)
    html = re.sub(r'<script\b[^>]*>.*?</script>', "", html, flags=re.DOTALL)
    html = re.sub(r'<meta[^>]+content="http://127\.0\.0\.1:[^"]+"[^>]*>', "", html)

    replacements = {
        'href="/concepts/ledger"': 'href="ledger.html"',
        'href="/concepts/open-field"': 'href="open-field.html"',
        'href="/concepts/signal"': 'href="signal.html"',
        'href="/"': 'href="index.html"',
    }
    for source, destination in replacements.items():
        html = html.replace(source, destination)

    message = (
        "Offline visual review — Signal is the selected FinAccess Eswatini design."
        if page_name == "index.html"
        else "Offline overview preview — use Compare to return to all three designs."
    )
    html = html.replace("</head>", f"{OFFLINE_STYLE}</head>")
    html = html.replace("<body>", f'<body><div class="offline-review-note">{message}</div>', 1)
    return html


def main() -> int:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for filename, route in PAGES.items():
        rendered = fetch(urljoin(BASE_URL, route))
        offline = make_offline(rendered, filename)
        (OUTPUT_DIR / filename).write_text(offline, encoding="utf-8")
        print(f"Created {filename} ({len(offline):,} characters)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
