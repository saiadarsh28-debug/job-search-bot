# import os

import os
from pathlib import Path

# --- Load .env into environment before any os.getenv() calls ---
def _load_env_file(path):
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(
            key.strip(),
            value.strip().strip('"').strip("'")
        )

_load_env_file(Path(__file__).resolve().parent / ".env")

# ---------------------------------------------------------
# GEMINI
# ---------------------------------------------------------

GEMINI_ENABLED = False

GEMINI_MODEL = "gemini-2.0-flash"

GEMINI_API_KEY = os.getenv(
    "GEMINI_API_KEY",
    ""
)

# ---------------------------------------------------------
# ADZUNA API
# ---------------------------------------------------------
ADZUNA_APP_ID = os.getenv("ADZUNA_APP_ID", "")
ADZUNA_APP_KEY = os.getenv("ADZUNA_APP_KEY", "")
# ADZUNA_APP_ID_2 = os.getenv("ADZUNA_APP_ID_2", "")
# ADZUNA_APP_KEY_2 = os.getenv("ADZUNA_APP_KEY_2", "")

APIFY_API_TOKEN = os.getenv("APIFY_API_TOKEN", "")

# ---------------------------------------------------------
# EMAIL
# FIX: .env uses GMAIL_SENDER/GMAIL_PASSWORD/GMAIL_RECEIVER
# These names MUST match your .env file exactly.
# ---------------------------------------------------------

EMAIL_SENDER = os.getenv(
    "GMAIL_SENDER",
    ""
)

EMAIL_PASSWORD = os.getenv(
    "GMAIL_PASSWORD",
    ""
)

EMAIL_RECEIVER = os.getenv(
    "GMAIL_RECEIVER",
    EMAIL_SENDER
)

# ---------------------------------------------------------
# SCRAPER SETTINGS
# ---------------------------------------------------------

REQUEST_DELAY_SECONDS = 1.5

MAX_RETRIES = 1

LOOKBACK_HOURS_DEFAULT = 24

DESCRIPTION_CACHE_DAYS = 30

# ---------------------------------------------------------
# PLAYWRIGHT
# Disabled greenhouse/lever/wellfound — 0% hit rate.
# Only LinkedIn is worth running via Playwright.
# ---------------------------------------------------------

ENABLE_PLAYWRIGHT = True

ENABLE_PLAYWRIGHT_LINKEDIN = True

ENABLE_PLAYWRIGHT_GREENHOUSE = False

ENABLE_PLAYWRIGHT_LEVER = False

ENABLE_PLAYWRIGHT_WELLFOUND = False

PLAYWRIGHT_HEADLESS = True

PLAYWRIGHT_TIMEOUT = 60000

PLAYWRIGHT_SCROLLS = 10

# ---------------------------------------------------------
# PROFILE ROLE WEIGHTS
# Max 35 points from title (best match only, no stacking).
# ---------------------------------------------------------

PROFILE_ROLE_TITLES = {
    "analytics engineer":              35,
    "bi engineer":                     35,
    "looker developer":                35,
    "lookml developer":                35,
    "data warehouse engineer":         32,
    "business intelligence engineer":  32,
    "bi developer":                    30,
    "business intelligence analyst":   30,
    "bi analyst":                      30,
    "senior data analyst":             30,
    "data analyst":                    30,   # was 22 — too low for most common target role
    "reporting analyst":               25,
    "product analyst":                 22,
    "data engineer":                   15,
    "analytics manager":               20,
}

# ---------------------------------------------------------
# PROFILE SKILLS
# Capped at 45 total in scorer. Individual weights preserved.
# ---------------------------------------------------------

