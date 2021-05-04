def get_project_api_service_url(client, service_name):
    """Returns the full url pointing to a project service.

    Args:
       client: the client
       service_name(str): the name of the service for which the url should be generated

    Returns:
        str: The full url
    """
    return "{client.url}/api/projects/{client.project}/{service}/".format(client=client, service=service_name)
