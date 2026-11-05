import unittest
from datetime import date

from fibermap.build import summarize
from fibermap.permits.base import Permit


def permit(pid, company, created, fiber=True, kind="row", status="Issued"):
    from fibermap.permits.base import phase_for
    return Permit(id=pid, source="t", kind=kind, company=company, fiber=fiber, status=status, phase=phase_for(status),
                  created=created, issued=None, closed=None, address="", lat=None, lng=None, scope="", holder="")


class SummarizeTests(unittest.TestCase):
    def test_counts(self):
        today = date(2026, 11, 5)
        items = [
            permit("1", "AT&T", "2026-10-01"),
            permit("2", "AT&T", "2026-01-15", kind="traffic", fiber=False),
            permit("3", "AT&T", "2025-06-01"),            # prior 12 months
            permit("4", "Cox", "2024-03-01", status="Closed"),
            permit("5", "Wyyerd", "2026-11-01", status="Opened"),
        ]
        s = summarize(items, today)
        self.assertEqual(s["total"], 5)
        self.assertEqual(s["active"], 4)
        self.assertEqual(s["fiber_active"], 3)
        self.assertEqual(s["by_year"]["2026"]["AT&T"]["total"], 2)
        self.assertEqual(s["by_year"]["2026"]["AT&T"]["fiber"], 1)
        self.assertEqual(s["by_year"]["2026"]["AT&T"]["traffic"], 1)
        self.assertEqual(s["trailing12"]["AT&T"]["fiber"], 1)
        self.assertEqual(s["prior12"]["AT&T"]["fiber"], 1)
        self.assertNotIn("Cox", s["trailing12"])
        self.assertEqual(s["trailing12"]["Wyyerd"]["fiber"], 1)


if __name__ == "__main__":
    unittest.main()
