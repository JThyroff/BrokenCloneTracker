from teamscale_client import TeamscaleClient

from src.main.analysis.analysis import analyse_one_alert_commit
from src.main.analysis.analysis_utils import are_left_lines_affected_at_diff, is_file_affected_at_file_changes
from src.main.api.data import DiffType, Commit, DiffDescription
from src.main.persistence import parse_args
from src.main.pretty_print import MyLogger, LogLevel

logger: MyLogger = MyLogger(LogLevel.INFO)


def show_projects(client: TeamscaleClient) -> None:
    """
    print the projects to console
    :param client: the teamscale client
    """
    logger.yellow("List of available Projects: ")

    projects = client.get_projects()
    for project in projects:
        print(str(project))
    logger.separator()


def main(client: TeamscaleClient) -> None:
    client.check_api_version()
    analyse_one_alert_commit(client, 1521580769000)

    return
    get_clone_finding_churn(client, 1521580769000)
    get_repository_summary(client)
    update_filtered_alert_commits(client)
    show_projects(client)
    alert_commits: [Commit] = get_repository_commits(client)
    commit: Commit = Commit.from_json(alert_commits[0])
    get_commit_alerts(client, 1608743869000)
    a = get_affected_files(client, commit.timestamp)
    b = is_file_affected_at_file_changes("src/main/java/org/jabref/JabRefGUI.java", a)
    print(b)
    d: DiffDescription = get_diff(client, DiffType.TOKEN_BASED,
                                  "src/main/java/org/jabref/logic/importer/WebFetchers.java",
                                  1606807412000,
                                  "src/main/java/org/jabref/logic/importer/WebFetchers.java", 1608743869000)
    print(str(d))
    print(str(are_left_lines_affected_at_diff(93, 105, d)))


if __name__ == "__main__":
    teamscale_client = parse_args()
    main(teamscale_client)
