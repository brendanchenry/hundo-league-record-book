#!/usr/bin/env python3
"""Render dist/index.html to PNG screenshots for quick visual QA.

Wraps the artifact body (which has no <html>/<head>/<body> of its own, since
claude.ai adds those at publish time) in a minimal page skeleton, then uses
headless Chrome to screenshot it in dark, light, and mobile.

Usage:
    python scripts/preview.py            # all three
    python scripts/preview.py dark       # just one

Screenshots land in scripts/_shots/. Requires Google Chrome installed.
"""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DIST = ROOT / "dist" / "index.html"
SHOTS = ROOT / "scripts" / "_shots"

CHROME_CANDIDATES = [
    r"C:/Program Files/Google/Chrome/Application/chrome.exe",
    r"C:/Program Files (x86)/Google/Chrome/Application/chrome.exe",
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "google-chrome", "chromium",
]

VIEWS = {
    "dark":  ("dark",  1180, 4600),
    "light": ("light", 1180, 4600),
    "mobile":("dark",  430,  5200),
}


def find_chrome() -> str:
    for c in CHROME_CANDIDATES:
        if Path(c).exists() or "/" not in c:
            return c
    raise SystemExit("Chrome not found; edit CHROME_CANDIDATES in scripts/preview.py")


def wrap(theme: str) -> str:
    body = DIST.read_text(encoding="utf-8")
    # Force scroll-reveal + count-up into their final state so a static capture
    # shows real content (these animate on a live scroll).
    force = (
        "<style>*{transition:none!important;animation:none!important}"
        ".reveal{opacity:1!important;transform:none!important}"
        # Tabs hide all but the active group; unhide everything for a full-page shot.
        ".chapter[hidden]{display:block!important}.tabs{display:none!important}</style>"
        "<script>window.addEventListener('load',()=>{setTimeout(()=>{"
        "document.querySelectorAll('.reveal').forEach(e=>e.classList.add('in'));"
        "document.querySelectorAll('.bar-fill').forEach(f=>f.style.width=f.dataset.w+'%');"
        "document.querySelectorAll('.hstat .v').forEach(n=>n.textContent=(+n.dataset.count).toLocaleString());"
        "document.querySelectorAll('.sb .fill').forEach(f=>f.style.height=f.dataset.h+'%');"
        "},100);});</script>")
    return (f'<!doctype html><html data-theme="{theme}"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1">'
            '<style>*{margin:0}img{max-width:100%}</style></head><body>'
            f'{body}{force}</body></html>')


def main() -> None:
    SHOTS.mkdir(exist_ok=True)
    chrome = find_chrome()
    wanted = sys.argv[1:] or list(VIEWS)
    for name in wanted:
        theme, w, h = VIEWS[name]
        page = SHOTS / f"_wrap-{name}.html"
        page.write_text(wrap(theme), encoding="utf-8")
        out = SHOTS / f"{name}.png"
        subprocess.run([chrome, "--headless", "--disable-gpu", "--hide-scrollbars",
                        "--virtual-time-budget=2000", f"--window-size={w},{h}",
                        f"--screenshot={out}", str(page)],
                       check=False, stderr=subprocess.DEVNULL)
        print(f"  {name:6} -> {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
