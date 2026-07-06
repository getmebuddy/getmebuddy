# Job Application Assistant

Given the **URL of a single job posting** and your **baseline resume**, this
tool:

1. Loads the posting and extracts the job description.
2. Uses an LLM to **tailor your resume** to that JD — reshaping your summary and
   bullets to surface relevant *real* experience and keywords for ATS, under a
   hard truthfulness constraint (**it never invents skills or experience**).
3. Renders a clean **PDF/DOCX** to `output_resumes/Resume_Company_Title.pdf`.
4. Opens the application page, **fills the form** from your saved answers, and
   uploads the tailored resume.
5. Appends an **audit record** to `application_log.jsonl`.

## Scope & ground rules (read this)

- **Review-before-submit by default.** The form is filled but *not* submitted
  until you flip `AUTO_SUBMIT` on (or pass `--submit`). Treat auto-submit like a
  live deploy — turn it on deliberately, one application at a time.
- **Use it on company/ATS application pages** — Greenhouse, Lever, Ashby,
  Workday, and similar. It works on standard web forms.
- **Do not point it at LinkedIn Easy Apply.** Automating submissions on LinkedIn
  violates their User Agreement and is the classic way to get your account
  restricted. The tool makes no attempt to defeat bot detection, and you
  shouldn't want it to.
- It's a *heuristic* form filler — forms vary, so it logs everything and
  **escalates any field it can't confidently answer to you** rather than
  guessing.

## Architecture

| Module | Responsibility |
| --- | --- |
| `models.py` | Pydantic models: `JobDescription`, `TailoredResume`, `ApplicationRecord` |
| `jd_fetch.py` | Load the JD page with Playwright, return visible text |
| `llm.py` | litellm calls: structure the JD, tailor the resume (swappable model) |
| `resume_render.py` | Deterministic PDF (reportlab) / DOCX (python-docx) render |
| `form_filler.py` | Playwright: click Apply, fill/upload, review or submit |
| `main.py` | Orchestrates the pipeline + loguru logging |
| `config.py` | Your credentials-free config: answers, model, formats (git-ignored) |

## Prerequisites & setup

- Python 3.10+
- An API key for your chosen LLM provider (OpenAI / Anthropic / Gemini).

```bash
cd job_apply_assistant
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium          # one-time browser download

# Your personal files (both git-ignored):
cp config.example.py config.py                 # edit answers, model, formats
cp baseline_resume.example.md baseline_resume.md   # paste in your real resume
```

Set your API key in the environment (a `.env` in this folder is auto-loaded if
you `source` it, or export directly):

```bash
export ANTHROPIC_API_KEY=sk-...      # or OPENAI_API_KEY / GEMINI_API_KEY
```

The model is chosen in `config.py` (`LLM_MODEL`) — litellm routes to the right
provider, so swapping models is a one-line change.

## Running it

```bash
# 1. Just tailor the resume — no browser form-filling:
python main.py "https://boards.greenhouse.io/acme/jobs/12345" --tailor-only

# 2. Tailor + fill the form, then stop for your review (default, safe):
python main.py "https://boards.greenhouse.io/acme/jobs/12345"

# 3. Tailor + fill + auto-submit (only when you mean it):
python main.py "https://boards.greenhouse.io/acme/jobs/12345" --submit
```

When a field can't be matched to your `ANSWERS`, the tool (per
`ON_UNKNOWN_REQUIRED_FIELD`) either pauses so you can finish that field by hand,
or aborts and logs `needs_human`. Screenshots (`ready_to_submit.png`,
`needs_human.png`, `error.png`) are saved to help you see where it stopped.

## Configuring your answers

`config.py` holds a `CONTACT` dict and an `ANSWERS` table. Each answer matches a
form field by regex against its label/placeholder/name and supplies a value of
type `text`, `select`, `radio`, or `checkbox`. Add rows for questions specific
to the roles you apply to — first match wins, so put specific patterns first.

## The truthfulness constraint

The tailoring system prompt (`llm.py`) forbids the model from adding any skill,
tool, employer, title, date, or achievement not present in your baseline
resume. It only re-emphasises and rephrases what's genuinely there. Review the
generated resume before sending — `matched_keywords` and `change_notes` in the
logs show what it keyed on.
