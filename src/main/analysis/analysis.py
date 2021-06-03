from json import JSONDecodeError
from pathlib import Path
from typing import TextIO

import jsonpickle
from teamscale_client import TeamscaleClient

from defintions import get_alert_file_name, get_project_dir
from src.main.analysis.analysis_utils import (is_file_affected_at_file_changes, are_left_lines_affected_at_diff,
                                              correct_lines, filter_clone_finding_churn_by_file, Affectedness, AnalysisResult,
                                              TextSectionDeletedError, InstanceMetrics)
from src.main.api.api import get_repository_summary, get_repository_commits, get_commit_alerts, get_affected_files, \
    get_diff, get_clone_finding_churn
from src.main.api.data import CommitAlert, Commit, FileChange, DiffType, DiffDescription, CloneFindingChurn
from src.main.persistence import AlertFile
from src.main.pretty_print import MyLogger, LogLevel, SEPARATOR

logger: MyLogger = MyLogger(LogLevel.DEBUG)


def create_project_dir(project: str):
    """Creates the directory where the project specific files are saved. For example the """
    Path(get_project_dir(project)).mkdir(parents=True, exist_ok=True)


def update_filtered_alert_commits(client: TeamscaleClient):
    """This function updates the alert commit of the project in the corresponding file.
    It reads the current alert file and compares appends new relevant commits from the server."""
    logger.yellow("Updating filtered alert commits...", level=LogLevel.INFO)
    file_name: str = get_alert_file_name(client.project)
    # create structure if non-existent
    create_project_dir(project=client.project)
    summary: tuple[int, int] = get_repository_summary(client)

    alert_file: AlertFile
    try:
        open(file_name, 'x')  # throws FileExistsError if File existent
        # the file was not existent before. Reading is useless
        # create a new object to work on
        alert_file = AlertFile.from_summary(client.project, summary)

    except FileExistsError:
        # the file already exists
        # read the current data from the file, process and update it
        with open(file_name, 'r') as file:
            file: TextIO
            try:
                alert_file = jsonpickle.decode(file.read())
                # update most recent commit date
                alert_file.most_recent_commit = summary[1]
            except JSONDecodeError:
                alert_file = AlertFile.from_summary(client.project, summary)

    # start analysis
    analysis_start: int = alert_file.analysed_until
    analysis_step: int = 15555555_000  # milliseconds. 6 months
    while analysis_start < alert_file.most_recent_commit:
        step = analysis_start + analysis_step
        if step > alert_file.most_recent_commit:
            step = alert_file.most_recent_commit
        alert_file.alert_commit_list.extend(get_repository_commits(client, analysis_start, step, filter_alerts=True))
        alert_file.analysed_until = step
        with open(file_name, "w") as file:
            file.write(jsonpickle.encode(alert_file))
        analysis_start = step + 1
        pass


