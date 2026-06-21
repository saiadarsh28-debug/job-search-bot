import json
import time

from google import genai

from config import (
    GEMINI_API_KEY,
    GEMINI_ENABLED,
    GEMINI_MODEL,
)

from database import (
    get_cached_ai_score,
    save_cached_ai_score,
)

from logger import log_message


# ---------------------------------------------------------
# CLIENT INIT
# ---------------------------------------------------------

CLIENT = None

if GEMINI_ENABLED and GEMINI_API_KEY:

    try:

        CLIENT = genai.Client(
            api_key=GEMINI_API_KEY
        )

        log_message(
            "Gemini client initialized"
        )

    except Exception as exc:

        log_message(
            f"Gemini init failed: {exc}"
        )

# ---------------------------------------------------------
# PROFILE SUMMARY
# ---------------------------------------------------------

PROFILE_SUMMARY = """
Candidate Profile:

- 6 years experience in:
  SQL
  Looker
  LookML
  Analytics
  Dashboarding
  Reporting
  Product analytics
  BI
  KPI reporting
  Data warehousing

Strong fit:
- Data Analyst
- BI Analyst
- Analytics Engineer
- Looker Developer
- Product Analyst

Avoid:
- frontend engineering
- backend engineering
- mobile development
"""

# ---------------------------------------------------------
# GEMINI SCORING
# ---------------------------------------------------------

def score_with_gemini(job, category):

    start_time = time.time()

    if not GEMINI_ENABLED:
        return None

    if CLIENT is None:

        log_message(
            "Gemini client unavailable"
        )

        return None

    # -----------------------------------------------------
    # CACHE
    # -----------------------------------------------------

    cached = get_cached_ai_score(
        job["job_id"],
        category
    )

    if cached:

        log_message(
            f"Gemini cache hit | "
            f"{job['title']}"
        )

        return cached

    # -----------------------------------------------------
    # PROMPT
    # -----------------------------------------------------

    prompt = f"""
You are evaluating role relevance.

Candidate:
{PROFILE_SUMMARY}

Job Title:
{job.get("title", "")}

Company:
{job.get("company", "")}

Location:
{job.get("location", "")}

Description:
{job.get("summary", "")[:4000]}

Return ONLY valid JSON.

{{
  "score": 0-100,
  "reasons": [
    "reason 1",
    "reason 2"
  ]
}}
"""

    try:

        response = CLIENT.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt,
        )

        raw_text = (
            response.text
            .replace("```json", "")
            .replace("```", "")
            .strip()
        )

        parsed = json.loads(raw_text)

        score = int(
            parsed.get("score", 0)
        )

        reasons = parsed.get(
            "reasons",
            []
        )

        score = max(
            0,
            min(100, score)
        )

        result = {
            "score": score,
            "reasons": reasons,
        }

        save_cached_ai_score(
            job["job_id"],
            category,
            score,
            reasons,
            GEMINI_MODEL
        )

        duration = round(
            time.time() - start_time,
            2
        )

        log_message(
            f"Gemini success | "
            f"score={score} | "
            f"duration={duration}s"
        )

        return result

    except Exception as exc:

        duration = round(
            time.time() - start_time,
            2
        )

        log_message(
            f"Gemini failed | "
            f"duration={duration}s | "
            f"{exc}"
        )

        return None