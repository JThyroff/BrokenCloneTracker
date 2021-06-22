from dataclasses import dataclass
from enum import Enum

import portion
from portion import Interval

from defintions import NEW_CLONE_SIMILARITY_THRESHOLD
from src.main.api.data import FileChange, DiffDescription, CloneFindingChurn, CloneFinding, CommitAlert, \
    CommitAlertContext
from src.main.pretty_print import SEPARATOR
from src.main.utils.interval_utils import get_interval_length, overlaps_more_than_threshold
from src.main.utils.time_utils import display_time, timestamp_to_str


class FileDeletedError(Exception):
    pass


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
class InstanceMetrics:
    corrected_start_line: int
    corrected_end_line: int
    file_affected_count: int = 0
    affected_critical_count: int = 0
    deleted: bool = False
    time_alive = -1

    def get_corrected_interval(self) -> str:
        return "[" + str(self.corrected_start_line) + "," + str(self.corrected_end_line) + ")"


@dataclass
class AnalysisResult:
    """A class representing one analysis result"""

    project: str
    first_commit: int
    most_recent_commit: int
    analysed_until: int
    commit_alert: CommitAlert
    # Instance metrics
    instance_metrics: InstanceMetrics
    sibling_instance_metrics: InstanceMetrics
    #
    one_file_affected_count: int = 0
    both_files_affected_count: int = 0
    one_instance_affected_critical_count: int = 0
    both_instances_affected_critical_count: int = 0
    clone_findings_count: int = 0

    def __str__(self):
        return ("Analysis Result for " + self.project + ": first commit: " + timestamp_to_str(self.first_commit) + ", most recent commit: "
                + timestamp_to_str(self.most_recent_commit) + ", "
                + "\nanalysed until: " + timestamp_to_str(self.analysed_until)
                + "\n" + SEPARATOR
                + "\n" + str(self.commit_alert)
                + "\n" + SEPARATOR
                + "\nFile affected count: " + str(self.instance_metrics.file_affected_count)
                + "\nInstance affected critical count: " + str(self.instance_metrics.affected_critical_count)
                + "\nInstance deleted: " + str(self.instance_metrics.deleted)
                + "\nCorrected instance interval: " + self.instance_metrics.get_corrected_interval()
                + "\nInstance time alive: " + display_time(self.instance_metrics.time_alive) + " ~ " + str(self.instance_metrics.time_alive)
                + "\nSibling file affected count: " + str(self.sibling_instance_metrics.file_affected_count)
                + "\nSibling instance affected critical count: " + str(self.sibling_instance_metrics.affected_critical_count)
                + "\nSibling instance deleted: " + str(self.sibling_instance_metrics.deleted)
                + "\nCorrected sibling interval: " + self.sibling_instance_metrics.get_corrected_interval()
                + "\nSibling instance time alive: " + display_time(self.sibling_instance_metrics.time_alive)
                + " ~ " + str(self.sibling_instance_metrics.time_alive)
                + "\nOne file affected count: " + str(self.one_file_affected_count)
                + "\nBoth files affected count: " + str(self.both_files_affected_count)
                + "\nOne instance affected critical count: " + str(self.one_instance_affected_critical_count)
                + "\nBoth instances affected critical count: " + str(self.both_instances_affected_critical_count)
                + "\nRelevant clone findings count: " + str(self.clone_findings_count))

    @staticmethod
    def from_alert(project: str, first_commit: int, most_recent_commit: int, analysed_until: int,
                   commit_alert: CommitAlert):
        """create an analysis result from project meta and given commit alert. All counters are initialized with 0."""
        ctx: CommitAlertContext = commit_alert.context
        return AnalysisResult(project, first_commit, most_recent_commit, analysed_until, commit_alert,
                              InstanceMetrics(ctx.expected_clone_location.raw_start_line,
                                              ctx.expected_clone_location.raw_end_line),
                              InstanceMetrics(ctx.expected_sibling_location.raw_start_line,
                                              ctx.expected_sibling_location.raw_end_line))


def is_file_affected_at_file_changes(file_uniform_path: str, affected_files: [FileChange]) -> bool:
    return file_uniform_path in [e.uniform_path for e in affected_files]


def filter_file_changes(file_uniform_path: str, affected_files: [FileChange]) -> [FileChange]:
    return list(filter(lambda f: f.uniform_path == file_uniform_path or f.origin_path == file_uniform_path, affected_files))


