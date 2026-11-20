import tempfile
import unittest
from pathlib import Path

import search


class SearchTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / "grammar.txt"
        self.path.write_text(
            "현재 시제는 반복되는 습관을 나타냅니다.\n"
            "미래 시제는 앞으로 일어날 일을 나타냅니다.\n"
            "현재 완료는 과거부터 지금까지 이어지는 일을 나타냅니다.\n",
            encoding="utf-8",
        )
        self.index = search.prepare_index(self.path)

    def tearDown(self):
        self.temp.cleanup()

    def test_korean_meaning_search(self):
        results = search.search("반복하는 습관", self.index)
        self.assertIn("현재 시제", results[0][1])
        self.assertGreater(results[0][0], results[1][0])

    def test_result_count_and_bounds(self):
        results = search.search("앞으로 일어날 일", self.index, top_k=2)
        self.assertEqual(2, len(results))
        self.assertTrue(all(0 <= score <= 1 for score, _ in results))


if __name__ == "__main__":
    unittest.main()
