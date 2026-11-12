import sys
import unittest
from math import cos, sin, radians
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from visuals import direction_index, atlas_region


class DirectionTests(unittest.TestCase):
    def test_all_eight_aim_directions_and_angle_wrap(self):
        for index in range(8):
            for offset in (-20, 0, 20):
                angle = radians(index*45+offset)
                self.assertEqual(direction_index(cos(angle), sin(angle)), index)
        self.assertEqual(direction_index(0, 0), 0)

    def test_odd_size_atlas_regions_tile_without_gaps_or_overrun(self):
        width = height = 1254
        area = 0
        for index in range(16):
            x,y,w,h = atlas_region(index, width, height)
            self.assertTrue(0 <= x < x+w <= width)
            self.assertTrue(0 <= y < y+h <= height)
            area += w*h
        self.assertEqual(area, width*height)
        with self.assertRaises(ValueError):
            atlas_region(16, width, height)
