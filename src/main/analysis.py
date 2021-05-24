import json
from json import JSONDecodeError
from pathlib import Path
from typing import TextIO

import jsonpickle
from teamscale_client import TeamscaleClient

from defintions import get_alert_file_name, get_project_dir
from src.main.api import get_repository_summary, get_repository_commits, get_commit_alerts
from src.main.data import CommitAlert, Commit, CommitAlertContext, TextRegionLocation
from src.main.persistence import AlertFile


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


def analyse_one_alert_commit(client: TeamscaleClient, commit_timestamp: int):
    alerts: dict[Commit, [CommitAlert]] = get_commit_alerts(client, commit_timestamp)
    s = jsonpickle.encode(alerts)
    parsed = json.loads(s)
    print(json.dumps(parsed, indent=4))

    alert_list: [CommitAlert] = []
    for key in alerts.keys():
        if key.type == Commit and key.timestamp == commit_timestamp:
            alert_list = alerts[key]
            pass
    for i in alert_list:
        i: CommitAlert
        ac: CommitAlertContext = i.context
        old_clone_loc: TextRegionLocation = ac.old_clone_location

        print(i)
        pass

        summary: tuple[int, int] = get_repository_summary(client)

        # start analysis
        analysis_start: int = commit_timestamp
        analysis_step: int = 15555555_000  # milliseconds. 6 months
        commit_list: [Commit] = []
        while analysis_start < summary[1]:
            step = analysis_start + analysis_step
            if step > summary[1]:
                step = summary[1]
            new_commits = get_repository_commits(client, analysis_start, step)
            for commit in new_commits:
                # Goal: In the end one want to say which category fits the file. three options
                # so check diff
                pass
            commit_list.extend(new_commits)

            analysis_start = step + 1
            pass

    print(alerts.keys())
    pass
