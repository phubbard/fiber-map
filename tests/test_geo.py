import math
import unittest

from fibermap import geo


class GeoTests(unittest.TestCase):
    def test_bbox_is_symmetric_and_square_in_km(self):
        lat, lng = 32.857, -117.205
        s, w, n, e = geo.bbox_from_center(lat, lng, 2.5)
        self.assertAlmostEqual((n - s) / 2 * geo.KM_PER_DEG_LAT, 2.5, places=3)
        self.assertAlmostEqual((e - w) / 2 * geo.KM_PER_DEG_LAT * math.cos(math.radians(lat)), 2.5, places=3)
        self.assertTrue(geo.in_bbox(lat, lng, [s, w, n, e]))
        self.assertFalse(geo.in_bbox(lat + 1, lng, [s, w, n, e]))

    def test_tile_xy_known_points(self):
        self.assertEqual(geo.tile_xy(0, 0, 0), (0, 0))
        self.assertEqual(geo.tile_xy(32.857, -117.205, 1), (0, 0))   # west, north hemisphere
        self.assertEqual(geo.tile_xy(-33.0, 151.0, 1), (1, 1))      # east, south
        self.assertEqual(geo.tile_xy(0, 0, 1), (1, 1))
        self.assertEqual(geo.tile_xy(85.0, 179.9, 3), (7, 0))
        x, y = geo.tile_xy(32.857, -117.205, 15)
        self.assertEqual(x, 5715)
        self.assertTrue(13200 < y < 13230)

    def test_tiles_for_bbox_covers_corners(self):
        bbox = geo.bbox_from_center(32.857, -117.205, 2.5)
        tiles = geo.tiles_for_bbox(bbox, 14, margin=0)
        s, w, n, e = bbox
        for lat, lng in ((s, w), (n, e), (s, e), (n, w)):
            x, y = geo.tile_xy(lat, lng, 14)
            self.assertIn((14, x, y), tiles)
        self.assertLess(len(tiles), 60)


if __name__ == "__main__":
    unittest.main()
