import argparse
import os
from configparser import ConfigParser
from json import JSONDecodeError
from pathlib import Path
from typing import TextIO

import jsonpickle
from teamscale_client import TeamscaleClient
from teamscale_client.teamscale_client_config import TeamscaleClientConfig
from teamscale_client.utils import auto_str

from defintions import get_alert_file_name, get_project_dir
from src.main.api.api import get_repository_summary
from src.main.api.data import Commit
from src.main.pretty_print import LogLevel, MyPrinter

printer: MyPrinter = MyPrinter(LogLevel.INFO)


def from_config_file(config_file):
    """Reads a Teamscale client configuration from the specified file.
    Args:
        config_file (str): Path of the client configuration to use.
    """
    if not os.path.exists(config_file) or not os.path.isfile(config_file):
        raise RuntimeError('Config file could not be found: %s' % config_file)

    parser = ConfigParser()
    parser.read(config_file)

    url = parser.get('teamscale', 'url', fallback=None)
    username = parser.get('teamscale', 'username', fallback=None)
    access_token = parser.get('teamscale', 'access_token', fallback=None)
    project_id = parser.get('project', 'id', fallback='')
    project_branch = parser.get('project', 'branch', fallback='')

    config = TeamscaleClientConfig(url, username, access_token, project_id)
    config.project_branch = project_branch
    config.config_file = config_file
    return config


def parse_args() -> TeamscaleClient:
    # region default
    teamscale_url = "http://localhost:8080"
    username = "admin"
    access_token = "ide-access-token"
    project_id = "jabref"
    project_branch = 'main'
    # endregion

    parser = argparse.ArgumentParser()
    parser.add_argument("--teamscale_client_config",
                        help="provide a teamscale client config file. "
                             "https://github.com/cqse/teamscale-client-python/blob/master/examples/.teamscale-client.config")
    parser.add_argument("--teamscale_url", help="provide a teamscale URL other than default: " + teamscale_url)
    parser.add_argument("--username", help="provide a username other than default: " + username)
    parser.add_argument("--access_token", help="provide a access_token other than default: " + access_token)
    parser.add_argument("--project_id", help="provide a project_id other than default: " + project_id)
    parser.add_argument("--project_branch", help="provide a project_branch other than default: " + project_branch)

    args = parser.parse_args()

    if args.teamscale_client_config:
        config: TeamscaleClientConfig = from_config_file(args.teamscale_client_config)
        teamscale_url = config.url
        username = config.username
        access_token = config.access_token
        project_id = config.project_id
        project_branch = config.project_branch
    if args.teamscale_url:
        teamscale_url = args.teamscale_url
    if args.username:
        username = args.username
    if args.access_token:
        access_token = args.access_token
    if args.project_id:
        project_id = args.project_id
    if args.project_branch:
        project_branch = args.project_branch

    printer.separator(level=LogLevel.CRUCIAL)
    printer.yellow("Parsed Arguments:", level=LogLevel.CRUCIAL)
    printer.white("%s\n%s\n%s\n%s\n%s" % (
        "Teamscale URL : " + str(teamscale_url), "Username : " + str(username), "Access Token : " + str(access_token),
        "Project ID : " + str(project_id), "Project Branch : " + str(project_branch)
    ), level=LogLevel.CRUCIAL)
    printer.separator(level=LogLevel.CRUCIAL)

    return TeamscaleClient(teamscale_url, username, access_token, project_id, branch=project_branch)


def create_project_dir(project: str):
    """Creates the directory where the project specific files are saved. For example the """
    Path(get_project_dir(project)).mkdir(parents=True, exist_ok=True)


def read_alert_file(client: TeamscaleClient, overwrite=False):
    file_name: str = get_alert_file_name(client.project)
    # create structure if non-existent
    create_project_dir(project=client.project)
    summary: tuple[int, int] = get_repository_summary(client)

    if overwrite:
        os.remove(file_name)

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
                # if error occurs while decoding -> fetch all data from repo
                alert_file = AlertFile.from_summary(client.project, summary)
    return file_name, alert_file


def read_from_file(file_name: str):
    with open(file_name, "r") as file:
        file: TextIO
        return jsonpickle.decode(file.read())


def write_to_file(file_name: str, content):
    with open(file_name, "w") as file:
        file.write(jsonpickle.encode(content))


@auto_str
class AlertFile:
    """Alert File serialization structure"""

    def __init__(self, project: str, first_commit: int, most_recent_commit: int, analysed_until: int,
                 alert_commit_list: [Commit]):
        self.project = project
        self.first_commit = first_commit
        self.most_recent_commit = most_recent_commit
        self.analysed_until = analysed_until
        self.alert_commit_list = alert_commit_list

    def __eq__(self, other):
        if not isinstance(other, AlertFile):
            return NotImplemented
        elif self is other:
            return True
        else:
            return self.project == other.project and self.first_commit == other.first_commit \
                   and self.most_recent_commit == other.most_recent_commit \
                   and self.analysed_until == other.analysed_until and self.alert_commit_list == other.alert_commit_list

    @staticmethod
    def from_summary(project: str, repository_summary: tuple[int, int]):
        return AlertFile(project, repository_summary[0], repository_summary[1], repository_summary[0] - 1, [])

    @classmethod
    def from_json(cls, json):
        return AlertFile(json['project'], json['first_commit'], json['most_recent_commit'],
                         json["analysed_until"],
                         json["alert_list"])
