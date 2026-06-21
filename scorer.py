import re
import time

from ai_scorer import score_with_gemini
from config import (
    COUNTRY_KEYWORDS,
    GEMINI_ENABLED,
    INTERNATIONAL_COUNTRY_PRIORITY,
    NEGATIVE_KEYWORDS,
    PROFILE_DOMAIN_KEYWORDS,
    PROFILE_ROLE_TITLES,
    PROFILE_SKILLS,
    REMOTE_KEYWORDS,
    REMOTE_RESTRICTION_KEYWORDS,
)
from logger import log_message
from visa_checker import check_visa_signal


# ---------------------------------------------------------
# KEYWORD HELPERS
# ---------------------------------------------------------

def contains_keyword(text, keyword):
    """Case-insensitive whole-word match for short keywords."""
    keyword = keyword.lower()
    if len(keyword) <= 3:
        return re.search(
            rf"(?<![a-z0-9]){re.escape(keyword)}(?![a-z0-9])",
            text
        ) is not None
    return keyword in text


def job_text(job, include_location=True):
    parts = [
        job.get("title", ""),
        job.get("company", ""),
        job.get("summary", ""),
        job.get("source", ""),
    ]
    if include_location:
        parts.append(job.get("location", ""))
    return " ".join(parts).lower()


# ---------------------------------------------------------
# SIGNAL DETECTION
# ---------------------------------------------------------

def detect_country(location, text):
    combined = f"{location or ''} {text or ''}".lower()
    for country, keywords in COUNTRY_KEYWORDS.items():
        if any(contains_keyword(combined, kw) for kw in keywords):
            return country
    return "Unknown"


def has_remote_restriction(text):
    return any(kw in text for kw in REMOTE_RESTRICTION_KEYWORDS)


def has_remote_signal(text):
    return any(kw in text for kw in REMOTE_KEYWORDS)


def has_hyderabad_signal(job):
    text = job_text(job, include_location=True)
    return any(
        contains_keyword(text, kw)
        for kw in ["hyderabad", "secunderabad", "telangana"]
    )


def has_international_visa_signal(text):
    visa = check_visa_signal(text)
    return visa["visa_status"] == "positive"


# ---------------------------------------------------------
# HARD DISQUALIFIERS — checked on TITLE ONLY
#
# Why title only?
# Checking full description causes massive false negatives.
# Words like "contract", "intern", "citizen" appear constantly
# in legitimate job descriptions. Only flag when they're in
# the TITLE — that's when the job IS that thing.
# ---------------------------------------------------------

def has_hard_disqualifier_in_title(title_text):
    """Returns (True, matched_keyword) if title contains a hard disqualifier."""
    for kw in NEGATIVE_KEYWORDS:
        if contains_keyword(title_text, kw):
            return True, kw
    return False, None


# ---------------------------------------------------------
# PROFILE FIT SCORING
#
# Score breakdown — MAX 100:
#   Title match  : 0–35  (BEST single match only, no stacking)
#   Skill matches: 0–45  (capped, sum of matched skills)
#   Domain match : 0–15  (capped)
#   Hard neg flag: –40   (title only, see above)
#
# Without caps, "data analyst" + sql(14) + looker(16) +
# lookml(20) + analytics(10) + reporting(10) + dashboard(10)
# = 115 -> everyone scores 100. Caps fix this.
# ---------------------------------------------------------

def profile_fit_score(job):

    start_time = time.time()

    title_text = job.get("title", "").lower()
    full_text = job_text(job, include_location=False)

    score = 0
    reasons = []

    # --- Title: best single match only (no stacking) ---
    best_title_pts = 0
    best_title_kw = None
    for title_kw, points in PROFILE_ROLE_TITLES.items():
        if contains_keyword(title_text, title_kw):
            if points > best_title_pts:
                best_title_pts = points
                best_title_kw = title_kw

    if best_title_kw:
        score += best_title_pts
        reasons.append(f"Title: {best_title_kw}")

    # --- Skills: capped at 45 ---
    skill_score = 0
    matched_skills = []
    for skill, points in PROFILE_SKILLS.items():
        if contains_keyword(full_text, skill):
            skill_score += points
            matched_skills.append(skill)
    skill_score = min(skill_score, 45)
    score += skill_score
    if matched_skills:
        reasons.append(f"Skills: {', '.join(matched_skills[:8])}")

    # --- Domain: capped at 15 ---
    domain_score = 0
    matched_domain = []
    for kw, points in PROFILE_DOMAIN_KEYWORDS.items():
        if contains_keyword(full_text, kw):
            domain_score += points
            matched_domain.append(kw)
    domain_score = min(domain_score, 15)
    score += domain_score
    if matched_domain:
        reasons.append(f"Domain: {', '.join(matched_domain[:4])}")

    # --- Hard disqualifier: TITLE ONLY ---
    disqualified, disq_kw = has_hard_disqualifier_in_title(title_text)
    if disqualified:
        score -= 40
        reasons.append(f"Title flag: {disq_kw}")

    score = max(0, min(100, score))

    duration = round(time.time() - start_time, 4)
    log_message(
        f"Profile score={score} | "
        f"title={best_title_kw} | "
        f"skills={len(matched_skills)} | "
        f"duration={duration}s"
    )

    return {
        "score": score,
        "reasons": reasons or ["No strong profile match signals."],
    }


