import csv
import io
import unittest

from fibermap.permits import sandiego

HEADER = ["APPROVAL_ID", "APPROVAL_TYPE", "APPROVAL_STATUS", "APPROVAL_PERMIT_HOLDER", "PROJECT_TITLE",
          "PROJECT_SCOPE", "APPROVAL_SCOPE", "APPROVAL_CREATE_DATE", "APPROVAL_ISSUE_DATE", "APPROVAL_CLOSE_DATE",
          "GIS_ADDRESS", "GIS_LATITUDE", "GIS_LONGITUDE"]
ROWS = [
    ["1", "Approval - Construction - Right Of Way Pmt-Const Plan", "Issued", "AT&T California", "",
     "AT&T FIBER (A05EE9V): Public Right of Way Permit", "", "2026-05-15 00:00:00", "2026-05-15", "",
     "3898 1/3 Conrad Av, San Diego, CA", "32.84", "-117.21"],
    ["2", "Traffic Control Permit", "Issued", "Cox Communications", "", "", "", "2026-07-15", "2026-07-15", "",
     "4275 Executive Sq, San Diego, CA", "32.87", "-117.20"],
    ["3", "Plumbing Pmt", "Issued", "AT&T California", "", "water heater", "", "2026-01-01", "", "", "x", "32.8", "-117.2"],
    ["4", "Approval - Construction - Right Of Way Pmt", "Opened", "", "", "Wyyerd Fiber: Public Right of Way Permit", "",
     "2026-10-12", "", "", "", "", ""],
    ["5", "Approval - Construction - Right Of Way Pmt", "Closed", "Yan Fu Lin", "", "new 1 inch water meter", "",
     "2026-08-21", "2026-08-21", "2026-09-01", "5073 Amnest St", "32.85", "-117.19"],
]


def rows():
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(HEADER)
    w.writerows(ROWS)
    buf.seek(0)
    return csv.DictReader(buf)


class SanDiegoParseTests(unittest.TestCase):
    def test_parse(self):
        permits = {p.id: p for p in sandiego.parse_rows(rows())}
        self.assertEqual(set(permits), {"1", "2", "4"})
        att = permits["1"]
        self.assertEqual((att.kind, att.company, att.fiber, att.phase), ("row", "AT&T", True, "active"))
        self.assertEqual(att.created, "2026-05-15")
        self.assertEqual(att.job, "A05EE9V")
        self.assertEqual((att.lat, att.lng), (32.84, -117.21))
        cox = permits["2"]
        self.assertEqual((cox.kind, cox.company, cox.fiber), ("traffic", "Cox", False))
        wy = permits["4"]
        self.assertEqual((wy.phase, wy.lat, wy.lng), ("planned", None, None))

    def test_unmatched_holders_are_collected(self):
        unmatched = {}
        list(sandiego.parse_rows(rows(), None, unmatched))
        self.assertEqual(set(unmatched), {"Yan Fu Lin"})
        self.assertEqual(unmatched["Yan Fu Lin"]["count"], 1)
        self.assertEqual(unmatched["Yan Fu Lin"]["first_created"], "2026-08-21")

    def test_kind_for(self):
        self.assertEqual(sandiego.kind_for("Approval - Construction - Grading-Right of Way Pmt"), "row")
        self.assertEqual(sandiego.kind_for("Encroachment Agreement"), "encroachment")
        self.assertIsNone(sandiego.kind_for("Building Permit"))


if __name__ == "__main__":
    unittest.main()
