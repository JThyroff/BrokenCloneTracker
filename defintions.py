import os

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECTS_DIR = 'projects'

FILE_NAME_ALERT = 'alerts.json'


def get_project_dir(project: str) -> str:
    return ROOT_DIR + '/' + PROJECTS_DIR + '/' + project


def get_alert_file_name(project: str) -> str:
    return get_project_dir(project) + '/' + FILE_NAME_ALERT
