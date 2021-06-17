import time
import traceback
from functools import reduce

import matplotlib.pyplot as plt
from teamscale_client import TeamscaleClient

from defintions import get_result_file_name
from src.main.analysis.analysis import update_filtered_alert_commits, analyse_one_alert_commit
from src.main.analysis.analysis_utils import AnalysisResult
from src.main.api.api import get_affected_files
from src.main.api.data import Commit
from src.main.persistence import parse_args, AlertFile, write_to_file, read_from_file
from src.main.plotter import plot_instance_metrics, plot_pie, plot_bar
from src.main.pretty_print import MyPrinter, LogLevel
from src.main.utils.time_utils import display_time

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
    printer.separator(LogLevel.RELEVANT)
    printer.blue(
        "Successful run count:\t\t" + str(len(successful_runs))
        + "\nSuccessful result count:\t" + str(successful_result_count)
        + "\nFailed result count:\t\t" + str(len(failed_runs))
        , LogLevel.RELEVANT
    )

    plot_pie(project, successful_runs, failed_runs, successful_result_count)
    plot_bar(project, successful_runs, successful_result_count)
    plot_instance_metrics(project, successful_runs, failed_runs, boxplot=True, with_file_affections=False)
    plot_instance_metrics(project, successful_runs, failed_runs, with_file_affections=False)

    plt.show()


def run_analysis(client: TeamscaleClient):
    client.check_api_version()
    alert_file: AlertFile = update_filtered_alert_commits(client, overwrite=False)
    printer.separator(LogLevel.INFO)
    printer.blue("Alert commit count: " + str(len(alert_file.alert_commit_list)), LogLevel.INFO)
    start = int(time.time())

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
        except Exception:
            traceback.print_exc()
            printer.red("ERROR")
            failed_runs.append(alert_commit.timestamp)
    printer.blue("Analysis took: " + display_time(int((time.time() - start) * 1000)), LogLevel.INFO)
    printer.blue("Alert commit count: " + str(len(alert_file.alert_commit_list)), LogLevel.INFO)
    printer.blue("Successful analysis count: " + str(successful_analysis_count))

    result_dict = {"successful runs": successful_runs, "failed runs": failed_runs}
    write_to_file(get_result_file_name(client.project), result_dict)
    plot_results(client.project, successful_runs, failed_runs)
    return


def main(client: TeamscaleClient) -> None:
    client.check_api_version()

    def read_and_plot():
        result_dict: dict = read_from_file(get_result_file_name(client.project))
        successful_runs = result_dict.get("successful runs")
        failed_runs = result_dict.get("failed runs")
        plot_results(client.project, successful_runs, failed_runs)

    run_analysis(client)
    return
    update_filtered_alert_commits(client, overwrite=True)
    read_and_plot()
    analyse_one_alert_commit(client, 1485528948779)
    get_affected_files(client, 1612210799000)


if __name__ == "__main__":
    teamscale_client = parse_args()
    main(teamscale_client)
