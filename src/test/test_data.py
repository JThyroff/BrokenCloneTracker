import unittest

from src.main.data import Commit


class TestCommit(unittest.TestCase):
    def test_from_json(self):
        json = {"branchName": "main",
                "parentCommits": [
                    {
                        "branchName": "main",
                        "timestamp": 1597694093000,
                        "type": "simple"
                    }
                ],
                "timestamp": 1597731723000,
                "type": "parented"}
        commit: Commit = Commit.from_json(json)
        self.assertEqual(commit.branch, "main")
        parent_should: Commit = Commit(branch="main", timestamp=1597694093000, type="simple")
        parent_actual: Commit = Commit.from_json(commit.parent_commits[0])
        self.assertEqual(parent_should, parent_actual)
        self.assertEqual(commit.timestamp, 1597731723000)
        self.assertEqual(commit.type, "parented")
        pass


if __name__ == '__main__':
    unittest.main()
