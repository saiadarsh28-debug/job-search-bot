from datetime import datetime
from pathlib import Path


LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)

LOG_FILE = LOG_DIR / "runtime.log"

MAX_LOG_SIZE_MB = 5


def rotate_logs_if_needed():

    if not LOG_FILE.exists():
        return

    size_mb = LOG_FILE.stat().st_size / (1024 * 1024)

    if size_mb < MAX_LOG_SIZE_MB:
        return

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    archived_file = LOG_DIR / f"runtime_{timestamp}.log"

    LOG_FILE.rename(archived_file)

    with open(LOG_FILE, "w", encoding="utf-8") as file:
        file.write(
            f"[{datetime.now()}] "
            f"Log rotated automatically\n"
        )


def log_message(message, level="INFO"):

    rotate_logs_if_needed()

    timestamp = datetime.now().strftime(
        "%Y-%m-%d %H:%M:%S"
    )

    line = f"[{timestamp}] [{level}] {message}"

    print(line)

    try:

        with open(
            LOG_FILE,
            "a",
            encoding="utf-8"
        ) as file:

            file.write(line + "\n")

    except Exception as exc:

        print(
            f"[LOGGER FAILURE] "
            f"Could not write to log file: {exc}"
        )






# from datetime import datetime
# from pathlib import Path

# LOG_DIR = Path("logs")
# LOG_DIR.mkdir(exist_ok=True)

# LOG_FILE = LOG_DIR / "runtime.log"


# def log_message(message):
#     timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

#     line = f"[{timestamp}] {message}"

#     print(line)

#     with open(LOG_FILE, "a", encoding="utf-8") as file:
#         file.write(line + "\n")