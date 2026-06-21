import hashlib
import re
import time
from datetime import datetime
from urllib.parse import urljoin

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright

from config import (
    ENABLE_PLAYWRIGHT_GREENHOUSE,
    ENABLE_PLAYWRIGHT_LEVER,
    ENABLE_PLAYWRIGHT_LINKEDIN,
    ENABLE_PLAYWRIGHT_WELLFOUND,
    PLAYWRIGHT_HEADLESS,
    PLAYWRIGHT_SCROLLS,
    PLAYWRIGHT_TIMEOUT,
)

from logger import log_message


# ---------------------------------------------------------
# SOURCE CONFIG
# ---------------------------------------------------------

PLAYWRIGHT_SOURCE_SPECS = [

    {
        "enabled": ENABLE_PLAYWRIGHT_LINKEDIN,
        "type": "linkedin",
        "name": "linkedin_uk_data_analyst",
        "url": (
            "https://www.linkedin.com/jobs/search/"
            "?keywords=Data%20Analyst"
            "&location=United%20Kingdom"
            "&f_TPR=r86400"
        ),
    },

    {
        "enabled": ENABLE_PLAYWRIGHT_LINKEDIN,
        "type": "linkedin",
        "name": "linkedin_australia_analytics_engineer",
        "url": (
            "https://www.linkedin.com/jobs/search/"
            "?keywords=Analytics%20Engineer"
            "&location=Australia"
            "&f_TPR=r86400"
        ),
    },

    {
        "enabled": ENABLE_PLAYWRIGHT_GREENHOUSE,
        "type": "greenhouse",
        "name": "greenhouse_public_boards",
        "url": "https://boards.greenhouse.io/",
    },

    {
        "enabled": ENABLE_PLAYWRIGHT_LEVER,
        "type": "lever",
        "name": "lever_public_boards",
        "url": "https://jobs.lever.co/",
    },

    {
        "enabled": ENABLE_PLAYWRIGHT_WELLFOUND,
        "type": "wellfound",
        "name": "wellfound_jobs",
        "url": "https://wellfound.com/jobs",
    },
]


# ---------------------------------------------------------
# RELEVANCE FILTERS
# ---------------------------------------------------------

JOB_KEYWORDS = [

    "data analyst",
    "business intelligence",
    "bi analyst",
    "analytics engineer",
    "reporting analyst",
    "product analyst",
    "data analytics",
    "sql",
    "looker",
    "lookml",
    "power bi",
    "tableau",
]

HIGH_PRIORITY_KEYWORDS = [

    "sql",
    "looker",
    "lookml",
    "analytics",
    "dashboard",
    "reporting",
    "business intelligence",
    "power bi",
    "tableau",
]

NEGATIVE_JOB_KEYWORDS = [

    "sales",
    "marketing",
    "writer",
    "ios",
    "android",
    "frontend",
    "backend",
    "react",
    "full stack",
    "full-stack",
    "devops",
    "support",
    "customer support",
    "video editor",
    "designer",
    "copywriter",
    "bookkeeper",
    "finance manager",
    "content reviewer",
    "recruiter",
    "account executive",
]

NOISE_PHRASES = [

    "open mobile navigation",
    "close mobile sub-navigation",
    "bias audit statement",
    "events & webinars",
    "events and webinars",
    "sign in",
    "join now",
    "privacy",
    "terms",
    "cookies",
]


# ---------------------------------------------------------
# SELECTORS
# ---------------------------------------------------------

TITLE_SELECTORS = [

    "h1",
    ".top-card-layout__title",
    ".posting-headline h2",
    ".job-header h1",
    "[data-qa='job-title']",
    ".job-title",
]

COMPANY_SELECTORS = [

    ".topcard__org-name-link",
    ".top-card-layout__card .topcard__flavor",
    "[data-qa='job-company-name']",
    ".company_name",
    ".posting-company",
    ".company",
]

LOCATION_SELECTORS = [

    ".topcard__flavor--bullet",
    "[data-qa='job-location']",
    ".location",
    ".job-location",
]

DESCRIPTION_SELECTORS = [

    ".show-more-less-html__markup",
    ".jobs-description-content__text",
    ".description__text",
    "[data-qa='job-description']",
    ".job-description",
    ".posting-description",
    ".job-posting__description",
    ".job-posting__content",
    "article",
]


# ---------------------------------------------------------
# HELPERS
# ---------------------------------------------------------

def clean_text(value):

    if not value:
        return ""

    value = re.sub(
        r"\s+",
        " ",
        str(value)
    )

    return value.strip()


