import unittest

from power_sizing import current_cases, required_nominal_wh


class PowerSizingTest(unittest.TestCase):
    def test_motor_envelope(self):
        cases = current_cases()
        self.assertEqual(cases["no_load"], 0.2)
        self.assertAlmostEqual(cases["working_estimate"], 0.568, places=2)
        self.assertAlmostEqual(cases["design_estimate"], 1.123, places=2)
        self.assertEqual(cases["stall_extrapolation"] * 2, 11.0)

    def test_nominal_energy_uses_real_system_average(self):
        self.assertAlmostEqual(required_nominal_wh(20.0, 1.0, 0.8, 0.2), 30.0)

    def test_invalid_inputs_rejected(self):
        for values in ((0, 1, 0.8, 0.2), (20, 0, 0.8, 0.2),
                       (20, 1, 0, 0.2), (20, 1, 1.1, 0.2),
                       (20, 1, 0.8, -0.1)):
            with self.subTest(values=values), self.assertRaises(ValueError):
                required_nominal_wh(*values)


if __name__ == "__main__":
    unittest.main()
