import json
from json import JSONDecodeError
from pathlib import Path
from typing import TextIO

import jsonpickle
from teamscale_client import TeamscaleClient

from defintions import get_alert_file_name, get_project_dir
from src.main.analysis_utils import is_file_affected_at_file_changes, are_left_lines_affected_at_diff, correct_lines
from src.main.api import get_repository_summary, get_repository_commits, get_commit_alerts, get_affected_files, get_diff
from src.main.data import CommitAlert, Commit, FileChange, DiffType, DiffDescription, TextRegionLocation
from src.main.persistence import AlertFile
from src.main.pretty_print import MyLogger, LogLevel

logger: MyLogger = MyLogger(LogLevel.VERBOSE)


def create_project_dir(project: str):
    Path(get_project_dir(project)).mkdir(parents=True, exist_ok=True)


def update_filtered_alert_commits(client: TeamscaleClient):
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
    logger.yellow("Analysing one alert commit...", level=LogLevel.INFO)
    logger.white("Timestamp : " + str(alert_commit_timestamp), level=LogLevel.INFO)

    alerts: dict[Commit, [CommitAlert]] = get_commit_alerts(client, alert_commit_timestamp)
    s = jsonpickle.encode(alerts, keys=True)
    x = jsonpickle.decode(s, keys=True)

    parsed = json.loads(s)
    logger.white(json.dumps(parsed, indent=4), level=LogLevel.DEBUG)

    alert_list: [CommitAlert] = []
    for key in alerts.keys():  # search for key and read alert list
        if type(key) == Commit and key.timestamp == alert_commit_timestamp:
            alert_list = alerts[key]

    # fetch repository summary
    summary: tuple[int, int] = get_repository_summary(client)

    for i in alert_list:
        i: CommitAlert
        loc: TextRegionLocation = i.context.expected_clone_location

        # region logging
        logger.separator(level=LogLevel.VERBOSE)
        logger.yellow("Analysing Alert: " + i.message, LogLevel.VERBOSE)
        logger.yellow("Location.raw_start_line : " + str(loc.raw_start_line), level=LogLevel.VERBOSE)
        logger.yellow("Location.raw_end_line : " + str(loc.raw_end_line), level=LogLevel.VERBOSE)
        logger.separator(LogLevel.VERBOSE)
        # endregion
        # start analysis
        analysis_start: int = alert_commit_timestamp + 1
        analysis_step: int = 15555555_000  # milliseconds. 6 months
        # two variables two handle the offset of the broken clone region over time
        loc_start_line = loc.raw_start_line
        loc_end_line = loc.raw_end_line
        commit_list: [Commit] = []
        while analysis_start < summary[1]:
            step = analysis_start + analysis_step
            if step > summary[1]:
                step = summary[1]
            new_commits = get_repository_commits(client, analysis_start, step)
            expected_file = i.context.expected_clone_location.uniform_path
            expected_sibling = i.context.expected_sibling_location.uniform_path
            previous_commit_timestamp = alert_commit_timestamp

            for commit in new_commits:
                # Goal: In the end one want to say which category fits the file. three options
                # so check diff
                affected_files: [FileChange] = get_affected_files(client, commit.timestamp)
                b = (False, False)
                if is_file_affected_at_file_changes(expected_file, affected_files):
                    logger.white("File affected at commit    : " + str(commit.timestamp), level=LogLevel.VERBOSE)
                    diff_dict: dict[DiffType, DiffDescription] = get_diff(client, DiffType.TOKEN_BASED, expected_file,
                                                                          previous_commit_timestamp, expected_file,
                                                                          commit.timestamp)
                    loc_start_line, loc_end_line = correct_lines(loc_start_line, loc_end_line,
                                                                 diff_dict.get(DiffType.LINE_BASED_IGNORE_WHITESPACE))
                    if are_left_lines_affected_at_diff(loc_start_line, loc_end_line,
                                                       diff_dict.get(DiffType.TOKEN_BASED)):
                        logger.yellow("File affected critical", LogLevel.INFO)
                    else:
                        logger.yellow("File is not affected critical", LogLevel.INFO)
                    b = (True, False)
                if is_file_affected_at_file_changes(expected_sibling, affected_files):
                    logger.white("Sibling affected at commit : " + str(commit.timestamp), level=LogLevel.VERBOSE)
                    diff_dict: dict[DiffType, DiffDescription] = get_diff(client, DiffType.TOKEN_BASED, expected_file,
                                                                          previous_commit_timestamp, expected_file,
                                                                          commit.timestamp)
                    loc_start_line, loc_end_line = correct_lines(loc_start_line, loc_end_line,
                                                                 diff_dict.get(DiffType.LINE_BASED_IGNORE_WHITESPACE))
                    if are_left_lines_affected_at_diff(loc_start_line, loc_end_line,
                                                       diff_dict.get(DiffType.TOKEN_BASED)):
                        logger.yellow("Sibling affected critical", LogLevel.INFO)
                    else:
                        logger.yellow("Sibling is not affected critical", LogLevel.INFO)
                    b = (b[0], True)
                if b == (True, True):
                    logger.white("-> Both affected", LogLevel.INFO)
                elif b == (True, False) or b == (False, True):
                    logger.white("-> One affected", LogLevel.INFO)
                previous_commit_timestamp = commit.timestamp
            commit_list.extend(new_commits)

            analysis_start = step + 1
            pass

    pass
