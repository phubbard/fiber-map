import unittest

from fibermap.permits.classify import classify, company_from_holder, is_drop, mentions_fiber, parse_job, watchlist_candidate


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

    def test_telecom_named_holder_is_kept_under_its_own_name(self):
        self.assertEqual(classify("ACME NETWORKS LLC", "Install conduit and handholes"), "Acme Networks")
        self.assertEqual(classify("San Diego Broadband", ""), "San Diego Broadband")
        self.assertEqual(company_from_holder("Smartlink Wireless, Inc."), "Smartlink Wireless")
        self.assertIsNone(company_from_holder("Mastec North America"))
        self.assertIsNone(classify("Mastec North America", "trench for conduit"))

    def test_holder_person_suffix_and_casing(self):
        self.assertEqual(company_from_holder("BOLDYN NETWORKS - Scott Lewis"), "Boldyn Networks")
        self.assertEqual(company_from_holder("HP COMMUNICATIONS INC"), "HP Communications")
        self.assertEqual(company_from_holder("HP Communications"), "HP Communications")

    def test_exclusion_is_about_the_holder_not_a_passing_mention(self):
        self.assertEqual(classify("AT&T California", "ATT FIBER (A05B699): bore under storm drain"), "AT&T")
        self.assertIsNone(classify("City of San Diego", "fiber conduit for traffic signals"))
        self.assertIsNone(classify("Some Contractor", "fiber to the new water meter vault"))

    def test_watchlist_candidate(self):
        self.assertTrue(watchlist_candidate("IKE Smart City") is False)
        self.assertFalse(watchlist_candidate("Clinton Boogaard"))
        self.assertFalse(watchlist_candidate("California American Water Company"))
        self.assertTrue(watchlist_candidate("Mastec North America"))
        self.assertTrue(watchlist_candidate("Ruto Vo Inc"))
        self.assertTrue(watchlist_candidate("Clinton Boogaard", telecomish=2))  # a PM whose jobs smell like telecom
        self.assertFalse(watchlist_candidate("Clinton Boogaard", telecomish=1))
        self.assertEqual(classify("", "INTREPID FIBER: Public Right of Way Permit"), "Intrepid Fiber")

    def test_known_overbuilders(self):
        self.assertEqual(classify("", "METRONET: Public Right of Way Permit"), "Metronet")
        self.assertEqual(classify("SiFi Networks Fullerton LLC", ""), "SiFi Networks")

    def test_ting_needs_word_boundary(self):
        self.assertIsNone(classify("", "street lighting conduit"))


if __name__ == "__main__":
    unittest.main()
