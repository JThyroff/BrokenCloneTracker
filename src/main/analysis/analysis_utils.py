from enum import Enum

import portion
from portion import Interval

from src.main.data import FileChange, DiffDescription, CloneFindingChurn, CloneFinding, CommitAlert


class Affectedness(Enum):
    NOT_AFFECTED = 1
    AFFECTED_BY_COMMIT = 2
    AFFECTED_CRITICAL = 3

    def __mul__(self, other):
        return self.value * other.value

    def __rmul__(self, other):
        return self.value * other.value


class AnalysisResult:
    """A class representing one analysis result"""

    def __init__(self, project: str, first_commit: int, most_recent_commit: int, analysed_until: int,
                 commit_alert: CommitAlert, corrected_clone_start_line: int, corrected_clone_end_line: int,
                 corrected_sibling_start_line: int, corrected_sibling_end_line: int,
                 file_affected_count: int,
                 file_affected_critical_count: int,
                 sibling_affected_count: int,
                 sibling_affected_critical_count: int, one_file_affected_count: int, both_files_affected_count: int,
                 one_file_affected_critical_count: int, both_files_affected_critical_count: int,
                 clone_findings_count: int):
        # project meta
        self.project = project
        self.first_commit = first_commit
        self.most_recent_commit = most_recent_commit
        self.analysed_until = analysed_until
        self.commit_alert = commit_alert
        # corrected line intervals
        self.corrected_clone_start_line = corrected_clone_start_line
        self.corrected_clone_end_line = corrected_clone_end_line
        self.corrected_sibling_start_line = corrected_sibling_start_line
        self.corrected_sibling_end_line = corrected_sibling_end_line
        # how often a file was affected by a commit and how often it was affected in the relevant text passage
        self.file_affected_count = file_affected_count
        self.file_affected_critical_count = file_affected_critical_count
        self.sibling_affected_count = sibling_affected_count
        self.sibling_affected_critical_count = sibling_affected_critical_count
        # how often only one file was affected by a commit or how often both - and how often it was critical
        self.one_file_affected_count = one_file_affected_count
        self.both_files_affected_count = both_files_affected_count
        self.one_file_affected_critical_count = one_file_affected_critical_count
        self.both_files_affected_critical_count = both_files_affected_critical_count
        # later introduced clone findings where both files are affected
        # TODO? Lacking of a critical classification for introduced clones. Happens not that often
        self.clone_findings_count = clone_findings_count

    def __eq__(self, other):
        if not isinstance(other, AnalysisResult):
            return NotImplemented
        elif self is other:
            return True
        else:
            other: AnalysisResult
            return self.project == other.project \
                   and self.first_commit == other.first_commit \
                   and self.most_recent_commit == other.most_recent_commit \
                   and self.analysed_until == other.analysed_until \
                   and self.commit_alert == other.commit_alert \
                   and self.file_affected_count == other.file_affected_count \
                   and self.file_affected_critical_count == other.file_affected_critical_count \
                   and self.sibling_affected_count == other.sibling_affected_count \
                   and self.sibling_affected_critical_count == other.sibling_affected_critical_count \
                   and self.one_file_affected_count == other.one_file_affected_count \
                   and self.both_files_affected_count == other.both_files_affected_count \
                   and self.one_file_affected_critical_count == other.one_file_affected_critical_count \
                   and self.both_files_affected_critical_count == other.both_files_affected_critical_count \
                   and self.clone_findings_count == other.clone_findings_count


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

    for left_interval, right_interval in zip(diff_desc.left_change_line_intervals,
                                             diff_desc.right_change_line_intervals):
        left_length = get_interval_length(left_interval)
        right_length = get_interval_length(right_interval)
        # [4,6) -> [4,5)
        x = right_length - left_length
        if left_interval < loc_interval:
            # need to adjust the lines
            loc_start_line = loc_start_line + x
            loc_end_line = loc_end_line + x
        elif left_interval in loc_interval:
            # apply change only to end line as start line stays unaffected
            loc_end_line = loc_end_line + x
        elif left_interval > loc_interval:
            # return cause intervals are sorted -> No important intervals will follow
            return loc_start_line, loc_end_line
        elif left_interval <= loc_interval:
            loc_end_line = loc_end_line + x
        elif left_interval >= loc_interval:
            # loc_start_line = loc_start_line + x
            raise NotImplementedError("I currently do not know how to handle this special case")

    return loc_start_line, loc_end_line
