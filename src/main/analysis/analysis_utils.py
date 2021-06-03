from dataclasses import dataclass
from enum import Enum

import portion
from portion import Interval

from src.main.api.data import FileChange, DiffDescription, CloneFindingChurn, CloneFinding, CommitAlert, \
    CommitAlertContext


class TextSectionDeletedError(Exception):
    pass


class Affectedness(Enum):
    NOT_AFFECTED = 1
    AFFECTED_BY_COMMIT = 2
    AFFECTED_CRITICAL = 3

    def __mul__(self, other):
        return self.value * other.value

    def __rmul__(self, other):
        return self.value * other.value


@dataclass
class FileMetrics:
    corrected_instance_start_line: int
    corrected_instance_end_line: int
    file_affected_count: int
    instance_affected_count: int
    instance_deleted: bool


class AnalysisResult:
    """A class representing one analysis result"""

    def __init__(self, project: str, first_commit: int, most_recent_commit: int, analysed_until: int,
                 commit_alert: CommitAlert,
                 corrected_instance_start_line: int, corrected_instance_end_line: int,
                 corrected_sibling_start_line: int, corrected_sibling_end_line: int,
                 file_affected_count: int = 0,
                 instance_affected_critical_count: int = 0,
                 sibling_file_affected_count: int = 0,
                 sibling_instance_affected_critical_count: int = 0,
                 instance_deleted: bool = False,
                 sibling_deleted: bool = False,
                 one_file_affected_count: int = 0,
                 both_files_affected_count: int = 0,
                 one_instance_affected_critical_count: int = 0,
                 both_instances_affected_critical_count: int = 0,
                 clone_findings_count: int = 0):
        # project meta
        self.project = project
        self.first_commit = first_commit
        self.most_recent_commit = most_recent_commit
        self.analysed_until = analysed_until
        self.commit_alert = commit_alert
        # corrected line intervals
        self.corrected_instance_start_line = corrected_instance_start_line
        self.corrected_instance_end_line = corrected_instance_end_line
        self.corrected_sibling_start_line = corrected_sibling_start_line
        self.corrected_sibling_end_line = corrected_sibling_end_line
        # how often a file was affected by a commit and how often it was affected in the relevant text passage
        self.file_affected_count = file_affected_count
        self.instance_affected_critical_count = instance_affected_critical_count
        self.sibling_file_affected_count = sibling_file_affected_count
        self.sibling_instance_affected_critical_count = sibling_instance_affected_critical_count
        #
        self.instance_deleted = instance_deleted
        self.sibling_instance_deleted = sibling_deleted
        # how often only one file was affected by a commit or how often both - and how often it was critical
        self.one_file_affected_count = one_file_affected_count
        self.both_files_affected_count = both_files_affected_count
        self.one_instance_affected_critical_count = one_instance_affected_critical_count
        self.both_instances_affected_critical_count = both_instances_affected_critical_count
        # later introduced clone findings where both files are affected
        # TODO? Lacking of a critical classification for introduced clones. Happens not that often
        self.clone_findings_count = clone_findings_count

    def __str__(self):
        return ("Analysis Result for: " + str(self.project) + " first commit: " + str(self.first_commit) + " most recent commit: "
                + str(self.most_recent_commit) + " analysed until: " + str(self.analysed_until) + "\nCommit Alert: "
                + str(self.commit_alert) + "\nCorrected instance interval: [" + str(self.corrected_instance_start_line) + ","
                + str(self.corrected_instance_end_line) + ")\nCorrected sibling interval: [" + str(self.corrected_sibling_start_line) + ","
                + str(self.corrected_sibling_end_line) + ")\nFile affected count: " + str(self.file_affected_count)
                + "\nInstance affected critical count: " + str(self.instance_affected_critical_count) + "\nSibling file affected count: "
                + str(self.sibling_file_affected_count) + "\nSibling instance affected critical count: " + str(
                    self.sibling_instance_affected_critical_count)
                + "\nOne file affected count: " + str(self.one_file_affected_count) + "\nBoth files affected count: "
                + str(self.both_files_affected_count) + "\nOne file affected critical count: "
                + str(self.one_instance_affected_critical_count) + "\nBoth files affected critical count: "
                + str(self.both_instances_affected_critical_count) + "\nRelevant clone findings count: " + str(self.clone_findings_count))

    def set_file_args(self, corrected_instance_start_line, corrected_instance_end_line, file_affected_count,
                      file_affected_critical_count):
        self.corrected_instance_start_line = corrected_instance_start_line
        self.corrected_instance_end_line = corrected_instance_end_line
        self.file_affected_count = file_affected_count
        self.instance_affected_critical_count = file_affected_critical_count

    def set_sibling_args(self, corrected_sibling_start_line, corrected_sibling_end_line, sibling_affected_count,
                         sibling_affected_critical_count):
        self.corrected_sibling_start_line = corrected_sibling_start_line
        self.corrected_sibling_end_line = corrected_sibling_end_line
        self.sibling_file_affected_count = sibling_affected_count
        self.sibling_instance_affected_critical_count = sibling_affected_critical_count

    def get_file_args(self):
        return [self.corrected_instance_start_line, self.corrected_instance_end_line, self.file_affected_count,
                self.instance_affected_critical_count]

    def get_sibling_args(self):
        return [self.corrected_sibling_start_line, self.corrected_sibling_end_line, self.sibling_file_affected_count,
                self.sibling_instance_affected_critical_count]

    @staticmethod
    def from_alert(project: str, first_commit: int, most_recent_commit: int, analysed_until: int,
                   commit_alert: CommitAlert):
        """create an analysis result from project meta and given commit alert. All counters are initialized with 0."""
        ctx: CommitAlertContext = commit_alert.context
        return AnalysisResult(project, first_commit, most_recent_commit, analysed_until, commit_alert,
                              ctx.expected_clone_location.raw_start_line,
                              ctx.expected_clone_location.raw_end_line,
                              ctx.expected_sibling_location.raw_start_line,
                              ctx.expected_sibling_location.raw_end_line, *([0] * 9))

    def __eq__(self, other):
        if not isinstance(other, AnalysisResult):
            return NotImplemented
        elif self is other:
            return True
        else:
            other: AnalysisResult
            return (self.project == other.project
                    and self.first_commit == other.first_commit
                    and self.most_recent_commit == other.most_recent_commit
                    and self.analysed_until == other.analysed_until
                    and self.commit_alert == other.commit_alert
                    and self.file_affected_count == other.file_affected_count
                    and self.instance_affected_critical_count == other.instance_affected_critical_count
                    and self.sibling_file_affected_count == other.sibling_file_affected_count
                    and self.sibling_instance_affected_critical_count == other.sibling_instance_affected_critical_count
                    and self.instance_deleted == other.instance_deleted
                    and self.sibling_instance_deleted == other.sibling_instance_deleted
                    and self.one_file_affected_count == other.one_file_affected_count
                    and self.both_files_affected_count == other.both_files_affected_count
                    and self.one_instance_affected_critical_count == other.one_instance_affected_critical_count
                    and self.both_instances_affected_critical_count == other.both_instances_affected_critical_count
                    and self.clone_findings_count == other.clone_findings_count)


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
    # the Interval which start and end location should be corrected
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
        # below are edge cases which may introduce errors
        elif loc_interval in left_interval:  # location is entirely in the modified interval. Check for deletion
            if right_length == 0:  # the relevant section was deleted
                raise TextSectionDeletedError("The relevant text section was deleted with this diff.")
            else:
                raise NotImplementedError("I currently do not know how to handle this special case")
        elif left_interval <= loc_interval:
            loc_end_line = loc_end_line + x
        elif left_interval >= loc_interval:
            # loc_start_line = loc_start_line + x
            raise NotImplementedError("I currently do not know how to handle this special case")

    return loc_start_line, loc_end_line
