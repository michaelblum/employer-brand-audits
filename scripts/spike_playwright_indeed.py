"""
Spike: Playwright (Python) capture test against Indeed.com

Tests whether Playwright driving system Chrome can reach Indeed's company
reviews pages without triggering bot detection. Saves screenshots to disk
for human evaluation — Claude does not evaluate the pixels.

Run from repo root:
    source mcp-server/.venv/bin/activate
    python scripts/spike_playwright_indeed.py

Two modes:
    --fresh   Launch system Chrome with a fresh profile (default)
              Tests Playwright's own process driving Chrome
    --cdp     Connect to an already-running Chrome via CDP
              Requires Chrome launched with: --remote-debugging-port=9222
              Tests real profile / real sessions (closest to Claude in Chrome)

Output: /tmp/playwright-indeed-spike/  (three screenshots, one per step)
"""

import argparse
import asyncio
import sys
from pathlib import Path

from playwright.async_api import async_playwright

CHROME_PATH = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
OUT_DIR = Path("/tmp/playwright-indeed-spike")
CDP_URL = "http://localhost:9222"


async def run(mode: str) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    async with async_playwright() as pw:
        if mode == "cdp":
            print(f"Connecting to Chrome via CDP at {CDP_URL} ...")
            browser = await pw.chromium.connect_over_cdp(CDP_URL)
            # Use the first existing context (real profile, real sessions)
            context = browser.contexts[0] if browser.contexts else await browser.new_context()
            page = await context.new_page()
        else:
            print("Launching system Chrome with fresh profile ...")
            browser = await pw.chromium.launch(
                executable_path=CHROME_PATH,
                headless=False,
                slow_mo=400,
            )
            context = await browser.new_context(
                viewport={"width": 1280, "height": 900},
            )
            page = await context.new_page()

        # Step 1: Homepage
        print("Navigating to Indeed...")
        await page.goto("https://www.indeed.com", wait_until="domcontentloaded", timeout=30_000)
        await page.screenshot(path=str(OUT_DIR / "01-homepage.png"))
        print(f"  URL:   {page.url}")
        print(f"  Title: {await page.title()}")

        # Step 2: Search
        print("Searching for Microsoft...")
        try:
            await page.fill('input[name="q"], input[id="text-input-what"]', "Microsoft", timeout=5_000)
            await page.keyboard.press("Enter")
            await page.wait_for_load_state("domcontentloaded", timeout=15_000)
        except Exception as e:
            print(f"  Search fill failed: {e}")
        await page.screenshot(path=str(OUT_DIR / "02-search.png"))
        print(f"  URL:   {page.url}")

        # Step 3: Reviews page
        print("Navigating to Microsoft reviews...")
        await page.goto(
            "https://www.indeed.com/cmp/Microsoft/reviews",
            wait_until="domcontentloaded",
            timeout=30_000,
        )
        await page.screenshot(path=str(OUT_DIR / "03-reviews.png"))
        print(f"  URL:   {page.url}")
        print(f"  Title: {await page.title()}")

        print(f"\nDone. Evaluate screenshots in {OUT_DIR}")
        print("  01-homepage.png  — did Indeed load?")
        print("  02-search.png    — did search work?")
        print("  03-reviews.png   — blocked (bot challenge) or real reviews?")

        if mode != "cdp":
            await browser.close()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--cdp", action="store_true", help="Connect to real Chrome via CDP instead of launching fresh")
    args = parser.parse_args()
    asyncio.run(run("cdp" if args.cdp else "fresh"))


if __name__ == "__main__":
    main()
