import json
import os
from datetime import datetime
from logger import log_message

SHEET_ID = "1Vh44UdwVbt7IXWoS5kXafVTMxIChrCVKYzbDe-7WCmg"


def append_jobs_to_sheet(matches_by_category):
    """Appends matched jobs to the Google Sheet tracker."""

    try:
        import gspread
        from google.oauth2.service_account import Credentials
    except ImportError:
        log_message("gspread not installed — skipping sheet update")
        return

    creds_json = os.getenv("GOOGLE_SHEETS_CREDENTIALS")
    if not creds_json:
        log_message("GOOGLE_SHEETS_CREDENTIALS not set — skipping sheet update")
        return

    try:
        creds_dict = json.loads(creds_json)
        scopes = ["https://www.googleapis.com/auth/spreadsheets"]
        creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        client = gspread.authorize(creds)
        sheet = client.open_by_key(SHEET_ID).sheet1

        today = datetime.now().strftime("%d-%b")
        rows = []

        for category_name, matches in matches_by_category.items():
            for job in matches:

                profile_match = "; ".join(job.get("reasons", []))
                if len(profile_match) > 300:
                    profile_match = profile_match[:300] + "..."

                unique_key = job.get("job_id", "")[:20]

                row = [
                    today,                        # A: Email Date
                    category_name,                # B: Category
                    job.get("title", ""),          # C: Role
                    job.get("company", ""),        # D: Company
                    job.get("location", ""),       # E: Location
                    job.get("score", ""),          # F: Score
                    job.get("country", "Unknown"), # G: Country
                    profile_match,                 # H: Profile Match
                    job.get("url", ""),            # I: Apply Link
                    unique_key,                    # J: Unique Key
                ]
                rows.append(row)

        if rows:
            sheet.append_rows(rows, value_input_option="USER_ENTERED")
            log_message(f"Google Sheet updated — {len(rows)} jobs added")
        else:
            log_message("No jobs to add to Google Sheet")

    except Exception as exc:
        log_message(f"Google Sheet update failed: {exc}")