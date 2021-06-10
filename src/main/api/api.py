import json

import requests
from teamscale_client import TeamscaleClient

from defintions import JAVA_INT_MAX
from src.main.api.api_utils import get_project_api_service_url, get_global_service_url
from src.main.api.data import Commit, CommitAlert, FileChange, DiffDescription, DiffType, CloneFindingChurn
from src.main.pretty_print import MyPrinter, LogLevel
from src.main.utils.time_utils import timestamp_to_str

printer: MyPrinter = MyPrinter(LogLevel.VERBOSE)


def get_repository_commits(client: TeamscaleClient, start_commit_timestamp: int, end_commit_timestamp,
                           filter_alerts=False) -> [Commit]:
    """
    get repository commits for the project.
    filters for alert commits only optionally
    Section: project
    """
    url = get_project_api_service_url(client=client, service_name="repository-log-range")
    parameters = {"start": start_commit_timestamp,
                  "end": end_commit_timestamp,
                  "entry-count": JAVA_INT_MAX,
                  # preserve-newer: Whether to preserve commits newer or older than the given timestamp.
                  "preserve-newer": True,
                  # include-bounds: Whether or not commits for the timestamps from the start and/or end commit are
                  # included.
                  "include-bounds": True,
                  "t": "HEAD",
                  "commit-types": ["CODE_COMMIT",
                                   "ARCHITECTURE_CHANGE",
                                   "CODE_REVIEW",
                                   "EXTERNAL_ANALYSIS",
                                   "BLACKLIST_COMMIT"],
                  "exclude-other-branches": False,
                  # privacy-aware: Controls whether only repository log entries are returned where the current user
                  # was the committer.
                  "privacy-aware": False}

    if filter_alerts:
        parameters.update({"commit-attribute": "HAS_ALERTS"})

    response: requests.Response = client.get(url, parameters)
    parsed = json.loads(response.text)

    commit_list = [Commit.from_json(entry['commit']) for entry in parsed]

    return commit_list


def get_commit_alerts(client: TeamscaleClient, commit_timestamps: [int]) -> dict[Commit, [CommitAlert]]:
    """
    get commit alerts for given commit timestamps. Returns a tuple list of (Commit, [CommitAlert])
    Section: default
    """
    url = get_project_api_service_url(client, "commit-alerts")
    parameters = {"commit": commit_timestamps}

    printer.separator(level=LogLevel.DEBUG)
    printer.yellow("Getting commit alerts for timestamp " + str(commit_timestamps) + " at URL: " + str(url),
                   level=LogLevel.DEBUG)

    response: requests.Response = client.get(url, parameters)
    parsed = json.loads(response.text)
    printer.white(json.dumps(parsed, indent=4, sort_keys=False), level=LogLevel.DUMP)

    commit_alert_list_dict: dict[Commit, [CommitAlert]] = dict()

    for commit_alert_dict_entry in parsed:
        alert_list: [CommitAlert] = []
        for entry in commit_alert_dict_entry['alerts']:
            alert_list.append(CommitAlert.from_json(entry))
        commit: Commit = Commit.from_json(commit_alert_dict_entry['commit'])

        commit_alert_list_dict.update({commit: alert_list})

    return commit_alert_list_dict


def get_affected_files(client: TeamscaleClient, commit_timestamp: int) -> [FileChange]:
    """
    get affected files for given commit timestamp.
    """
    url = get_project_api_service_url(client, "commits/affected-files")
    parameters = {"commit": commit_timestamp}

    printer.separator(level=LogLevel.DEBUG)
    printer.yellow(
        "Getting affected files for timestamp " + str(commit_timestamp) + " at URL: " + str(url),
        level=LogLevel.DEBUG)

    response: requests.Response = client.get(url, parameters)
    parsed = json.loads(response.text)

    printer.white(json.dumps(parsed, indent=4, sort_keys=True), level=LogLevel.DUMP)

    affected_files: [FileChange] = [FileChange.from_json(j) for j in parsed]

    return affected_files


def get_diff(client: TeamscaleClient, left_file: str, left_commit_timestamp: int, right_file: str,
             right_commit_timestamp) -> dict[DiffType: DiffDescription]:
    """get a diff for two files and given timestamps"""
    url = get_global_service_url(client, "api/compare-elements")
    left = str(client.project) + "/" + left_file + "#@#" + str(left_commit_timestamp)
    right = str(client.project) + "/" + right_file + "#@#" + str(right_commit_timestamp)
    parameters = {"left": left,
                  "right": right,
                  "normalized": False}
    # I currently do not understand, whether "normalized" should be true or not : line-based? when disabled?

    printer.white("Getting diff for left: " + left_file + " at commit " + str(left_commit_timestamp),
                  level=LogLevel.DEBUG)
    printer.white("            and right: " + right_file + " at commit " + str(right_commit_timestamp),
                  level=LogLevel.DEBUG)
    link = client.url + "/compare.html#/" + left + "#&#" + right

    response: requests.Response = client.get(url, parameters)
    parsed = json.loads(response.text)

    printer.white(json.dumps(parsed, indent=4, sort_keys=True), level=LogLevel.DUMP)

    diff_dict = {}

    for e in parsed:
        d: DiffDescription = DiffDescription.from_json(e)
        diff_dict.update({d.name: d})

    return diff_dict, link


def get_repository_summary(client: TeamscaleClient) -> tuple[int, int]:
    """get repository summary: means start commit and most recent commit timestamp."""
    printer.white("Getting repository summary:", LogLevel.VERBOSE)
    url = get_project_api_service_url(client, "repository-summary")
    parameters = {"only-first-and-last": True}

    response: requests.Response = client.get(url, parameters)
    parsed = json.loads(response.text)
    printer.white(
        "First commit: " + timestamp_to_str(parsed['firstCommit']) + ", Most recent commit: " + timestamp_to_str(parsed['mostRecentCommit'])
        , level=LogLevel.VERBOSE
    )
    return parsed['firstCommit'], parsed['mostRecentCommit']


def get_clone_finding_churn(client: TeamscaleClient, commit_timestamp: int) -> CloneFindingChurn:
    """get clone finding churn for given commit timestamp"""
    printer.white("Getting clone finding churn for commit: " + str(commit_timestamp), LogLevel.DEBUG)
    url = get_project_api_service_url(client, "finding-churn/list")
    parameters = {
        "t": commit_timestamp
    }

    response: requests.Response = client.get(url, parameters)
    parsed = json.loads(response.text)
    printer.white(json.dumps(parsed, indent=4, sort_keys=True), level=LogLevel.DUMP)

    clone_finding_churn: CloneFindingChurn = CloneFindingChurn.from_json(parsed)

    return clone_finding_churn
