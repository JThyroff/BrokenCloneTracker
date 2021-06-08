import time
import traceback
from functools import reduce

import matplotlib.colors as m_colors
import matplotlib.pyplot as plt
import numpy as np
from teamscale_client import TeamscaleClient

from defintions import get_result_file_name, get_window_title
from src.main.analysis.analysis import update_filtered_alert_commits, analyse_one_alert_commit
from src.main.analysis.analysis_utils import are_left_lines_affected_at_diff, is_file_affected_at_file_changes, AnalysisResult, \
    TextSectionDeletedError
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


def plot_pie(project: str, successful_runs, failed_runs, successful_result_count):
    not_modified_count = 0
    one_instance_affected_critical_count = 0
    both_instances_affected_critical_count = 0
    instance_deletion_count = 0
    both_instances_deleted_count = 0
    clone_finding_count = 0
    # Interpretation of the result and categorization of the findings
    # Importance:  -1. Error while analysing            -> Fix code or special handling
    #               0. Deletion of relevant passage     -> A relevant text passage was deleted in further development
    #               1. New clone finding                -> The broken clone seems to appear as normal clone afterwards
    #               2. Only one instance affected critic-> The broken clone was modified at one point in time only at one text passage
    #                                                       => possibly even more inconsistency introduced
    #               3. Both instance affected critical  -> The relevant text passages are at least modified once together
    #                                                       => possibly consistent maintenance
    #               4. Not modified at all              -> after the introduction of the broken clone the relevant text passages were not
    #                                                       modified at all
    for entry in successful_runs:  # TODO clone finding count?
        analysis_results: [AnalysisResult] = entry[1]
        for result in analysis_results:
            result: AnalysisResult
            if result.instance_metrics.deleted and result.sibling_instance_metrics.deleted:
                both_instances_deleted_count += 1
            elif result.instance_metrics.deleted or result.sibling_instance_metrics.deleted:
                instance_deletion_count += 1
            elif result.clone_findings_count != 0:
                clone_finding_count += 1
            elif result.one_file_affected_count != 0:
                one_instance_affected_critical_count += 1
            elif result.both_instances_affected_critical_count != 0:
                both_instances_affected_critical_count += 1
            else:
                not_modified_count += 1

    labels = (
        'Not Modified at All', 'New Clone', 'Only One Affected Critical', 'Both Affected Critical', 'Only One Instance Deleted'
        , 'Both Instances Deleted', 'Analysis Error'
    )
    run_count = len(failed_runs) + successful_result_count
    sizes = [
        not_modified_count / run_count, clone_finding_count / run_count, one_instance_affected_critical_count / run_count
        , both_instances_affected_critical_count / run_count, instance_deletion_count / run_count
        , both_instances_deleted_count / run_count, len(failed_runs) / run_count
    ]
    idx = sizes.index(max(sizes))
    # all weights sum up to 1.0
    assert reduce(lambda a, b: a + b, sizes) == 1.0

    tab_colors = m_colors.TABLEAU_COLORS
    color_set = (
        tab_colors.get("tab:blue"), tab_colors.get("tab:orange"), tab_colors.get("tab:green"), tab_colors.get("tab:olive")
        , tab_colors.get("tab:purple"), tab_colors.get("tab:pink"), tab_colors.get("tab:red")
    )

    fig1, ax1 = plt.subplots(figsize=(12, 8))
    ax1.pie(sizes, labels=labels, autopct='%1.1f%%', shadow=False, startangle=180, colors=color_set)
    ax1.axis('equal')  # Equal aspect ratio ensures that pie is drawn as a circle.
    my_circle = plt.Circle((0, 0), 0.7, color='white')
    ax1.add_artist(my_circle)
    fig1.canvas.set_window_title(get_window_title(project))
    plt.legend(loc=(-0.14, -0.12))
    fig1.tight_layout()


