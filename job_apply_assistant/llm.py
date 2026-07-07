"""
LLM tailoring engine.

Two responsibilities, both via litellm so the model is swappable from config:

1. `extract_job_description` — turn scraped page text into a structured
   JobDescription (title / company / location / clean description).
2. `tailor_resume` — reshape the baseline resume to a specific JD, under a
   hard truthfulness constraint, returning a structured TailoredResume.

Both call the model in JSON mode and validate the result with Pydantic, so a
malformed model response fails loudly instead of silently corrupting a resume.
"""

from __future__ import annotations

import json

import litellm
from loguru import logger
from models import JobDescription, TailoredResume
from tenacity import retry, stop_after_attempt, wait_exponential

# Keep litellm quiet unless something's wrong; we do our own logging.
litellm.suppress_debug_info = True


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=2, min=2, max=20))
def _complete_json(model: str, system: str, user: str, temperature: float) -> dict:
    """Call the model and parse a JSON object from the reply.

    Retries with backoff on transient API errors *and* on unparseable output.
    """
    resp = litellm.completion(
        model=model,
        temperature=temperature,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        # Most providers honour this; harmless where unsupported.
        response_format={"type": "json_object"},
    )
    content = resp["choices"][0]["message"]["content"]
    return json.loads(content)


# ---------------------------------------------------------------------------
# 1. Job-description extraction
# ---------------------------------------------------------------------------
_EXTRACT_SYSTEM = """You extract structured job-posting data from raw web page text.
Return ONLY a JSON object with keys: title, company, location, description.
- title:       the job title
- company:     the hiring company
- location:    city/region or "Remote" if stated, else null
- description: the full role description, responsibilities, and requirements as
               clean plain text. Strip site navigation, cookie banners, and
               "similar jobs" clutter. Do not summarise — keep the real content.
If a field is genuinely absent, use null (or "Unknown ...").
"""


def extract_job_description(
    url: str, page_text: str, model: str, temperature: float = 0.0
) -> JobDescription:
    logger.info(
        "Extracting structured JD via LLM ({} chars of page text)", len(page_text)
    )
    data = _complete_json(
        model=model,
        system=_EXTRACT_SYSTEM,
        user=f"PAGE URL: {url}\n\nPAGE TEXT:\n{page_text[:20000]}",
        temperature=temperature,
    )
    jd = JobDescription(
        url=url,
        title=data.get("title") or "Unknown Title",
        company=data.get("company") or "Unknown Company",
        location=data.get("location"),
        description=data.get("description") or page_text[:8000],
    )
    logger.success("Parsed JD: {} @ {}", jd.title, jd.company)
    return jd


# ---------------------------------------------------------------------------
# 2. Resume tailoring
# ---------------------------------------------------------------------------
_TAILOR_SYSTEM = """You are an expert resume editor specialising in ATS optimisation.

You are given a candidate's BASELINE resume and a target JOB DESCRIPTION.
Your job is to re-shape the baseline resume so it speaks directly to this role.

ABSOLUTE RULES — these override everything else:
1. TRUTHFULNESS. You may ONLY use skills, tools, employers, titles, dates, and
   achievements that appear in the baseline resume. NEVER invent, add, or imply
   experience, seniority, metrics, or skills that are not already present.
   Rephrasing and re-emphasising real content is fine; fabricating is not.
2. If the job asks for something the candidate does not have, do NOT claim it.
   Simply emphasise the most relevant genuine experience instead.

WHAT TO DO:
- Rewrite the professional summary to foreground the candidate's genuine
  experience most relevant to this role.
- Reorder and rephrase bullet points to surface relevant real achievements and
  to naturally include keywords/tools from the JD *that the candidate actually
  has*. Prefer strong action verbs and quantified results already present.
- Keep every real employer, title, and date exactly as in the baseline.

OUTPUT: return ONLY a JSON object with this schema:
{
  "name": "<candidate name>",
  "contact_line": "<one line: email · phone · city · linkedin — from baseline>",
  "summary": "<rewritten professional summary, 2-4 sentences>",
  "sections": [
    {
      "title": "Experience",
      "entries": [
        {"heading": "<title>", "subheading": "<company>",
         "date_range": "<dates>", "bullets": ["<bullet>", "..."]}
      ],
      "lines": []
    },
    {
      "title": "Skills",
      "entries": [],
      "lines": ["<skill line>", "..."]
    }
  ],
  "matched_keywords": ["<JD keyword the candidate genuinely has>", "..."],
  "change_notes": ["<short note on what you re-emphasised and why>", "..."]
}
Preserve all real sections from the baseline (Experience, Projects, Education,
Skills, Certifications, ...). Use "entries" for role-style sections and "lines"
for flat lists like Skills.
"""


def tailor_resume(
    baseline_markdown: str,
    jd: JobDescription,
    model: str,
    temperature: float = 0.3,
) -> TailoredResume:
    logger.info("Tailoring resume for {} @ {}", jd.title, jd.company)
    user = (
        f"=== BASELINE RESUME (the ONLY source of truth for facts) ===\n"
        f"{baseline_markdown}\n\n"
        f"=== TARGET JOB DESCRIPTION ===\n"
        f"Title: {jd.title}\nCompany: {jd.company}\nLocation: {jd.location}\n\n"
        f"{jd.description}"
    )
    data = _complete_json(
        model=model, system=_TAILOR_SYSTEM, user=user, temperature=temperature
    )
    resume = TailoredResume.model_validate(data)
    logger.success(
        "Tailored resume ready — {} sections, {} matched keywords",
        len(resume.sections),
        len(resume.matched_keywords),
    )
    if resume.matched_keywords:
        logger.info("Keywords surfaced: {}", ", ".join(resume.matched_keywords[:15]))
    return resume
