"""
Generic application-form auto-filler (Playwright).

This drives a real browser to:
  1. Open the job URL and click its "Apply" button.
  2. Walk multi-step forms/modals, filling fields from your config answers.
  3. Upload the tailored resume.
  4. Either stop for human review (default) or click Submit (AUTO_SUBMIT).

Design notes
------------
* Forms vary wildly across ATS vendors, so matching is *heuristic*: each field
  is described by its label / placeholder / name / legend, and matched against
  your `ANSWERS` regex table. This is best-effort by nature — every action is
  logged, and anything it can't answer is escalated to you rather than guessed.
* Nothing here tries to hide that it's automation or defeat bot protection. It
  behaves like a person filling a form, at a person's pace. On sites whose
  terms forbid automated submission (e.g. LinkedIn), don't point it there.
"""
from __future__ import annotations

import asyncio
import random
import re
from typing import List, Optional

from loguru import logger
from playwright.async_api import async_playwright, Page, ElementHandle

from models import ApplicationOutcome

# Button labels we treat as "advance the form" vs "finish".
_NEXT_LABELS = re.compile(r"\b(next|continue|save and continue|review)\b", re.I)
_SUBMIT_LABELS = re.compile(r"\b(submit application|submit|send application|apply now)\b", re.I)
_APPLY_LABELS = re.compile(r"\b(easy apply|apply now|apply for this|apply)\b", re.I)

# JS that computes a human-readable label for a form control.
_LABEL_JS = """
(el) => {
  const bits = [];
  if (el.labels) for (const l of el.labels) bits.push(l.innerText || '');
  const al = el.getAttribute && el.getAttribute('aria-label'); if (al) bits.push(al);
  const alb = el.getAttribute && el.getAttribute('aria-labelledby');
  if (alb) alb.split(/\\s+/).forEach(id => { const n = document.getElementById(id); if (n) bits.push(n.innerText); });
  if (el.placeholder) bits.push(el.placeholder);
  if (el.name) bits.push(el.name);
  const fs = el.closest && el.closest('fieldset');
  if (fs) { const lg = fs.querySelector('legend'); if (lg) bits.push(lg.innerText); }
  return bits.join(' | ').replace(/\\s+/g, ' ').trim();
}
"""


async def human_pause(cfg) -> None:
    await asyncio.sleep(random.uniform(cfg.MIN_ACTION_DELAY, cfg.MAX_ACTION_DELAY))


def _match_answer(label: str, answers: list, want_type: Optional[str] = None) -> Optional[dict]:
    """First answer whose regex matches the label (optionally of a given type)."""
    for a in answers:
        if want_type and a.get("type") != want_type:
            continue
        if re.search(a["match"], label, re.I):
            return a
    return None


async def _visible(handle: ElementHandle) -> bool:
    try:
        return await handle.is_visible()
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Field fillers
# ---------------------------------------------------------------------------
async def _fill_text_and_selects(page: Page, cfg) -> None:
    for handle in await page.query_selector_all("input, textarea, select"):
        if not await _visible(handle):
            continue
        tag = (await handle.evaluate("el => el.tagName.toLowerCase()"))
        input_type = (await handle.evaluate("el => (el.type || '').toLowerCase()")) if tag == "input" else ""
        if input_type in ("radio", "checkbox", "file", "hidden", "submit", "button"):
            continue

        label = await handle.evaluate(_LABEL_JS)
        if not label:
            continue

        if tag == "select":
            ans = _match_answer(label, cfg.ANSWERS, want_type="select")
            if not ans:
                continue
            try:
                await handle.select_option(label=re.compile(ans["value"], re.I))
                logger.info("select  [{}] -> {}", label[:50], ans["value"])
            except Exception:
                # Fall back to first option that contains the value text.
                try:
                    await handle.select_option(label=ans["value"])
                    logger.info("select  [{}] -> {}", label[:50], ans["value"])
                except Exception as e:
                    logger.warning("select  [{}] could not pick '{}': {}", label[:50], ans["value"], e)
        else:  # text / textarea
            ans = _match_answer(label, cfg.ANSWERS, want_type="text")
            if not ans:
                continue
            try:
                current = await handle.input_value()
            except Exception:
                current = ""
            if current.strip():
                continue  # don't clobber pre-filled values (e.g. from a saved profile)
            await handle.fill(str(ans["value"]))
            logger.info("text    [{}] -> {}", label[:50], ans["value"])
        await human_pause(cfg)


