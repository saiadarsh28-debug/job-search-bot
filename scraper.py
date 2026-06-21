import hashlib
import re
import time
from datetime import datetime

import requests

from config import (
    ADZUNA_APP_ID,
    ADZUNA_APP_KEY,
    DESCRIPTION_CACHE_DAYS,
    JOB_FEEDS,
    REQUEST_DELAY_SECONDS,
)
from database import (
    get_cached_description,
    record_source_run,
    save_cached_description,
)
from logger import log_message
from playwright_scraper import scrape_playwright_jobs


# ---------------------------------------------------------
# HTTP SESSION — realistic browser headers
# ---------------------------------------------------------

SESSION = requests.Session()
SESSION.headers.update({
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/html, */*",
    "Accept-Language": "en-US,en;q=0.9",
})


# ---------------------------------------------------------
# HELPERS
# ---------------------------------------------------------

def safe_get_json(url, params=None, timeout=30):
    try:
        response = SESSION.get(url, params=params, timeout=timeout)
        response.raise_for_status()
        log_message(f"Fetched: {url}")
        return response.json()
    except Exception as exc:
        log_message(f"Request failed: {url} | {exc}")
        return None


def clean_html(text):
    if not text:
        return ""
    text = re.sub(r"<[^>]+>", " ", str(text))
    text = re.sub(r"&[a-zA-Z]+;", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def normalize_job(source, title, company, location, url, summary):
    raw = f"{source}|{title.lower().strip()}|{company.lower().strip()}|{url}"
    job_id = hashlib.md5(raw.encode()).hexdigest()
    return {
        "job_id":      job_id,
        "source":      source,
        "title":       title or "",
        "company":     company or "",
        "location":    location or "",
        "url":         url or "",
        "summary":     summary or "",
        "posted_date": datetime.now().isoformat(),
    }


# ---------------------------------------------------------
# REMOTIVE
# ---------------------------------------------------------

def parse_remotive(feed):
    jobs = []
    data = safe_get_json(feed["url"])
    if not data:
        return jobs

    for item in data.get("jobs", []):
        try:
            jobs.append(normalize_job(
                source="remotive",
                title=item.get("title", ""),
                company=item.get("company_name", ""),
                location=item.get("candidate_required_location", "Remote"),
                url=item.get("url", ""),
                summary=clean_html(item.get("description", "")),
            ))
        except Exception as exc:
            log_message(f"Remotive parse error: {exc}")

    log_message(f"{feed['name']}: {len(jobs)} jobs")
    return jobs


# ---------------------------------------------------------
# MYCAREERSFUTURE (Singapore)
# ---------------------------------------------------------

def parse_mcf(feed):
    jobs = []
    data = safe_get_json(feed["url"])
    if not data:
        return jobs

    for item in data.get("results", []):
        try:
            job_uuid = item.get("uuid", "")
            url = f"https://www.mycareersfuture.gov.sg/job/{job_uuid}"
            jobs.append({
                "job_id":      f"mcf-{job_uuid}",
                "source":      "mcf",
                "title":       item.get("title", ""),
                "company":     item.get("company", ""),
                "location":    "Singapore",
                "url":         url,
                "summary":     clean_html(item.get("description", "")),
                "posted_date": datetime.now().isoformat(),
            })
        except Exception as exc:
            log_message(f"MCF parse error: {exc}")

    log_message(f"{feed['name']}: {len(jobs)} jobs")
    return jobs


# ---------------------------------------------------------
# ARBEITNOW
# FIX: enforce visa_sponsorship == True at the API field level.
# Previous version only did title keyword filtering, which let
# through random German accounting/bookkeeping jobs.
# Also filter by data-relevant keywords in title as a second pass.
# ---------------------------------------------------------

DATA_KEYWORDS = [
    "data", "analytics", "analyst", "bi", "sql",
    "looker", "business intelligence", "reporting",
    "warehouse", "insight", "metric",
]

def parse_arbeitnow(feed):
    jobs = []
    data = safe_get_json(feed["url"])
    if not data:
        return jobs

    for item in data.get("data", []):
        try:
            # Hard filter 1: visa sponsorship must be True at API level
            if not item.get("visa_sponsorship", False):
                continue

            title = item.get("title", "")
            title_lower = title.lower()

            # Hard filter 2: must be a data-adjacent role
            if not any(kw in title_lower for kw in DATA_KEYWORDS):
                continue

            jobs.append(normalize_job(
                source="arbeitnow",
                title=title,
                company=item.get("company_name", ""),
                location=item.get("location", feed.get("country_hint", "Germany")),
                url=item.get("url", ""),
                # Inject phrase so visa_checker detects it in text scoring
                summary="visa sponsorship confirmed. " + clean_html(item.get("description", "")),
            ))
        except Exception as exc:
            log_message(f"Arbeitnow parse error: {exc}")

    log_message(f"{feed['name']}: {len(jobs)} visa-sponsored data jobs")
    return jobs


# ---------------------------------------------------------
# ADZUNA
# Builds its own URL — handled BEFORE any feed["url"] access.
# ---------------------------------------------------------

def parse_adzuna(feed):
    if not ADZUNA_APP_ID or not ADZUNA_APP_KEY:
        log_message(f"{feed['name']}: Adzuna keys missing — skipping")
        return []

    country = feed.get("country_code", "gb")
    search = feed.get("search_term", "data analyst")
    url = f"https://api.adzuna.com/v1/api/jobs/{country}/search/1"

    data = safe_get_json(url, params={
        "app_id":           ADZUNA_APP_ID,
        "app_key":          ADZUNA_APP_KEY,
        "results_per_page": 50,
        "what":             search,
        "sort_by":          "date",
        "content-type":     "application/json",
    })

    if not data:
        return []

    jobs = []
    for item in data.get("results", []):
        try:
            jobs.append(normalize_job(
                source="adzuna",
                title=item.get("title", ""),
                company=item.get("company", {}).get("display_name", ""),
                location=item.get("location", {}).get("display_name", "")
                         or feed.get("country_hint", ""),
                url=item.get("redirect_url", ""),
                summary=clean_html(item.get("description", "")),
            ))
        except Exception as exc:
            log_message(f"Adzuna parse error: {exc}")

    log_message(f"{feed['name']}: {len(jobs)} jobs")
    return jobs


# ---------------------------------------------------------
# LINKEDIN GUEST API
# Unauthenticated endpoint — no login required.
# Returns HTML with embedded job cards.
# ---------------------------------------------------------

def parse_linkedin_guest(feed):
    try:
        response = SESSION.get(feed["url"], timeout=20)
        response.raise_for_status()
        content = response.text
    except Exception as exc:
        log_message(f"{feed['name']}: fetch failed: {exc}")
        return []

    jobs = []
    # Extract job card blocks
    cards = re.findall(
        r'<li[^>]*>(.*?)</li>',
        content,
        re.DOTALL,
    )

    for card in cards:
        title_m   = re.search(r'class="[^"]*base-search-card__title[^"]*"[^>]*>\s*([^<]+)', card)
        company_m = re.search(r'class="[^"]*base-search-card__subtitle[^"]*"[^>]*>\s*([^<]+)', card)
        location_m= re.search(r'class="[^"]*job-search-card__location[^"]*"[^>]*>\s*([^<]+)', card)
        url_m     = re.search(r'href="(https://[^"]+/jobs/view/[^"?]+)', card)

        title   = title_m.group(1).strip()   if title_m   else ""
        company = company_m.group(1).strip() if company_m else "Unknown"
        location= location_m.group(1).strip()if location_m else feed.get("country_hint","")
        url     = url_m.group(1)             if url_m     else ""

        if not title or not url:
            continue

        jobs.append(normalize_job(
            source="linkedin_guest",
            title=title,
            company=company,
            location=location,
            url=url,
            summary="",
        ))

    log_message(f"{feed['name']}: {len(jobs)} jobs")
    return jobs


# ---------------------------------------------------------
# DESCRIPTION CACHE
# ---------------------------------------------------------

def enrich_job_description(job):
    cached = get_cached_description(job["job_id"], DESCRIPTION_CACHE_DAYS)
    if cached:
        job["summary"] = cached
        return job
    summary = job.get("summary", "")
    if summary:
        save_cached_description(
            job["job_id"], job["source"], job["url"], summary
        )
    return job


# ---------------------------------------------------------
# MAIN FETCH FUNCTION
#
# CRITICAL ORDERING:
# adzuna_api builds its own URL → must be handled FIRST,
# before any code tries to access feed["url"].
# ---------------------------------------------------------
# def parse_adzuna(feed):
#     from config import ADZUNA_APP_ID_1, ADZUNA_APP_KEY_1, ADZUNA_APP_ID_2, ADZUNA_APP_KEY_2
#     import datetime
#     hour = datetime.datetime.now().hour
#     app_id = ADZUNA_APP_ID_1 if hour < 12 else ADZUNA_APP_ID_2
#     app_key = ADZUNA_APP_KEY_1 if hour < 12 else ADZUNA_APP_KEY_2
#     if not app_id or not app_key:
#         log_message(f"{feed['name']}: Adzuna keys missing")
#         return []
#     # rest of function uses app_id and app_key instead of ADZUNA_APP_ID

def fetch_jobs(lookback_hours=24):
    log_message(f"Scraper started | lookback={lookback_hours}h")

    all_jobs = []

    for feed in JOB_FEEDS:

        source_name = feed["name"]
        source_kind = feed.get("kind", "rss")

        log_message(f"Source: {source_name} ({source_kind})")

        time.sleep(REQUEST_DELAY_SECONDS)

        start = time.time()
        source_jobs = []

        try:
            # --- Adzuna: builds its own URL, MUST be first ---
            if source_kind == "adzuna_api":
                source_jobs = parse_adzuna(feed)

            elif source_kind == "remotive_api":
                source_jobs = parse_remotive(feed)

            elif source_kind == "mcf_api":
                source_jobs = parse_mcf(feed)

            elif source_kind == "arbeitnow_api":
                source_jobs = parse_arbeitnow(feed)

            elif source_kind == "apify_actor":
                source_jobs = parse_apify(feed)

            elif source_kind == "linkedin_guest":
                source_jobs = parse_linkedin_guest(feed)

            elif source_kind == "remoteok_api": 
                source_jobs = parse_remoteok(feed)

            elif source_kind == "jobicy_api": 
                source_jobs = parse_jobicy(feed)

            elif source_kind == "reed_api": 
                source_jobs = parse_reed(feed)

            else:
                log_message(f"Unknown feed kind: {source_kind} — skipping")

            enriched = [enrich_job_description(j) for j in source_jobs]
            duration = round(time.time() - start, 2)

            record_source_run(source_name, "success", len(enriched))
            log_message(f"{source_name}: {len(enriched)} jobs in {duration}s")
            all_jobs.extend(enriched)

        except Exception as exc:
            duration = round(time.time() - start, 2)
            record_source_run(source_name, "failed", 0, str(exc))
            log_message(f"{source_name} FAILED | {duration}s | {exc}")

    # ---------------------------------------------------------
    # PLAYWRIGHT PREMIUM LAYER (LinkedIn only now)
    # greenhouse/lever/wellfound disabled in config — 0% hit rate
    # ---------------------------------------------------------

    try:
        log_message("Starting Playwright layer")
        playwright_jobs = scrape_playwright_jobs()
        log_message(f"Playwright: {len(playwright_jobs)} jobs")
        all_jobs.extend(playwright_jobs)
    except Exception as exc:
        log_message(f"Playwright layer failed: {exc}")

    log_message(f"Scraper done. Total: {len(all_jobs)} jobs")
    return all_jobs


def parse_remoteok(feed):
    data = safe_get_json(feed["url"])
    if not data:
        return []
    jobs = []
    for item in data:
        if not isinstance(item, dict):
            continue
        url = item.get("url", "")
        title = item.get("position", "")
        company = item.get("company", "")
        if not title or not url:
            continue
        jobs.append(normalize_job(
            source="remoteok",
            title=title,
            company=company,
            location="Remote",
            url=f"https://remoteok.io{url}" if url.startswith("/") else url,
            summary=" ".join(item.get("tags", [])),
        ))
    log_message(f"{feed['name']} parsed {len(jobs)} jobs")
    return jobs

def parse_jobicy(feed):
    data = safe_get_json(feed["url"])
    if not data:
        return []
    jobs = []
    for item in data.get("jobs", []):
        url = item.get("url", "")
        title = item.get("jobTitle", "")
        company = item.get("companyName", "")
        location = item.get("jobGeo", "Remote")
        summary = item.get("jobExcerpt", "")
        if not title or not url:
            continue
        jobs.append(normalize_job(
            source="jobicy",
            title=title,
            company=company,
            location=location,
            url=url,
            summary=summary,
        ))
    log_message(f"{feed['name']} parsed {len(jobs)} jobs")
    return jobs

def parse_reed(feed):
    from config import REED_API_KEY
    if not REED_API_KEY:
        log_message(f"{feed['name']}: REED_API_KEY not set")
        return []
    import base64
    credentials = base64.b64encode(
        f"{REED_API_KEY}:".encode()
    ).decode()
    url = (
        f"https://www.reed.co.uk/api/1.0/search"
        f"?keywords={feed['search_term'].replace(' ', '%20')}"
        f"&locationName={feed.get('location','').replace(' ', '%20')}"
        f"&resultsToTake=50"
    )
    try:
        response = SESSION.get(
            url,
            headers={"Authorization": f"Basic {credentials}"},
            timeout=30
        )
        response.raise_for_status()
        data = response.json()
    except Exception as exc:
        log_message(f"{feed['name']} failed: {exc}")
        return []
    jobs = []
    for item in data.get("results", []):
        url_job = f"https://www.reed.co.uk/jobs/{item.get('jobId', '')}"
        title = item.get("jobTitle", "")
        company = item.get("employerName", "")
        location = item.get("locationName", "United Kingdom")
        summary = item.get("jobDescription", "")
        if not title:
            continue
        jobs.append(normalize_job(
            source="reed",
            title=title,
            company=company,
            location=location,
            url=url_job,
            summary=summary,
        ))
    log_message(f"{feed['name']} parsed {len(jobs)} jobs")
    return jobs


def parse_apify(feed):
    from config import APIFY_API_TOKEN
    if not APIFY_API_TOKEN:
        log_message(f"{feed['name']}: APIFY_API_TOKEN not set")
        return []

    actor_id = feed["actor_id"]
    actor_input = feed["actor_input"]

    # Trigger the actor run
    run_url = f"https://api.apify.com/v2/acts/{actor_id}/run-sync-get-dataset-items"
    try:
        response = SESSION.post(
            run_url,
            json=actor_input,
            headers={"Authorization": f"Bearer {APIFY_API_TOKEN}"},
            timeout=120,  # Apify runs take 30-90 seconds
        )
        response.raise_for_status()
        data = response.json()
    except Exception as exc:
        log_message(f"{feed['name']} Apify failed: {exc}")
        return []

    jobs = []
    for item in data:
        title = item.get("title") or item.get("positionName") or item.get("jobTitle") or ""
        company = item.get("company") or item.get("companyName") or ""
        location = item.get("location") or item.get("jobLocation") or feed.get("country_hint", "")
        url = item.get("url") or item.get("jobUrl") or item.get("applyUrl") or ""
        summary = item.get("description") or item.get("jobDescription") or ""

        if not title or not url:
            continue

        jobs.append(normalize_job(
            source=f"apify_{actor_id.split('/')[1]}",
            title=title,
            company=company,
            location=location,
            url=url,
            summary=summary,
        ))

    log_message(f"{feed['name']} parsed {len(jobs)} jobs via Apify")
    return jobs