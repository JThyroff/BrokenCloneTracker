import portion
from portion import Interval

from src.main.data import FileChange, DiffDescription


def is_file_affected_at_file_changes(file: str, affected_files: [FileChange]) -> bool:
    return file in [e.uniform_path for e in affected_files]


def are_left_lines_affected_at_diff(raw_start_line: int, raw_end_line: int, diff_desc: DiffDescription) -> bool:
    raw_interval: Interval = portion.closedopen(raw_start_line, raw_end_line)

    left_line_interval: Interval
    for left_line_interval in diff_desc.left_change_line_intervals:
        if not raw_interval.intersection(left_line_interval).empty:
            return True

    return False
