"""Checks that the validator accepts the sample night and rejects broken data.

Run: python -m unittest discover -s tests
"""
import copy
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from validate import validate  # noqa: E402

SAMPLE = json.loads((ROOT / "data" / "2026-10-08.json").read_text(encoding="utf-8"))


def broken(mutate):
    data = copy.deepcopy(SAMPLE)
    mutate(data)
    return validate(data, "test")


class ValidateTests(unittest.TestCase):
    def test_sample_night_is_valid(self):
        self.assertEqual(validate(SAMPLE, "sample"), [])

    def test_quarters_must_sum_to_score(self):
        def m(d): d["games"][0]["away"]["q"][0] += 1
        self.assertTrue(any("sums to" in p for p in broken(m)))

    def test_box_points_must_match_score(self):
        def m(d):
            row = d["games"][0]["box"]["away"][0]
            row[-1] += 2; row[4] += 1; row[5] += 1  # pts, fgm, fga
        self.assertTrue(any("points sum to" in p for p in broken(m)))

    def test_player_line_must_add_up(self):
        def m(d): d["games"][0]["box"]["home"][0][-1] += 1
        self.assertTrue(any("2*FGM" in p for p in broken(m)))

    def test_flow_must_be_in_order(self):
        def m(d):
            f = d["games"][0]["flow"]
            f[3], f[4] = f[4], f[3]
        self.assertTrue(any("flow" in p for p in broken(m)))

    def test_flow_must_end_at_final(self):
        def m(d): d["games"][0]["flow"].pop()
        self.assertTrue(any("flow ends at" in p for p in broken(m)))

    def test_partial_game_needs_note(self):
        def m(d):
            g = next(g for g in d["games"] if "flowThrough" in g)
            del g["partial"]
        self.assertTrue(any("partial" in p for p in broken(m)))

    def test_sources_must_be_nba(self):
        def m(d): d["games"][0]["sources"].append("https://www.espn.com/nba/")
        self.assertTrue(any("NBA-owned" in p for p in broken(m)))

    def test_script_tag_in_text_is_rejected(self):
        def m(d): d["summary"] += "</script>"
        self.assertTrue(any("</script" in p for p in broken(m)))

    def test_bad_bbref_id_is_rejected(self):
        def m(d): d["games"][0]["box"]["away"][0][2] = "Luka Garza"
        self.assertTrue(any("bbref" in p for p in broken(m)))


if __name__ == "__main__":
    unittest.main()
