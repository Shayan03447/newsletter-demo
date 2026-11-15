"""Generate on-brand infographic PNGs from a JSON spec (Gmail-safe: PNG, not SVG).

Spec file (list of infographics):
[
  {"cid": "chart1", "type": "bar", "title": "...", "labels": [...], "values": [...], "unit": "%", "source": "..."},
  {"cid": "chart2", "type": "line", ...same fields...},
  {"cid": "chart3", "type": "donut", ...same fields...}
]

Usage:
  python tools/make_infographic.py --spec .tmp/infographics.json [--outdir .tmp/infographics]
"""
import argparse
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parent.parent


def _palette(brand):
    c = brand["colors"]
    return [c["primary"], c["accent"], "#2BB58E", "#8A5CF6", "#E5484D", "#0EA5E9"]


def _fmt(v, unit):
    s = f"{v:,.1f}".rstrip("0").rstrip(".") if isinstance(v, float) else f"{v:,}"
    return f"{s}{unit}"


def draw(spec, brand, outdir: Path):
    c = brand["colors"]
    pal = _palette(brand)
    unit = spec.get("unit", "")
    labels, values = spec["labels"], spec["values"]

    fig, ax = plt.subplots(figsize=(8, 4.4), dpi=200)
    fig.patch.set_facecolor(c["card"])
    ax.set_facecolor(c["card"])

    t = spec["type"]
    if t == "bar":
        bars = ax.bar(labels, values, color=pal[0], width=0.6)
        top = max(values)
        bars[values.index(top)].set_color(c["accent"])  # highlight the max
        for b, v in zip(bars, values):
            ax.text(b.get_x() + b.get_width() / 2, v + top * 0.02, _fmt(v, unit),
                    ha="center", va="bottom", fontsize=10, color=c["ink"], fontweight="bold")
        ax.set_ylim(0, top * 1.15)
    elif t == "line":
        ax.plot(labels, values, color=pal[0], linewidth=3, marker="o", markersize=7)
        ax.fill_between(labels, values, color=pal[0], alpha=0.1)
        for x, v in zip(labels, values):
            ax.annotate(_fmt(v, unit), (x, v), textcoords="offset points", xytext=(0, 9),
                        ha="center", fontsize=9, color=c["ink"])
        ax.set_ylim(min(values) * 0.9 if min(values) > 0 else min(values) * 1.1, max(values) * 1.12)
    elif t == "donut":
        ax.pie(values, labels=None, colors=pal[: len(values)], startangle=90, counterclock=False,
               wedgeprops={"width": 0.38, "edgecolor": c["card"], "linewidth": 2})
        ax.legend([f"{l}  ({_fmt(v, unit)})" for l, v in zip(labels, values)],
                  loc="center left", bbox_to_anchor=(1, 0.5), frameon=False, fontsize=10, labelcolor=c["ink"])
        ax.set_aspect("equal")
    else:
        raise ValueError(f"Unknown type: {t}")

    if t != "donut":
        for sp in ("top", "right", "left"):
            ax.spines[sp].set_visible(False)
        ax.spines["bottom"].set_color(c["muted"])
        ax.tick_params(axis="x", colors=c["muted"], labelsize=10, length=0)
        ax.set_yticks([])

    fig.suptitle(spec["title"], x=0.06, ha="left", fontsize=15, fontweight="bold", color=c["ink"], y=0.97)
    if spec.get("source"):
        fig.text(0.06, 0.02, f"Source: {spec['source']}", fontsize=8, color=c["muted"], ha="left")
    fig.tight_layout(rect=(0.02, 0.05, 0.98, 0.92))

    outdir.mkdir(parents=True, exist_ok=True)
    out = outdir / f"{spec['cid']}.png"
    fig.savefig(out, facecolor=fig.get_facecolor())
    plt.close(fig)
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--spec", default=str(ROOT / ".tmp" / "infographics.json"))
    ap.add_argument("--outdir", default=str(ROOT / ".tmp" / "infographics"))
    ap.add_argument("--brand", default=str(ROOT / "brand" / "brand.json"))
    a = ap.parse_args()
    brand = json.loads(Path(a.brand).read_text(encoding="utf-8"))
    for s in json.loads(Path(a.spec).read_text(encoding="utf-8")):
        print("Wrote", draw(s, brand, Path(a.outdir)))
