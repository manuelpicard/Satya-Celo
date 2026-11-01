#!/usr/bin/env python3
"""Record the real Satya preview UI; no generated or mocked product screens."""
from __future__ import annotations

import asyncio
import os
from pathlib import Path
from playwright.async_api import async_playwright

URL = os.environ.get(
    "SATYA_DEMO_URL",
    "https://3000-ik0hj4pg1fxauwdkyapdp-ca9f6603.sg2.manus.computer/",
)
OUT = Path(os.environ.get("SATYA_DEMO_DIR", Path(__file__).resolve().parents[1] / "demo-video"))
RAW = OUT / "raw"

async def main() -> None:
    RAW.mkdir(parents=True, exist_ok=True)
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            executable_path=os.environ.get("CHROMIUM_PATH", "/usr/bin/chromium"),
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"],
        )
        context = await browser.new_context(
            viewport={"width": 1280, "height": 720},
            device_scale_factor=1,
            record_video_dir=str(RAW),
            record_video_size={"width": 1280, "height": 720},
        )
        page = await context.new_page()
        await page.goto(URL, wait_until="domcontentloaded", timeout=45_000)
        await page.locator("h1").wait_for(timeout=20_000)
        await page.wait_for_timeout(1_500)
        await page.get_by_role("button", name="Beispiel laden").click()
        await page.evaluate("window.scrollTo({ top: 0, behavior: 'instant' })")
        await page.locator(".verdict").wait_for(timeout=25_000)
        await page.locator(".result-card").scroll_into_view_if_needed()
        await page.wait_for_timeout(4_000)
        await page.screenshot(path=str(OUT / "register-result.png"), full_page=True)
        await page.locator(".feature-row").scroll_into_view_if_needed()
        await page.wait_for_timeout(1_200)
        await page.get_by_role("button", name="Preis unverbindlich anzeigen").click()
        await page.get_by_text("ZAHLUNGSANFORDERUNG").wait_for(timeout=20_000)
        await page.locator(".quote-box").scroll_into_view_if_needed()
        await page.wait_for_timeout(4_000)
        await page.screenshot(path=str(OUT / "x402-quote.png"), full_page=True)
        await context.close()
        await browser.close()

    recordings = sorted(RAW.glob("*.webm"), key=lambda f: f.stat().st_mtime, reverse=True)
    if not recordings:
        raise RuntimeError("Playwright hat keine WebM-Aufnahme erstellt.")
    target = OUT / "satya-demo-raw.webm"
    recordings[0].replace(target)
    print(f"Recorded real UI: {target}")

if __name__ == "__main__":
    asyncio.run(main())