async def _fill_radios(page: Page, cfg) -> None:
    # Group radios by `name`; the question is the shared legend/label.
    groups: dict = {}
    for handle in await page.query_selector_all("input[type=radio]"):
        if not await _visible(handle):
            continue
        name = await handle.evaluate("el => el.name || ''")
        groups.setdefault(name, []).append(handle)

    for name, handles in groups.items():
        # Use the first radio's fieldset/legend as the question text.
        question = await handles[0].evaluate(_LABEL_JS)
        ans = _match_answer(question, cfg.ANSWERS, want_type="radio")
        if not ans:
            continue
        wanted = str(ans["value"])
        for h in handles:
            own_label = await h.evaluate(_LABEL_JS)
            if re.search(re.escape(wanted), own_label, re.I):
                try:
                    await h.check()
                    logger.info("radio   [{}] -> {}", question[:50], wanted)
                except Exception as e:
                    logger.warning("radio   [{}] failed: {}", question[:50], e)
                break
        await human_pause(cfg)


async def _fill_checkboxes(page: Page, cfg) -> None:
    for handle in await page.query_selector_all("input[type=checkbox]"):
        if not await _visible(handle):
            continue
        label = await handle.evaluate(_LABEL_JS)
        ans = _match_answer(label, cfg.ANSWERS, want_type="checkbox")
        if ans and ans.get("value"):
            try:
                await handle.check()
                logger.info("check   [{}]", label[:50])
            except Exception as e:
                logger.warning("check   [{}] failed: {}", label[:50], e)


async def _upload_resume(page: Page, resume_path: str, cfg) -> bool:
    uploaded = False
    for handle in await page.query_selector_all("input[type=file]"):
        try:
            await handle.set_input_files(resume_path)
            logger.success("Uploaded resume -> file input")
            uploaded = True
            await human_pause(cfg)
        except Exception as e:
            logger.warning("Resume upload failed on one input: {}", e)
    return uploaded


async def _unanswered_required(page: Page, cfg) -> List[str]:
    """Labels of visible, required fields still left empty after filling."""
    missing: List[str] = []
    for handle in await page.query_selector_all(
        "input[required], select[required], textarea[required], "
        "input[aria-required=true], select[aria-required=true], textarea[aria-required=true]"
    ):
        if not await _visible(handle):
            continue
        input_type = await handle.evaluate("el => (el.type || '').toLowerCase()")
        if input_type in ("file", "hidden", "submit", "button"):
            continue
        try:
            val = await handle.input_value()
        except Exception:
            val = "x"  # selects/radios: assume handled elsewhere
        if not val.strip() and input_type not in ("radio", "checkbox"):
            label = await handle.evaluate(_LABEL_JS)
            missing.append(label or "(unlabelled field)")
    return missing


# ---------------------------------------------------------------------------
# Orchestration for one page/step
# ---------------------------------------------------------------------------
async def _fill_current_step(page: Page, resume_path: str, cfg) -> None:
    await _upload_resume(page, resume_path, cfg)
    await _fill_text_and_selects(page, cfg)
    await _fill_radios(page, cfg)
    await _fill_checkboxes(page, cfg)


async def _click_by_label(page: Page, pattern: re.Pattern) -> bool:
    """Click the first visible, enabled button/link whose text matches."""
    for role in ("button", "link"):
        loc = page.get_by_role(role)
        count = await loc.count()
        for i in range(count):
            item = loc.nth(i)
            try:
                if not await item.is_visible() or not await item.is_enabled():
                    continue
                text = (await item.inner_text()) or (await item.get_attribute("aria-label") or "")
                if pattern.search(text):
                    await item.click()
                    logger.info("Clicked button: '{}'", text.strip()[:40])
                    return True
            except Exception:
                continue
    return False


