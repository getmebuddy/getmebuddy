"""
Configuration template.

Copy this file to `config.py` and fill in your details:

    cp config.example.py config.py

`config.py` is git-ignored so your personal data and answers never get
committed. API keys are read from the environment (see .env), NOT hard-coded
here.
"""

import os

# ---------------------------------------------------------------------------
# LLM — swappable via litellm. Just change the model string.
#   OpenAI:     "gpt-4o", "gpt-4o-mini"
#   Anthropic:  "claude-sonnet-5", "claude-opus-4-8"
#   Gemini:     "gemini/gemini-1.5-pro"
# The matching API key must be present in the environment, e.g.
#   OPENAI_API_KEY / ANTHROPIC_API_KEY / GEMINI_API_KEY
# ---------------------------------------------------------------------------
LLM_MODEL = os.getenv("APPLY_LLM_MODEL", "claude-sonnet-5")
LLM_TEMPERATURE = 0.3  # low — we want faithful rewrites, not creativity

# ---------------------------------------------------------------------------
# Baseline resume. Point at your master resume in Markdown / plain text.
# The LLM only ever *reshapes* this content — it is instructed never to add
# skills or experience that don't appear here.
# ---------------------------------------------------------------------------
BASELINE_RESUME_PATH = "baseline_resume.md"

# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------
OUTPUT_DIR = "output_resumes"
RESUME_FORMATS = ["pdf", "docx"]  # any subset of {"pdf", "docx"}
APPLICATION_LOG = "application_log.jsonl"

# ---------------------------------------------------------------------------
# Browser / submission behaviour
# ---------------------------------------------------------------------------
# If True the filler clicks the final "Submit". If False (default) it fills
# everything, takes a screenshot, and stops so YOU review before submitting.
# Treat True like a live deploy — turn it on deliberately.
AUTO_SUBMIT = False

# Run with a visible browser window (recommended) so you can watch/intervene.
HEADLESS = False

# Optional persistent browser profile dir. Point this at a Chrome/Chromium
# user-data dir where you're already logged in to the ATS/job site, so you
# don't re-enter credentials each run. Leave None for a fresh context.
USER_DATA_DIR = None

# Politeness delays between actions (seconds). Keeps the automation from
# hammering the page faster than a person could.
MIN_ACTION_DELAY = 1.5
MAX_ACTION_DELAY = 3.5

# ---------------------------------------------------------------------------
# Answers used to auto-fill application form fields.
#
# Each entry: the field is matched by running `match` (a case-insensitive
# regex) against the field's visible label / placeholder / name. First match
# wins, so put more specific patterns first.
#
# type: "text"     -> types `value` into an input/textarea
#         "select"   -> picks the option whose text best matches `value`
#         "radio"    -> selects the radio/button whose label matches `value`
#         "checkbox" -> checks the box if `value` is truthy
# ---------------------------------------------------------------------------
CONTACT = {
    "first_name": "Vivek",
    "last_name": "Singh",
    "full_name": "Vivek Singh",
    "email": "vxs159830@gmail.com",
    "phone": "(347)-295-4269",
    "city": "Dallas, TX",
    "linkedin": "",  # add your LinkedIn profile URL
    "website": "",  # add a portfolio/website URL if you have one
}

ANSWERS = [
    # --- identity / contact ---
    {"match": r"first\s*name", "type": "text", "value": CONTACT["first_name"]},
    {
        "match": r"last\s*name|surname|family\s*name",
        "type": "text",
        "value": CONTACT["last_name"],
    },
    {"match": r"full\s*name|^name$", "type": "text", "value": CONTACT["full_name"]},
    {"match": r"e-?mail", "type": "text", "value": CONTACT["email"]},
    {
        "match": r"phone|mobile|contact\s*number",
        "type": "text",
        "value": CONTACT["phone"],
    },
    {"match": r"linkedin", "type": "text", "value": CONTACT["linkedin"]},
    {
        "match": r"portfolio|website|personal\s*site",
        "type": "text",
        "value": CONTACT["website"],
    },
    {"match": r"city|location|where.*based", "type": "text", "value": CONTACT["city"]},
    # --- common screening questions ---
    {"match": r"years?.*experience", "type": "text", "value": "10"},
    {
        "match": r"authorized|authorised|eligible.*work|work\s*authorization",
        "type": "radio",
        "value": "Yes",
    },
    {
        "match": r"require.*sponsor|need.*sponsor|visa\s*sponsor",
        "type": "radio",
        "value": "No",
    },
    {"match": r"willing.*relocate|open.*relocat", "type": "radio", "value": "Yes"},
    {
        "match": r"remote|hybrid|on-?site|work\s*arrangement",
        "type": "select",
        "value": "Remote",
    },
    {"match": r"notice\s*period", "type": "text", "value": "2 weeks"},
    {
        "match": r"salary|compensation.*expect|expected\s*pay",
        "type": "text",
        "value": "Open / negotiable",
    },
    {"match": r"how did you hear", "type": "select", "value": "LinkedIn"},
    {"match": r"gender", "type": "select", "value": "Decline to self-identify"},
    {"match": r"race|ethnicity", "type": "select", "value": "Decline to self-identify"},
    {"match": r"veteran", "type": "select", "value": "Decline to self-identify"},
    {"match": r"disability", "type": "select", "value": "Decline to self-identify"},
]

# If a REQUIRED field can't be matched to any answer above, what should we do?
#   "pause" -> stop and leave the browser open for you to finish by hand
#   "abort" -> close and log NEEDS_HUMAN, move on
ON_UNKNOWN_REQUIRED_FIELD = "pause"
