import unittest
from datetime import date

from fibermap.build import compute_alerts, mark_section, summarize
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


class AlertTests(unittest.TestCase):
    NOW = "2026-11-05T12:00:00Z"

    def test_sections_prefer_the_item_own_date(self):
        state = {}
        mark_section(state, "permits", [("a", "2026-11-04"), ("b", "2024-01-01"), ("c", None)], self.NOW)
        self.assertEqual(state["permits"]["a"], "2026-11-04T00:00:00Z")
        self.assertEqual(state["permits"]["b"], "2024-01-01T00:00:00Z")
        self.assertEqual(state["permits"]["c"], self.NOW)
        mark_section(state, "permits", [("d", "2020-01-01"), ("a", "1999-01-01")], "2026-11-06T12:00:00Z")
        self.assertEqual(state["permits"]["d"], "2020-01-01T00:00:00Z")  # old permit surfaced by a rule change: still old
        self.assertEqual(state["permits"]["a"], "2026-11-04T00:00:00Z")  # first record wins

    def test_alerts(self):
        items = [
            permit("1", "AT&T", "2026-11-04"),                      # new fiber permit here, AT&T old
            permit("2", "AT&T", "2024-05-01"),
            permit("3", "Ezee Networks", "2026-11-03", fiber=False),  # company new here and city-wide
            permit("4", "Cox", "2026-11-04", kind="traffic", fiber=False),  # traffic: never an alert
        ]
        state = {
            "permits": {"1": "2026-11-04T00:00:00Z", "2": "2024-05-01T00:00:00Z", "3": "2026-11-03T00:00:00Z", "4": "2026-11-04T00:00:00Z"},
            "companies": {"AT&T": "2024-01-01T00:00:00Z", "Ezee Networks": "2026-11-03T00:00:00Z", "Cox": "2024-01-01T00:00:00Z",
                          "Wyyerd": "2026-11-01T00:00:00Z"},
        }
        alerts = compute_alerts(items, state, self.NOW, 7, "City of San Diego")
        kinds = sorted((a["kind"], a["company"]) for a in alerts)
        self.assertEqual(kinds, [("new_company", "Ezee Networks"), ("new_company", "Wyyerd"),
                                 ("new_fiber_permit", "AT&T"), ("new_permit", "Ezee Networks")])
        by_co = {a["company"]: a for a in alerts if a["kind"] == "new_company"}
        self.assertIn("and it is in this area", by_co["Ezee Networks"]["text"])
        self.assertIn("outside this area", by_co["Wyyerd"]["text"])
        self.assertEqual(alerts[0]["date"], "2026-11-04T00:00:00Z")  # newest first