# ---------------------------------------------------------
# BASE JOB SCORE (used for DB persistence only)
# ---------------------------------------------------------

def score_job(job):
    text_with_location = job_text(job, include_location=True)
    visa = check_visa_signal(text_with_location)
    fit = profile_fit_score(job)
    country = detect_country(job.get("location", ""), text_with_location)

    return {
        "score":          fit["score"],
        "country":        country,
        "visa_confirmed": visa["visa_confirmed"],
        "visa_status":    visa["visa_status"],
        "reasons":        fit["reasons"],
    }


# ---------------------------------------------------------
# CATEGORY ELIGIBILITY
# ---------------------------------------------------------

def category_eligibility(job, category):

    text_with_location = job_text(job, include_location=True)
    country = detect_country(job.get("location", ""), text_with_location)
    visa = check_visa_signal(text_with_location)

    # --- Remote Global ---
    if category["kind"] == "remote_global":
        if not has_remote_signal(text_with_location):
            return None
        if has_remote_restriction(text_with_location):
            return None
        return {
            "category":          category["name"],
            "country":           country,
            "visa_status":       "not_required",
            "visa_confirmed":    False,
            "eligibility_reasons": ["Remote role", "No geo restriction found"],
        }

    # --- Hyderabad ---
    if category["kind"] == "hyderabad":
        if not has_hyderabad_signal(job):
            return None
        return {
            "category":          category["name"],
            "country":           "India",
            "visa_status":       "not_required",
            "visa_confirmed":    False,
            "eligibility_reasons": ["Hyderabad / Telangana role"],
        }

    # --- International Visa ---
    if category["kind"] == "international_visa":
        if country not in INTERNATIONAL_COUNTRY_PRIORITY:
            return None
        # Arbeitnow injects "visa sponsorship confirmed." prefix in summary.
        # For all other sources, require an explicit visa signal in the text.
        if not has_international_visa_signal(text_with_location):
            return None
        return {
            "category":          category["name"],
            "country":           country,
            "visa_status":       visa["visa_status"],
            "visa_confirmed":    visa["visa_confirmed"],
            "eligibility_reasons": [
                f"Target country: {country}",
                "Visa sponsorship signal found",
            ],
        }
    
    if category["kind"] == "international_any":
        if country not in INTERNATIONAL_COUNTRY_PRIORITY:
            return None
    return {
        "category": category["name"],
        "country": country,
        "visa_status": "unverified",
        "visa_confirmed": False,
        "eligibility_reasons": [
            f"Target country: {country}",
            "Visa status not confirmed — verify with employer before applying",
        ],
    }

    return None


# ---------------------------------------------------------
# FINAL CATEGORY SCORE
# ---------------------------------------------------------

def score_job_for_category(job, category, use_gemini=True):

    scoring_start = time.time()

    # Hard disqualifier check first — cheapest exit
    title_text = job.get("title", "").lower()
    disqualified, disq_kw = has_hard_disqualifier_in_title(title_text)
    if disqualified:
        log_message(f"Hard disqualified: '{job['title']}' — {disq_kw}")
        return None

    eligibility = category_eligibility(job, category)
    if not eligibility:
        return None

    fit = profile_fit_score(job)

    # Only call Gemini for strong candidates (saves API quota)
    if use_gemini and GEMINI_ENABLED and fit["score"] >= 70:
        try:
            gemini_result = score_with_gemini(job, category["name"])
            if gemini_result:
                fit = gemini_result
                log_message(f"Gemini scored: {job['title']}")
        except Exception as exc:
            log_message(f"Gemini failed: {exc}")

    if fit["score"] < category["threshold"]:
        return None

    duration = round(time.time() - scoring_start, 2)
    log_message(
        f"MATCH | {category['name']} | "
        f"score={fit['score']} | "
        f"duration={duration}s"
    )

    result = dict(job)
    result.update(eligibility)
    result["score"]               = fit["score"]
    result["threshold"]           = category["threshold"]
    result["reasons"]             = fit["reasons"]
    result["eligibility_reasons"] = eligibility["eligibility_reasons"]
    return result