PROFILE_SKILLS = {
  "sql": 14,
  "advanced sql": 14,
  "looker": 14,
  "lookml": 13,
  "looker studio": 14,
  "mixpanel": 8,
  "salesforce": 8,
  "salesforce analytics": 6,
  "plx": 14,
  "data warehouse": 8,
  "data warehousing": 8,
  "data modeling": 8,
  "analytical data modeling": 8,
  "data transformation": 7,
  "data pipelines": 7,
  "dashboard": 13,
  "dashboard development": 13,
  "dashboard automation": 11,
  "dashboarding": 12,
  "reporting": 12,
  "reporting automation": 10,
  "kpi reporting": 12,
  "business intelligence": 14,
  "bi": 13,
  "analytics": 8,
  "data analytics": 14,
  "business analytics": 13,
  "product analytics": 13,
  "revenue analytics": 12,
  "growth analytics": 11,
  "operational analytics": 11,
  "analytics engineering": 12,
  "data visualization": 12,
  "business metrics": 11,
  "performance metrics": 10,
  "kpi analytics": 11,
  "kpi frameworks": 10,
  "executive dashboards": 11,
  "operational dashboards": 10,
  "real-time monitoring": 9,
  "strategic analytics": 10,
  "strategic insights": 9,
  "data-driven decision making": 11,
  "revenue operations": 10,
  "revenue operations analytics": 10,
  "sales enablement analytics": 9,
  "business performance analytics": 10,
  "business performance monitoring": 9,
  "revenue leakage analysis": 9,
  "operational efficiency": 9,
  "operational intelligence": 9,
  "scalable analytics": 10,
  "scalable reporting": 9,
  "scalable bi solutions": 9,
  "metrics layer": 8,
  "bi infrastructure": 8,
  "reporting architecture": 8,
  "data governance": 8,
  "sql optimization": 10,
  "data quality": 9,
  "funnel analytics": 11,
  "cohort analysis": 10,
  "a/b testing": 9,
  "user retention analysis": 10,
  "retention analytics": 10,
  "user journey analytics": 9,
  "customer lifecycle analytics": 9,
  "behavioral analytics": 9,
  "engagement analytics": 9,
  "growth metrics": 9,
  "product insights": 9,
  "feature adoption analysis": 8,
  "user segmentation": 8,
  "ltv optimization": 8,
  "churn analysis": 9,
  "experimentation analytics": 8,
  "saas analytics": 11,
  "edtech analytics": 10,
  "us market analytics": 9,
  "cross-functional stakeholder management": 10,
  "executive reporting": 11,
  "c-level reporting": 10,
  "global stakeholder management": 8,
  "global analytics experience": 8,
  "international stakeholder management": 8,
  "remote collaboration": 7,
  "cross-border teams": 7,
  "us stakeholder experience": 9,
  "global business operations": 8,
  "decision support analytics": 8
}


# ---------------------------------------------------------
# DOMAIN KEYWORDS
# Capped at 15 total in scorer.
# ---------------------------------------------------------

PROFILE_DOMAIN_KEYWORDS = {
    "data analytics": 14,
    "business analytics": 13,
    "product analytics": 13,
    "revenue analytics": 12,
    "growth analytics": 11,
    "saas analytics": 11,
    "edtech analytics": 10,
    "us market analytics": 9,
    "operational analytics": 11,
    "analytics engineering": 12,
    "growth analytics":     10,
    "marketing analytics":   8,
    "ab testing":           6,
    "user behavior":         6,
    "stakeholder":           5,
    "executive reporting":   6,
}

# ---------------------------------------------------------
# NEGATIVE SIGNALS
# Checked on JOB TITLE ONLY. Do NOT add words that appear
# naturally in job descriptions (e.g. bare "contract").
# ---------------------------------------------------------

NEGATIVE_KEYWORDS = [
    # Wrong role type
    "senior architect",
    "principal engineer",
    "staff engineer",
    "ios developer",
    "android developer",
    "react native",
    "full stack",
    "full-stack",
    "frontend",
    "backend",
    "php developer",
    "devops",
    "copywriter",
    "video editor",
    "snowflake",
    "Azure",
    "Power BI",
    "Tablue",
    "recruiter",

    # Contract/temp signals IN TITLE
    "contract role",
    "contract position",
    "fixed term",
    "6 month contract",
    "3 month contract",
    "12 month contract",
    "1 year contract",
    "(contract)",

    # Part-time
    "part time",
    "part-time",
    "(part time)",

    # Internship
    "internship",
    "(intern)",
    "intern -",

    # Citizenship/residency hard blocks IN TITLE
    "singaporean only",
    "citizen only",
    "citizens only",
    "pr only",
    "permanent resident only",
    "locals only",
    "local candidates",
    "us citizen",
    "gc only",
]

