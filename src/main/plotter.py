import math
from functools import reduce

import matplotlib.colors as m_colors
import numpy as np
from matplotlib import pyplot as plt

from defintions import get_window_title, get_pgf_dir, LATEX_TEXT_WIDTH
from src.main.analysis.analysis_utils import AnalysisResult
# https://jwalton.info/Matplotlib-latex-PGF/
# \showthe\textwidth
from src.main.utils.time_utils import display_time


def set_size(width_pt, fraction=1, subplots=(1, 1)):
    """Set figure dimensions to sit nicely in our document.

    Parameters
    ----------
    width_pt: float
            Document width in points
    fraction: float, optional
            Fraction of the width which you wish the figure to occupy
    subplots: array-like, optional
            The number of rows and columns of subplots.
    Returns
    -------
    fig_dim: tuple
            Dimensions of figure in inches
    """
    # Width of figure (in pts)
    fig_width_pt = width_pt * fraction
    # Convert from pt to inches
    inches_per_pt = 1 / 72.27

    # Golden ratio to set aesthetic figure height
    golden_ratio = (5 ** .5 - 1) / 2

    # Figure width in inches
    fig_width_in = fig_width_pt * inches_per_pt
    # Figure height in inches
    fig_height_in = fig_width_in * golden_ratio * (subplots[0] / subplots[1])

    return fig_width_in, fig_height_in


def plot_pie(project: str, successful_runs, failed_runs, successful_result_count, pgf=False):
    not_modified_count = 0
    one_instance_affected_critical_count = 0
    both_instances_affected_critical_count = 0
    instance_deletion_count = 0
    both_instances_deleted_count = 0
    clone_finding_count = 0
    # Interpretation of the result and categorization of the findings
    # Importance:  -1. Error while analysing            -> Fix code or special handling
    #               0. Deletion of both passages        -> Both relevant text passages were deleted in further development
    #               1. Deletion of relevant passage     -> A relevant text passage was deleted in further development
    #               2. New clone finding                -> The broken clone seems to appear as normal clone afterwards
    #               3. Only one instance affected critic-> The broken clone was modified at one point in time only at one text passage
    #                                                       => possibly even more inconsistency introduced
    #               4. Both instance affected critical  -> The relevant text passages are at least modified once together
    #                                                       => possibly consistent maintenance
    #               5. Not modified at all              -> after the introduction of the broken clone the relevant text passages were not
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
            elif result.one_instance_affected_critical_count != 0:
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
    assert math.isclose(reduce(lambda a, b: a + b, sizes), 1.0, abs_tol=0.01)

    tab_colors = m_colors.TABLEAU_COLORS
    color_set = (
        tab_colors.get("tab:blue"), tab_colors.get("tab:orange"), tab_colors.get("tab:green"), tab_colors.get("tab:olive")
        , tab_colors.get("tab:purple"), tab_colors.get("tab:pink"), tab_colors.get("tab:red")
    )

    x, y = set_size(LATEX_TEXT_WIDTH)
    fig1, ax1 = plt.subplots(figsize=(x, y + 3))
    ax1.pie(sizes, labels=labels, autopct='%1.1f%%', shadow=False, startangle=180, colors=color_set)
    ax1.axis('equal')  # Equal aspect ratio ensures that pie is drawn as a circle.
    my_circle = plt.Circle((0, 0), 0.7, color='white')
    ax1.add_artist(my_circle)
    fig1.canvas.set_window_title(get_window_title(project))
    plt.legend(loc=(-0.0, -0.0))
    fig1.tight_layout()
    if pgf:
        plt.savefig(get_pgf_dir(project) + project + '_pie.pgf')


def plot_instance_metrics(project, successful_runs, failed_runs, boxplot=False, with_file_affections=True, pgf=False):
    fig, axs = plt.subplots(figsize=set_size(LATEX_TEXT_WIDTH))

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

    if with_file_affections:
        all_data = [
            affected_critical_count_list, one_instance_affected_critical_count_list, both_instances_affected_critical_count_list
            , file_affected_count_list, one_file_affected_count_list, both_files_affected_critical_count_list, clone_findings_count_list
        ]
    else:
        all_data = [
            affected_critical_count_list, one_instance_affected_critical_count_list, both_instances_affected_critical_count_list
            , clone_findings_count_list
        ]

    # plot violin plot
    if boxplot:
        axs.boxplot(all_data, showmeans=False, vert=False)
    else:
        axs.violinplot(all_data, showmeans=False, showmedians=True, vert=False)
    axs.set_title('Instance Metrics')

    # adding vertical grid lines
    axs.xaxis.grid(True)
    total = []
    for i in all_data:
        total += i
    axs.set_xticks([x for x in range(0, max(total) + 1, 3)])
    # add y-tick labels

    plt.setp(
        axs, yticks=[y + 1 for y in range(len(all_data))]
        , yticklabels=[
            'Affected Critical', 'One Instance Affected Critical', 'Both Instances Affected Critical', 'File Affected', 'One File Affected'
            , 'Both Files Affected', 'New Clone Findings'
        ] if with_file_affections else [
            'Affected Critical', 'One Instance Affected Critical', 'Both Instances Affected Critical', 'New Clone Findings'
        ]
    )
    axs.invert_yaxis()
    fig.canvas.set_window_title(get_window_title(project))
    fig.tight_layout()
    if pgf:
        if boxplot:
            plt.savefig(get_pgf_dir(project) + project + '_box.pgf')
        else:
            plt.savefig(get_pgf_dir(project) + project + '_violin.pgf')


def plot_bar(project, successful_runs, successful_result_count, pgf=False):
    instance_deleted_count = 0
    sibling_deleted_count = 0
    one_instance_deleted_count = 0
    both_instances_deleted_count = 0
    instance_time_alive = 0
    sibling_time_alive = 0
    for run in successful_runs:
        alert_commit_timestamp, results = run
        for r in results:
            r: AnalysisResult
            instance_time_alive += r.instance_metrics.time_alive
            sibling_time_alive += r.sibling_instance_metrics.time_alive
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

    fig, ax = plt.subplots(figsize=set_size(LATEX_TEXT_WIDTH))
    rects1 = ax.barh(y - width / 2, true_count, width, label='True')
    rects2 = ax.barh(y + width / 2, false_count, width, label='False')

    # Add some text for labels, title and custom y-axis tick labels, etc.
    ax.set_yticks(y)
    ax.set_yticklabels(labels)
    ax.invert_yaxis()
    ax.legend()
    avg_time_alive = round((instance_time_alive + sibling_time_alive) / (2 * successful_result_count))
    ax.set_title('Deletion Metrics')
    #    ax.bar_label(rects1, padding=3)
    #   ax.bar_label(rects2, padding=3)
    ax.text(x=0, y=4.4, s='Average Time Alive: = ' + display_time(avg_time_alive))
    ax.text(x=0, y=4.8, s='Average instance lifetime = ' + display_time(round(instance_time_alive / successful_result_count)))
    ax.text(x=0, y=5.2, s='Average sibling lifetime = ' + display_time(round(sibling_time_alive / successful_result_count)))
    fig.canvas.set_window_title(get_window_title(project))
    fig.tight_layout()
    if pgf:
        plt.savefig(get_pgf_dir(project) + project + '_bar.pgf')
