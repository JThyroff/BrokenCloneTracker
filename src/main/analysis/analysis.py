import traceback

from teamscale_client import TeamscaleClient

from src.main.analysis.analysis_utils import (
    is_file_affected_at_file_changes, are_left_lines_affected_at_diff, correct_lines, filter_clone_finding_churn_by_file, Affectedness,
    AnalysisResult, TextSectionDeletedError, InstanceMetrics
)
from src.main.api.api import (
    get_repository_summary, get_repository_commits, get_commit_alerts, get_affected_files, get_diff, get_clone_finding_churn
)
from src.main.api.data import CommitAlert, Commit, FileChange, DiffType, DiffDescription, CloneFindingChurn
from src.main.persistence import AlertFile, read_alert_file, write_to_file
from src.main.pretty_print import MyPrinter, LogLevel, SEPARATOR
from src.main.utils.time_utils import timestamp_to_str

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

    return alert_file


def analyse_one_alert_commit(client: TeamscaleClient, alert_commit_timestamp: int) -> [AnalysisResult]:
    """Analyzes one given alert commit. This function scans all commits after the given timestamp for relevant changes
    in the code base."""
    printer.yellow("Analysing one alert commit...", level=LogLevel.INFO)
    printer.white("Timestamp : " + timestamp_to_str(alert_commit_timestamp), level=LogLevel.INFO)

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
        printer.yellow("Analysing " + str(commit_alert), level=LogLevel.VERBOSE)
        printer.white("Link to Broken Clone: " + commit_alert.get_broken_clone_link(client, alert_commit_timestamp), level=LogLevel.VERBOSE)
        printer.white("Link to Old Clone: " + commit_alert.get_old_clone_link(client, alert_commit_timestamp), level=LogLevel.VERBOSE)
        printer.separator(LogLevel.VERBOSE)
        # endregion
        # start analysis
        analysis_start: int = alert_commit_timestamp + 1
        analysis_step: int = 15555555_000  # milliseconds. 6 months

        commit_list: [Commit] = []
        while analysis_start < repository_summary[1]:
            step = analysis_start + analysis_step
            if step > repository_summary[1]:
                step = repository_summary[1]
            if analysis_result.sibling_instance_metrics.deleted and analysis_result.instance_metrics.deleted:
                printer.yellow("Both relevant sections are deleted. Skipping rest of analysis.", level=LogLevel.VERBOSE)
                analysis_result.analysed_until = repository_summary[1]
                break
            # get repository data in chunks - this was to be able to write temporary results to a file
            # this is maybe unnecessary yet
            new_commits = get_repository_commits(client, analysis_start, step)
            expected_file = commit_alert.context.expected_clone_location.uniform_path
            expected_sibling = commit_alert.context.expected_sibling_location.uniform_path
            previous_commit_timestamp = alert_commit_timestamp

            for commit in new_commits:
                # goal: retrieve affectedness of the relevant text passages for each commit
                affected_files: [FileChange] = get_affected_files(client, commit.timestamp)
                project_meta = (client, commit.timestamp, previous_commit_timestamp, affected_files)

                # region check file
                file_affectedness: Affectedness = Affectedness.NOT_AFFECTED
                if not analysis_result.instance_metrics.deleted:
                    try:
                        file_affectedness = check_file(expected_file, *project_meta, analysis_result.instance_metrics)
                    except TextSectionDeletedError as e:
                        analysis_result.instance_metrics.deleted = True
                        printer.red("Instance deleted.", LogLevel.INFO)
                        printer.blue(str(e), LogLevel.INFO)
                # endregion

                # region check sibling
                sibling_affectedness: Affectedness = Affectedness.NOT_AFFECTED
                if not analysis_result.sibling_instance_metrics.deleted:
                    try:
                        sibling_affectedness = check_file(expected_sibling, *project_meta, analysis_result.sibling_instance_metrics)
                    except TextSectionDeletedError as e:
                        analysis_result.sibling_instance_metrics.deleted = True
                        printer.red("Sibling deleted.", LogLevel.INFO)
                        printer.blue(str(e), LogLevel.INFO)
                # endregion        

                # region get clone finding churn for commit: filter for clones where both files are affected
                clone_finding_churn: CloneFindingChurn = get_clone_finding_churn(client, commit.timestamp)
                clone_finding_churn = filter_clone_finding_churn_by_file([expected_file, expected_sibling], clone_finding_churn)
                if not clone_finding_churn.is_empty():
                    printer.yellow(str(clone_finding_churn), level=LogLevel.INFO)
                    for s in clone_finding_churn.get_finding_links(client, commit.timestamp):
                        printer.blue(s, level=LogLevel.INFO)
                    if clone_finding_churn.is_relevant():
                        analysis_result.clone_findings_count += 1
                # endregion

                # region interpret affectedness
                affectedness_product: int = file_affectedness * sibling_affectedness
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
                # endregion

                previous_commit_timestamp = commit.timestamp
                commit_list.extend(new_commits)

                analysis_start = step + 1
                analysis_result.analysed_until = step
                pass
        printer.white(SEPARATOR + "\n" + str(analysis_result), LogLevel.RELEVANT)
        results.append(analysis_result)
    return results


def check_file(file: str, client: TeamscaleClient, commit_timestamp: int, previous_commit_timestamp: int,
               affected_files: [FileChange], instance_metrics: InstanceMetrics) -> Affectedness:
    """Check for given file whether it is affected at a specific commit timestamp. If it is modified the diff will be analysed and looked up
    whether the relevant text passage is modified in this commit."""
    if is_file_affected_at_file_changes(file, affected_files):
        file_name = file.split('/')[-1]
        printer.white(
            "{0:51}".format(file_name + " affected at commit:") + timestamp_to_str(commit_timestamp), level=LogLevel.VERBOSE
        )

        diff_dict, link = get_diff(client, file, previous_commit_timestamp, file, commit_timestamp)
        diff_dict: dict[DiffType, DiffDescription]
        link: str
        try:
            instance_metrics.corrected_start_line, instance_metrics.corrected_end_line = correct_lines(
                instance_metrics.corrected_start_line, instance_metrics.corrected_end_line, diff_dict.get(DiffType.LINE_BASED)
            )
        except Exception as e:
            traceback.print_exc()
            raise type(e)(link)

        if are_left_lines_affected_at_diff(
                instance_metrics.corrected_start_line, instance_metrics.corrected_end_line, diff_dict.get(DiffType.TOKEN_BASED)
        ):
            instance_metrics.affected_critical_count += 1
            printer.red(
                file_name + " affected critical."
                + " interval [" + str(instance_metrics.corrected_start_line) + "-" + str(instance_metrics.corrected_end_line) + ")"
                , LogLevel.INFO
            )
            printer.blue(link, LogLevel.INFO)
            return Affectedness.AFFECTED_CRITICAL
        else:
            instance_metrics.file_affected_count += 1
            printer.white(
                file_name + " is not affected critical."
                + " interval [" + str(instance_metrics.corrected_start_line) + "-" + str(instance_metrics.corrected_end_line) + ")"
                , LogLevel.DEBUG)
            printer.blue(link, LogLevel.DEBUG)
            return Affectedness.AFFECTED_BY_COMMIT
    else:
        return Affectedness.NOT_AFFECTED
