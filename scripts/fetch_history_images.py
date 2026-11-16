"""Fetch the nine documented Commons photographs used on History pages."""
import json
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
RECORD = ROOT / "data/history/north_africa_1940_1942.json"
API = "https://commons.wikimedia.org/w/api.php"
HEADERS = {"User-Agent": "BenghaziHandicapHistory/1.0 (archival illustration fetch)"}


def fetch(url):
    with urlopen(Request(url, headers=HEADERS), timeout=30) as response:
        return response.read()


def main():
    periods = json.loads(RECORD.read_text(encoding="utf-8"))["episodes"]
    for period in periods:
        image = period["image"]
        params = urlencode({"action": "query", "titles": "File:" + image["commons_file"],
                            "prop": "imageinfo", "iiprop": "url", "iiurlwidth": "800",
                            "format": "json"})
        pages = json.loads(fetch(f"{API}?{params}"))["query"]["pages"]
        page = next(iter(pages.values()))
        if "imageinfo" not in page:
            raise ValueError(f"Commons file missing: {image['commons_file']}")
        info = page["imageinfo"][0]
        url = info.get("thumburl", info["url"])
        if not url.startswith(("https://thumb.wikimedia.org/", "https://upload.wikimedia.org/")):
            raise ValueError(f"Unexpected image host: {url}")
        target = ROOT / image["file"]
        target.parent.mkdir(parents=True, exist_ok=True)
        data = fetch(url)
        if not data.startswith(b"\xff\xd8\xff") or len(data) > 5_000_000:
            raise ValueError(f"Invalid JPEG: {image['commons_file']}")
        target.write_bytes(data)
        print(f"{period['id']}: {len(data):,} bytes")


if __name__ == "__main__":
    main()