async def apply_to_job(url: str, resume_path: str, cfg) -> tuple[ApplicationOutcome, str]:
    """Drive a full application. Returns (outcome, detail)."""
    async with async_playwright() as p:
        if cfg.USER_DATA_DIR:
            context = await p.chromium.launch_persistent_context(
                cfg.USER_DATA_DIR, headless=cfg.HEADLESS
            )
            page = context.pages[0] if context.pages else await context.new_page()
            browser = None
        else:
            browser = await p.chromium.launch(headless=cfg.HEADLESS)
            context = await browser.new_context()
            page = await context.new_page()

        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=45000)
            await human_pause(cfg)

            # 1. Open the application form.
            if not await _click_by_label(page, _APPLY_LABELS):
                logger.warning("No 'Apply' button found — the page may already be the form.")
            await human_pause(cfg)

            # 2. Walk up to N steps. Guard against infinite loops.
            for step in range(1, 13):
                logger.info("--- form step {} ---", step)
                await _fill_current_step(page, resume_path, cfg)

                # Bail out to a human if a required field is unanswered.
                missing = await _unanswered_required(page, cfg)
                if missing:
                    detail = "Unanswered required field(s): " + "; ".join(m[:60] for m in missing[:5])
                    logger.warning(detail)
                    if cfg.ON_UNKNOWN_REQUIRED_FIELD == "pause":
                        logger.warning("Pausing for human input. Complete the form, then press Enter here.")
                        await page.screenshot(path="needs_human.png")
                        try:
                            input("Press Enter once you've handled the flagged fields... ")
                        except EOFError:
                            pass
                    else:
                        await page.screenshot(path="needs_human.png")
                        return ApplicationOutcome.NEEDS_HUMAN, detail

                # 3. Submit vs advance.
                can_submit = await _has_button(page, _SUBMIT_LABELS)
                if can_submit:
                    if cfg.AUTO_SUBMIT:
                        await _click_by_label(page, _SUBMIT_LABELS)
                        await human_pause(cfg)
                        logger.success("Submitted application.")
                        await page.screenshot(path="submitted.png")
                        return ApplicationOutcome.SUBMITTED, "submitted"
                    logger.info("AUTO_SUBMIT is off — form filled, stopping for your review.")
                    await page.screenshot(path="ready_to_submit.png")
                    if not cfg.HEADLESS:
                        try:
                            input("Review the form in the browser, then press Enter to close... ")
                        except EOFError:
                            pass
                    return (ApplicationOutcome.FILLED_PENDING_REVIEW,
                            "form filled; awaiting human submit (AUTO_SUBMIT=False)")

                if not await _click_by_label(page, _NEXT_LABELS):
                    logger.warning("No Next/Submit button found — cannot advance.")
                    await page.screenshot(path="stuck.png")
                    return ApplicationOutcome.NEEDS_HUMAN, "could not find a Next/Submit button"
                await human_pause(cfg)

            return ApplicationOutcome.NEEDS_HUMAN, "exceeded step limit without a Submit button"
        except Exception as e:
            logger.exception("Application flow failed")
            try:
                await page.screenshot(path="error.png")
            except Exception:
                pass
            return ApplicationOutcome.FAILED, str(e)
        finally:
            if browser is not None:
                await browser.close()
            else:
                await context.close()


async def _has_button(page: Page, pattern: re.Pattern) -> bool:
    for role in ("button", "link"):
        loc = page.get_by_role(role)
        for i in range(await loc.count()):
            item = loc.nth(i)
            try:
                if await item.is_visible():
                    text = (await item.inner_text()) or (await item.get_attribute("aria-label") or "")
                    if pattern.search(text):
                        return True
            except Exception:
                continue
    return False
