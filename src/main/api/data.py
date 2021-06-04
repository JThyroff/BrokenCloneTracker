from enum import Enum

import portion
from portion import Interval
from teamscale_client import TeamscaleClient
from teamscale_client.utils import auto_str


@auto_str
class Commit(object):
    def __init__(self, branch: str, timestamp: int, commit_type: str, parent_commits=None):
        if parent_commits is None:
            parent_commits = []
        self.branch = branch
        self.timestamp = timestamp
        self.commit_type = commit_type
        self.parent_commits = parent_commits

    def __eq__(self, other):
        if not isinstance(other, Commit):
            return NotImplemented
        elif self is other:
            return True
        else:
            return self.branch == other.branch and self.timestamp == other.timestamp \
                   and self.parent_commits == other.parent_commits and self.commit_type == other.commit_type

    def __hash__(self):
        return hash((self.branch, self.timestamp))

    @classmethod
    def from_json(cls, json):
        if "parentCommits" in json:
            return Commit(json['branchName'], json['timestamp'], json['type'], json['parentCommits'])
        else:
            return Commit(json['branchName'], json['timestamp'], json['type'])


class TextRegionLocation(object):
    def __init__(self, location: str, raw_end_line: int, raw_end_offset: int, raw_start_line: int,
                 raw_start_offset: int, location_type: str, uniform_path: str):
        self.location = location  # file path
        self.raw_end_line = raw_end_line
        self.raw_end_offset = raw_end_offset
        self.raw_start_line = raw_start_line
        self.raw_start_offset = raw_start_offset
        self.location_type = location_type  # TextRegionLocation ?
        self.uniform_path = uniform_path  # also file path ?

    def __str__(self):
        return "Location: " + self.uniform_path + " " + self.get_interval()

    def __eq__(self, other):
        if not isinstance(other, TextRegionLocation):
            return NotImplemented
        elif self is other:
            return True
        else:
            return self.location == other.location and self.raw_end_line == other.raw_end_line \
                   and self.raw_end_offset == other.raw_end_offset and self.raw_start_line == other.raw_start_line \
                   and self.raw_start_offset == other.raw_start_offset and self.location_type == other.location_type \
                   and self.uniform_path == other.uniform_path

    def get_interval(self):
        return "[" + str(self.raw_start_line) + "-" + str(self.raw_end_line) + ")"

    @classmethod
    def from_json(cls, json):
        return TextRegionLocation(json['location'], json['rawEndLine'],
                                  json['rawEndOffset'], json['rawStartLine'], json['rawStartOffset'],
                                  json['type'],
                                  json['uniformPath'])


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

    @classmethod
    def from_json(cls, json):
        return CommitAlertContext(TextRegionLocation.from_json(json['expectedCloneLocation']),
                                  TextRegionLocation.from_json(json['expectedSiblingLocation']),
                                  TextRegionLocation.from_json(json['oldCloneLocation']),
                                  json['removedCloneId'])


class CommitAlert(object):
    def __init__(self, context: CommitAlertContext, message: str):
        self.context = context
        self.message = message

    def __eq__(self, other):
        if not isinstance(other, CommitAlert):
            return NotImplemented
        elif self is other:
            return True
        else:
            return self.context == other.context and self.message == other.message

    def __str__(self):
        return ("Commit Alert: " + self.message + "\nExpected clone location: " + self.context.expected_clone_location.uniform_path
                + "\nInstance interval: " + self.context.expected_clone_location.get_interval() + "\nExpected sibling location: " +
                self.context.expected_sibling_location.uniform_path + "\nSibling interval: "
                + self.context.expected_sibling_location.get_interval())

    def get_link(self, client: TeamscaleClient, commit_timestamp: int) -> str:

        return (client.url + "/compare.html#/"
                + client.project + "/" + self.context.expected_sibling_location.uniform_path + "#@#"
                + client.branch + ":" + str(commit_timestamp) + "#&#"
                + client.project + "/" + self.context.expected_clone_location.uniform_path + "#@#"
                + client.branch + ":" + str(commit_timestamp) + "#&#"
                + str(self.context.expected_sibling_location.raw_start_line) + "-"
                + str(self.context.expected_sibling_location.raw_end_line) + ":"
                + str(self.context.expected_clone_location.raw_start_line) + "-"
                + str(self.context.expected_clone_location.raw_end_line)
                + "#&#isInconsistentClone")

    @classmethod
    def from_json(cls, json):
        return CommitAlert(CommitAlertContext.from_json(json['context']), json['message'])


