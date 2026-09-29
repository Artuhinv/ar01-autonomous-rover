import unittest

from wheel_screen import screen


class WheelScreenTests(unittest.TestCase):
    def test_90_mm_does_not_meet_design_factor_at_maximum_speed(self):
        result = screen(0.09)
        self.assertAlmostEqual(result["required_rpm"], 127.324, places=3)
        self.assertLess(result["design_margin"], 1.0)

    def test_100_mm_meets_analytical_screen(self):
        result = screen(0.10)
        self.assertAlmostEqual(result["required_rpm"], 114.592, places=3)
        self.assertGreater(result["design_margin"], 1.0)

    def test_invalid_diameter_rejected(self):
        with self.assertRaises(ValueError):
            screen(0)


if __name__ == "__main__":
    unittest.main()
