import json

import requests
from teamscale_client import TeamscaleClient

from src.main.api_utils import get_project_api_service_url
from src.main.data import Commit, CommitAlert, FileChange
from src.main.pretty_print import print_separator, print_highlighted


def filter_alert_commits(client: TeamscaleClient) -> [Commit]:
    """
    filters the project for commits with alerts.
    """
    url = get_project_api_service_url(client=client, service_name="repository-log-range")
    parameters = {"entry-count": 10,
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
                  "commit-attribute": "HAS_ALERTS",
                  "exclude-other-branches": False,
                  # privacy-aware: Controls whether only repository log entries are returned where the current user
                  # was the committer.
                  "privacy-aware": False}

    print_separator()
    print_highlighted("Filtering for alert commits: " + str(url))

    response: requests.Response = client.get(url, parameters)
    parsed = json.loads(response.text)

    commit_list = [entry['commit'] for entry in parsed]

    print(json.dumps(commit_list, indent=4, sort_keys=False))
    return commit_list


def get_commit_alerts(client: TeamscaleClient, commit_timestamp: int) -> [(Commit, [CommitAlert])]:
    """
    get commit alerts for given commit timestamp. Returns a tuple list of (Commit, [CommitAlert])
    """
    url = get_project_api_service_url(client, "commit-alerts")
    parameters = {"commit": commit_timestamp}

    print_separator()
    print_highlighted("Getting commit alerts for timestamp " + str(commit_timestamp) + " at URL: " + str(url))

    response: requests.Response = client.get(url, parameters)
    parsed = json.loads(response.text)
    print(json.dumps(parsed, indent=4, sort_keys=False))

    commit_alert_list_tuple_list: [(Commit, [CommitAlert])] = []

    for i in range(len(parsed)):
        alert_list: [CommitAlert] = []
        for entry in parsed[i]['alerts']:
            alert_list.append(CommitAlert.from_json(entry))
        commit: Commit = Commit.from_json(parsed[i]['commit'])

        commit_alert_list_tuple_list.append((commit, alert_list))

    return commit_alert_list_tuple_list


def get_affected_files(client: TeamscaleClient, commit_timestamp: int) -> [FileChange]:
    """
    get affected files for given commit timestamp.
    """
    url = get_project_api_service_url(client, "commits/affected-files")
    parameters = {"commit": commit_timestamp}

    print_separator()
    print_highlighted("Getting affected files for timestamp " + str(commit_timestamp) + " at URL: " + str(url))

    response: requests.Response = client.get(url, parameters)
    parsed = json.loads(response.text)
    print(json.dumps(parsed, indent=4, sort_keys=True))

    affected_files: [FileChange] = [FileChange.from_json(j) for j in parsed]

    return affected_files
