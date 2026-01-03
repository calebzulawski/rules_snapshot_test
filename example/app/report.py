import datetime


def generate_timestamps():
    now = datetime.datetime.now(datetime.timezone.utc)
    return {
        "utc": now,
        "est": now.astimezone(datetime.timezone(datetime.timedelta(hours=-5))),
    }


def generate_lines():
    stamps = generate_timestamps()
    utc = stamps["utc"]
    est = stamps["est"]
    utc_line = "The current time in UTC is {}".format(utc.isoformat())
    est_line = "The current time in EST is {}".format(est.isoformat())
    return [utc_line, est_line]
