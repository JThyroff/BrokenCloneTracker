from teamscale_client.utils import auto_str


@auto_str
class Commit(object):
    def __init__(self, branch: str, parentCommits: [], timestamp: int, type: str):
        self.branch = branch
        self.parentCommits = parentCommits
        self.timestamp = timestamp
        self.type = type

    @classmethod
    def from_json(cls, json):
        return Commit(json['branchName'], json['parentCommits'], json['timestamp'], json['type'])
