import argparse

from teamscale_client import TeamscaleClient
from teamscale_client.teamscale_client_config import TeamscaleClientConfig

from pretty_print import print_separator, print_highlighted
from src.main.analysis import update_filtered_alert_commits, analyse_one_alert_commit
from src.main.analysis_utils import are_left_lines_affected_at_diff, is_file_affected_at_commit
from src.main.api import get_diff, filter_alert_commits, get_commit_alerts, get_affected_files, get_repository_summary
from src.main.data import DiffType, Commit, DiffDescription

TEAMSCALE_URL = "http://localhost:8080"

USERNAME = "admin"
ACCESS_TOKEN = "ide-access-token"

PROJECT_ID = "jabref"


def show_projects(client: TeamscaleClient) -> None:
    """
    print the projects to console
    :param client: the teamscale client
    """
    print_separator()
    print_highlighted("List of available Projects: ")

    projects = client.get_projects()
    for project in projects:
        print(str(project))


def main() -> None:
    client = TeamscaleClient(TEAMSCALE_URL, USERNAME, ACCESS_TOKEN, PROJECT_ID)
    client.check_api_version()
    analyse_one_alert_commit(client, 1521580769000)
    return
    update_filtered_alert_commits(client)
    get_repository_summary(client)
    show_projects(client)
    alert_commits: [Commit] = filter_alert_commits(client)
    commit: Commit = Commit.from_json(alert_commits[0])
    get_commit_alerts(client, 1608743869000)
    a = get_affected_files(client, commit.timestamp)
    b = is_file_affected_at_commit("src/main/java/org/jabref/JabRefGUI.java", a)
    print(b)
    d: DiffDescription = get_diff(client, DiffType.TOKEN_BASED,
                                  "src/main/java/org/jabref/logic/importer/WebFetchers.java",
                                  1606807412000,
                                  "src/main/java/org/jabref/logic/importer/WebFetchers.java", 1608743869000)
    print(str(d))
    print(str(are_left_lines_affected_at_diff(93, 105, d)))


def parse_args() -> None:
    global TEAMSCALE_URL
    global USERNAME
    global ACCESS_TOKEN
    global PROJECT_ID

    parser = argparse.ArgumentParser()
    parser.add_argument("--teamscale_client_config",
                        help="provide a teamscale client config file. "
                             "https://github.com/cqse/teamscale-client-python/blob/master/examples/.teamscale-client"
                             ".config")
    parser.add_argument("--teamscale_url", help="provide a teamscale URL other than default: " + TEAMSCALE_URL)
    parser.add_argument("--username", help="provide a username other than default: " + USERNAME)
    parser.add_argument("--access_token", help="provide a access_token other than default: " + ACCESS_TOKEN)
    parser.add_argument("--project_id", help="provide a project_id other than default: " + PROJECT_ID)

    args = parser.parse_args()

    if args.teamscale_client_config:
        config: TeamscaleClientConfig = TeamscaleClientConfig.from_config_file(args.teamscale_client_config)
        TEAMSCALE_URL = config.url
        USERNAME = config.username
        ACCESS_TOKEN = config.access_token
        PROJECT_ID = config.project_id
    if args.teamscale_url:
        TEAMSCALE_URL = args.teamscale_url
    if args.username:
        USERNAME = args.username
    if args.access_token:
        ACCESS_TOKEN = args.access_token
    if args.project_id:
        PROJECT_ID = args.project_id

    print_separator()
    print_highlighted("Parsed Arguments:")
    print("%s %s\n%s %s\n%s %s\n%s %s" % (
        "Teamscale URL :", str(TEAMSCALE_URL), "Username :", str(USERNAME), "Access Token :", str(ACCESS_TOKEN),
        "Project ID :", str(PROJECT_ID)))


if __name__ == "__main__":
    parse_args()
    main()
