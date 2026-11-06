import json
import os
import tempfile
import unittest

from fibermap import config


def write(tmp, obj):
    path = os.path.join(tmp, "config.json")
    with open(path, "w") as f:
        json.dump(obj, f)
    return path


class ConfigTests(unittest.TestCase):
    def test_single_zip_layout_becomes_one_area(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg = config.load(write(tmp, {"zip": "92122", "label": "UC", "radius_km": 2.5, "zoom_offset": 2}))
        self.assertEqual(len(cfg["areas"]), 1)
        a = cfg["areas"][0]
        self.assertEqual((a["key"], a["zip"], a["label"], a["radius_km"], a["zoom_offset"]), ("92122", "92122", "UC", 2.5, 2))
        self.assertEqual(a["news"]["queries"], [])

    def test_areas_list_inherits_defaults(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg = config.load(write(tmp, {
                "zoom_offset": 1,
                "areas": [{"zip": 92126}, {"zip": "92129", "zoom_offset": 0, "news": {"queries": [{"label": "L", "q": "x"}]}},
                          {"label": "Downtown core", "bbox": [32.70, -117.17, 32.72, -117.15]}],
            }))
        keys = [a["key"] for a in cfg["areas"]]
        self.assertEqual(keys, ["92126", "92129", "downtown-core"])
        self.assertEqual(cfg["areas"][0]["zoom_offset"], 1)
        self.assertEqual(cfg["areas"][1]["zoom_offset"], 0)
        self.assertEqual(cfg["areas"][1]["news"]["queries"][0]["label"], "L")

    def test_rejects_area_without_location_or_duplicates(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                config.load(write(tmp, {"areas": [{"label": "nowhere"}]}))
            with self.assertRaises(ValueError):
                config.load(write(tmp, {"areas": [{"zip": "92122"}, {"zip": "92122"}]}))

    def test_resolve_area_from_bbox(self):
        area = config.resolve_area({"key": "x", "bbox": [32.70, -117.17, 32.72, -117.15]}, "/nonexistent")
        self.assertEqual(area["center"], [32.71, -117.16])
        self.assertEqual(area["label"], "Selected area")
        self.assertGreater(area["radius_km"], 1.0)


if __name__ == "__main__":
    unittest.main()
