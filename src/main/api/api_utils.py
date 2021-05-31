from teamscale_client import TeamscaleClient


def get_project_api_service_url(client: TeamscaleClient, service_name: str):
    """Returns the full url pointing to a project api service.

    Args:
       client: the client
       service_name(str): the name of the service for which the url should be generated

    Returns:
        str: The full url
    """
    return "{client.url}/api/projects/{client.project}/{service}/".format(client=client, service=service_name)


def get_global_service_url(client: TeamscaleClient, service_name: str):
    return client.get_global_service_url(service_name)


def get_project_service_url(client: TeamscaleClient, service_name: str):
    return client.get_project_service_url(service_name)
