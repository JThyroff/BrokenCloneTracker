import traceback

from teamscale_client import TeamscaleClient

from defintions import get_alert_timestamp_list_file_name
from src.main.analysis.analysis_utils import (
    are_left_lines_affected_at_diff, correct_lines, filter_clone_finding_churn_by_file, Affectedness,
    AnalysisResult, TextSectionDeletedError, InstanceMetrics, filter_file_changes, FileDeletedError, filter_relevant_clone_findings
)
from src.main.api.api import (
    get_repository_summary, get_repository_commits, get_commit_alerts, get_affected_files, get_diff, get_clone_finding_churn,
    get_delta_affected_files
)
from src.main.api.data import CommitAlert, Commit, FileChange, DiffType, DiffDescription, CloneFindingChurn, ChangeType, CloneFinding
from src.main.persistence import AlertFile, read_alert_file, write_to_file
from src.main.pretty_print import MyPrinter, LogLevel, SEPARATOR
from src.main.utils.time_utils import timestamp_to_str, display_time

printer: MyPrinter = MyPrinter(LogLevel.DEBUG)


def update_filtered_alert_commits(client: TeamscaleClient, overwrite=False) -> AlertFile:
    """This function updates the alert commit of the project in the corresponding file.
    It reads the current alert file and compares appends new relevant commits from the server."""
    printer.yellow("Updating filtered alert commits... Overwrite = " + str(overwrite), level=LogLevel.INFO)

    file_name, alert_file = read_alert_file(client, overwrite)
    alert_file: AlertFile

    # start analysis
    analysis_start: int = alert_file.analysed_until
    analysis_step: int = 15555555_000  # milliseconds. 6 months
    while analysis_start < alert_file.most_recent_commit:
        step = analysis_start + analysis_step
        if step > alert_file.most_recent_commit:
            step = alert_file.most_recent_commit
        alert_file.alert_commit_list.extend(get_repository_commits(client, analysis_start, step, filter_alerts=True))
        alert_file.analysed_until = step
        write_to_file(file_name, alert_file)
        analysis_start = step + 1

    d = dict()
    x = list((alert.timestamp for alert in alert_file.alert_commit_list))
    for i in x:
        d.update({i: ""})
    write_to_file(get_alert_timestamp_list_file_name(client.project), d)

    return alert_file


