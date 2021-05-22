from json import JSONDecodeError
from pathlib import Path
from typing import TextIO

import jsonpickle
from teamscale_client import TeamscaleClient

from defintions import get_alert_file_name, get_project_dir
from src.main.api import get_repository_summary, filter_alert_commits
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
        alert_file.alert_commit_list.extend(filter_alert_commits(client, analysis_start, step))
        alert_file.analysed_until = step
        with open(file_name, "w") as file:
            file.write(jsonpickle.encode(alert_file))
        analysis_start = step + 1
        pass
