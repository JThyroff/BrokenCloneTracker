import portion
from portion import Interval


def get_interval_length(interval: Interval) -> int:
    if interval.empty:
        return 0
    return interval.upper - interval.lower


def list_to_interval_list(int_list: [int]) -> [Interval]:
    """Takes an int list and converts every two ints to an interval"""
    assert len(int_list) % 2 == 0
    to_return: [Interval] = []
    idx: int = 0
    while idx < len(int_list):
        to_return.append(
            portion.closedopen(int_list[idx], int_list[idx + 1]))
        idx = idx + 2
    return to_return


def overlaps_more_than_threshold(interval: Interval, other: Interval, threshold: float) -> bool:
    if threshold <= 0 or threshold > 1:
        raise ValueError("Threshold should be greater than zero and smaller equals one.")

    intersection = interval.intersection(other)

    if intersection.empty:
        return False

    interval_length = get_interval_length(interval)
    other_length = get_interval_length(other)
    minimum_overlap = min(interval_length, other_length) * threshold

    if get_interval_length(intersection) >= minimum_overlap:
        return True
    else:
        return False