def safe_text(locator):

    try:
        return clean_text(
            locator.inner_text()
        )

    except Exception:
        return ""


def safe_attr(locator, attr):

    try:

        value = locator.get_attribute(attr)

        return clean_text(value)

    except Exception:
        return ""


def looks_like_noise(text):

    text = clean_text(text).lower()

    if not text:
        return True

    return any(
        phrase in text
        for phrase in NOISE_PHRASES
    )


def calculate_candidate_priority(text):

    text = clean_text(text).lower()

    if not text:
        return -100

    for keyword in NEGATIVE_JOB_KEYWORDS:

        if keyword in text:
            return -100

    score = 0

    for keyword in JOB_KEYWORDS:

        if keyword in text:
            score += 10

    for keyword in HIGH_PRIORITY_KEYWORDS:

        if keyword in text:
            score += 5

    return score


def looks_like_job_text(text):

    return calculate_candidate_priority(text) > 0


def first_match_text(page, selectors):

    for selector in selectors:

        try:

            loc = page.locator(selector).first

            if loc.count() == 0:
                continue

            text = safe_text(loc)

            if text:
                return text

        except Exception:
            continue

    return ""


def sha_job_id(source_name, url):

    return hashlib.sha1(
        f"{source_name}|{url}".encode("utf-8")
    ).hexdigest()[:24]


# ---------------------------------------------------------
# PAGE SCROLL
# ---------------------------------------------------------

def scroll_page(page):

    previous_height = 0

    for _ in range(PLAYWRIGHT_SCROLLS):

        try:
            page.mouse.wheel(0, 7000)
        except Exception:
            pass

        time.sleep(1)

        try:

            current_height = page.evaluate(
                "document.body.scrollHeight"
            )

        except Exception:

            current_height = previous_height

        if current_height == previous_height:
            break

        previous_height = current_height


# ---------------------------------------------------------
# DETAIL EXTRACTION
# ---------------------------------------------------------

def extract_job_page_fields(page):

    title = first_match_text(
        page,
        TITLE_SELECTORS
    )

    company = first_match_text(
        page,
        COMPANY_SELECTORS
    )

    location = first_match_text(
        page,
        LOCATION_SELECTORS
    )

    description = first_match_text(
        page,
        DESCRIPTION_SELECTORS
    )

    if not description:

        try:

            body_text = clean_text(
                page.locator("body").inner_text()
            )

            if len(body_text) > 300:
                description = body_text[:5000]

        except Exception:
            pass

    return {
        "title": title,
        "company": company,
        "location": location,
        "summary": description,
    }


# ---------------------------------------------------------
# LINKEDIN LIST EXTRACTION
# ---------------------------------------------------------

def extract_linkedin_candidates(
    page,
    source_name
):

    candidates = []

    seen = set()

    cards = page.locator(
        ".base-card"
    ).all()

    log_message(
        f"{source_name} cards found: "
        f"{len(cards)}"
    )

    for card in cards:

        try:

            title = safe_text(
                card.locator(
                    ".base-search-card__title"
                )
            )

            company = safe_text(
                card.locator(
                    ".base-search-card__subtitle"
                )
            )

            location = safe_text(
                card.locator(
                    ".job-search-card__location"
                )
            )

            url = safe_attr(
                card.locator(
                    "a.base-card__full-link"
                ),
                "href"
            )

            if not title or not url:
                continue

            title_lower = title.lower()

            if looks_like_noise(title_lower):
                continue

            priority = calculate_candidate_priority(
                f"{title} {company}"
            )

            if priority <= 0:
                continue

            url = url.split("?")[0]

            if url in seen:
                continue

            seen.add(url)

            candidates.append({

                "priority": priority,
                "source_name": source_name,
                "url": url,
                "title": title,
                "company": company,
                "location": location,
            })

        except Exception as exc:

            log_message(
                f"LinkedIn parse failed: {exc}"
            )

    candidates = sorted(
        candidates,
        key=lambda x: x["priority"],
        reverse=True
    )

    return candidates[:10]


# ---------------------------------------------------------
# GENERIC SOURCES
# ---------------------------------------------------------

