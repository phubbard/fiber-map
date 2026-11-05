import unittest

from fibermap.zcta import parse_gazetteer, suggested_radius_km

TEXT = "GEOID\tALAND\tAWATER\tALAND_SQMI\tAWATER_SQMI\tINTPTLAT\tINTPTLONG   \n" \
       "92121\t20000000\t0\t7.7\t0\t32.90\t-117.20   \n" \
       "92122\t11000000\t0\t4.2\t0\t32.857\t-117.205   \n"


class ZctaTests(unittest.TestCase):
    def test_parse(self):
        row = parse_gazetteer(TEXT, "92122")
        self.assertEqual((row["lat"], row["lng"]), (32.857, -117.205))
        self.assertEqual(row["land_km2"], 11.0)
        self.assertEqual(row["radius_km"], suggested_radius_km(11.0))
        self.assertIsNone(parse_gazetteer(TEXT, "00000"))

    def test_radius(self):
        self.assertEqual(suggested_radius_km(0), 2.0)
        self.assertGreaterEqual(suggested_radius_km(0.5), 1.0)
        self.assertAlmostEqual(suggested_radius_km(11.0), 2.2, places=1)


if __name__ == "__main__":
    unittest.main()
