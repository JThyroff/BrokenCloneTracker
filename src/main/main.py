import traceback

import matplotlib.pyplot as plt
from teamscale_client import TeamscaleClient

from defintions import get_result_file_name
from src.main.analysis.analysis import update_filtered_alert_commits, analyse_one_alert_commit
from src.main.analysis.analysis_utils import are_left_lines_affected_at_diff, is_file_affected_at_file_changes, AnalysisResult
from src.main.api.data import DiffType, Commit, DiffDescription
from src.main.persistence import parse_args, AlertFile, write_to_file
from src.main.pretty_print import MyPrinter, LogLevel

printer: MyPrinter = MyPrinter(LogLevel.INFO)


def show_projects(client: TeamscaleClient) -> None:
    """
    print the projects to console
    :param client: the teamscale client
    """
    printer.yellow("List of available Projects: ")

    projects = client.get_projects()
    for project in projects:
        print(str(project))
    printer.separator()


def plot_results(successful_runs, failed_runs):
    printer.blue("Successful runs: ")
    printer.white(", ".join(str(entry[0]) for entry in successful_runs))
    printer.blue("Failed runs: ")
    printer.red(", ".join(str(commit_timestamp) for commit_timestamp in failed_runs))
    labels = 'Frogs', 'Hogs', 'Dogs', 'Logs'
    sizes = [15, 30, 45, 10]
    explode = (0, 0.1, 0, 0)  # only "explode" the 2nd slice (i.e. 'Hogs')

    fig1, ax1 = plt.subplots()
    ax1.pie(sizes, explode=explode, labels=labels, autopct='%1.1f%%',
            shadow=True, startangle=90)
    ax1.axis('equal')  # Equal aspect ratio ensures that pie is drawn as a circle.

    plt.show()


def run_analysis(client: TeamscaleClient):
    client.check_api_version()
    alert_file: AlertFile = update_filtered_alert_commits(client, overwrite=False)
    printer.separator(LogLevel.INFO)
    printer.blue("Alert commit count: " + str(len(alert_file.alert_commit_list)), LogLevel.INFO)

    successful_analysis_count = 0
    successful_runs = []
    failed_runs = []
    for alert_commit in alert_file.alert_commit_list:
        printer.separator(LogLevel.INFO)
        alert_commit: Commit
        try:
            results: [AnalysisResult] = analyse_one_alert_commit(client, alert_commit.timestamp)
            successful_analysis_count += 1
            successful_runs.append((alert_commit.timestamp, results))
        except Exception as e:
            traceback.print_exc()
            printer.red("ERROR")
            failed_runs.append(alert_commit.timestamp)
    printer.blue("Alert commit count: " + str(len(alert_file.alert_commit_list)), LogLevel.INFO)
    printer.blue("Successful analysis count: " + str(successful_analysis_count))

    write_to_file(get_result_file_name(client.project), successful_runs)
    plot_results(successful_runs, failed_runs)
    return


def main(client: TeamscaleClient) -> None:
    client.check_api_version()
    run_analysis(client)
    return
    analyse_one_alert_commit(client, 1521580769000)
    get_clone_finding_churn(client, 1521580769000)
    get_repository_summary(client)

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
