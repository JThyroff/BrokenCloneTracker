import unittest

from src.main.data import Commit, CommitAlert, CommitAlertContext, TextRegionLocation


class TestCommit(unittest.TestCase):
    def test_from_json(self):
        json = {
            "branchName": "main",
            "parentCommits": [
                {
                    "branchName": "main",
                    "timestamp": 1597694093000,
                    "type": "simple"
                }
            ],
            "timestamp": 1597731723000,
            "type": "parented"
        }
        commit: Commit = Commit.from_json(json)
        self.assertEqual(commit.branch, "main")
        parent_should: Commit = Commit(branch="main", timestamp=1597694093000, type="simple")
        parent_actual: Commit = Commit.from_json(commit.parent_commits[0])
        self.assertEqual(parent_should, parent_actual)
        self.assertEqual(commit.timestamp, 1597731723000)
        self.assertEqual(commit.type, "parented")
        pass


class TestTextRegionLocation(unittest.TestCase):
    def test_from_json(self):
        json = {
            "location": "src/main/java/org/jabref/logic/layout/format/HTMLChars.java",
            "rawEndLine": 77,
            "rawEndOffset": 3309,
            "rawStartLine": 26,
            "rawStartOffset": 1065,
            "type": "TextRegionLocation",
            "uniformPath": "src/main/java/org/jabref/logic/layout/format/HTMLChars.java"
        }
        text_region_location: TextRegionLocation = TextRegionLocation.from_json(json)
        self.assertEqual(text_region_location.location, "src/main/java/org/jabref/logic/layout/format/HTMLChars.java")
        self.assertEqual(text_region_location.raw_end_line, 77)
        self.assertEqual(text_region_location.raw_end_offset, 3309)
        self.assertEqual(text_region_location.raw_start_line, 26)
        self.assertEqual(text_region_location.raw_start_offset, 1065)
        self.assertEqual(text_region_location.type, 'TextRegionLocation')
        self.assertEqual(text_region_location.uniform_path,
                         "src/main/java/org/jabref/logic/layout/format/HTMLChars.java")
        pass


class TestCommitAlertContext(unittest.TestCase):
    def test_from_json(self):
        json = {
            "expectedCloneLocation": {
                "location": "src/main/java/org/jabref/logic/layout/format/HTMLChars.java",
                "rawEndLine": 77,
                "rawEndOffset": 3309,
                "rawStartLine": 26,
                "rawStartOffset": 1065,
                "type": "TextRegionLocation",
                "uniformPath": "src/main/java/org/jabref/logic/layout/format/HTMLChars.java"
            },
            "expectedSiblingLocation": {
                "location": "src/main/java/org/jabref/logic/openoffice/OOPreFormatter.java",
                "rawEndLine": 78,
                "rawEndOffset": 3347,
                "rawStartLine": 25,
                "rawStartOffset": 988,
                "type": "TextRegionLocation",
                "uniformPath": "src/main/java/org/jabref/logic/openoffice/OOPreFormatter.java"
            },
            "oldCloneLocation": {
                "location": "src/main/java/org/jabref/logic/layout/format/HTMLChars.java",
                "rawEndLine": 78,
                "rawEndOffset": 3343,
                "rawStartLine": 26,
                "rawStartOffset": 1065,
                "type": "TextRegionLocation",
                "uniformPath": "src/main/java/org/jabref/logic/layout/format/HTMLChars.java"
            },
            "removedCloneId": "72F239C5870DF14B3CFB6A5196DF7E97"
        }
        commit_alert_context: CommitAlertContext = CommitAlertContext.from_json(json)
        self.assertEqual(commit_alert_context.expected_clone_location, TextRegionLocation.from_json(
            json['expectedCloneLocation']))
        self.assertEqual(commit_alert_context.expected_sibling_location,
                         TextRegionLocation.from_json(json['expectedSiblingLocation']))
        self.assertEqual(commit_alert_context.old_clone_location,
                         TextRegionLocation.from_json(json['oldCloneLocation']))
        self.assertEqual(commit_alert_context.removed_clone_id, "72F239C5870DF14B3CFB6A5196DF7E97")


class TestCommitAlert(unittest.TestCase):
    def test_from_json(self):
        commit_alert_json = {
            "context": {
                "expectedCloneLocation": {
                    "location": "src/main/java/org/jabref/logic/layout/format/HTMLChars.java",
                    "rawEndLine": 77,
                    "rawEndOffset": 3309,
                    "rawStartLine": 26,
                    "rawStartOffset": 1065,
                    "type": "TextRegionLocation",
                    "uniformPath": "src/main/java/org/jabref/logic/layout/format/HTMLChars.java"
                },
                "expectedSiblingLocation": {
                    "location": "src/main/java/org/jabref/logic/openoffice/OOPreFormatter.java",
                    "rawEndLine": 78,
                    "rawEndOffset": 3347,
                    "rawStartLine": 25,
                    "rawStartOffset": 988,
                    "type": "TextRegionLocation",
                    "uniformPath": "src/main/java/org/jabref/logic/openoffice/OOPreFormatter.java"
                },
                "oldCloneLocation": {
                    "location": "src/main/java/org/jabref/logic/layout/format/HTMLChars.java",
                    "rawEndLine": 78,
                    "rawEndOffset": 3343,
                    "rawStartLine": 26,
                    "rawStartOffset": 1065,
                    "type": "TextRegionLocation",
                    "uniformPath": "src/main/java/org/jabref/logic/layout/format/HTMLChars.java"
                },
                "removedCloneId": "72F239C5870DF14B3CFB6A5196DF7E97"
            },
            "message": "Found potential inconsistent clone change in HTMLChars.java"
        }

        alert: CommitAlert = CommitAlert.from_json(commit_alert_json)
        self.assertEqual(alert.context, CommitAlertContext.from_json(commit_alert_json['context']))
        self.assertEqual(alert.message, "Found potential inconsistent clone change in HTMLChars.java")
        pass


if __name__ == '__main__':
    unittest.main()
