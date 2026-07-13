"""
Fetch a job posting from a URL and return its visible text.

Uses Playwright so JD pages that render their content with JavaScript (most
modern ATS/job sites) still yield real text. The raw text is handed to the LLM
(`llm.extract_job_description`) for structuring — we deliberately keep the
scraping dumb (grab visible text) and let the model do the parsing.
"""

from __future__ import annotations

from loguru import logger
from playwright.async_api import async_playwright


async def fetch_page_text(
    url: str, headless: bool = True, timeout_ms: int = 45000
) -> str:
    """Load `url` and return the page's visible inner text."""
    logger.info("Fetching JD page: {}", url)
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=headless)
        try:
            page = await browser.new_page()
            await page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
            # Give client-side rendering a moment to settle.
            try:
                await page.wait_for_load_state("networkidle", timeout=8000)
            except Exception:
                pass  # networkidle is best-effort; not all pages reach it.

            # Some JD pages hide the full description behind a "see more" toggle.
            for label in ("See more", "Show more", "Read more"):
                try:
                    btn = page.get_by_role("button", name=label)
                    if await btn.count():
                        await btn.first.click(timeout=2000)
                except Exception:
                    pass

            text = await page.inner_text("body")
            logger.success("Fetched {} characters of page text", len(text))
            return text
        finally:
            await browser.close()