def analyse_one_alert_commit(client: TeamscaleClient, alert_commit_timestamp: int) -> [AnalysisResult]:
    """Analyzes one given alert commit. This function scans all commits after the given timestamp for relevant changes
    in the code base."""
    printer.yellow("Analysing one alert commit...", level=LogLevel.INFO)

    alerts: dict[Commit, [CommitAlert]] = get_commit_alerts(client, alert_commit_timestamp)

    alert_list: [CommitAlert] = []
    for key in alerts.keys():  # search for key timestamp and read alert list
        if type(key) == Commit and key.timestamp == alert_commit_timestamp:
            alert_list = alerts[key]

    # fetch repository repository_summary
    repository_summary: tuple[int, int] = get_repository_summary(client)

    results: [AnalysisResult] = []

    for commit_alert in alert_list:  # sometimes more than one alert is attached to a commit
        commit_alert: CommitAlert

        analysis_result: AnalysisResult = AnalysisResult.from_alert(
            client.project, *repository_summary, repository_summary[0] - 1, commit_alert=commit_alert
        )
        # region logging
        printer.separator(level=LogLevel.VERBOSE)
        printer.blue("Timestamp : " + timestamp_to_str(alert_commit_timestamp), level=LogLevel.INFO)
        printer.yellow("Analysing " + str(commit_alert), level=LogLevel.VERBOSE)
        printer.white("Link to Broken Clone: " + commit_alert.get_broken_clone_link(client, alert_commit_timestamp), level=LogLevel.VERBOSE)
        printer.white("Link to Old Clone: " + commit_alert.get_old_clone_link(client, alert_commit_timestamp), level=LogLevel.VERBOSE)
        printer.separator(LogLevel.VERBOSE)
        # endregion
        # start analysis
        analysis_start: int = alert_commit_timestamp + 1
        analysis_step: int = 7890000_000  # milliseconds. 3 months # 15555555_000 ~ 6 months

        # get repository data in chunks - this was to be able to write temporary results to a file
        # this is maybe unnecessary yet
        expected_file = commit_alert.context.expected_clone_location.uniform_path
        expected_sibling = commit_alert.context.expected_sibling_location.uniform_path
        previous_commit_timestamp = alert_commit_timestamp

        while analysis_start < repository_summary[1]:
            step = analysis_start + analysis_step
            if step > repository_summary[1]:
                step = repository_summary[1]
            if analysis_result.sibling_instance_metrics.deleted and analysis_result.instance_metrics.deleted:
                printer.green("Both relevant sections are deleted. Skipping rest of analysis.", level=LogLevel.VERBOSE)
                analysis_result.analysed_until = repository_summary[1]
                break

            if (not (get_delta_affected_files(client, analysis_start, step, expected_file) is None
                     and get_delta_affected_files(client, analysis_start, step, expected_sibling) is None)):
                # if no changes are in this interval
                new_commits = get_repository_commits(client, analysis_start, step)
                for commit in new_commits:
                    # goal: retrieve affectedness of the relevant text passages for each commit
                    affected_files: [FileChange] = get_affected_files(client, commit.timestamp)
                    project_meta = (client, commit.timestamp, previous_commit_timestamp, affected_files)

                    # region check file
                    instance_affectedness: Affectedness = Affectedness.NOT_AFFECTED
                    if not analysis_result.instance_metrics.deleted:
                        try:
                            instance_affectedness, expected_file = check_file(expected_file, *project_meta,
                                                                              analysis_result.instance_metrics)
                        except (TextSectionDeletedError, FileDeletedError) as e:
                            analysis_result.instance_metrics.deleted = True
                            analysis_result.instance_metrics.time_alive = commit.timestamp - alert_commit_timestamp
                            printer.red("Instance deleted.", LogLevel.INFO)
                            printer.blue(str(e), LogLevel.INFO)
                    # endregion

                    # region check sibling
                    sibling_instance_affectedness: Affectedness = Affectedness.NOT_AFFECTED
                    if not analysis_result.sibling_instance_metrics.deleted:
                        try:
                            sibling_instance_affectedness, expected_sibling = check_file(
                                expected_sibling, *project_meta, analysis_result.sibling_instance_metrics
                            )
                        except (TextSectionDeletedError, FileDeletedError) as e:
                            analysis_result.sibling_instance_metrics.deleted = True
                            analysis_result.sibling_instance_metrics.time_alive = commit.timestamp - alert_commit_timestamp
                            printer.red("Sibling deleted.", LogLevel.INFO)
                            printer.blue(str(e), LogLevel.INFO)
                    # endregion

                    # get clone finding churn for commit: filter for clones where both files are affected
                    inspect_clone_finding_churn(analysis_result, client, commit, expected_file, expected_sibling)

                    # interpret affectedness
                    interpret_affectedness(analysis_result, instance_affectedness, sibling_instance_affectedness)

                    previous_commit_timestamp = commit.timestamp
                # end for
            # end if
            else:
                printer.green("S K I P  :  " + display_time(analysis_step) + " : No File affected in this Interval.")
            analysis_start = step + 1
            analysis_result.analysed_until = step
            pass
        # end while
        # region calc time alive
        time_until_today = analysis_result.most_recent_commit - alert_commit_timestamp
        if not analysis_result.instance_metrics.deleted:
            analysis_result.instance_metrics.time_alive = time_until_today
        if not analysis_result.sibling_instance_metrics.deleted:
            analysis_result.sibling_instance_metrics.time_alive = time_until_today
        # endregion
        printer.white(SEPARATOR + "\n" + str(analysis_result), LogLevel.RELEVANT)
        results.append(analysis_result)
    return results


