"""
Job-application assistant — orchestrator.

Pipeline for ONE job URL:
    fetch page text -> LLM structures JD -> LLM tailors your resume
    -> render PDF/DOCX -> (optionally) fill & submit the application
    -> append an audit record to the application log.

Usage:
    python main.py "https://boards.greenhouse.io/acme/jobs/12345"
    python main.py "<url>" --tailor-only        # stop after generating the resume
    python main.py "<url>" --submit             # override config to auto-submit

Copy config.example.py -> config.py first and fill in your details.
"""
from __future__ import annotations

import argparse
import asyncio
import sys

from loguru import logger

import config
import jd_fetch
import llm
import resume_render
from models import ApplicationOutcome, ApplicationRecord


def _configure_logging() -> None:
    logger.remove()
    logger.add(sys.stderr, level="INFO",
               format="<green>{time:HH:mm:ss}</green> | <level>{level:<8}</level> | {message}")
    logger.add("run.log", level="DEBUG", rotation="5 MB", retention=5)


def _load_baseline() -> str:
    with open(config.BASELINE_RESUME_PATH, "r", encoding="utf-8") as fh:
        text = fh.read().strip()
    if not text:
        raise SystemExit(f"Baseline resume at {config.BASELINE_RESUME_PATH} is empty.")
    return text


def _log_record(record: ApplicationRecord) -> None:
    with open(config.APPLICATION_LOG, "a", encoding="utf-8") as fh:
        fh.write(record.model_dump_json() + "\n")
    logger.info("Logged application record: {} -> {}", record.company, record.outcome.value)


async def run(url: str, tailor_only: bool, force_submit: bool) -> None:
    baseline = _load_baseline()

    # 1. Fetch + structure the job description.
    page_text = await jd_fetch.fetch_page_text(url, headless=config.HEADLESS)
    jd = llm.extract_job_description(url, page_text, model=config.LLM_MODEL)

    # 2. Tailor the resume (truthfully) to this JD.
    resume = llm.tailor_resume(
        baseline, jd, model=config.LLM_MODEL, temperature=config.LLM_TEMPERATURE
    )
    if resume.change_notes:
        for note in resume.change_notes:
            logger.info("tailoring note: {}", note)

    # 3. Render to disk.
    paths = resume_render.render(resume, jd, config.OUTPUT_DIR, config.RESUME_FORMATS)
    primary_resume = paths[0]  # PDF first when present — best for uploads.

    if tailor_only:
        _log_record(ApplicationRecord(
            url=url, company=jd.company, title=jd.title,
            resume_path=primary_resume, outcome=ApplicationOutcome.TAILORED,
            detail="tailor-only mode",
        ))
        logger.success("Done (tailor-only). Resume(s): {}", ", ".join(paths))
        return

    # 4. Fill & (optionally) submit the application.
    if force_submit:
        config.AUTO_SUBMIT = True
        logger.warning("--submit passed: AUTO_SUBMIT overridden to True for this run.")

    import form_filler  # imported here so tailor-only runs need no browser deps loaded
    outcome, detail = await form_filler.apply_to_job(url, primary_resume, config)

    _log_record(ApplicationRecord(
        url=url, company=jd.company, title=jd.title,
        resume_path=primary_resume, outcome=outcome, detail=detail,
    ))
    logger.success("Finished: {} ({})", outcome.value, detail)


def main() -> None:
    parser = argparse.ArgumentParser(description="Tailor a resume to a JD and fill the application.")
    parser.add_argument("url", help="URL of the job posting / application page")
    parser.add_argument("--tailor-only", action="store_true",
                        help="Generate the tailored resume only; don't touch the application form.")
    parser.add_argument("--submit", action="store_true",
                        help="Override config and auto-click Submit (use deliberately).")
    args = parser.parse_args()

    _configure_logging()
    try:
        asyncio.run(run(args.url, args.tailor_only, args.submit))
    except KeyboardInterrupt:
        logger.warning("Interrupted by user.")


if __name__ == "__main__":
    main()
