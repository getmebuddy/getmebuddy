"""
Typed data models for the job-application assistant.

Everything that crosses a module boundary is a Pydantic model so we get
validation "for free" and a single source of truth for the shapes of data
flowing between the JD fetcher, the LLM tailoring engine, the renderer, and
the form filler.
"""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Job description
# ---------------------------------------------------------------------------
class JobDescription(BaseModel):
    """A single job posting, parsed from the URL the user supplies."""

    url: str
    title: str = "Unknown Title"
    company: str = "Unknown Company"
    location: Optional[str] = None
    # The full, cleaned job-description text used to tailor the resume.
    description: str = ""

    def safe_slug(self) -> str:
        """Filesystem-safe `Company_Title` fragment for output filenames."""
        raw = f"{self.company}_{self.title}"
        keep = [c if (c.isalnum() or c in " -_") else "_" for c in raw]
        slug = "".join(keep).strip().replace(" ", "_")
        # Collapse runs of underscores and cap length.
        while "__" in slug:
            slug = slug.replace("__", "_")
        return slug[:80] or "job"


# ---------------------------------------------------------------------------
# Tailored resume (structured — rendered deterministically to PDF/DOCX)
# ---------------------------------------------------------------------------
class ResumeEntry(BaseModel):
    """One role/project/education line item within a section."""

    heading: str = ""            # e.g. "Senior Backend Engineer"
    subheading: str = ""         # e.g. "Acme Corp"
    date_range: str = ""         # e.g. "2021 – Present"
    bullets: List[str] = Field(default_factory=list)


class ResumeSection(BaseModel):
    """A resume section, e.g. Experience / Projects / Education / Skills."""

    title: str
    entries: List[ResumeEntry] = Field(default_factory=list)
    # For flat sections like "Skills" that are just lines, not entries.
    lines: List[str] = Field(default_factory=list)


class TailoredResume(BaseModel):
    """The LLM's tailored resume — structured so rendering is deterministic."""

    name: str
    contact_line: str = ""       # "email · phone · city · linkedin"
    summary: str = ""            # rewritten professional summary
    sections: List[ResumeSection] = Field(default_factory=list)

    # Transparency: what the model keyed on and changed. Purely informational,
    # surfaced in logs so a human can sanity-check the tailoring.
    matched_keywords: List[str] = Field(default_factory=list)
    change_notes: List[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Application status / audit record
# ---------------------------------------------------------------------------
class ApplicationOutcome(str, Enum):
    TAILORED = "tailored"                 # resume generated, not yet applied
    FILLED_PENDING_REVIEW = "filled_pending_review"  # form filled, waiting on human submit
    SUBMITTED = "submitted"               # application submitted
    NEEDS_HUMAN = "needs_human"           # unanswered/unknown field — paused
    SKIPPED = "skipped"
    FAILED = "failed"


class ApplicationRecord(BaseModel):
    """One row in the append-only application log."""

    timestamp: datetime = Field(default_factory=datetime.utcnow)
    url: str
    company: str = ""
    title: str = ""
    resume_path: Optional[str] = None
    outcome: ApplicationOutcome
    detail: str = ""             # human-readable note (error, unanswered field, ...)