def are_left_lines_affected_at_diff(raw_start_line: int, raw_end_line: int, diff_desc: DiffDescription) -> bool:
    raw_interval: Interval = portion.closedopen(raw_start_line, raw_end_line)

    left_line_interval: Interval
    for left_line_interval in diff_desc.left_change_line_intervals:
        if raw_interval.overlaps(left_line_interval):
            return True

    return False


def filter_clone_finding_churn_by_file(file_uniform_paths: [str], clone_finding_churn: CloneFindingChurn) -> CloneFindingChurn:
    """filter a clone finding churn by files. All findings will be reduced to the one where all files in the given
    list are affected"""

    def file_filter(x: CloneFinding) -> bool:
        for file_path in file_uniform_paths:
            # if one file not affected return False
            if not (x.location.uniform_path == file_path or file_path in [e.uniform_path for e in x.sibling_locations]):
                return False
        return True

    clone_finding_churn.added_findings = list(filter(lambda x: file_filter(x), clone_finding_churn.added_findings))
    clone_finding_churn.findings_added_in_branch = list(filter(lambda x: file_filter(x), clone_finding_churn.findings_added_in_branch))
    clone_finding_churn.findings_in_changed_code = list(filter(lambda x: file_filter(x), clone_finding_churn.findings_in_changed_code))
    clone_finding_churn.removed_findings = list(filter(lambda x: file_filter(x), clone_finding_churn.removed_findings))
    clone_finding_churn.findings_removed_in_branch = list(filter(lambda x: file_filter(x), clone_finding_churn.findings_removed_in_branch))
    return clone_finding_churn


def filter_relevant_clone_findings(
        clone_finding_churn: CloneFindingChurn, expected_file: str, expected_sibling: str, analysis_result: AnalysisResult
) -> [CloneFinding]:
    """Filter for clone findings which are actually newly introduced"""
    instance_start = analysis_result.instance_metrics.corrected_start_line
    instance_end = analysis_result.instance_metrics.corrected_end_line
    instance_interval = portion.closedopen(instance_start, instance_end)
    sibling_start = analysis_result.sibling_instance_metrics.corrected_start_line
    sibling_end = analysis_result.sibling_instance_metrics.corrected_end_line
    sibling_interval = portion.closedopen(sibling_start, sibling_end)

    relevant = []
    for clone_finding in (
            clone_finding_churn.added_findings + clone_finding_churn.findings_added_in_branch + clone_finding_churn.findings_in_changed_code
    ):
        clone_finding: CloneFinding
        locations = [clone_finding.location, *clone_finding.sibling_locations]
        b = [False, False]
        for loc in locations:
            # check whether the clone matches the two files with the corresponding intervals more than threshold
            if loc.is_overlapping_more_than_threshold(expected_file, instance_interval, NEW_CLONE_SIMILARITY_THRESHOLD):
                b[0] = True
            if loc.is_overlapping_more_than_threshold(expected_sibling, sibling_interval, NEW_CLONE_SIMILARITY_THRESHOLD):
                b[1] = True

        if b == [True, True] and clone_finding.death_commit is None:
            relevant.append(clone_finding)
    return relevant


def is_file_affected_at_clone_finding_churn(file_uniform_path: str, clone_finding_churn: CloneFindingChurn) -> bool:
    """returns whether given file is affected by given CloneFindingChurn."""
    clone_finding_churn = filter_clone_finding_churn_by_file(file_uniform_path, clone_finding_churn)
    return not clone_finding_churn.is_empty()


