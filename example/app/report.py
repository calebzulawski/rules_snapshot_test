import datetime


def generate_lines():
    now = datetime.datetime.utcnow()
    utc_line = f"The current time in UTC is {now.isoformat()}Z"
    est_line = "The current time in EST is {}".format(
        (now - datetime.timedelta(hours=5)).strftime("%Y-%m-%d %H:%M:%S"),
    )
    return [utc_line, est_line]