# ---------------------------------------------------------
# REMOTE SIGNALS
# ---------------------------------------------------------

REMOTE_KEYWORDS = [
    "remote",
    "work from home",
    "distributed",
    "anywhere",
    "global remote",
    "fully remote",
    "100% remote",
]

REMOTE_RESTRICTION_KEYWORDS = [
    "us only",
    "europe only",
    "must reside",
    "citizens only",
    "local candidates only",
    "based in the us",
    "based in usa",
    "united states only",
    "no sponsorship",
    "cannot sponsor",
    "must have work authorization",
    "citizens only",
    "visa not provided",
    "no visa sponsorship",
    "will not sponsor",
    "unable to sponsor",
    "green card required",
    "us citizen only",
    "usc only",
    "gc only",
    "security clearance required",
    "permanent resident required",
    "pr required",
    "must be authorized to work",
    "must be authorised to work",
    "citizen only",
    "citisen only",
    "resident only",
    "residence only",
    "right to work required",
]

# ---------------------------------------------------------
# VISA SIGNALS
# ---------------------------------------------------------

VISA_POSITIVE_KEYWORDS = [
    "visa sponsorship",
    "sponsorship available",
    "work visa",
    "will sponsor",
    "sponsor visa",
    "visa support",
    "relocation support",
    "international applicants",
    "open to international",
    "tier 2 sponsor",
    "skilled worker visa",
    "global talent",
]

VISA_NEGATIVE_KEYWORDS = [
    "no sponsorship",
    "cannot sponsor",
    "must have work authorization",
    "citizens only",
    "visa not provided",
    "no visa sponsorship",
    "will not sponsor",
    "unable to sponsor",
    "green card required",
    "us citizen only",
    "usc only",
    "gc only",
    "security clearance required",
    "permanent resident required",
    "pr required",
    "must be authorized to work",
    "must be authorised to work",
    "citizen only",
    "citisen only",
    "resident only",
    "residence only",
    "right to work required",
]

# ---------------------------------------------------------
# COUNTRY DETECTION
# ---------------------------------------------------------

COUNTRY_KEYWORDS = {
    "United Kingdom": [
        "united kingdom", "uk", "england",
        "london", "manchester", "birmingham", "edinburgh",
    ],
    "Australia": [
        "australia", "sydney", "melbourne",
        "brisbane", "perth", "canberra",
    ],
    "Singapore": [
        "singapore", "sg",
    ],
    "Germany": [
        "germany", "berlin", "munich", "hamburg", "frankfurt",
    ],
    "Netherlands": [
        "netherlands", "amsterdam", "rotterdam",
    ],
    "Canada": [
        "canada", "toronto", "vancouver", "montreal",
    ],
    "Japan": [
        "japan", "tokyo", "osaka",
    ],
    "India": [
        "india", "hyderabad", "bangalore", "bengaluru",
        "mumbai", "pune", "chennai", "telangana",
    ],
}

# ---------------------------------------------------------
# INTERNATIONAL TARGETS
# Priority order per Adarsh's stated preference.
# ---------------------------------------------------------

INTERNATIONAL_COUNTRY_PRIORITY = [
    "United Kingdom",
    "Australia",
    "Singapore",
    "Netherlands",
    "Germany",
    "Canada",
    "Japan",
]

# ---------------------------------------------------------
# ALERT CATEGORIES
# Thresholds deliberately lowered from 70-72 to 60-65.
# Previous thresholds + broken scoring = zero matches.
# ---------------------------------------------------------
ALERT_CATEGORIES = [
    {
        "name": "Remote",
        "kind": "remote_global",
        "threshold": 50,
        "priority": 1,
    },
    {
        "name": "Hyderabad",
        "kind": "hyderabad",
        "threshold": 45,
        "priority": 2,
    },
    {
        "name": "International Visa Confirmed",
        "kind": "international_visa",
        "threshold": 60,
        "priority": 3,
    },
    {
        "name": "International Apply and Verify",
        "kind": "international_any",
        "threshold": 70,
        "priority": 4,
    },
]

