import json
from json import JSONDecodeError
from pathlib import Path
from typing import TextIO

import jsonpickle
from teamscale_client import TeamscaleClient

from defintions import get_alert_file_name, get_project_dir
from src.main.analysis_utils import is_file_affected_at_file_changes, are_left_lines_affected_at_diff
from src.main.api import get_repository_summary, get_repository_commits, get_commit_alerts, get_affected_files, get_diff
from src.main.data import CommitAlert, Commit, FileChange, DiffType, DiffDescription, TextRegionLocation
from src.main.persistence import AlertFile
from src.main.pretty_print import MyLogger

logger: MyLogger = MyLogger.get_logger()


def create_project_dir(project: str):
    Path(get_project_dir(project)).mkdir(parents=True, exist_ok=True)


def update_filtered_alert_commits(client: TeamscaleClient):
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
    alerts: dict[Commit, [CommitAlert]] = get_commit_alerts(client, alert_commit_timestamp)
    s = jsonpickle.encode(alerts, keys=True)
    x = jsonpickle.decode(s, keys=True)
    parsed = json.loads(s)
    print(json.dumps(parsed, indent=4))

    alert_list: [CommitAlert] = []
    for key in alerts.keys():  # search for key and read alert list
        print("Timestamp : " + str(key.timestamp))
        if type(key) == Commit and key.timestamp == alert_commit_timestamp:
            alert_list = alerts[key]

    # print repository summary
    summary: tuple[int, int] = get_repository_summary(client)

    for i in alert_list:
        i: CommitAlert
        loc: TextRegionLocation = i.context.expected_clone_location

        logger.print_separator()
        logger.print_highlighted("Analysing Alert: " + i.message)
        # start analysis
        analysis_start: int = alert_commit_timestamp + 1
        analysis_step: int = 15555555_000  # milliseconds. 6 months
        commit_list: [Commit] = []
        while analysis_start < summary[1]:
            step = analysis_start + analysis_step
            if step > summary[1]:
                step = summary[1]
            new_commits = get_repository_commits(client, analysis_start, step)
            expected_file = i.context.expected_clone_location.uniform_path
            expected_sibling = i.context.expected_sibling_location.uniform_path
            for commit in new_commits:
                # Goal: In the end one want to say which category fits the file. three options
                # so check diff
                affected_files: [FileChange] = get_affected_files(client, commit.timestamp)
                b = (False, False)
                if is_file_affected_at_file_changes(expected_file, affected_files):
                    print("File affected at commit    : " + str(commit.timestamp))
                    diff_description: DiffDescription = get_diff(client, DiffType.TOKEN_BASED, expected_file,
                                                                 alert_commit_timestamp, expected_file,
                                                                 commit.timestamp)
                    if are_left_lines_affected_at_diff(loc.raw_start_line, loc.raw_end_line, diff_description):
                        logger.print_highlighted("File affected critical")
                    else:
                        logger.print_highlighted("File is not affected critical")
                    b = (True, False)
                    pass
                if is_file_affected_at_file_changes(expected_sibling, affected_files):
                    print("Sibling affected at commit : " + str(commit.timestamp))
                    diff_description: DiffDescription = get_diff(client, DiffType.TOKEN_BASED, expected_file,
                                                                 alert_commit_timestamp, expected_file,
                                                                 commit.timestamp)
                    if are_left_lines_affected_at_diff(loc.raw_start_line, loc.raw_end_line, diff_description):
                        logger.print_highlighted("Sibling affected critical")
                    else:
                        logger.print_highlighted("Sibling is not affected critical")
                    b = (b[0], True)
                if b == (True, True):
                    print("-> Both affected")
                elif b == (True, False) or b == (False, True):
                    print("-> One affected")
            commit_list.extend(new_commits)

            analysis_start = step + 1
            pass

    pass
