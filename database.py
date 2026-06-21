import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta

from logger import log_message

# ---------------------------------------------------------
# DATABASE PATH
# ---------------------------------------------------------

DB_PATH = os.path.join(
    os.path.dirname(__file__),
    'data',
    'jobs.db'
)

# ---------------------------------------------------------
# CONNECTION HANDLER
# ---------------------------------------------------------

@contextmanager
def get_connection():

    conn = sqlite3.connect(
        DB_PATH,
        timeout=30
    )

    try:

        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")

        yield conn

        conn.commit()

    except Exception:

        conn.rollback()
        raise

    finally:

        conn.close()

# ---------------------------------------------------------
# DATABASE INIT
# ---------------------------------------------------------

def init_db():
    """Creates database and tables."""

    with get_connection() as conn:

        cursor = conn.cursor()

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS seen_jobs (
                id               INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id           TEXT UNIQUE,
                title            TEXT,
                company          TEXT,
                location         TEXT,
                url              TEXT,
                score            INTEGER,
                country          TEXT,
                visa_confirmed   BOOLEAN,
                date_found       TIMESTAMP,
                applied          BOOLEAN DEFAULT FALSE,
                outreach_sent    BOOLEAN DEFAULT FALSE
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sent_alerts (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id      TEXT,
                category    TEXT,
                score       INTEGER,
                date_sent   TIMESTAMP,
                UNIQUE(job_id, category)
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS run_history (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                started_at      TIMESTAMP,
                finished_at     TIMESTAMP,
                lookback_hours  INTEGER,
                jobs_fetched    INTEGER DEFAULT 0,
                matches_found   INTEGER DEFAULT 0,
                emails_sent     INTEGER DEFAULT 0,
                status          TEXT,
                notes           TEXT
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS job_descriptions (
                job_id       TEXT PRIMARY KEY,
                source       TEXT,
                url          TEXT,
                description  TEXT,
                fetched_at   TIMESTAMP
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS source_runs (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                source_name  TEXT,
                status       TEXT,
                jobs_found   INTEGER DEFAULT 0,
                error        TEXT,
                run_at       TIMESTAMP
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS ai_scores (
                cache_key    TEXT PRIMARY KEY,
                job_id       TEXT,
                category     TEXT,
                score        INTEGER,
                reasons      TEXT,
                model        TEXT,
                scored_at    TIMESTAMP
            )
        ''')

    log_message("Database initialized")

# ---------------------------------------------------------
# RUN MANAGEMENT
# ---------------------------------------------------------

def get_completed_run_count():

    with get_connection() as conn:

        cursor = conn.cursor()

        cursor.execute(
            "SELECT COUNT(*) "
            "FROM run_history "
            "WHERE status = 'success'"
        )

        count = cursor.fetchone()[0]

    return count


def get_current_lookback_hours():
    """
    First 4 successful runs:
    scan last 7 days.

    Afterwards:
    scan last 24 hours.
    """

    completed_runs = get_completed_run_count()

    lookback = 168 if completed_runs < 4 else 24

    log_message(
        f"Lookback hours selected: {lookback}"
    )

    return lookback


def start_run(lookback_hours):

    with get_connection() as conn:

        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO run_history (
                started_at,
                lookback_hours,
                status
            )
            VALUES (?, ?, ?)
        ''', (
            datetime.now(),
            lookback_hours,
            "running"
        ))

        run_id = cursor.lastrowid

    log_message(f"Run started: {run_id}")

    return run_id


def finish_run(
    run_id,
    jobs_fetched,
    matches_found,
    emails_sent,
    status="success",
    notes=""
):

    with get_connection() as conn:

        cursor = conn.cursor()

        cursor.execute('''
            UPDATE run_history
            SET
                finished_at = ?,
                jobs_fetched = ?,
                matches_found = ?,
                emails_sent = ?,
                status = ?,
                notes = ?
            WHERE id = ?
        ''', (
            datetime.now(),
            jobs_fetched,
            matches_found,
            emails_sent,
            status,
            notes,
            run_id
        ))

    log_message(
        f"Run completed | "
        f"status={status} | "
        f"jobs={jobs_fetched} | "
        f"matches={matches_found} | "
        f"emails={emails_sent}"
    )

# ---------------------------------------------------------
# SOURCE TRACKING
# ---------------------------------------------------------

def record_source_run(
    source_name,
    status,
    jobs_found=0,
    error=""
):

    with get_connection() as conn:

        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO source_runs (
                source_name,
                status,
                jobs_found,
                error,
                run_at
            )
            VALUES (?, ?, ?, ?, ?)
        ''', (
            source_name,
            status,
            jobs_found,
            error,
            datetime.now()
        ))

    log_message(
        f"Source run | "
        f"{source_name} | "
        f"status={status} | "
        f"jobs={jobs_found}"
    )

# ---------------------------------------------------------
# DESCRIPTION CACHE
# ---------------------------------------------------------

def get_cached_description(
    job_id,
    max_age_days=30
):

    with get_connection() as conn:

        cursor = conn.cursor()

        cursor.execute(
            '''
            SELECT description, fetched_at
            FROM job_descriptions
            WHERE job_id = ?
            ''',
            (job_id,)
        )

        row = cursor.fetchone()

    if not row:
        return None

    description, fetched_at = row

    if not fetched_at:
        return description

    fetched_time = datetime.fromisoformat(
        str(fetched_at)
    )

    if fetched_time < datetime.now() - timedelta(days=max_age_days):

        log_message(
            f"Description cache expired: {job_id}"
        )

        return None

    log_message(
        f"Description cache hit: {job_id}"
    )

    return description


def save_cached_description(
    job_id,
    source,
    url,
    description
):

    with get_connection() as conn:

        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO job_descriptions (
                job_id,
                source,
                url,
                description,
                fetched_at
            )
            VALUES (?, ?, ?, ?, ?)

            ON CONFLICT(job_id)
            DO UPDATE SET
                source = excluded.source,
                url = excluded.url,
                description = excluded.description,
                fetched_at = excluded.fetched_at
        ''', (
            job_id,
            source,
            url,
            description,
            datetime.now()
        ))

# ---------------------------------------------------------
# AI SCORE CACHE
# ---------------------------------------------------------

def get_cached_ai_score(
    job_id,
    category
):

    with get_connection() as conn:

        cursor = conn.cursor()

        cache_key = f"{job_id}|{category}"

        cursor.execute(
            '''
            SELECT score, reasons
            FROM ai_scores
            WHERE cache_key = ?
            ''',
            (cache_key,)
        )

        row = cursor.fetchone()

    if not row:
        return None

    log_message(
        f"AI cache hit | "
        f"{job_id} | "
        f"{category}"
    )

    return {
        "score": row[0],
        "reasons": row[1].split(" | ")
        if row[1] else []
    }


def save_cached_ai_score(
    job_id,
    category,
    score,
    reasons,
    model
):

    with get_connection() as conn:

        cursor = conn.cursor()

        cache_key = f"{job_id}|{category}"

        cursor.execute('''
            INSERT INTO ai_scores (
                cache_key,
                job_id,
                category,
                score,
                reasons,
                model,
                scored_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)

            ON CONFLICT(cache_key)
            DO UPDATE SET
                score = excluded.score,
                reasons = excluded.reasons,
                model = excluded.model,
                scored_at = excluded.scored_at
        ''', (
            cache_key,
            job_id,
            category,
            score,
            " | ".join(reasons),
            model,
            datetime.now()
        ))

# ---------------------------------------------------------
# JOB STORAGE
# ---------------------------------------------------------

def is_job_seen(job_id):

    with get_connection() as conn:

        cursor = conn.cursor()

        cursor.execute(
            '''
            SELECT id
            FROM seen_jobs
            WHERE job_id = ?
            ''',
            (job_id,)
        )

        result = cursor.fetchone()

    return result is not None


def save_job(
    job_id,
    title,
    company,
    location,
    url,
    score,
    country,
    visa_confirmed
):

    with get_connection() as conn:

        cursor = conn.cursor()

        try:

            cursor.execute('''
                INSERT INTO seen_jobs (
                    job_id,
                    title,
                    company,
                    location,
                    url,
                    score,
                    country,
                    visa_confirmed,
                    date_found
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                job_id,
                title,
                company,
                location,
                url,
                score,
                country,
                visa_confirmed,
                datetime.now()
            ))

        except sqlite3.IntegrityError:
            pass

# ---------------------------------------------------------
# ALERT TRACKING
# ---------------------------------------------------------

def is_alert_sent(
    job_id,
    category
):

    with get_connection() as conn:

        cursor = conn.cursor()

        cursor.execute(
            '''
            SELECT id
            FROM sent_alerts
            WHERE job_id = ?
            AND category = ?
            ''',
            (
                job_id,
                category
            )
        )

        result = cursor.fetchone()

    return result is not None


def mark_alert_sent(
    job_id,
    category,
    score
):

    with get_connection() as conn:

        cursor = conn.cursor()

        try:

            cursor.execute('''
                INSERT INTO sent_alerts (
                    job_id,
                    category,
                    score,
                    date_sent
                )
                VALUES (?, ?, ?, ?)
            ''', (
                job_id,
                category,
                score,
                datetime.now()
            ))

        except sqlite3.IntegrityError:
            pass

# ---------------------------------------------------------
# STATUS UPDATES
# ---------------------------------------------------------

def mark_applied(job_id):

    with get_connection() as conn:

        cursor = conn.cursor()

        cursor.execute(
            '''
            UPDATE seen_jobs
            SET applied = TRUE
            WHERE job_id = ?
            ''',
            (job_id,)
        )


def mark_outreach_sent(job_id):

    with get_connection() as conn:

        cursor = conn.cursor()

        cursor.execute(
            '''
            UPDATE seen_jobs
            SET outreach_sent = TRUE
            WHERE job_id = ?
            ''',
            (job_id,)
        )

# ---------------------------------------------------------
# DEBUG HELPERS
# ---------------------------------------------------------

def get_recent_jobs(limit=50):

    with get_connection() as conn:

        cursor = conn.cursor()

        cursor.execute('''
            SELECT *
            FROM seen_jobs
            ORDER BY date_found DESC
            LIMIT ?
        ''', (limit,))

        jobs = cursor.fetchall()

    return jobs


if __name__ == '__main__':

    init_db()

    print("Database initialized successfully!")