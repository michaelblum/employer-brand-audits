"""
Spike: HITL (human-in-the-loop) capture gate with persistent Chrome profile.

Tests whether a dedicated persistent profile accumulates enough session state
to reduce bot challenges over time, with a human-solvable pause when challenged.

Two subcommands:

    start --url <url>
        Launch Chrome with the plugin profile if not already running.
        Navigate to <url>, detect challenges, capture screenshot on success.

    retry
        Reconnect to the already-running Chrome, retry the last URL.
        Use after solving a challenge manually in the browser.

Profile lives at: <repo>/chrome-profile/  (gitignored)
State file:       /tmp/playwright-hitl-spike/state.json
Screenshots:      /tmp/playwright-hitl-spike/

Run from repo root:
    source mcp-server/.venv/bin/activate
    python scripts/spike_hitl_capture.py start --url https://www.indeed.com/cmp/Microsoft/reviews
    # ...solve any challenge in the browser...
    python scripts/spike_hitl_capture.py retry
"""

import argparse
import asyncio
import json
import subprocess
import sys
import urllib.request
from datetime import datetime
from pathlib import Path

from playwright.async_api import async_playwright

CHROME_PATH = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
REPO_ROOT = Path(__file__).parent.parent
PROFILE_DIR = REPO_ROOT / "chrome-profile"
CDP_URL = "http://localhost:9222"
OUT_DIR = Path("/tmp/playwright-hitl-spike")
STATE_FILE = OUT_DIR / "state.json"

CHALLENGE_TITLES = [
    "just a moment",
    "attention required",
    "checking your browser",
    "please verify",
    "access denied",
    "security check",
    "are you human",
    "ddos-guard",
]

CHALLENGE_URL_PATTERNS = [
    "__cf_chl",
    "/challenge/",
    "cf_challenge",
    "captcha",
]

LOGIN_PATTERNS = ["/login", "/signin", "/sign-in", "/auth/", "/account/login"]


def save_state(url: str, status: str, screenshot: str | None = None) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps({
        "url": url,
        "status": status,
        "screenshot": screenshot,
        "timestamp": datetime.now().isoformat(),
    }, indent=2))


def load_state() -> dict:
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {}


def chrome_is_running() -> bool:
    try:
        urllib.request.urlopen(f"{CDP_URL}/json/version", timeout=1)
        return True
    except Exception:
        return False


def launch_chrome() -> None:
    print(f"Launching Chrome with plugin profile at {PROFILE_DIR} ...")
    PROFILE_DIR.mkdir(parents=True, exist_ok=True)
    subprocess.Popen(
        [
            CHROME_PATH,
            f"--user-data-dir={PROFILE_DIR}",
            "--remote-debugging-port=9222",
            "--no-first-run",
            "--no-default-browser-check",
            "--disable-default-apps",
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


async def wait_for_chrome(timeout: int = 10) -> bool:
    for _ in range(timeout * 2):
        if chrome_is_running():
            return True
        await asyncio.sleep(0.5)
    return False


async def detect_challenge(page) -> tuple[bool, str]:
    title = (await page.title()).lower()
    url = page.url

    for pattern in CHALLENGE_TITLES:
        if pattern in title:
            return True, f"title: '{await page.title()}'"

    for pattern in CHALLENGE_URL_PATTERNS:
        if pattern in url:
            return True, f"URL pattern '{pattern}' in {url}"

    captcha_count = await page.locator(
        'iframe[src*="hcaptcha"], iframe[src*="recaptcha"], iframe[title*="challenge"]'
    ).count()
    if captcha_count > 0:
        return True, "CAPTCHA iframe present"

    return False, ""


def is_unexpected_login(target_url: str, current_url: str) -> bool:
    if any(p in current_url for p in LOGIN_PATTERNS):
        if not any(p in target_url for p in LOGIN_PATTERNS):
            return True
    return False


async def capture(url: str) -> None:
    async with async_playwright() as pw:
        print(f"Connecting to Chrome via CDP ...")
        browser = await pw.chromium.connect_over_cdp(CDP_URL)
        context = browser.contexts[0] if browser.contexts else await browser.new_context()
        page = await context.new_page()

        print(f"Navigating to {url} ...")
        await page.goto(url, wait_until="domcontentloaded", timeout=30_000)
        await page.wait_for_timeout(1500)

        current_url = page.url
        title = await page.title()
        print(f"  URL:   {current_url}")
        print(f"  Title: {title}")

        # Check for unexpected login redirect
        if is_unexpected_login(url, current_url):
            print(f"\n⚠️  Login redirect detected — not signed in.")
            print(f"   Sign in at the browser window, then reply 'ready' to retry.\n")
            save_state(url, "login_redirect")
            return

        # Check for bot challenge
        challenged, reason = await detect_challenge(page)
        if challenged:
            print(f"\n⚠️  Challenge detected ({reason}).")
            print(f"   Solve it in the browser window, then reply 'ready' to retry.\n")
            save_state(url, "challenged")
            return

        # Success — capture screenshot
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        screenshot_path = str(OUT_DIR / f"capture_{ts}.png")
        await page.screenshot(path=screenshot_path, full_page=False)
        save_state(url, "success", screenshot_path)

        print(f"\n✓  No challenge detected.")
        print(f"   Screenshot saved: {screenshot_path}")
        print(f"   Evaluate the pixels yourself — open {screenshot_path}\n")


async def cmd_start(url: str) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    if chrome_is_running():
        print("Chrome already running on port 9222 — reusing existing session.")
    else:
        launch_chrome()
        print("Waiting for Chrome to be ready ...")
        if not await wait_for_chrome():
            print("ERROR: Chrome did not start in time.")
            sys.exit(1)
        print("Chrome ready.")

    await capture(url)


async def cmd_retry() -> None:
    state = load_state()
    if not state:
        print("No state file found. Run 'start' first.")
        sys.exit(1)

    url = state["url"]
    prev_status = state["status"]
    print(f"Retrying {url} (previous status: {prev_status}) ...")

    if not chrome_is_running():
        print("ERROR: Chrome is not running. Launch it with 'start' first.")
        sys.exit(1)

    await capture(url)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="cmd")

    p_start = sub.add_parser("start", help="Launch Chrome and attempt capture")
    p_start.add_argument("--url", required=True, help="URL to capture")

    sub.add_parser("retry", help="Reconnect and retry last URL after solving challenge")

    args = parser.parse_args()

    if args.cmd == "start":
        asyncio.run(cmd_start(args.url))
    elif args.cmd == "retry":
        asyncio.run(cmd_retry())
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
