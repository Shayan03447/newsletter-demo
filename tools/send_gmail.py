"""Send the rendered newsletter through the Gmail API with inline (CID) images.

First run opens a browser for OAuth consent and saves token.json.

Usage:
  python tools/send_gmail.py --to you@example.com --content .tmp/content.json            # send
  python tools/send_gmail.py --to you@example.com --content .tmp/content.json --draft    # save as Gmail draft
  python tools/send_gmail.py --auth-only                                                   # just authorize

Recipients: pass several with --to a@x.com b@x.com. They go in Bcc so addresses stay private.
Always do a test send to yourself before a real send.
"""
import argparse
import base64
import json
import re
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

ROOT = Path(__file__).resolve().parent.parent
SCOPES = ["https://www.googleapis.com/auth/gmail.compose"]  # create drafts + send only


def get_service():
    token_path, cred_path = ROOT / "token.json", ROOT / "credentials.json"
    creds = None
    if token_path.exists():
        creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not cred_path.exists():
                raise SystemExit("credentials.json not found in project root. See workflow/setup notes.")
            creds = InstalledAppFlow.from_client_secrets_file(str(cred_path), SCOPES).run_local_server(port=0)
        token_path.write_text(creds.to_json())
    return build("gmail", "v1", credentials=creds)


def html_to_text(html: str) -> str:
    t = re.sub(r"(?is)<(style|head|script).*?</\1>", "", html)
    t = re.sub(r"(?i)<br\s*/?>|</p>|</tr>|</h\d>", "\n", t)
    t = re.sub(r"<[^>]+>", "", t)
    t = re.sub(r"&middot;", "·", t)
    return re.sub(r"\n\s*\n+", "\n\n", t).strip()


def build_message(html, subject, to_list, images_dir: Path, sender="me"):
    root = MIMEMultipart("related")
    root["To"] = sender if len(to_list) > 1 else to_list[0]
    if len(to_list) > 1:
        root["Bcc"] = ", ".join(to_list)
    root["Subject"] = subject

    alt = MIMEMultipart("alternative")
    alt.attach(MIMEText(html_to_text(html), "plain", "utf-8"))
    alt.attach(MIMEText(html, "html", "utf-8"))
    root.attach(alt)

    for cid in sorted(set(re.findall(r'src="cid:([^"]+)"', html))):
        png = images_dir / f"{cid}.png"
        if not png.exists():
            raise SystemExit(f"Missing image for cid:{cid} -> {png}")
        img = MIMEImage(png.read_bytes(), _subtype="png")
        img.add_header("Content-ID", f"<{cid}>")
        img.add_header("Content-Disposition", "inline", filename=png.name)
        root.attach(img)
    return {"raw": base64.urlsafe_b64encode(root.as_bytes()).decode()}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--to", nargs="+")
    ap.add_argument("--content", default=str(ROOT / ".tmp" / "content.json"))
    ap.add_argument("--html", default=str(ROOT / ".tmp" / "newsletter.html"))
    ap.add_argument("--images", default=str(ROOT / ".tmp" / "infographics"))
    ap.add_argument("--subject")
    ap.add_argument("--draft", action="store_true")
    ap.add_argument("--auth-only", action="store_true")
    a = ap.parse_args()

    svc = get_service()
    if a.auth_only:
        print("Authorized. token.json saved.")
        raise SystemExit(0)
    if not a.to:
        raise SystemExit("--to required")

    subject = a.subject or json.loads(Path(a.content).read_text(encoding="utf-8"))["subject"]
    html = Path(a.html).read_text(encoding="utf-8")
    msg = build_message(html, subject, a.to, Path(a.images))
    if a.draft:
        r = svc.users().drafts().create(userId="me", body={"message": msg}).execute()
        print("Draft created:", r["id"])
    else:
        r = svc.users().messages().send(userId="me", body=msg).execute()
        print("Sent:", r["id"], "->", ", ".join(a.to))
