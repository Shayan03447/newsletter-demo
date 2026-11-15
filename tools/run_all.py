"""Run the whole newsletter pipeline with ONE command (no Claude Code needed).

Steps: charts (make_infographic) -> HTML (render_newsletter) -> optional Gmail (send_gmail).

Inputs you fill in beforehand:
  .tmp/content.json         the newsletter text
  .tmp/infographics.json    the chart data

Examples:
  python tools/run_all.py                              # build only, then open preview yourself
  python tools/run_all.py --to me@gmail.com            # build + save as Gmail DRAFT (safe default)
  python tools/run_all.py --to me@gmail.com --send     # build + really SEND (explicit)
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TMP = ROOT / ".tmp"

# Make sibling tool modules importable (tools/ is this script's folder).
sys.path.insert(0, str(Path(__file__).resolve().parent))

import make_infographic  # noqa: E402
import render_newsletter  # noqa: E402


def step(n, text):
    print(f"\n[{n}] {text}")


def main():
    ap = argparse.ArgumentParser(description="Build (and optionally email) the newsletter.")
    ap.add_argument("--content", default=str(TMP / "content.json"))
    ap.add_argument("--spec", default=str(TMP / "infographics.json"))
    ap.add_argument("--brand", default=str(ROOT / "brand" / "brand.json"))
    ap.add_argument("--to", nargs="+", help="recipient email(s); without this nothing is emailed")
    ap.add_argument("--send", action="store_true", help="really send; default with --to is a draft")
    ap.add_argument("--subject", help="override the subject from content.json")
    a = ap.parse_args()

    for label, p in (("content", a.content), ("chart spec", a.spec), ("brand", a.brand)):
        if not Path(p).exists():
            sys.exit(f"ERROR: {label} file not found: {p}")

    brand = json.loads(Path(a.brand).read_text(encoding="utf-8"))
    images_dir = TMP / "infographics"
    html_path = TMP / "newsletter.html"

    step(1, "Making infographics (PNG)")
    for spec in json.loads(Path(a.spec).read_text(encoding="utf-8")):
        print("   wrote", make_infographic.draw(spec, brand, images_dir))

    step(2, "Rendering email HTML")
    render_newsletter.render(Path(a.content), html_path, Path(a.brand))

    if not a.to:
        print("\nDone. No email sent (no --to given).")
        print(f"Preview in your browser: {TMP / 'newsletter_preview.html'}")
        return

    # Imported late so build-only runs don't need Google login libraries/token.
    import send_gmail

    step(3, "Sending via Gmail" if a.send else "Saving Gmail draft (not sent)")
    subject = a.subject or json.loads(Path(a.content).read_text(encoding="utf-8"))["subject"]
    html = html_path.read_text(encoding="utf-8")
    msg = send_gmail.build_message(html, subject, a.to, images_dir)
    svc = send_gmail.get_service()
    if a.send:
        r = svc.users().messages().send(userId="me", body=msg).execute()
        print("   Sent:", r["id"], "->", ", ".join(a.to))
    else:
        r = svc.users().drafts().create(userId="me", body={"message": msg}).execute()
        print("   Draft created:", r["id"], "(check Gmail > Drafts)")


if __name__ == "__main__":
    main()