def deletion_pre_check(relevant_interval: Interval, diff_desc: DiffDescription):
    # if less than deletion_pre_check_factor * relevant_interval_length lines stay after a modification of a relevant text
    # section, the whole section is considered as deleted
    deletion_pre_check_factor = 0.2
    deletion_pre_check_factor_inverse_string = str((1 - deletion_pre_check_factor) * 100)
    relevant_interval_length = get_interval_length(relevant_interval)

    intersecting_intervals: [(Interval, Interval)] = list(
        filter(
            lambda interval_tuple: not interval_tuple[0].intersection(relevant_interval).empty,
            zip(diff_desc.left_change_line_intervals, diff_desc.right_change_line_intervals)
        )
    )

    # check full deletion of intersecting Intervals
    deleted_lines = 0
    for left_interval, right_interval in intersecting_intervals:
        if right_interval.empty:
            deleted_lines += get_interval_length(left_interval.intersection(relevant_interval))
    if relevant_interval_length - deleted_lines < deletion_pre_check_factor * relevant_interval_length:
        raise TextSectionDeletedError(
            "more than " + deletion_pre_check_factor_inverse_string + "% of the relevant clone section is deleted."
        )

    # filter the intervals that overlap more than 80% with the relevant interval
    overlapping_intervals: [(Interval, Interval)] = list(
        filter(
            lambda interval_tuple: (overlaps_more_than_threshold(interval_tuple[0], relevant_interval, 0.8)),
            intersecting_intervals
        )
    )

    # calculate line diff count - for the case that the Interval is not fully deleted but still modified in a relevant way
    line_diff_count = 0
    for left_interval, right_interval in overlapping_intervals:
        left_length = get_interval_length(left_interval)
        right_length = get_interval_length(right_interval)
        line_diff_count += (right_length - left_length)

    # if the overlapping intervals are mostly line deletions -> the relevant clone section is also deleted
    if relevant_interval_length + line_diff_count < deletion_pre_check_factor * relevant_interval_length:
        # more than (1 - deletion_pre_check_factor) * 100% of the relevant clone section is deleted for sure
        raise TextSectionDeletedError(
            "more than " + deletion_pre_check_factor_inverse_string + "% of the relevant clone section is deleted."
        )


def correct_lines(loc_start_line: int, loc_end_line: int, diff_desc: DiffDescription) -> (int, int):
    """ While tracking the relevant region of a broken clone by its affected lines, it could be the case
    that the relevant lines of one instance of the code clone are shifted due to code modifications in the lines
    above. This function addresses this issue and corrects the given line numbers respecting the diff.
    It basically adds the diff of the lines above the relevant part to its line numbers.
    :return the corrected line number respecting the diff"""
    # if "line-based" not in diff_desc.name.value:
    # raise ValueError('DiffDescription should be a kind of line based diff.')
    # the Interval whose start and end location should be corrected
    loc_interval: Interval = portion.closedopen(loc_start_line, loc_end_line)

    deletion_pre_check(loc_interval, diff_desc)

    for left_interval, right_interval in zip(diff_desc.left_change_line_intervals, diff_desc.right_change_line_intervals):
        left_length = get_interval_length(left_interval)
        right_length = get_interval_length(right_interval)
        # [4,6) -> [4,5)
        x = right_length - left_length
        if left_interval.empty:
            new_interval: Interval = portion.closedopen(loc_start_line, loc_end_line)
            assert x > 0
            if right_interval.lower < new_interval:  # insertion above the relevant text section
                loc_start_line = loc_start_line + x
                loc_end_line = loc_end_line + x
            elif right_interval > new_interval:
                pass
            elif right_interval.lower in new_interval:
                loc_end_line = loc_end_line + x
            else:
                raise NotImplementedError("I currently do not know how to handle this special case")
        elif left_interval < loc_interval:
            # the modification is entirely above the relevant text passage -> need to adjust start and end line
            loc_start_line = loc_start_line + x
            loc_end_line = loc_end_line + x
        elif left_interval in loc_interval:
            # the modification is within the relevant text passage -> apply change only to end line as start line stays unaffected
            loc_end_line = loc_end_line + x
        elif left_interval > loc_interval:
            # the modification is entirely on the right of the relevant passage
            # return cause intervals are sorted -> No important intervals will follow
            return loc_start_line, loc_end_line
        # below are edge cases which may introduce errors
        elif loc_interval in left_interval:  # location is entirely affected by the modified interval. Check for deletion
            # check for empty interval or even for whole file deletion (which results in portion.closedopen(1,2))
            if right_length == 0 or (right_interval == portion.closedopen(1, 2)):  # the relevant section was deleted
                raise TextSectionDeletedError("The relevant text section was deleted with this diff.")
            else:
                # else track the whole interval now
                return right_interval.lower, right_interval.upper
        elif left_interval <= loc_interval:
            # the modification is left of the upper bound of the relevant passage. So the end line is affected for sure.
            # what about the start line?
            loc_end_line = loc_end_line + x
        elif left_interval >= loc_interval:
            # the relevant text section is modified in the last few lines, add them to the clone
            loc_end_line = loc_end_line + x

    return loc_start_line, loc_end_line
