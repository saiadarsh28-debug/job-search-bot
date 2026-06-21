from logger import log_message


SOURCE_STATS = {}


def register_source_result(
    source_name,
    status,
    jobs_found,
    duration=0,
):

    if source_name not in SOURCE_STATS:

        SOURCE_STATS[source_name] = {
            "runs": 0,
            "successes": 0,
            "failures": 0,
            "empty_runs": 0,
            "jobs_total": 0,
            "last_status": None,
            "total_duration": 0,
        }

    stats = SOURCE_STATS[source_name]

    stats["runs"] += 1
    stats["jobs_total"] += jobs_found
    stats["last_status"] = status
    stats["total_duration"] += duration

    if status == "success":

        stats["successes"] += 1

        if jobs_found == 0:
            stats["empty_runs"] += 1

    else:

        stats["failures"] += 1

    log_message(
        f"SOURCE HEALTH | "
        f"{source_name} | "
        f"status={status} | "
        f"runs={stats['runs']} | "
        f"success={stats['successes']} | "
        f"failures={stats['failures']} | "
        f"empty={stats['empty_runs']} | "
        f"jobs={stats['jobs_total']}"
    )


def source_should_run(source_name):

    stats = SOURCE_STATS.get(source_name)

    if not stats:
        return True

    # -----------------------------------------------------
    # disable heavily failing sources
    # -----------------------------------------------------

    if stats["failures"] >= 5:

        log_message(
            f"Source skipped due to repeated failures: "
            f"{source_name}"
        )

        return False

    # -----------------------------------------------------
    # disable chronically empty sources
    # -----------------------------------------------------

    if (
        stats["runs"] >= 10
        and stats["jobs_total"] == 0
    ):

        log_message(
            f"Source skipped due to chronic emptiness: "
            f"{source_name}"
        )

        return False

    return True


def get_source_summary():

    return SOURCE_STATS