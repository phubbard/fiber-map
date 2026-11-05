import unittest

from fibermap.permits.classify import classify, is_drop, mentions_fiber, parse_job


class ClassifyTests(unittest.TestCase):
    def test_att_fiber_job(self):
        scope = "AT&T FIBER (A05EE9V): Public Right of Way Permit - Construction plans"
        self.assertEqual(classify("AT&T California", scope), "AT&T")
        self.assertTrue(mentions_fiber(scope))
        self.assertEqual(parse_job(scope), "A05EE9V")

    def test_job_with_prefix_and_spaces(self):
        self.assertEqual(parse_job("AT&T Fiber (JOB 38416625): work"), "38416625")

    def test_holder_only(self):
        self.assertEqual(classify("Cox Communications", ""), "Cox")
        self.assertEqual(classify("MCI Metro/Verizon", ""), "Verizon")
        self.assertEqual(classify("Charter Communications", ""), "Spectrum")

    def test_scope_names_company_when_holder_is_a_person(self):
        self.assertEqual(classify("John Pullman", "ZAYO: Public Right of Way Permit"), "Zayo")
        self.assertEqual(classify("", "Wyyerd Fiber: Public Right of Way Permit"), "Wyyerd")

    def test_non_telecom_is_none(self):
        self.assertIsNone(classify("Yan Fu Lin", "CLAIREMONT MESA: new 1 inch water meter"))
        self.assertIsNone(classify("SDG&E", "SDG&E fiber for substation SCADA"))

    def test_unknown_fiber_company_falls_back(self):
        self.assertEqual(classify("Some Contractor LLC", "Install fiber optic conduit"), "Fiber (other)")

    def test_extra_rules_win(self):
        extra = [{"name": "Localnet", "pattern": r"localnet"}]
        self.assertEqual(classify("LocalNet Fiber Co", "fiber", extra), "Localnet")

    def test_drop_detection(self):
        self.assertTrue(is_drop("PLACE 1-4\" DUCT FROM EXISTING AT&T SAI TO PROPERTY OWNER'S DEMARCATION POINT"))
        self.assertFalse(is_drop("Place 2,400 ft of 2-inch conduit and 3 handholes along Governor Dr"))

    def test_ting_needs_word_boundary(self):
        self.assertIsNone(classify("", "street lighting conduit"))


if __name__ == "__main__":
    unittest.main()
