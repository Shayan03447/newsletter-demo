"""Render content.json + brand.json into email-safe, CSS-inlined HTML.

Usage:
  python tools/render_newsletter.py --content .tmp/content.json [--out .tmp/newsletter.html]

Writes the email HTML (images referenced as cid:...) and a *_preview.html where
cid: references point at local PNG files in .tmp/infographics/ for browser preview.
"""
import argparse
import json
import re
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape
from premailer import transform

ROOT = Path(__file__).resolve().parent.parent


def render(content_path: Path, out_path: Path, brand_path: Path) -> None:
    content = json.loads(content_path.read_text(encoding="utf-8"))
    brand = json.loads(brand_path.read_text(encoding="utf-8"))

    env = Environment(
        loader=FileSystemLoader(ROOT / "templates"),
        autoescape=select_autoescape(["html", "j2"]),
    )
    html = env.get_template("newsletter.html.j2").render(c=content, b=brand)
    html = transform(html, keep_style_tags=True, remove_classes=False, strip_important=False)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html, encoding="utf-8")

    # Browser preview: swap cid: for local file paths
    infog = out_path.parent / "infographics"
    preview = re.sub(r'src="cid:([^"]+)"', lambda m: f'src="infographics/{m.group(1)}.png"', html)
    preview_path = out_path.with_name(out_path.stem + "_preview.html")
    preview_path.write_text(preview, encoding="utf-8")
    print(f"Email HTML : {out_path}")
    print(f"Preview    : {preview_path}  (images from {infog})")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--content", default=str(ROOT / ".tmp" / "content.json"))
    ap.add_argument("--out", default=str(ROOT / ".tmp" / "newsletter.html"))
    ap.add_argument("--brand", default=str(ROOT / "brand" / "brand.json"))
    a = ap.parse_args()
    render(Path(a.content), Path(a.out), Path(a.brand))
