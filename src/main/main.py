import time
import traceback
from functools import reduce

import matplotlib.pyplot as plt
from teamscale_client import TeamscaleClient

from defintions import get_result_file_name
from src.main.analysis.analysis import update_filtered_alert_commits, analyse_one_alert_commit
from src.main.analysis.analysis_utils import are_left_lines_affected_at_diff, is_file_affected_at_file_changes, AnalysisResult
from src.main.api.data import DiffType, Commit, DiffDescription
from src.main.persistence import parse_args, AlertFile, write_to_file, read_from_file
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


def plot_results(project: str, successful_runs, failed_runs):
    printer.blue("Successful runs: ", LogLevel.RELEVANT)
    printer.white(", ".join(str(entry[0]) for entry in successful_runs), LogLevel.RELEVANT)
    printer.blue("Failed runs: ", LogLevel.RELEVANT)
    printer.red(", ".join(str(commit_timestamp) for commit_timestamp in failed_runs), LogLevel.RELEVANT)

    successful_result_count = reduce(lambda a, b: a + b, (len(entry[1]) for entry in successful_runs))
    run_count = len(failed_runs) + successful_result_count
    printer.separator(LogLevel.RELEVANT)
    printer.blue(
        "Successful run count:\t\t" + str(len(successful_runs))
        + "\nSuccessful result count:\t" + str(successful_result_count)
        + "\nFailed result count:\t\t" + str(len(failed_runs))
        , LogLevel.RELEVANT
    )

    clone_finding_count = 0
    one_instance_affected_critical_count = 0
    instance_deletion_count = 0
    both_instances_affected_critical_count = 0
    not_modified_count = 0
    # Interpretation of the result and categorization of the findings
    # Importance:   0. Error while analysing            -> Fix code or special handling
    #               1. New clone finding                -> The broken clone seems to appear as normal clone afterwards
    #               2. Only one instance affected critic-> The broken clone was modified at one point in time only at one text passage
    #                  or deletion of relevant passage      => possibly even more inconsistency introduced
    #               3. Both instance affected critical  -> The relevant text passages are at least modified once together
    #                                                       => possibly consistent maintenance
    #               4. Not modified at all              -> after the introduction of the broken clone the relevant text passages were not
    #                                                       modified at all
    for entry in successful_runs:
        analysis_results: [AnalysisResult] = entry[1]
        for result in analysis_results:
            result: AnalysisResult
            if result.clone_findings_count != 0:
                clone_finding_count += 1
            elif result.instance_metrics.deleted or result.sibling_instance_metrics.deleted:
                instance_deletion_count += 1
            elif result.one_file_affected_count != 0:
                one_instance_affected_critical_count += 1
            elif result.both_instances_affected_critical_count != 0:
                both_instances_affected_critical_count += 1
            else:
                not_modified_count += 1

    labels = 'Not Modified at All', 'Only One Affected Critical', 'New Clone', 'Error', 'Both Affected Critical', 'Instance deletion'
    sizes = [
        not_modified_count / run_count, one_instance_affected_critical_count / run_count,
        clone_finding_count / one_instance_affected_critical_count, len(failed_runs) / run_count,
        both_instances_affected_critical_count / run_count, instance_deletion_count / run_count
    ]
    explode = (0.0, 0.1, 0.0, 0.0, 0.0, 0.0)

    fig1, ax1 = plt.subplots(figsize=(12, 8))
    ax1.pie(sizes, explode=explode, labels=labels, autopct='%1.1f%%',
            shadow=True, startangle=90)
    ax1.axis('equal')  # Equal aspect ratio ensures that pie is drawn as a circle.
    fig1.canvas.set_window_title("Broken Clone Lifecycles for " + project)
    plt.legend()
    plt.show()


def run_analysis(client: TeamscaleClient):
    client.check_api_version()
    alert_file: AlertFile = update_filtered_alert_commits(client, overwrite=False)
    printer.separator(LogLevel.INFO)
    printer.blue("Alert commit count: " + str(len(alert_file.alert_commit_list)), LogLevel.INFO)
    start = time.process_time()

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
    printer.blue("Analysis took: " + str(time.process_time() - start) + " time.", LogLevel.INFO)
    printer.blue("Alert commit count: " + str(len(alert_file.alert_commit_list)), LogLevel.INFO)
    printer.blue("Successful analysis count: " + str(successful_analysis_count))

    result_dict = {"successful runs": successful_runs, "failed runs": failed_runs}
    write_to_file(get_result_file_name(client.project), result_dict)
    plot_results(successful_runs, failed_runs)
    return


def main(client: TeamscaleClient) -> None:
    client.check_api_version()
    client.branch = "main"

    def read_and_plot():
        result_dict: dict = read_from_file(get_result_file_name(client.project))
        successful_runs = result_dict.get("successful runs")
        failed_runs = result_dict.get("failed runs")
        plot_results(client.project, successful_runs, failed_runs)

    analyse_one_alert_commit(client, 1504177241000)
    return
    run_analysis(client)
    read_and_plot()

    get_clone_finding_churn(client, 1521580769000)
    get_repository_summary(client)

    show_projects(client)
    alert_commits: [Commit] = get_repository_commits(client)
    commit: Commit = Commit.from_json(alert_commits[0])
    get_commit_alerts(client, 1608743869000)
    a = get_affected_files(client, commit.timestamp)
    b = is_file_affected_at_file_changes("src/main/java/org/jabref/JabRefGUI.java", a)
    print(b)
    d: DiffDescription = get_diff(
        client, DiffType.TOKEN_BASED
        , "src/main/java/org/jabref/logic/importer/WebFetchers.java", 1606807412000
        , "src/main/java/org/jabref/logic/importer/WebFetchers.java", 1608743869000
    )
    print(str(d))
    print(str(are_left_lines_affected_at_diff(93, 105, d)))


if __name__ == "__main__":
    teamscale_client = parse_args()
    main(teamscale_client)
