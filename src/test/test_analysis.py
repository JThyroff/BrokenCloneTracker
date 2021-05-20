import unittest

from src.main.analysis import is_file_affected_at_commit, are_left_lines_affected_at_diff
from src.main.data import FileChange, DiffDescription


def build_test_list() -> [FileChange]:
    file_change_json_1 = {
        "changeType": "EDIT",
        "commit": {
            "branchName": "master",
            "timestamp": 1534709210000,
            "type": "simple"
        },
        "uniformPath": "src/main/java/org/jabref/gui/util/ThemeLoader.java"
    }
    file_change_json_2 = {
        "changeType": "EDIT",
        "commit": {
            "branchName": "master",
            "timestamp": 1534709210000,
            "type": "simple"
        },
        "uniformPath": "src/main/java/org/jabref/logic/formatter/bibtexfields/CleanupURLFormatter.java"
    }

    return [FileChange.from_json(file_change_json_1), FileChange.from_json(file_change_json_2)]


class TestAnalysis(unittest.TestCase):
    def test_is_file_affected_at_commit(self):
        tl = build_test_list()
        self.assertEqual(True, is_file_affected_at_commit("src/main/java/org/jabref/gui/util/ThemeLoader.java", tl))
        self.assertEqual(False, is_file_affected_at_commit("src/main/java/org/ThisFileIsNot.java", tl))

    def test_are_left_lines_affected_at_diff(self):
        diff_desc_json = {
            "leftChangeLines": [
                23,
                25,  #
                29,
                31,  #
                99,
                100,  #
                108,
                109,  #
                130,
                131,  #
                172,
                174  #
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
        diff_desc: DiffDescription = DiffDescription.from_json(diff_desc_json)
        """Standard easy cases"""
        self.assertEqual(True, are_left_lines_affected_at_diff(93, 105, diff_desc))
        self.assertEqual(False, are_left_lines_affected_at_diff(101, 105, diff_desc))
        self.assertEqual(False, are_left_lines_affected_at_diff(132, 171, diff_desc))
        """Complicated ones - Note that the intervals above in diff_desc are given in the following way: Quote the 
        docs: 'Line changes for the left lines. The integers are organized in pairs, giving the start (inclusive) and 
        end (exclusive) lines of a region.' Thus portion.closedOpen Intervals are used. For example: [23,25)
        Thus [23,25) and [25,28) should not intersect."""
        self.assertEqual(False, are_left_lines_affected_at_diff(25, 28, diff_desc))
        self.assertEqual(False, are_left_lines_affected_at_diff(109, 130, diff_desc))