def analyse_one_alert_commit(client: TeamscaleClient, alert_commit_timestamp: int):
    """Analyzes one given alert commit. This function scans all commits after the given timestamp for relevant changes
    in the code base."""
    logger.yellow("Analysing one alert commit...", level=LogLevel.INFO)
    logger.white("Timestamp : " + str(alert_commit_timestamp), level=LogLevel.INFO)

    alerts: dict[Commit, [CommitAlert]] = get_commit_alerts(client, alert_commit_timestamp)

    alert_list: [CommitAlert] = []
    for key in alerts.keys():  # search for key timestamp and read alert list
        if type(key) == Commit and key.timestamp == alert_commit_timestamp:
            alert_list = alerts[key]

    # fetch repository repository_summary
    repository_summary: tuple[int, int] = get_repository_summary(client)

    for commit_alert in alert_list:  # sometimes more than one alert is attached to a commit
        commit_alert: CommitAlert

        analysis_result: AnalysisResult = AnalysisResult.from_alert(client.project, *repository_summary, repository_summary[0] - 1,
                                                                    commit_alert=commit_alert)
        # region logging
        logger.separator(level=LogLevel.VERBOSE)
        logger.yellow("Analysing " + str(commit_alert))
        logger.separator(LogLevel.VERBOSE)
        # endregion
        # start analysis
        analysis_start: int = alert_commit_timestamp + 1
        analysis_step: int = 15555555_000  # milliseconds. 6 months

        commit_list: [Commit] = []
        while analysis_start < repository_summary[1]:
            step = analysis_start + analysis_step
            if step > repository_summary[1]:
                step = repository_summary[1]
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
                # check file
                file_affectedness: Affectedness = Affectedness.NOT_AFFECTED
                if not analysis_result.instance_metrics.deleted:
                    try:
                        file_affectedness = check_file(expected_file, *project_meta, analysis_result.instance_metrics)
                    except TextSectionDeletedError as e:
                        analysis_result.instance_metrics.deleted = True
                        logger.red("Instance deleted.", LogLevel.VERBOSE)
                        logger.blue(str(e), LogLevel.VERBOSE)
                # check sibling
                sibling_affectedness: Affectedness = Affectedness.NOT_AFFECTED
                if not analysis_result.sibling_instance_metrics.deleted:
                    try:
                        sibling_affectedness = check_file(expected_sibling, *project_meta, analysis_result.sibling_instance_metrics)
                    except TextSectionDeletedError as e:
                        analysis_result.sibling_instance_metrics.deleted = True
                        logger.red("Sibling deleted.", LogLevel.VERBOSE)
                        logger.blue(str(e), LogLevel.VERBOSE)
                # get clone finding churn for commit: filter for clones where both files are affected
                clone_finding_churn: CloneFindingChurn = get_clone_finding_churn(client, commit.timestamp)
                filter_clone_finding_churn_by_file([expected_file, expected_sibling], clone_finding_churn)
                if not clone_finding_churn.is_empty():
                    logger.yellow(str(clone_finding_churn), level=LogLevel.VERBOSE)
                for s in clone_finding_churn.get_finding_links(client):
                    logger.blue(s, level=LogLevel.VERBOSE)

                affectedness_product: int = file_affectedness * sibling_affectedness
                if affectedness_product == 9:
                    analysis_result.both_instances_affected_critical_count += 1
                    logger.red("-> Both affected critical", LogLevel.VERBOSE)
                elif affectedness_product == 3 or affectedness_product == 6:
                    analysis_result.one_instance_affected_critical_count += 1
                    logger.red("-> One affected critical", LogLevel.VERBOSE)
                elif affectedness_product == 4:
                    analysis_result.both_files_affected_count += 1
                    logger.white("-> Both affected", LogLevel.VERBOSE)
                elif affectedness_product == 2:
                    analysis_result.one_file_affected_count += 1
                    logger.white("-> One affected", LogLevel.VERBOSE)
                previous_commit_timestamp = commit.timestamp
                commit_list.extend(new_commits)

                analysis_start = step + 1
                analysis_result.analysed_until = step
                pass
        logger.white(SEPARATOR + "\n" + str(analysis_result))
        pass


def check_file(file: str, client: TeamscaleClient, commit_timestamp: int, previous_commit_timestamp: int,
               affected_files: [FileChange], instance_metrics: InstanceMetrics) -> Affectedness:
    if is_file_affected_at_file_changes(file, affected_files):
        file_name = file.split('/')[-1]
        logger.white("{0:51}".format(file_name + " affected at commit:") + str(commit_timestamp), level=LogLevel.VERBOSE)

        diff_dict, link = get_diff(client, file, previous_commit_timestamp, file, commit_timestamp)
        diff_dict: dict[DiffType, DiffDescription]
        link: str
        try:
            instance_metrics.corrected_start_line, instance_metrics.corrected_end_line = correct_lines(
                instance_metrics.corrected_start_line,
                instance_metrics.corrected_end_line, diff_dict.get(
                    DiffType.LINE_BASED))
        except Exception as e:
            raise type(e)(link)

        if are_left_lines_affected_at_diff(instance_metrics.corrected_start_line, instance_metrics.corrected_end_line, diff_dict.get(
                DiffType.TOKEN_BASED)):
            instance_metrics.affected_critical_count += 1
            logger.red(file_name + " affected critical", LogLevel.VERBOSE)
            logger.blue(link, LogLevel.VERBOSE)
            return Affectedness.AFFECTED_CRITICAL
        else:
            instance_metrics.file_affected_count += 1
            logger.white(file_name + " is not affected critical", LogLevel.DEBUG)
            logger.blue(link, LogLevel.DEBUG)
            return Affectedness.AFFECTED_BY_COMMIT
    else:
        return Affectedness.NOT_AFFECTED
