import unittest
from datetime import date

from scout.ideas import idea_for, uncle_says
from scout.rules import eligibility, evaluate
from scout.sources import Event, parse_money, parse_period_end

TODAY = date(2026, 11, 25)


def ev(**kw):
    base = dict(id="devpost:1", title="Build an App", url="https://x.devpost.com/", source="Devpost",
                prize_usd=10000, cash_prizes=1, registrations=800, themes=["Mobile"],
                deadline=date(2026, 12, 15), rules_text="Open to participants worldwide.")
    base.update(kw)
    return Event(**base)


class Parsing(unittest.TestCase):
    def test_period_end(self):
        self.assertEqual(parse_period_end("Oct 27 - Dec 22, 2026"), date(2026, 12, 22))
        self.assertEqual(parse_period_end("Nov 20 - 23, 2026"), date(2026, 11, 23))
        self.assertEqual(parse_period_end("Nov 01, 2026 - Jan 12, 2027"), date(2027, 1, 12))

    def test_money(self):
        self.assertEqual(parse_money("$<span data-currency-value>120,000</span>"), 120000)


class Eligibility(unittest.TestCase):
    def test_australia_excluded(self):
        self.assertEqual(eligibility("Residents of Australia, Quebec and Cuba are not eligible.")[0], "no")

    def test_us_only(self):
        self.assertEqual(eligibility("The hackathon is open only to legal residents of the United States.")[0], "no")

    def test_worldwide(self):
        self.assertEqual(eligibility("Open to individuals in all countries except Cuba.")[0], "ok")

    def test_no_solo(self):
        self.assertEqual(eligibility("Teams must have at least 2 members.")[0], "no")


class Filter(unittest.TestCase):
    def test_keeps_app_hackathon(self):
        v = evaluate(ev(), TODAY)
        self.assertTrue(v.keep)
        self.assertGreaterEqual(v.score, 65)

    def test_skips_crypto(self):
        v = evaluate(ev(title="Solana DeFi Sprint"), TODAY)
        self.assertFalse(v.keep)
        self.assertIn("crypto", v.headline_reason)
        self.assertIn("bus", uncle_says(v))

    def test_skips_no_cash(self):
        self.assertFalse(evaluate(ev(cash_prizes=0), TODAY).keep)

    def test_skips_closing_tomorrow(self):
        self.assertFalse(evaluate(ev(deadline=date(2026, 11, 26)), TODAY).keep)

    def test_idea_matches_theme(self):
        v = evaluate(ev(title="Daily Game Jam", themes=["Gaming"]), TODAY)
        self.assertIn("Word Duel", idea_for(v))


if __name__ == "__main__":
    unittest.main()
