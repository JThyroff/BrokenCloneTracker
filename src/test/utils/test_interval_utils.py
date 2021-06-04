import unittest

import portion
from portion import Interval

from src.main.utils.interval_utils import overlaps_more_than_threshold


class MyTestCase(unittest.TestCase):
    def test_overlaps_more_than_threshold(self):
        interval: Interval = portion.closed(2, 11)
        other: Interval = portion.closed(0, 7)

        result = overlaps_more_than_threshold(interval, other, 0.9)
        self.assertEqual(result, False)
        result = overlaps_more_than_threshold(interval, other, 0.8)
        self.assertEqual(result, False)
        result = overlaps_more_than_threshold(interval, other, 0.7)
        self.assertEqual(result, True)
        result = overlaps_more_than_threshold(interval, other, 0.6)
        self.assertEqual(result, True)


if __name__ == '__main__':
    unittest.main()
