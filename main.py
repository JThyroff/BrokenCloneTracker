import argparse

from teamscale_client import TeamscaleClient
from teamscale_client.teamscale_client_config import TeamscaleClientConfig

from api_utils import get_project_api_service_url

TEAMSCALE_URL = "http://localhost:8080"

USERNAME = "admin"
ACCESS_TOKEN = "ide-access-token"

PROJECT_ID = "jabref"


def show_projects(client):
    projects = client.get_projects()
    print([str(project) for project in projects])


def filter_alert_commits(client: TeamscaleClient):
    # url = "%s/%s" % (client.get_global_service_url('api/projects/')), "jabref/repository-log-range"
    url = get_project_api_service_url(client=client, service_name="repository-log-range")
    print(url)


# client.get()
pass


def main():
    client = TeamscaleClient(TEAMSCALE_URL, USERNAME, ACCESS_TOKEN, PROJECT_ID)
    client.check_api_version()
    show_projects(client)
    filter_alert_commits(client)


def parse_args():
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

    print("∇Δ∇Δ∇Δ∇Δ∇Δ∇Δ∇Δ∇Δ∇Δ∇Δ∇Δ∇Δ∇Δ∇Δ∇Δ∇Δ∇Δ∇Δ∇")
    print("Parsed Arguments:")
    print("%s %s\n%s %s\n%s %s\n%s %s" % (
        "Teamscale URL :", str(TEAMSCALE_URL), "Username :", str(USERNAME), "Access Token :", str(ACCESS_TOKEN),
        "Project ID :", str(PROJECT_ID)))
    print("∇Δ∇Δ∇Δ∇Δ∇Δ∇Δ∇Δ∇Δ∇Δ∇Δ∇Δ∇Δ∇Δ∇Δ∇Δ∇Δ∇Δ∇Δ∇")


if __name__ == "__main__":
    parse_args()
    main()
