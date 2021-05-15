import unittest

from src.main.analysis import is_file_affected_at_commit
from src.main.data import FileChange


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
