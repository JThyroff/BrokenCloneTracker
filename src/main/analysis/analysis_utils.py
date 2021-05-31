import portion
from portion import Interval

from src.main.data import FileChange, DiffDescription, CloneFindingChurn, CloneFinding


def is_file_affected_at_file_changes(file_uniform_path: str, affected_files: [FileChange]) -> bool:
    return file_uniform_path in [e.uniform_path for e in affected_files]


def are_left_lines_affected_at_diff(raw_start_line: int, raw_end_line: int, diff_desc: DiffDescription) -> bool:
    raw_interval: Interval = portion.closedopen(raw_start_line, raw_end_line)

    left_line_interval: Interval
    for left_line_interval in diff_desc.left_change_line_intervals:
        if raw_interval.overlaps(left_line_interval):
            return True

    return False


def filter_clone_finding_churn_by_file(file_uniform_paths: [str],
                                       clone_finding_churn: CloneFindingChurn) -> CloneFindingChurn:
    """filter a clone finding churn by files. All findings will be reduced to the one where all files in the given
    list are affected"""

    def file_filter(x: CloneFinding) -> bool:
        for file_path in file_uniform_paths:
            # if one file not affected return False
            if not (x.location.uniform_path == file_path or file_path in [e.uniform_path for e in x.sibling_locations]):
                return False
        return True

    clone_finding_churn.added_findings = list(filter(lambda x: file_filter(x), clone_finding_churn.added_findings))
    clone_finding_churn.findings_added_in_branch = list(
        filter(lambda x: file_filter(x), clone_finding_churn.findings_added_in_branch))
    clone_finding_churn.findings_in_changed_code = list(
        filter(lambda x: file_filter(x), clone_finding_churn.findings_in_changed_code))
    clone_finding_churn.removed_findings = list(filter(lambda x: file_filter(x), clone_finding_churn.removed_findings))
    clone_finding_churn.findings_removed_in_branch = list(filter(lambda x: file_filter(x),
                                                                 clone_finding_churn.findings_removed_in_branch))
    return clone_finding_churn


def is_file_affected_at_clone_finding_churn(file_uniform_path: str, clone_finding_churn: CloneFindingChurn) -> bool:
    """returns whether given file is affected by given CloneFindingChurn."""
    clone_finding_churn = filter_clone_finding_churn_by_file(file_uniform_path, clone_finding_churn)
    return not clone_finding_churn.is_empty()


def get_interval_length(interval: Interval) -> int:
    if interval.empty:
        return 0
    return interval.upper - interval.lower


def correct_lines(loc_start_line: int, loc_end_line: int, diff_desc: DiffDescription):
    """ While tracking the relevant region of a broken clone by its affected lines, it could be the case
    that the relevant lines of one instance of the code clone are shifted due to code modifications in the lines
    above. This function addresses this issue and corrects the given line numbers respecting the diff.
    It basically adds the diff of the lines above the relevant part to its line numbers.
    :return the corrected line number respecting the diff"""
    if "line-based" not in diff_desc.name.value:
        raise ValueError('DiffDescription should be a kind of line based diff.')
    loc_interval: Interval = portion.closedopen(loc_start_line, loc_end_line)
    i = 0
    while i < len(diff_desc.left_change_line_intervals):
        left_length = get_interval_length(diff_desc.left_change_line_intervals[i])
        right_length = get_interval_length(diff_desc.right_change_line_intervals[i])
        # [4,6) -> [4,5)
        x = right_length - left_length
        if diff_desc.left_change_line_intervals[i] < loc_interval:
            # need to adjust the lines
            loc_start_line = loc_start_line + x
            loc_end_line = loc_end_line + x
        elif diff_desc.left_change_line_intervals[i] in loc_interval:
            # apply change only to end line as start line stays unaffected
            loc_end_line = loc_end_line + x
        elif diff_desc.left_change_line_intervals[i] > loc_interval:
            # return cause intervals are sorted -> No important intervals will follow
            return loc_start_line, loc_end_line
        elif diff_desc.left_change_line_intervals[i] <= loc_interval:
            loc_end_line = loc_end_line + x
        elif diff_desc.left_change_line_intervals[i] >= loc_interval:
            # loc_start_line = loc_start_line + x
            raise NotImplementedError("I currently do not know how to handle this special case")
        i = i + 1

    return loc_start_line, loc_end_line