@auto_str
class FileChange(object):
    def __init__(self, uniform_path: str, change_type: str, commit: Commit):
        self.uniform_path = uniform_path
        self.change_type = change_type
        self.commit = commit

    def __eq__(self, other):
        if not isinstance(other, FileChange):
            return NotImplemented
        elif self is other:
            return True
        else:
            return self.uniform_path == other.uniform_path and self.change_type == other.change_type \
                   and self.commit == other.commit

    @classmethod
    def from_json(cls, json):
        return FileChange(json['uniformPath'], json['changeType'], Commit.from_json(json['commit']))


class DiffType(Enum):
    TOKEN_BASED = "token-based"
    LINE_BASED = "line-based"
    LINE_BASED_IGNORE_WHITESPACE = "line-based (ignore whitespace)"

    @classmethod
    def from_json(cls, json):
        return DiffType[json.upper().replace("-", "_").replace("(", "").replace(")", "").replace(" ", "_")]


def list_to_interval_list(int_list: [int]) -> [Interval]:
    """Takes an int list and converts every two ints to an interval"""
    assert len(int_list) % 2 == 0
    to_return: [Interval] = []
    idx: int = 0
    while idx < len(int_list):
        to_return.append(
            portion.closedopen(int_list[idx], int_list[idx + 1]))
        idx = idx + 2
    return to_return


@auto_str
class DiffDescription:

    def __init__(self, name: DiffType, left_change_lines: [int], left_change_regions: [int], right_change_lines: [int],
                 right_change_regions: [int]):
        self.name = name
        self.left_change_line_intervals = []
        self.right_change_line_intervals = []
        self.left_change_region_intervals = []
        self.right_change_region_intervals = []
        """The lists are organised in pairs. Save them as Intervals"""
        self.left_change_line_intervals = list_to_interval_list(left_change_lines)
        self.right_change_line_intervals = list_to_interval_list(right_change_lines)
        self.left_change_region_intervals = list_to_interval_list(left_change_regions)
        self.right_change_region_intervals = list_to_interval_list(right_change_regions)
        assert len(self.left_change_line_intervals) == len(self.right_change_line_intervals)
        # assert len(self.left_change_region_intervals) == len(self.right_change_region_intervals)

    def __eq__(self, other):
        if not isinstance(other, DiffDescription):
            return NotImplemented
        elif self is other:
            return True
        else:
            return self.name == other.name and self.left_change_lines == other.left_change_lines \
                   and self.left_change_regions == other.left_change_regions \
                   and self.right_change_lines == other.right_change_lines \
                   and self.right_change_regions == other.right_change_regions

    @classmethod
    def from_json(cls, json):
        return DiffDescription(DiffType.from_json(json['name']), json['leftChangeLines'], json['leftChangeRegions'],
                               json["rightChangeLines"],
                               json["rightChangeRegions"])


@auto_str
class CloneProperties:
    def __init__(self, instances: int, length: int, gaps: int):
        self.instances = instances
        self.length = length
        self.gaps = gaps

    def __eq__(self, other):
        other: CloneProperties
        if not isinstance(other, CloneProperties):
            return NotImplemented
        elif self is other:
            return True
        else:
            return self.instances == other.instances and self.length == other.length and self.gaps == other.gaps

    @classmethod
    def from_json(cls, json):
        return CloneProperties(json["Instances"], json["Length"], json["Gaps"])


class CloneFinding:
    def __init__(self, group_name: str, category_name: str, message: str, location: TextRegionLocation,
                 finding_id: str, birth_commit: Commit, death_commit: Commit, assessment: str,
                 sibling_locations: [TextRegionLocation], properties: CloneProperties, analysis_timestamp: int,
                 type_id: str):
        self.group_name = group_name
        self.category_name = category_name
        self.message = message
        self.location = location
        self.finding_id = finding_id
        self.birth_commit = birth_commit
        self.death_commit = death_commit
        self.assessment = assessment
        self.sibling_locations = sibling_locations
        self.properties = properties
        self.analysis_timestamp = analysis_timestamp
        self.type_id = type_id

    def __str__(self):
        to_return: str = "{ Clone Finding: " + str(self.location) + "\n"
        for sibling in self.sibling_locations:
            sibling: TextRegionLocation
            to_return += "Sibling: " + str(sibling) + "\n"
        return to_return[:-1] + "}"

    def __eq__(self, other):
        if not isinstance(other, CloneFinding):
            return NotImplemented
        elif self is other:
            return True
        else:
            other: CloneFinding
            return self.group_name == other.group_name and self.category_name == other.category_name \
                   and self.message == other.message and self.location == other.location \
                   and self.finding_id == other.finding_id and self.birth_commit == other.birth_commit \
                   and self.death_commit == other.death_commit \
                   and self.assessment == other.assessment \
                   and self.sibling_locations == other.sibling_locations \
                   and self.properties == other.properties and self.analysis_timestamp == other.analysis_timestamp \
                   and self.type_id == other.type_id

    def get_finding_link(self, client: TeamscaleClient):
        return client.url + "/findings.html#details/" + client.project + "/?id=" + self.finding_id

    @classmethod
    def from_json(cls, json):
        sibling_locations = []
        for loc in json["siblingLocations"]:
            sibling_locations.append(TextRegionLocation.from_json(loc))
        death_commit = None
        if 'death' in json:
            death_commit = Commit.from_json(json['death'])
        return CloneFinding(json["groupName"], json["categoryName"], json["message"],
                            TextRegionLocation.from_json(json["location"]), json["id"],
                            Commit.from_json(json["birth"]),
                            death_commit, json["assessment"], sibling_locations,
                            CloneProperties.from_json(json["properties"]), json["analysisTimestamp"],
                            json["typeId"])


