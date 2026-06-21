import argparse
import hashlib
import time

from config import ALERT_CATEGORIES

from database import (
    finish_run,
    get_current_lookback_hours,
    init_db,
    is_alert_sent,
    mark_alert_sent,
    save_job,
    start_run,
)

from email_sender import (
    format_job_digest,
    send_email,
)

from logger import log_message

from scorer import (
    score_job,
    score_job_for_category,
)

from scraper import fetch_jobs


# ---------------------------------------------------------
# DEDUP KEY
# ---------------------------------------------------------

def normalize_key(title, company):

    raw = (
        f"{title.lower().strip()}|"
        f"{company.lower().strip()}"
    )

    return hashlib.md5(
        raw.encode()
    ).hexdigest()


# ---------------------------------------------------------
# MAIN RUNNER
# ---------------------------------------------------------

def run(
    send_digest=True,
    use_gemini=True
):

    total_start = time.time()

    log_message(
        "=================================================="
    )

    log_message(
        "JOB BOT RUN STARTED"
    )

    # -----------------------------------------------------
    # INIT
    # -----------------------------------------------------

    init_db()

    lookback_hours = (
        get_current_lookback_hours()
    )

    run_id = start_run(
        lookback_hours
    )

    # -----------------------------------------------------
    # FETCH JOBS
    # -----------------------------------------------------

    jobs = fetch_jobs(
        lookback_hours=lookback_hours
    )

    log_message(
        f"Fetched {len(jobs)} total jobs"
    )

    # -----------------------------------------------------
    # DEDUPLICATION
    # -----------------------------------------------------

    seen_norm_keys = set()

    unique_jobs = []

    duplicate_count = 0

    for job in jobs:

        key = normalize_key(
            job.get("title", ""),
            job.get("company", "")
        )

        if key in seen_norm_keys:

            duplicate_count += 1

            continue

        seen_norm_keys.add(key)

        unique_jobs.append(job)

    log_message(
        f"Duplicates removed: "
        f"{duplicate_count}"
    )

    log_message(
        f"Unique jobs remaining: "
        f"{len(unique_jobs)}"
    )

    # -----------------------------------------------------
    # CATEGORY BUCKETS
    # -----------------------------------------------------

    matches_by_category = {

        category["name"]: []

        for category in ALERT_CATEGORIES
    }

    assigned_job_keys = set()

    emails_sent = 0

    scoring_failures = 0

    # -----------------------------------------------------
    # PROCESS JOBS
    # -----------------------------------------------------

    try:

        for index, job in enumerate(
            unique_jobs,
            start=1
        ):

            try:

                log_message(
                    f"Scoring "
                    f"{index}/{len(unique_jobs)} | "
                    f"{job['title']}"
                )

                base_scoring = score_job(
                    job
                )

                save_job(
                    job_id=job["job_id"],
                    title=job["title"],
                    company=job["company"],
                    location=job["location"],
                    url=job["url"],
                    score=base_scoring["score"],
                    country=base_scoring["country"],
                    visa_confirmed=base_scoring[
                        "visa_confirmed"
                    ],
                )

                norm_key = normalize_key(
                    job.get("title", ""),
                    job.get("company", "")
                )

                for category in ALERT_CATEGORIES:

                    if norm_key in assigned_job_keys:
                        break

                    match = score_job_for_category(
                        job,
                        category,
                        use_gemini=use_gemini
                    )

                    if not match:
                        continue

                    if is_alert_sent(
                        job["job_id"],
                        category["name"]
                    ):
                        continue

                    matches_by_category[
                        category["name"]
                    ].append(match)

                    assigned_job_keys.add(
                        norm_key
                    )

            except Exception as exc:

                scoring_failures += 1

                log_message(
                    f"Scoring FAILED | "
                    f"{job.get('title')} | "
                    f"{exc}"
                )

        # -------------------------------------------------
        # TOTAL MATCHES
        # -------------------------------------------------

        total_matches = sum(
            len(matches)
            for matches in matches_by_category.values()
        )

        log_message(
            f"Total category matches: "
            f"{total_matches}"
        )

        # -------------------------------------------------
        # EMAIL DIGESTS
        # -------------------------------------------------

        if total_matches and send_digest:

            for (
                category_name,
                matches
            ) in matches_by_category.items():

                if not matches:
                    continue

                body = format_job_digest(
                    matches[:30],
                    category=category_name
                )

                send_email(
                    f"Job Search Bot - "
                    f"{category_name}",
                    body
                )

                emails_sent += 1

                log_message(
                    f"EMAIL SENT | "
                    f"{category_name} | "
                    f"{len(matches)} jobs"
                )

                for match in matches:

                    mark_alert_sent(
                        match["job_id"],
                        category_name,
                        match["score"]
                    )

        # -------------------------------------------------
        # COMPLETE
        # -------------------------------------------------

        total_duration = round(
            time.time() - total_start,
            2
        )

        finish_run(
            run_id,
            len(unique_jobs),
            total_matches,
            emails_sent,
            status="success"
        )

        log_message(
            f"RUN SUCCESS | "
            f"jobs={len(unique_jobs)} | "
            f"matches={total_matches} | "
            f"emails={emails_sent} | "
            f"failures={scoring_failures} | "
            f"duration={total_duration}s"
        )

    except Exception as exc:

        finish_run(
            run_id,
            len(unique_jobs),
            0,
            emails_sent,
            status="failed",
            notes=str(exc)
        )

        log_message(
            f"RUN FAILED | {exc}"
        )

        raise


# ---------------------------------------------------------
# CLI
# ---------------------------------------------------------

if __name__ == "__main__":

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--no-email",
        action="store_true"
    )

    parser.add_argument(
        "--no-gemini",
        action="store_true"
    )

    args = parser.parse_args()

    run(
        send_digest=not args.no_email,
        use_gemini=not args.no_gemini
    )