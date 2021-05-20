from pathlib import Path
from typing import TextIO

import jsonpickle
from teamscale_client import TeamscaleClient

from defintions import get_alert_file_name, get_project_dir
from src.main.api import get_repository_summary
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
        alert_file = AlertFile(client.project)

    except FileExistsError:
        # the file already exists
        # read the current data from the file, process and update it
        with open(file_name, 'r') as file:
            file: TextIO
            alert_file = jsonpickle.decode(file.read())
