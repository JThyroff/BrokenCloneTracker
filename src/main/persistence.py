import argparse

from teamscale_client import TeamscaleClient
from teamscale_client.teamscale_client_config import TeamscaleClientConfig
from teamscale_client.utils import auto_str

from src.main.api.data import Commit
from src.main.pretty_print import LogLevel, MyLogger

logger: MyLogger = MyLogger(LogLevel.INFO)


def parse_args() -> TeamscaleClient:
    # region default
    teamscale_url = "http://localhost:8080"
    username = "admin"
    access_token = "ide-access-token"
    project_id = "jabref"
    # endregion

    parser = argparse.ArgumentParser()
    parser.add_argument("--teamscale_client_config",
                        help="provide a teamscale client config file. "
                             "https://github.com/cqse/teamscale-client-python/blob/master/examples/.teamscale-client"
                             ".config")
    parser.add_argument("--teamscale_url", help="provide a teamscale URL other than default: " + teamscale_url)
    parser.add_argument("--username", help="provide a username other than default: " + username)
    parser.add_argument("--access_token", help="provide a access_token other than default: " + access_token)
    parser.add_argument("--project_id", help="provide a project_id other than default: " + project_id)

    args = parser.parse_args()

    if args.teamscale_client_config:
        config: TeamscaleClientConfig = TeamscaleClientConfig.from_config_file(args.teamscale_client_config)
        teamscale_url = config.url
        username = config.username
        access_token = config.access_token
        project_id = config.project_id
    if args.teamscale_url:
        teamscale_url = args.teamscale_url
    if args.username:
        username = args.username
    if args.access_token:
        access_token = args.access_token
    if args.project_id:
        project_id = args.project_id

    logger.separator(level=LogLevel.CRUCIAL)
    logger.yellow("Parsed Arguments:", level=LogLevel.CRUCIAL)
    logger.white("\t%s %s\n\t\t\t%s %s\n\t\t\t%s %s\n\t\t\t%s %s" % (
        "Teamscale URL :", str(teamscale_url), "Username :", str(username), "Access Token :", str(access_token),
        "Project ID :", str(project_id)), level=LogLevel.CRUCIAL)
    logger.separator(level=LogLevel.CRUCIAL)

    return TeamscaleClient(teamscale_url, username, access_token, project_id)


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

    @staticmethod
    def from_summary(project: str, repository_summary: tuple[int, int]):
        return AlertFile(project, repository_summary[0], repository_summary[1], repository_summary[0] - 1, [])

    @classmethod
    def from_json(cls, json):
        return AlertFile(json['project'], json['first_commit'], json['most_recent_commit'],
                         json["analysed_until"],
                         json["alert_list"])

    def __eq__(self, other):
        if not isinstance(other, AlertFile):
            return NotImplemented
        elif self is other:
            return True
        else:
            return self.project == other.project and self.first_commit == other.first_commit \
                   and self.most_recent_commit == other.most_recent_commit \
                   and self.analysed_until == other.analysed_until and self.alert_commit_list == other.alert_commit_list
