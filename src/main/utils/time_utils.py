from datetime import datetime


def timestamp_to_str(commit_timestamp) -> str:
    """get a printable string from a milliseconds commit timestamp"""
    date = datetime.fromtimestamp(float(str(commit_timestamp)[:-3]))
    d = date.strftime("%A, %B %d, %Y %H:%M")
    return str(commit_timestamp) + " (" + d + ")"
