from config import VISA_NEGATIVE_KEYWORDS, VISA_POSITIVE_KEYWORDS


def check_visa_signal(job_text):
    """Returns a simple visa signal based on text in the job post."""
    text = (job_text or "").lower()

    for keyword in VISA_NEGATIVE_KEYWORDS:
        if keyword in text:
            return {
                "visa_confirmed": False,
                "visa_status": "negative",
                "visa_reason": f"Found negative phrase: {keyword}",
            }

    for keyword in VISA_POSITIVE_KEYWORDS:
        if keyword in text:
            return {
                "visa_confirmed": True,
                "visa_status": "positive",
                "visa_reason": f"Found positive phrase: {keyword}",
            }

    return {
        "visa_confirmed": False,
        "visa_status": "unknown",
        "visa_reason": "No clear visa sponsorship phrase found.",
    }