def plot_violin_plot(project, successful_runs, failed_runs):
    fig, axs = plt.subplots(figsize=(10, 6))

    one_file_affected_count_list = []
    both_files_affected_critical_count_list = []
    one_instance_affected_critical_count_list = []
    both_instances_affected_critical_count_list = []
    # instance metrics
    file_affected_count_list = []
    affected_critical_count_list = []

    clone_findings_count_list = []

    for run in successful_runs:
        alert_commit_timestamp, results = run
        for r in results:
            one_file_affected_count_list.append(r.one_file_affected_count)
            both_files_affected_critical_count_list.append(r.both_files_affected_count)
            one_instance_affected_critical_count_list.append(r.one_instance_affected_critical_count)
            both_instances_affected_critical_count_list.append(r.both_instances_affected_critical_count)
            file_affected_count_list.append(r.instance_metrics.file_affected_count)
            file_affected_count_list.append(r.sibling_instance_metrics.file_affected_count)
            affected_critical_count_list.append(r.instance_metrics.affected_critical_count)
            affected_critical_count_list.append(r.sibling_instance_metrics.affected_critical_count)
            clone_findings_count_list.append(r.clone_findings_count)
            # clone.instance_metrics.deleted

    all_data = [
        affected_critical_count_list, one_instance_affected_critical_count_list, both_instances_affected_critical_count_list
        , file_affected_count_list, one_file_affected_count_list, both_files_affected_critical_count_list, clone_findings_count_list
    ]

    # plot violin plot
    axs.violinplot(all_data, showmeans=False, showmedians=True, vert=False)
    axs.set_title('Instance Metrics')

    # adding vertical grid lines
    axs.xaxis.grid(True)
    total = []
    for i in all_data:
        total += i
    axs.set_xticks([x for x in range(max(total) + 1)])
    # add y-tick labels
    plt.setp(
        axs, yticks=[y + 1 for y in range(len(all_data))]
        , yticklabels=[
            'Affected Critical', 'One Instance Affected Critical', 'Both Instances Affected Critical', 'File Affected', 'One File Affected'
            , 'Both Files Affected', 'New Clone Findings'
        ]
    )
    axs.invert_yaxis()
    fig.canvas.set_window_title(get_window_title(project))
    fig.tight_layout()


def plot_bar(project, successful_runs, successful_result_count):
    instance_deleted_count = 0
    sibling_deleted_count = 0
    one_instance_deleted_count = 0
    both_instances_deleted_count = 0
    for run in successful_runs:
        alert_commit_timestamp, results = run
        for r in results:
            if r.instance_metrics.deleted:
                instance_deleted_count += 1
            if r.sibling_instance_metrics.deleted:
                sibling_deleted_count += 1
            if r.instance_metrics.deleted and r.sibling_instance_metrics.deleted:
                both_instances_deleted_count += 1
            elif r.instance_metrics.deleted or r.sibling_instance_metrics.deleted:
                one_instance_deleted_count += 1
    labels = ['Instance Deleted', 'Sibling Deleted', 'One Instance Deleted', 'Both Instances Deleted']
    true_count = [instance_deleted_count, sibling_deleted_count, one_instance_deleted_count, both_instances_deleted_count]
    false_count = [
        successful_result_count - instance_deleted_count, successful_result_count - sibling_deleted_count
        , successful_result_count - one_instance_deleted_count, successful_result_count - both_instances_deleted_count
    ]
    for i, j in zip(true_count, false_count):
        assert (i + j) == successful_result_count

    y = np.arange(len(labels))  # the label locations
    width = 0.35  # the width of the bars

    fig, ax = plt.subplots()
    rects1 = ax.barh(y - width / 2, true_count, width, label='True')
    rects2 = ax.barh(y + width / 2, false_count, width, label='False')

    # Add some text for labels, title and custom y-axis tick labels, etc.
    ax.set_yticks(y)
    ax.set_yticklabels(labels)
    ax.invert_yaxis()
    ax.legend()

    #    ax.bar_label(rects1, padding=3)
    #   ax.bar_label(rects2, padding=3)
    fig.canvas.set_window_title(get_window_title(project))
    fig.tight_layout()


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

    plot_violin_plot(project, successful_runs, failed_runs)
    plot_pie(project, successful_runs, failed_runs, successful_result_count)
    plot_bar(project, successful_runs, successful_result_count)

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
        except (NotImplemented, TextSectionDeletedError):
            traceback.print_exc()
            printer.red("ERROR")
            failed_runs.append(alert_commit.timestamp)
    printer.blue("Analysis took: " + str(time.process_time() - start) + " time.", LogLevel.INFO)
    printer.blue("Alert commit count: " + str(len(alert_file.alert_commit_list)), LogLevel.INFO)
    printer.blue("Successful analysis count: " + str(successful_analysis_count))

    result_dict = {"successful runs": successful_runs, "failed runs": failed_runs}
    write_to_file(get_result_file_name(client.project), result_dict)
    plot_results(client.project, successful_runs, failed_runs)
    return


def main(client: TeamscaleClient) -> None:
    client.check_api_version()
    client.branch = "main"

    def read_and_plot():
        result_dict: dict = read_from_file(get_result_file_name(client.project))
        successful_runs = result_dict.get("successful runs")
        failed_runs = result_dict.get("failed runs")
        plot_results(client.project, successful_runs, failed_runs)

    read_and_plot()
    return
    run_analysis(client)
    analyse_one_alert_commit(client, 1493636171000)

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
