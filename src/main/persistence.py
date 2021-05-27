from teamscale_client.utils import auto_str

from src.main.data import Commit


@auto_str
class AlertFile:
    """Alert File serialization structure"""

    def __init__(self, project: str, first_commit: int, most_recent_commit: int, analysed_until: int,
                 alert_commit_list: [Commit]):
        self.project = project
        self.first_commit = first_commit
        self.most_recent_commit = most_recent_commit
        self.analysed_until = analysed_until
        self.alert_commit_list = alert_commit_list

    @staticmethod
    def from_summary(project: str, repository_summary: tuple[int, int]):
        return AlertFile(project, repository_summary[0], repository_summary[1], repository_summary[0] - 1, [])

    @classmethod
    def from_json(cls, json):
        return AlertFile(json['project'], json['first_commit'], json['most_recent_commit'],
                         json["analysed_until"],
                         json["alert_list"])

    def __eq__(self, other):
        if not isinstance(other, AlertFile):
            return NotImplemented
        elif self is other:
            return True
        else:
            return self.project == other.project and self.first_commit == other.first_commit \
                   and self.most_recent_commit == other.most_recent_commit \
                   and self.analysed_until == other.analysed_until and self.alert_commit_list == other.alert_commit_list