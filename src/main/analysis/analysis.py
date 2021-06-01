from json import JSONDecodeError
from pathlib import Path
from typing import TextIO

import jsonpickle
from teamscale_client import TeamscaleClient

from defintions import get_alert_file_name, get_project_dir
from src.main.analysis.analysis_utils import is_file_affected_at_file_changes, are_left_lines_affected_at_diff, \
    correct_lines, \
    filter_clone_finding_churn_by_file, Affectedness
from src.main.api.api import get_repository_summary, get_repository_commits, get_commit_alerts, get_affected_files, \
    get_diff, get_clone_finding_churn
from src.main.data import CommitAlert, Commit, FileChange, DiffType, DiffDescription, TextRegionLocation, \
    CloneFindingChurn
from src.main.persistence import AlertFile
from src.main.pretty_print import MyLogger, LogLevel

logger: MyLogger = MyLogger(LogLevel.VERBOSE)


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

    # fetch repository summary
    summary: tuple[int, int] = get_repository_summary(client)

    for i in alert_list:  # sometimes more than one alert is attached to a commit
        i: CommitAlert
        clone_loc: TextRegionLocation = i.context.expected_clone_location
        sibling_loc: TextRegionLocation = i.context.expected_sibling_location

        # region logging
        logger.separator(level=LogLevel.VERBOSE)
        logger.yellow("Analysing Alert: " + i.message, LogLevel.VERBOSE)
        logger.yellow("Expected clone location: " + str(i.context.expected_clone_location.uniform_path),
                      level=LogLevel.VERBOSE)
        logger.yellow("Clone.raw_start_line: " + str(clone_loc.raw_start_line), level=LogLevel.VERBOSE)
        logger.yellow("Clone.raw_end_line: " + str(clone_loc.raw_end_line), level=LogLevel.VERBOSE)
        logger.yellow("Expected sibling location: " + str(i.context.expected_sibling_location.uniform_path),
                      level=LogLevel.VERBOSE)
        logger.yellow("Sibling.raw_start_line: " + str(sibling_loc.raw_start_line), level=LogLevel.VERBOSE)
        logger.yellow("Sibling.raw_end_line: " + str(sibling_loc.raw_end_line), level=LogLevel.VERBOSE)
        logger.separator(LogLevel.VERBOSE)
        # endregion
        # start analysis
        analysis_start: int = alert_commit_timestamp + 1
        analysis_step: int = 15555555_000  # milliseconds. 6 months
        # two variables each two handle the offset of the broken clone region over time
        corrected_clone_start_line = clone_loc.raw_start_line
        corrected_clone_end_line = clone_loc.raw_end_line
        corrected_sibling_start_line = sibling_loc.raw_start_line
        corrected_sibling_end_line = sibling_loc.raw_end_line
        commit_list: [Commit] = []
        while analysis_start < summary[1]:
            step = analysis_start + analysis_step
            if step > summary[1]:
                step = summary[1]
            # get repository data in chunks - this was to be able to write temporary results to a file
            # this is maybe unnecessary yet
            new_commits = get_repository_commits(client, analysis_start, step)
            expected_file = i.context.expected_clone_location.uniform_path
            expected_sibling = i.context.expected_sibling_location.uniform_path
            previous_commit_timestamp = alert_commit_timestamp

            for commit in new_commits:
                # goal: retrieve affectedness of the relevant text passages for each commit
                affected_files: [FileChange] = get_affected_files(client, commit.timestamp)
                param_tuple = (client, commit.timestamp, previous_commit_timestamp, affected_files)
                # check file
                file_affectedness: Affectedness
                file_affectedness, corrected_clone_start_line, corrected_clone_end_line = \
                    check_file(*param_tuple, expected_file, corrected_clone_start_line, corrected_clone_end_line)
                # check sibling
                sibling_affectedness: Affectedness
                sibling_affectedness, corrected_sibling_start_line, corrected_sibling_end_line = \
                    check_file(*param_tuple, expected_sibling, corrected_sibling_start_line, corrected_sibling_end_line)
                # get clone finding churn for commit: filter for clones where both files are affected
                clone_finding_churn: CloneFindingChurn = get_clone_finding_churn(client, commit.timestamp)
                filter_clone_finding_churn_by_file([expected_file, expected_sibling], clone_finding_churn)
                if not clone_finding_churn.is_empty():
                    logger.yellow(str(clone_finding_churn), level=LogLevel.VERBOSE)
                    for s in clone_finding_churn.get_finding_links(client):
                        logger.blue(s, level=LogLevel.VERBOSE)

                affectedness_product: int = file_affectedness * sibling_affectedness
                if affectedness_product == 9:
                    logger.red("-> Both affected critical", LogLevel.VERBOSE)
                elif affectedness_product == 3 or affectedness_product == 6:
                    logger.red("-> One affected critical", LogLevel.VERBOSE)
                elif affectedness_product == 4:
                    logger.white("-> Both affected", LogLevel.VERBOSE)
                elif affectedness_product == 2:
                    logger.white("-> One affected", LogLevel.VERBOSE)
                previous_commit_timestamp = commit.timestamp
            commit_list.extend(new_commits)

            analysis_start = step + 1
            pass
        # region logging
        logger.separator(level=LogLevel.DEBUG)
        logger.white("Corrected lines:", level=LogLevel.DEBUG)
        logger.white("Expected clone location: " + str(i.context.expected_clone_location.uniform_path),
                     level=LogLevel.DEBUG)
        logger.white("Clone.start_line (corrected): " + str(corrected_clone_start_line), level=LogLevel.DEBUG)
        logger.white("Clone.end_line (corrected): " + str(corrected_clone_end_line), level=LogLevel.DEBUG)
        logger.white("Expected sibling location: " + str(i.context.expected_sibling_location.uniform_path),
                     level=LogLevel.DEBUG)
        logger.white("Sibling.start_line (corrected): " + str(corrected_sibling_start_line), level=LogLevel.DEBUG)
        logger.white("Sibling.end_line (corrected): " + str(corrected_sibling_end_line), level=LogLevel.DEBUG)
        # endregion
    pass


def check_file(client: TeamscaleClient, commit_timestamp: int, previous_commit_timestamp: int,
               affected_files: [FileChange], file: str, file_start_line: int, file_end_line: int) \
        -> (Affectedness, int, int):
    if is_file_affected_at_file_changes(file, affected_files):
        file_name = file.split('/')[-1]
        logger.white(file_name + " affected at commit    : " + str(commit_timestamp), level=LogLevel.VERBOSE)
        diff_dict: dict[DiffType, DiffDescription] = get_diff(client, file,
                                                              previous_commit_timestamp, file,
                                                              commit_timestamp)
        file_start_line, file_end_line = correct_lines(file_start_line, file_end_line,
                                                       diff_dict.get(
                                                           DiffType.LINE_BASED))
        if are_left_lines_affected_at_diff(file_start_line, file_end_line,
                                           diff_dict.get(DiffType.TOKEN_BASED)):
            logger.red(file_name + " affected critical", LogLevel.VERBOSE)
            return Affectedness.AFFECTED_CRITICAL, file_start_line, file_end_line
        else:
            logger.white(file_name + " is not affected critical", LogLevel.DEBUG)
            return Affectedness.AFFECTED_BY_COMMIT, file_start_line, file_end_line
    else:
        return Affectedness.NOT_AFFECTED, file_start_line, file_end_line
