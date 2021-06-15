from datetime import datetime

from teamscale_client import TeamscaleClient


def add_branch(client: TeamscaleClient, commit_timestamp) -> str:
    return client.branch + ":" + str(commit_timestamp)


def timestamp_to_str(commit_timestamp) -> str:
    """get a printable string from a milliseconds commit timestamp"""
    date = datetime.fromtimestamp(float(str(commit_timestamp)[:-3]))
    d = date.strftime("%A, %B %d, %Y %H:%M")
    return str(commit_timestamp) + " (" + d + ")"


# https://stackoverflow.com/questions/4048651/python-function-to-convert-seconds-into-minutes-hours-and-days
intervals = (
    ('years', 31536000),
    ('months', 2628000),
    ('weeks', 604800),  # 60 * 60 * 24 * 7
    ('days', 86400),  # 60 * 60 * 24
    ('hours', 3600),  # 60 * 60
    ('minutes', 60),
    ('seconds', 1),
)


def display_time(milliseconds, granularity=2):
    milliseconds = int(str(milliseconds)[:-3])
    result = []

    for name, count in intervals:
        value = milliseconds // count
        if value:
            milliseconds -= value * count
            if value == 1:
                name = name.rstrip('s')
            result.append("{} {}".format(value, name))
    return ', '.join(result[:granularity])
