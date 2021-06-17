import os

# region directories
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECTS_DIR = 'projects'
# endregion

WINDOW_TITLE = 'Broken Clone Lifecycle Analysis for '

FILE_NAME_ALERT_COMMIT_LIST = 'alert_timestamp_list.json'
FILE_NAME_ALERT = 'alerts.json'
FILE_NAME_RESULT = 'results.json'

JAVA_INT_MAX = 2147483647

NEW_CLONE_SIMILARITY_THRESHOLD = 0.8


def get_project_dir(project: str) -> str:
    return ROOT_DIR + '/' + PROJECTS_DIR + '/' + project


def get_alert_timestamp_list_file_name(project: str) -> str:
    return get_project_dir(project) + '/' + FILE_NAME_ALERT_COMMIT_LIST


def get_alert_file_name(project: str) -> str:
    return get_project_dir(project) + '/' + FILE_NAME_ALERT


def get_result_file_name(project: str) -> str:
    return get_project_dir(project) + '/' + FILE_NAME_RESULT


def get_window_title(project: str) -> str:
    return WINDOW_TITLE + project
