"""Render report diagrams (HTML -> PNG) and report documents (HTML -> PDF) with headless Chrome/Edge.

Each diagram HTML declares its canvas as <meta name="size" content="WIDTHxHEIGHT"> and its output
as <meta name="out" content="week0X_.../NAME.png">. Report HTMLs declare <meta name="pdf" content="...">.

Run from repo root: python docs/weekly_reports/_build/render.py
"""
import re
import shutil
import subprocess
from pathlib import Path

BUILD = Path(__file__).resolve().parent
REPORTS = BUILD.parent
CANDIDATES = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    "google-chrome", "chromium", "chrome",
]


def browser() -> str:
    for c in CANDIDATES:
        if Path(c).exists() or shutil.which(c):
            return c
    raise SystemExit("No Chrome/Edge found for headless rendering")


def meta(html: str, name: str):
    m = re.search(rf'<meta name="{name}" content="([^"]+)"', html)
    return m.group(1) if m else None


def main() -> None:
    exe = browser()
    for src in sorted((BUILD / "diagrams").glob("*.html")) + sorted(BUILD.glob("*.html")):
        html = src.read_text(encoding="utf-8")
        url = src.resolve().as_uri()
        common = [exe, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--no-first-run",
                  "--allow-file-access-from-files"]
        if out := meta(html, "out"):
            w, h = meta(html, "size").split("x")
            dest = REPORTS / out
            subprocess.run(common + ["--force-device-scale-factor=2", f"--window-size={w},{h}",
                                     f"--screenshot={dest}", url], check=True, capture_output=True)
            print("png ", dest.relative_to(REPORTS))
        elif out := meta(html, "pdf"):
            dest = REPORTS / out
            subprocess.run(common + ["--no-pdf-header-footer", f"--print-to-pdf={dest}", url],
                           check=True, capture_output=True)
            print("pdf ", dest.relative_to(REPORTS))


if __name__ == "__main__":
    main()
