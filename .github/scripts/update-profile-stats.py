"""Cache public GitHub statistics; keep the previous cards on service errors."""

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET


ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / "assets" / "profile"
PALETTE = {
    "username": "ReXooGen",
    "bg_color": "171e25",
    "title_color": "d5f570",
    "text_color": "c7d0d8",
    "icon_color": "d5f570",
    "border_color": "37424c",
    "border_radius": "16",
    "card_width": "430",
    "hide_border": "false",
    "disable_animations": "true",
}
CARDS = {
    "github-stats.svg": (
        "api",
        {"custom_title": "GitHub activity", "show_icons": "true", "hide_rank": "true"},
        ("GitHub activity", "Total Stars Earned", "Total PRs"),
    ),
    "github-languages.svg": (
        "api/top-langs/",
        {"custom_title": "Repository languages", "layout": "compact", "langs_count": "6"},
        ("Repository languages", "%"),
    ),
}


def fetch_card(item):
    name, (route, options, required) = item
    url = "https://github-readme-stats.vercel.app/" + route + "?" + urlencode(PALETTE | options)
    request = Request(url, headers={"User-Agent": "ReXooGen-profile-stats"})
    with urlopen(request, timeout=30) as response:
        data = response.read(1_000_001)
    if len(data) > 1_000_000:
        raise ValueError(f"{name}: unexpectedly large card")
    root = ET.fromstring(data)
    if root.tag != "{http://www.w3.org/2000/svg}svg":
        raise ValueError(f"{name}: response is not SVG")
    # Ignore stylesheet content when checking the card's actual text.
    text = " ".join(
        " ".join(element.itertext())
        for element in root.iter()
        if element.tag.rsplit("}", 1)[-1] in {"title", "desc", "text"}
    )
    if not all(marker in text for marker in required):
        raise ValueError(f"{name}: expected statistics are missing")
    if any(marker in text.lower() for marker in ("something went wrong", "could not fetch", "rate limit")):
        raise ValueError(f"{name}: service returned an error card")
    for element in root.iter():
        if element.tag.rsplit("}", 1)[-1] in {"script", "foreignObject"}:
            raise ValueError(f"{name}: unexpected active SVG content")
        for key, value in element.attrib.items():
            if key.lower().startswith("on") or (key.endswith("href") and not value.startswith("#")):
                raise ValueError(f"{name}: unexpected external SVG content")
    data = b"\n".join(line.rstrip() for line in data.splitlines()).strip() + b"\n"
    return name, data


def main():
    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            cards = list(pool.map(fetch_card, CARDS.items()))
    except Exception as error:
        if all((OUTPUT / name).is_file() for name in CARDS):
            print(f"Statistics unavailable; keeping previous cards: {error}")
            return
        raise
    OUTPUT.mkdir(parents=True, exist_ok=True)
    for name, data in cards:
        (OUTPUT / name).write_bytes(data)
        print(f"Updated {name}")


if __name__ == "__main__":
    main()
