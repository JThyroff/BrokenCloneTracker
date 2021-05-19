import unittest

from src.main.data import Commit, CommitAlert, CommitAlertContext, TextRegionLocation, FileChange, DiffDescription


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


class TestFileChange(unittest.TestCase):
    def test_from_json(self):
        file_change_json = {
            "uniformPath": "src/main/java/org/jabref/logic/importer/WebFetchers.java",
            "changeType": "EDIT",
            "commit": {
                "type": "simple",
                "branchName": "master",
                "timestamp": 1608743869000
            }
        }

        file_change: FileChange = FileChange.from_json(file_change_json)
        self.assertEqual(file_change.uniform_path, "src/main/java/org/jabref/logic/importer/WebFetchers.java")
        self.assertEqual(file_change.change_type, "EDIT")
        self.assertEqual(file_change.commit, Commit.from_json(file_change_json['commit']))


class TestDiffDescription(unittest.TestCase):
    def test_from_json(self):
        diff_description_json = {
            "leftChangeLines": [
                23,
                25,
                29,
                31,
                99,
                100,
                108,
                109,
                130,
                131,
                172,
                174
            ],
            "leftChangeRegions": [
                975,
                989,
                990,
                1031,
                1302,
                1315,
                1316,
                1357,
                4238,
                4239,
                4256,
                4257,
                4280,
                4282,
                4730,
                4731,
                4747,
                4748,
                4771,
                4773,
                5800,
                5801,
                5817,
                5818,
                5841,
                5843,
                7504,
                7505,
                7521,
                7522,
                7545,
                7547,
                7569,
                7570,
                7587,
                7588,
                7611,
                7613
            ],
            "name": "token-based",
            "rightChangeLines": [
                23,
                24,
                28,
                29,
                97,
                98,
                106,
                107,
                128,
                129,
                170,
                172
            ],
            "rightChangeRegions": []
        }

        diff_description: DiffDescription = DiffDescription.from_json(diff_description_json)
        self.assertEqual(diff_description.name, "token-based")
        self.assertEqual(diff_description.left_change_lines, [
            23,
            25,
            29,
            31,
            99,
            100,
            108,
            109,
            130,
            131,
            172,
            174
        ])
        self.assertEqual(diff_description.left_change_regions, [
            975,
            989,
            990,
            1031,
            1302,
            1315,
            1316,
            1357,
            4238,
            4239,
            4256,
            4257,
            4280,
            4282,
            4730,
            4731,
            4747,
            4748,
            4771,
            4773,
            5800,
            5801,
            5817,
            5818,
            5841,
            5843,
            7504,
            7505,
            7521,
            7522,
            7545,
            7547,
            7569,
            7570,
            7587,
            7588,
            7611,
            7613
        ])
        self.assertEqual(diff_description.right_change_lines, [
            23,
            24,
            28,
            29,
            97,
            98,
            106,
            107,
            128,
            129,
            170,
            172
        ])
        self.assertEqual(diff_description.right_change_regions, [])


if __name__ == '__main__':
    unittest.main()
