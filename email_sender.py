import smtplib
import ssl
import time
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from config import (
    EMAIL_PASSWORD,
    EMAIL_RECEIVER,
    EMAIL_SENDER,
)

from logger import log_message


SMTP_SERVER = "smtp.gmail.com"

SMTP_PORT = 465

MAX_EMAIL_RETRIES = 3


def format_job_digest(
    matches,
    category="Jobs"
):

    lines = []

    lines.append(
        f"<h2>{category} - "
        f"{len(matches)} matches</h2>"
    )

    lines.append("<hr>")

    for index, job in enumerate(matches, start=1):

        reasons = job.get(
            "reasons",
            []
        )

        eligibility = job.get(
            "eligibility_reasons",
            []
        )

        lines.append(
            f"""
            <h3>
                {index}. {job['title']}
            </h3>

            <p>
                <b>Company:</b>
                {job['company']}<br>

                <b>Location:</b>
                {job['location']}<br>

                <b>Score:</b>
                {job['score']}<br>

                <b>Country:</b>
                {job.get('country', 'Unknown')}<br>

                <b>Visa:</b>
                {job.get('visa_confirmed', False)}
            </p>

            <p>
                <b>Profile Match:</b><br>
                {'<br>'.join(reasons)}
            </p>

            <p>
                <b>Eligibility:</b><br>
                {'<br>'.join(eligibility)}
            </p>

            <p>
                <a href="{job['url']}">
                    Apply Here
                </a>
            </p>

            <hr>
            """
        )

    return "\n".join(lines)


def send_email(subject, body):

    if not EMAIL_SENDER:

        raise ValueError(
            "EMAIL_SENDER missing"
        )

    if not EMAIL_PASSWORD:

        raise ValueError(
            "EMAIL_PASSWORD missing"
        )

    if not EMAIL_RECEIVER:

        raise ValueError(
            "EMAIL_RECEIVER missing"
        )

    message = MIMEMultipart(
        "alternative"
    )

    message["Subject"] = subject
    message["From"] = EMAIL_SENDER
    message["To"] = EMAIL_RECEIVER

    html_part = MIMEText(
        body,
        "html"
    )

    message.attach(html_part)

    last_error = None

    for attempt in range(
        1,
        MAX_EMAIL_RETRIES + 1
    ):

        try:

            log_message(
                f"Sending email "
                f"attempt "
                f"{attempt}/"
                f"{MAX_EMAIL_RETRIES}"
            )

            context = ssl.create_default_context()

            with smtplib.SMTP_SSL(
                SMTP_SERVER,
                SMTP_PORT,
                context=context,
                timeout=30,
            ) as server:

                server.login(
                    EMAIL_SENDER,
                    EMAIL_PASSWORD
                )

                server.sendmail(
                    EMAIL_SENDER,
                    EMAIL_RECEIVER,
                    message.as_string(),
                )

            log_message(
                f"Email sent successfully: "
                f"{subject}"
            )

            return

        except Exception as exc:

            last_error = exc

            log_message(
                f"Email send failed "
                f"(attempt {attempt}): "
                f"{exc}",
                level="ERROR"
            )

            time.sleep(
                5 * attempt
            )

    raise RuntimeError(
        f"All email attempts failed: "
        f"{last_error}"
    )