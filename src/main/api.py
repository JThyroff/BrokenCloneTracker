import json

import requests
from teamscale_client import TeamscaleClient

from defintions import JAVA_INT_MAX
from src.main.api_utils import get_project_api_service_url, get_global_service_url
from src.main.data import Commit, CommitAlert, FileChange, DiffDescription, DiffType
from src.main.pretty_print import MyLogger, LogLevel

logger: MyLogger = MyLogger(LogLevel.VERBOSE)


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

    logger.print_separator(level=LogLevel.VERBOSE)
    logger.print_highlighted("Getting commit alerts for timestamp " + str(commit_timestamps) + " at URL: " + str(url),
                             level=LogLevel.VERBOSE)

    response: requests.Response = client.get(url, parameters)
    parsed = json.loads(response.text)
    logger.print(json.dumps(parsed, indent=4, sort_keys=False), level=LogLevel.DEBUG)

    commit_alert_list_dict: dict[Commit, [CommitAlert]] = dict()

    for i in range(len(parsed)):
        alert_list: [CommitAlert] = []
        for entry in parsed[i]['alerts']:
            alert_list.append(CommitAlert.from_json(entry))
        commit: Commit = Commit.from_json(parsed[i]['commit'])

        commit_alert_list_dict.update({commit: alert_list})

    return commit_alert_list_dict


def get_affected_files(client: TeamscaleClient, commit_timestamp: int) -> [FileChange]:
    """
    get affected files for given commit timestamp.
    """
    url = get_project_api_service_url(client, "commits/affected-files")
    parameters = {"commit": commit_timestamp}

    logger.print_separator(level=LogLevel.DEBUG)
    logger.print_highlighted(
        "Getting affected files for timestamp " + str(commit_timestamp) + " at URL: " + str(url),
        level=LogLevel.DEBUG)

    response: requests.Response = client.get(url, parameters)
    parsed = json.loads(response.text)

    logger.print(json.dumps(parsed, indent=4, sort_keys=True), level=LogLevel.DEBUG)

    affected_files: [FileChange] = [FileChange.from_json(j) for j in parsed]

    return affected_files


def get_diff(client: TeamscaleClient, diff_type: DiffType, left_file: str, left_commit_timestamp: int, right_file: str,
             right_commit_timestamp) -> DiffDescription:
    """get a diff for two files and given timestamps"""
    url = get_global_service_url(client, "api/compare-elements")

    parameters = {"left": str(client.project) + "/" + left_file + "#@#" + str(left_commit_timestamp),
                  "right": str(client.project) + "/" + right_file + "#@#" + str(right_commit_timestamp),
                  "normalized": False}
    # I currently do not understand, whether "normalized" should be true or not : line-based? when disabled?

    logger.print("Getting diff for left: " + left_file + " at commit " + str(left_commit_timestamp),
                 level=LogLevel.VERBOSE)
    logger.print("            and right: " + right_file + " at commit " + str(right_commit_timestamp),
                 level=LogLevel.VERBOSE)

    response: requests.Response = client.get(url, parameters)
    parsed = json.loads(response.text)

    logger.print(json.dumps(parsed, indent=4, sort_keys=True), level=LogLevel.DEBUG)

    for e in parsed:
        d: DiffDescription = DiffDescription.from_json(e)
        if d.name == diff_type.value:
            return d

    return NotImplemented


def get_repository_summary(client: TeamscaleClient) -> tuple[int, int]:
    url = get_project_api_service_url(client, "repository-summary")
    parameters = {"only-first-and-last": True}

    response: requests.Response = client.get(url, parameters)
    parsed = json.loads(response.text)
    logger.print(json.dumps(parsed, indent=4, sort_keys=True), level=LogLevel.VERBOSE)
    return parsed['firstCommit'], parsed['mostRecentCommit']