class CloneFindingChurn:
    def __init__(self, commit: Commit, added_findings: [CloneFinding], findings_added_in_branch: [CloneFinding],
                 findings_in_changed_code: [CloneFinding], removed_findings: [CloneFinding],
                 findings_removed_in_branch: [CloneFinding]):
        self.commit = commit
        self.added_findings = added_findings
        self.findings_added_in_branch = findings_added_in_branch
        self.findings_in_changed_code = findings_in_changed_code
        self.removed_findings = removed_findings
        self.findings_removed_in_branch = findings_removed_in_branch

    def __str__(self):
        to_return = "Clone Finding Churn for commit: " + str(self.commit.timestamp) + "\n"
        if self.added_findings:
            to_return += "added findings = "
            to_return += ',\n'.join(map(str, self.added_findings))
        if self.findings_added_in_branch:
            to_return += "findings added in branch = "
            to_return += ', '.join(map(str, self.findings_added_in_branch))
        if self.findings_in_changed_code:
            to_return += "findings in changed code = "
            to_return += ',\n'.join(map(str, self.findings_in_changed_code))
        if self.removed_findings:
            to_return += "removed findings = "
            to_return += ',\n'.join(map(str, self.removed_findings))
        if self.findings_removed_in_branch:
            to_return += "findings removed in branch = "
            to_return += ',\n'.join(map(str, self.findings_removed_in_branch))
        if self.is_empty():
            to_return = to_return[:-1] + " NO  CHURN"
        return to_return

    def __eq__(self, other):
        if not isinstance(other, CloneFindingChurn):
            return NotImplemented
        elif self is other:
            return True
        else:
            other: CloneFindingChurn
            return self.commit == other.commit and self.added_findings == other.added_findings \
                   and self.findings_added_in_branch == other.findings_added_in_branch \
                   and self.findings_in_changed_code == other.findings_in_changed_code \
                   and self.removed_findings == other.removed_findings \
                   and self.findings_removed_in_branch == other.findings_removed_in_branch

    def get_finding_links(self, client: TeamscaleClient) -> [str]:
        """returns a list of weblinks to the findings"""
        joined = self.added_findings + self.findings_added_in_branch + self.findings_in_changed_code + \
                 self.removed_findings + \
                 self.findings_removed_in_branch
        links: [str] = []
        for clone_finding in joined:
            clone_finding: CloneFinding
            links.append(clone_finding.get_finding_link(client))
        return links

    def is_relevant(self):
        return self.added_findings or self.findings_added_in_branch or self.findings_in_changed_code

    def is_empty(self):
        return not (self.added_findings or self.findings_added_in_branch or self.findings_in_changed_code
                    or self.removed_findings or self.findings_removed_in_branch)

    @classmethod
    def from_json(cls, json):
        # filters for findings in category 'Code Duplication'
        added_findings: [CloneFinding] = []
        for finding in json["addedFindings"]:
            if finding["categoryName"] == 'Code Duplication':
                added_findings.append(CloneFinding.from_json(finding))
        findings_added_in_branch: [CloneFinding] = []
        for finding in json["findingsAddedInBranch"]:
            if finding["categoryName"] == 'Code Duplication':
                findings_added_in_branch.append(CloneFinding.from_json(finding))
        findings_in_changed_code: [CloneFinding] = []
        for finding in json['findingsInChangedCode']:
            if finding["categoryName"] == 'Code Duplication':
                findings_in_changed_code.append(CloneFinding.from_json(finding))
        removed_findings: [CloneFinding] = []
        for finding in json['removedFindings']:
            if finding["categoryName"] == 'Code Duplication':
                removed_findings.append(CloneFinding.from_json(finding))
        findings_removed_in_branch: [CloneFinding] = []
        for finding in json['findingsRemovedInBranch']:
            if finding["categoryName"] == 'Code Duplication':
                findings_removed_in_branch.append(CloneFinding.from_json(finding))
        return CloneFindingChurn(Commit.from_json(json["commit"]), added_findings, findings_added_in_branch,
                                 findings_in_changed_code, removed_findings, findings_removed_in_branch)