# ---------------------------------------------------------
# JOB FEEDS
# Removed: greenhouse, lever, wellfound (0% hit rate)
# Added: Adzuna multi-country, extra Remotive searches,
#        LinkedIn guest API for Hyderabad, RemoteOK
# ---------------------------------------------------------

JOB_FEEDS = [

    # -------------------------------------------------------
    # SINGAPORE — MCF Government API
    # -------------------------------------------------------
    {
        "name": "MCF Singapore Data Analyst",
        "kind": "mcf_api",
        "url": (
            "https://api.mycareersfuture.gov.sg/"
            "v2/jobs?search=data+analyst&limit=30&freshness=7"
        ),
        "country_hint": "Singapore",
    },
    {
        "name": "RemoteOK Data Analyst",
        "kind": "remoteok_api",
        "url": "https://remoteok.io/api?tag=data-analyst",
        "country_hint": "Remote",
    },
    {
        "name": "RemoteOK Business Intelligence",
        "kind": "remoteok_api",
        "url": "https://remoteok.io/api?tag=analyst",
        "country_hint": "Remote",
    },
    {
        "name": "Jobicy Data Analytics Remote",
        "kind": "jobicy_api",
        "url": "https://jobicy.com/api/v2/remote-jobs?count=50&tag=data-analyst",
        "country_hint": "Remote",
    },
    # {
    #     "name": "Reed UK Data Analyst",
    #     "kind": "reed_api",
    #     "search_term": "data analyst",
    #     "location": "London",
    #     "country_hint": "United Kingdom",
    # },
    # {
    #     "name": "Reed UK Analytics Engineer",
    #     "kind": "reed_api",
    #     "search_term": "analytics engineer",
    #     "location": "United Kingdom",
    #     "country_hint": "United Kingdom",
    # },
    {
        "name": "Jobicy Business Intelligence Remote",
        "kind": "jobicy_api",
        "url": "https://jobicy.com/api/v2/remote-jobs?count=50&tag=business-intelligence",
        "country_hint": "Remote",
    },
    {
        "name": "MCF Singapore Analytics",
        "kind": "mcf_api",
        "url": (
            "https://api.mycareersfuture.gov.sg/"
            "v2/jobs?search=business+intelligence&limit=30&freshness=7"
        ),
        "country_hint": "Singapore",
    },

    # -------------------------------------------------------
    # REMOTE — Remotive API (confirmed working)
    # -------------------------------------------------------
    {
        "name": "Remotive Data Remote",
        "kind": "remotive_api",
        "url": "https://remotive.com/api/remote-jobs?search=data",
        "country_hint": "Remote",
    },
    {
        "name": "Remotive Analytics Engineer",
        "kind": "remotive_api",
        "url": "https://remotive.com/api/remote-jobs?search=analytics+engineer",
        "country_hint": "Remote",
    },
    {
        "name": "Remotive Looker",
        "kind": "remotive_api",
        "url": "https://remotive.com/api/remote-jobs?search=looker",
        "country_hint": "Remote",
    },
    {
        "name": "Remotive Business Intelligence",
        "kind": "remotive_api",
        "url": "https://remotive.com/api/remote-jobs?search=business+intelligence",
        "country_hint": "Remote",
    },

    # -------------------------------------------------------
    # EU — Arbeitnow (visa_sponsorship field enforced in parser)
    # -------------------------------------------------------
    {
        "name": "Arbeitnow EU Visa Tech",
        "kind": "arbeitnow_api",
        "url": "https://www.arbeitnow.com/api/job-board-api?page=1",
        "country_hint": "Germany",
    },
    {
        "name": "Arbeitnow EU Visa Tech Page 2",
        "kind": "arbeitnow_api",
        "url": "https://www.arbeitnow.com/api/job-board-api?page=2",
        "country_hint": "Germany",
    },

    # -------------------------------------------------------
    # ADZUNA — Confirmed working, multi-country coverage
    # Requires ADZUNA_APP_ID and ADZUNA_APP_KEY in .env
    # -------------------------------------------------------
    {
        "name": "Adzuna UK Data Analyst",
        "kind": "adzuna_api",
        "country_code": "gb",
        "search_term": "data analyst",
        "country_hint": "United Kingdom",
    },
    {
        "name": "Adzuna UK Analytics Engineer",
        "kind": "adzuna_api",
        "country_code": "gb",
        "search_term": "analytics engineer",
        "country_hint": "United Kingdom",
    },
    {
        "name": "Adzuna UK Looker",
        "kind": "adzuna_api",
        "country_code": "gb",
        "search_term": "looker",
        "country_hint": "United Kingdom",
    },
    {
        "name": "Adzuna Australia Data Analyst",
        "kind": "adzuna_api",
        "country_code": "au",
        "search_term": "data analyst",
        "country_hint": "Australia",
    },
    {
        "name": "Adzuna Australia Analytics Engineer",
        "kind": "adzuna_api",
        "country_code": "au",
        "search_term": "analytics engineer",
        "country_hint": "Australia",
    },
    {
        "name": "Adzuna Canada Data Analyst",
        "kind": "adzuna_api",
        "country_code": "ca",
        "search_term": "data analyst",
        "country_hint": "Canada",
    },
    {
        "name": "Adzuna Netherlands Data Analyst",
        "kind": "adzuna_api",
        "country_code": "nl",
        "search_term": "data analyst",
        "country_hint": "Netherlands",
    },
    {
        "name": "Adzuna Singapore Data Analyst",
        "kind": "adzuna_api",
        "country_code": "sg",
        "search_term": "data analyst",
        "country_hint": "Singapore",
    },
    {
        "name": "Adzuna India Data Analyst",
        "kind": "adzuna_api",
        "country_code": "in",
        "search_term": "data analyst hyderabad",
        "country_hint": "India",
    },
    {
        "name": "Adzuna India BI Analyst",
        "kind": "adzuna_api",
        "country_code": "in",
        "search_term": "business intelligence hyderabad",
        "country_hint": "India",
    },
    {
        "name": "Adzuna India Analytics Engineer",
        "kind": "adzuna_api",
        "country_code": "in",
        "search_term": "analytics engineer",
        "country_hint": "India",
    },

    # -------------------------------------------------------
    # LINKEDIN GUEST — Hyderabad (no auth required)
    # -------------------------------------------------------
    {
        "name": "LinkedIn Hyderabad Data Analyst",
        "kind": "linkedin_guest",
        "url": (
            "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"
            "?keywords=data%20analyst&location=Hyderabad%2C%20Telangana%2C%20India&start=0"
        ),
        "country_hint": "India",
    },
    {
        "name": "LinkedIn Hyderabad Analytics Engineer",
        "kind": "linkedin_guest",
        "url": (
            "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"
            "?keywords=analytics%20engineer&location=Hyderabad%2C%20Telangana%2C%20India&start=0"
        ),
        "country_hint": "India",
    },
    {
        "name": "LinkedIn Hyderabad Looker",
        "kind": "linkedin_guest",
        "url": (
            "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"
            "?keywords=looker&location=Hyderabad%2C%20Telangana%2C%20India&start=0"
        ),
        "country_hint": "India",
    },
    {
        "name": "LinkedIn Hyderabad BI",
        "kind": "linkedin_guest",
        "url": (
            "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"
            "?keywords=business%20intelligence&location=Hyderabad%2C%20Telangana%2C%20India&start=0"
        ),
        "country_hint": "India",
    },
    # --- APIFY ACTORS ---
    {
        "name": "Apify Naukri Hyderabad Data Analyst",
        "kind": "apify_actor",
        "actor_id": "blackfalcondata/naukri-jobs-feed",
        "actor_input": {
            "keyword": "data analyst",
            "location": "Hyderabad",
            "count": 50,
        },
        "country_hint": "India",
    },
    {
        "name": "Apify Naukri Hyderabad BI",
        "kind": "apify_actor",
        "actor_id": "blackfalcondata/naukri-jobs-feed",
        "actor_input": {
            "keyword": "business intelligence",
            "location": "Hyderabad",
            "count": 50,
        },
        "country_hint": "India",
    },
    {
        "name": "Apify Indeed UK Data Analyst",
        "kind": "apify_actor",
        "actor_id": "misceres/indeed-scraper",
        "actor_input": {
            "position": "data analyst",
            "country": "UK",
            "location": "London",
            "maxItems": 50,
        },
        "country_hint": "United Kingdom",
    },
]
