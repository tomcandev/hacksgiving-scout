import unittest
from datetime import date
from unittest import mock

from scout import programs

TODAY = date(2026, 11, 25)


class Programs(unittest.TestCase):
    def test_seed_loads_and_blocks(self):
        progs = {p.name: p for p in programs.load(TODAY)}
        self.assertIn("GSV Cup 50 2027", progs)
        self.assertEqual(progs["GSV Cup 50 2027"].blockers, [])
        self.assertTrue(any("company" in b for b in progs["NVIDIA Inception"].blockers))

    def test_dates_in_page(self):
        text = "Nominations close 27 Nov 2026. Results January 4, 2027. Founded 12 May 1999."
        self.assertEqual(programs._dates_in(text, TODAY), ["2026-11-27", "2027-01-04"])

    def test_change_detection(self):
        def fake_get(url):
            return "<p>Applications are now open. Deadline 12 December 2026.</p>"
        with mock.patch.object(programs, "http_get", fake_get):
            seen = {}
            first = programs.scan(TODAY, seen)
            self.assertTrue(all(p.change == "new" for p in first))
            programs.remember(first, seen)
            again = programs.scan(TODAY, seen)
            self.assertTrue(all(p.change == "" for p in again))
        with mock.patch.object(programs, "http_get", lambda u: "Applications closed. 12 December 2026"):
            third = programs.scan(TODAY, seen)
            self.assertTrue(all(p.change == "closed" for p in third))

    def test_section_renders(self):
        progs = programs.load(TODAY)
        lines = "\n".join(programs.render_section(progs, TODAY, first_run=True))
        self.assertIn("GSV Cup 50 2027", lines)
        self.assertIn("Always open", lines)


if __name__ == "__main__":
    unittest.main()
