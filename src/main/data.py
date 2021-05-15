from teamscale_client.utils import auto_str


@auto_str
class Commit(object):
    def __init__(self, branch: str, timestamp: int, type: str, parent_commits=None):
        if parent_commits is None:
            parent_commits = []
        self.branch = branch
        self.timestamp = timestamp
        self.type = type
        self.parent_commits = parent_commits

    @classmethod
    def from_json(cls, json):
        if "parentCommits" in json:
            return Commit(json['branchName'], json['timestamp'], json['type'], json['parentCommits'])
        else:
            return Commit(json['branchName'], json['timestamp'], json['type'])

    def __eq__(self, other):
        if not isinstance(other, Commit):
            return NotImplemented
        elif self is other:
            return True
        else:
            return self.branch == other.branch and self.timestamp == other.timestamp \
                   and self.parent_commits == other.parent_commits and self.type == other.type


@auto_str
class TextRegionLocation(object):
    def __init__(self, location: str, raw_end_line: int, raw_end_offset: int, raw_start_line: int,
                 raw_start_offset: int, type: str, uniform_path: str):
        self.location = location
        self.raw_end_line = raw_end_line
        self.raw_end_offset = raw_end_offset
        self.raw_start_line = raw_start_line
        self.raw_start_offset = raw_start_offset
        self.type = type
        self.uniform_path = uniform_path

    @classmethod
    def from_json(cls, json):
        return TextRegionLocation(json['location'], json['rawEndLine'],
                                  json['rawEndOffset'], json['rawStartLine'], json['rawStartOffset'],
                                  json['type'],
                                  json['uniformPath'])

    def __eq__(self, other):
        if not isinstance(other, TextRegionLocation):
            return NotImplemented
        elif self is other:
            return True
        else:
            return self.location == other.location and self.raw_end_line == other.raw_end_line \
                   and self.raw_end_offset == other.raw_end_offset and self.raw_start_line == other.raw_start_line \
                   and self.raw_start_offset == other.raw_start_offset and self.type == other.type \
                   and self.uniform_path == other.uniform_path


@auto_str
class CommitAlertContext(object):
    def __init__(self,
                 expected_clone_location: TextRegionLocation, expected_sibling_location: TextRegionLocation,
                 old_clone_location: TextRegionLocation,
                 removed_clone_id: str):
        self.expected_clone_location = expected_clone_location
        self.expected_sibling_location = expected_sibling_location
        self.old_clone_location = old_clone_location
        self.removed_clone_id = removed_clone_id

    @classmethod
    def from_json(cls, json):
        return CommitAlertContext(TextRegionLocation.from_json(json['expectedCloneLocation']),
                                  TextRegionLocation.from_json(json['expectedSiblingLocation']),
                                  TextRegionLocation.from_json(json['oldCloneLocation']),
                                  json['removedCloneId'])

    def __eq__(self, other):
        if not isinstance(other, CommitAlertContext):
            return NotImplemented
        elif self is other:
            return True
        else:
            return self.expected_clone_location == other.expected_clone_location \
                   and self.expected_sibling_location == other.expected_sibling_location \
                   and self.old_clone_location == other.old_clone_location \
                   and self.removed_clone_id == other.removed_clone_id


@auto_str
class CommitAlert(object):
    def __init__(self, context: CommitAlertContext, message: str):
        self.context = context
        self.message = message

    @classmethod
    def from_json(cls, json):
        return CommitAlert(CommitAlertContext.from_json(json['context']), json['message'])

    def __eq__(self, other):
        if not isinstance(other, CommitAlert):
            return NotImplemented
        elif self is other:
            return True
        else:
            return self.context == other.context and self.message == other.message


@auto_str
class FileChange(object):
    def __init__(self, uniform_path: str, change_type: str, commit: Commit):
        self.uniform_path = uniform_path
        self.change_type = change_type
        self.commit = commit

    @classmethod
    def from_json(cls, json):
        return FileChange(json['uniformPath'], json['changeType'], Commit.from_json(json['commit']))

    def __eq__(self, other):
        if not isinstance(other, FileChange):
            return NotImplemented
        elif self is other:
            return True
        else:
            return self.uniform_path == other.uniform_path and self.change_type == other.change_type \
                   and self.commit == other.commit