def extract_generic_candidates(
    page,
    source_name
):

    candidates = []

    seen = set()

    anchors = page.locator("a").all()

    log_message(
        f"{source_name} links found: "
        f"{len(anchors)}"
    )

    for anchor in anchors:

        try:

            text = safe_text(anchor)

            href = safe_attr(
                anchor,
                "href"
            )

            if not text or not href:
                continue

            if looks_like_noise(text):
                continue

            priority = calculate_candidate_priority(
                text
            )

            if priority <= 0:
                continue

            abs_url = urljoin(
                page.url,
                href
            )

            if abs_url in seen:
                continue

            seen.add(abs_url)

            candidates.append({

                "priority": priority,
                "source_name": source_name,
                "url": abs_url,
                "title": text,
                "company": "",
                "location": "",
            })

        except Exception as exc:

            log_message(
                f"Generic parse failed: {exc}"
            )

    candidates = sorted(
        candidates,
        key=lambda x: x["priority"],
        reverse=True
    )

    return candidates[:5]


# ---------------------------------------------------------
# DETAIL PAGE ENRICHMENT
# ---------------------------------------------------------

def enrich_candidate(
    context,
    candidate
):

    detail_page = context.new_page()

    try:

        detail_page.goto(
            candidate["url"],
            timeout=PLAYWRIGHT_TIMEOUT,
            wait_until="domcontentloaded",
        )

        time.sleep(1.5)

        fields = extract_job_page_fields(
            detail_page
        )

        title = (
            fields["title"]
            or candidate["title"]
        )

        company = (
            fields["company"]
            or candidate["company"]
        )

        location = (
            fields["location"]
            or candidate["location"]
        )

        summary = (
            fields["summary"]
            or ""
        )

        if not looks_like_job_text(title):
            return None

        return {

            "job_id": (
                f"{candidate['source_name']}-"
                f"{sha_job_id(candidate['source_name'], candidate['url'])}"
            ),

            "source": candidate["source_name"],
            "title": title,
            "company": company,
            "location": location,
            "url": candidate["url"],
            "summary": summary,
            "posted_date": datetime.now().isoformat(),
        }

    except PlaywrightTimeoutError:

        log_message(
            f"Timeout opening: "
            f"{candidate['url']}"
        )

        return None

    except Exception as exc:

        log_message(
            f"Detail parse failed: {exc}"
        )

        return None

    finally:

        try:
            detail_page.close()
        except Exception:
            pass


# ---------------------------------------------------------
# SOURCE SCRAPER
# ---------------------------------------------------------

def scrape_source(
    context,
    page,
    source
):

    source_name = source["name"]

    source_type = source["type"]

    start_time = time.time()

    try:

        log_message(
            f"Playwright loading: "
            f"{source_name}"
        )

        page.goto(
            source["url"],
            timeout=PLAYWRIGHT_TIMEOUT,
            wait_until="domcontentloaded",
        )

        time.sleep(2)

        scroll_page(page)

        try:

            page.screenshot(
                path=f"logs/{source_name}.png",
                full_page=True,
            )

        except Exception:
            pass

        if source_type == "linkedin":

            candidates = extract_linkedin_candidates(
                page,
                source_name
            )

        else:

            candidates = extract_generic_candidates(
                page,
                source_name
            )

        log_message(
            f"{source_name} filtered "
            f"candidates: {len(candidates)}"
        )

        jobs = []

        for candidate in candidates:

            enriched = enrich_candidate(
                context,
                candidate
            )

            if enriched:
                jobs.append(enriched)

        duration = round(
            time.time() - start_time,
            2
        )

        log_message(
            f"Playwright SUCCESS | "
            f"{source_name} | "
            f"jobs={len(jobs)} | "
            f"duration={duration}s"
        )

        return jobs

    except Exception as exc:

        duration = round(
            time.time() - start_time,
            2
        )

        log_message(
            f"Playwright FAILED | "
            f"{source_name} | "
            f"duration={duration}s | "
            f"{exc}"
        )

        return []


# ---------------------------------------------------------
# MAIN PLAYWRIGHT SCRAPER
# ---------------------------------------------------------

def scrape_playwright_jobs():

    all_jobs = []

    with sync_playwright() as p:

        browser = p.chromium.launch(
            headless=PLAYWRIGHT_HEADLESS
        )

        context = browser.new_context(

            viewport={
                "width": 1440,
                "height": 900,
            },

            user_agent=(
                "Mozilla/5.0 "
                "(Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 "
                "(KHTML, like Gecko) "
                "Chrome/124 Safari/537.36"
            ),
        )

        page = context.new_page()

        for source in PLAYWRIGHT_SOURCE_SPECS:

            if not source["enabled"]:
                continue

            jobs = scrape_source(
                context,
                page,
                source
            )

            all_jobs.extend(jobs)

        browser.close()

    log_message(
        f"Playwright total jobs: "
        f"{len(all_jobs)}"
    )

    return all_jobs