def check_file(file_path: str, client: TeamscaleClient, commit_timestamp: int, previous_commit_timestamp: int, affected_files: [FileChange]
               , instance_metrics: InstanceMetrics) -> (Affectedness, str):
    """Check for given file whether it is affected at a specific commit timestamp. If it is modified the diff will be analysed and looked up
    whether the relevant text passage is modified in this commit."""
    changes: [FileChange] = filter_file_changes(file_path, affected_files)
    if len(changes) != 0:
        change: FileChange = changes[0]
        for c in changes:
            c: FileChange
            if c.change_type is not ChangeType.DELETE:
                # take that?
                change = c

        file_name = change.uniform_path.split('/')[-1]
        printer.white(
            "{0:51}".format(file_name + " affected at commit:") + timestamp_to_str(commit_timestamp), level=LogLevel.VERBOSE
        )

        origin_path = file_path
        if change.change_type == ChangeType.DELETE:
            raise FileDeletedError("The file was deleted.")
        elif change.origin_path is not None:
            origin_path = change.origin_path
            file_path = change.uniform_path
            printer.yellow("The file was moved from " + change.origin_path + " to " + change.uniform_path, LogLevel.INFO)

        old_start_line = instance_metrics.corrected_start_line
        old_end_line = instance_metrics.corrected_end_line

        diff_dict, link = get_diff(client, origin_path, previous_commit_timestamp, file_path, commit_timestamp)
        diff_dict: dict[DiffType, DiffDescription]
        link: str

        try:
            instance_metrics.corrected_start_line, instance_metrics.corrected_end_line = correct_lines(
                instance_metrics.corrected_start_line, instance_metrics.corrected_end_line, diff_dict.get(DiffType.LINE_BASED)
            )
        except Exception as e:
            traceback.print_exc()
            raise type(e)("link: " + link)

        if are_left_lines_affected_at_diff(
                old_start_line, old_end_line, diff_dict.get(DiffType.TOKEN_BASED)
        ):
            instance_metrics.affected_critical_count += 1
            printer.red(
                file_name + " affected critical."
                + " interval [" + str(instance_metrics.corrected_start_line) + "-" + str(instance_metrics.corrected_end_line) + ")"
                , LogLevel.INFO
            )
            printer.blue(link, LogLevel.INFO)
            return Affectedness.AFFECTED_CRITICAL, file_path
        else:
            instance_metrics.file_affected_count += 1
            printer.white(
                file_name + " is not affected critical."
                + " interval [" + str(instance_metrics.corrected_start_line) + "-" + str(instance_metrics.corrected_end_line) + ")"
                , LogLevel.DEBUG)
            printer.blue(link, LogLevel.DEBUG)
            return Affectedness.AFFECTED_BY_COMMIT, file_path
    else:
        return Affectedness.NOT_AFFECTED, file_path


def interpret_affectedness(analysis_result, instance_affectedness, sibling_instance_affectedness):
    """interprets the affectedness of the two instances, logs and increases the counters."""
    affectedness_product: int = instance_affectedness * sibling_instance_affectedness
    if affectedness_product == 9:
        analysis_result.both_instances_affected_critical_count += 1
        printer.red("-> Both affected critical", LogLevel.INFO)
    elif affectedness_product == 3 or affectedness_product == 6:
        analysis_result.one_instance_affected_critical_count += 1
        printer.red("-> One affected critical", LogLevel.INFO)
    elif affectedness_product == 4:
        analysis_result.both_files_affected_count += 1
        printer.white("-> Both affected", LogLevel.VERBOSE)
    elif affectedness_product == 2:
        analysis_result.one_file_affected_count += 1
        printer.white("-> One affected", LogLevel.VERBOSE)


def inspect_clone_finding_churn(analysis_result, client, commit, expected_file, expected_sibling):
    """Get clone finding churn and filter it for clones where both files are affected. If there is a new clone added in this churn the
    clone_findings_count will be increased by one."""
    if analysis_result.instance_metrics.deleted or analysis_result.sibling_instance_metrics.deleted:
        # if at least one instance is already deleted, a new clone can not exist
        return

    clone_finding_churn: CloneFindingChurn = get_clone_finding_churn(client, commit.timestamp)
    clone_finding_churn = filter_clone_finding_churn_by_file([expected_file, expected_sibling], clone_finding_churn)
    relevant: [CloneFinding] = filter_relevant_clone_findings(clone_finding_churn, expected_file, expected_sibling, analysis_result)
    if relevant:
        printer.red('Found possibly relevant clone findings: ', LogLevel.RELEVANT)
        printer.yellow(
            ',\n'.join(
                str(finding) + "\n" + finding.get_finding_link(client=client, commit_timestamp=commit.timestamp)
                for finding in relevant
            )
            , level=LogLevel.INFO
        )
        analysis_result.clone_findings_count += len(relevant)
