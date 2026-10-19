import math
from pathlib import Path
import unittest
import xml.etree.ElementTree as ET

from layout_screen import (
    MassPoint, P0_POINTS, SUPPORT_M, centre_of_mass, screen, static_margin,
    stop_distance,
)


class LayoutScreenTest(unittest.TestCase):
    def test_p0_baseline(self):
        result = screen(P0_POINTS)
        self.assertEqual(result["mass_kg"], 3.0)
        self.assertAlmostEqual(result["cog_m"][0], -0.020916666666666667)
        self.assertAlmostEqual(result["cog_m"][2], 0.09625)
        self.assertAlmostEqual(result["worst_edge_margin_mm"], 7.571435332187043)

    def test_support_boundary_and_outside(self):
        for vertex in SUPPORT_M:
            self.assertAlmostEqual(static_margin(vertex), 0.0)
        self.assertGreater(static_margin((-0.040, 0.0)), 0)
        self.assertLess(static_margin((0.001, 0.0)), 0)
        self.assertFalse(screen((MassPoint("edge", 1, 0, 0, 0),))[
            "inside_under_assumptions"])

    def test_signed_loads_cannot_turn_static_failure_into_pass(self):
        high = P0_POINTS + (MassPoint("payload", 1, 0.070, 0, 0.250),)
        expected = screen(high, 0.5, 5)
        self.assertLess(expected["static_edge_margin_mm"], 0)
        for acceleration in (-0.5, 0.5):
            for slope in (-5, 5):
                with self.subTest(acceleration=acceleration, slope=slope):
                    actual = screen(high, acceleration, slope)
                    self.assertEqual(actual, expected)
                    self.assertFalse(actual["inside_under_assumptions"])

    def test_low_rear_payload_and_zero_height(self):
        low = P0_POINTS + (MassPoint("payload", 1, -0.070, 0, 0.045),)
        self.assertAlmostEqual(screen(low)["worst_edge_margin_mm"], 21.618744265240068)
        flat = screen((MassPoint("ground", 1, -0.040, 0, 0),), 2, 10)
        self.assertEqual(flat["worst_load_shift_mm"], 0)

    def test_travel_distance_is_symmetric_for_reverse(self):
        self.assertAlmostEqual(stop_distance(0.6, 0.2, 0.5), 0.48)
        self.assertAlmostEqual(stop_distance(-0.6, 0.2, 0.5), 0.48)
        self.assertAlmostEqual(stop_distance(-0.6, 0.5, 0.5), 0.66)
        self.assertEqual(stop_distance(0, 0.2, 0.5), 0)

    def test_invalid_loads_rejected(self):
        for acceleration, slope in ((math.nan, 5), (math.inf, 5),
                                    (0.5, math.nan), (0.5, 90), (0.5, -90)):
            with self.subTest(acceleration=acceleration, slope=slope):
                with self.assertRaises(ValueError):
                    screen(P0_POINTS, acceleration, slope)
        for parts in ((), (MassPoint("bad", 0, 0, 0, 0),),
                      (MassPoint("bad", -1, 0, 0, 0),),
                      (MassPoint("bad", 1, math.nan, 0, 0),),
                      (MassPoint("bad", 1, 0, 0, -0.1),)):
            with self.subTest(parts=parts), self.assertRaises(ValueError):
                centre_of_mass(parts)

    def test_invalid_braking_rejected(self):
        for values in ((0.6, -0.2, 0.5), (0.6, 0.2, 0),
                       (0.6, 0.2, -0.5), (math.nan, 0.2, 0.5),
                       (0.6, math.inf, 0.5), (0.6, 0.2, math.nan)):
            with self.subTest(values=values), self.assertRaises(ValueError):
                stop_distance(*values)

    def test_snapshot_matches_actual_xacro(self):
        """Fail when P0 masses, frames or contact geometry drift from the screen."""
        root = Path(__file__).resolve().parents[2] / "src/ar01_description/urdf"
        ns = "{http://www.ros.org/wiki/xacro}"
        base = ET.parse(root / "ar01_base.xacro").getroot().find(ns + "macro")
        sensors = ET.parse(root / "ar01_sensors.xacro").getroot().find(ns + "macro")
        properties = {node.get("name"): node.get("value")
                      for macro in (base, sensors)
                      for node in macro.findall(ns + "property")}

        def xyz(node):
            origin = node.find("origin")
            self.assertEqual([float(v) for v in origin.get("rpy", "0 0 0").split()],
                             [0, 0, 0])
            return tuple(float(v) for v in origin.get("xyz").split())

        anchor = xyz(base.find("joint[@name='base_footprint_joint']"))
        self.assertEqual(anchor[:2], (0, 0))
        body = xyz(base.find("link[@name='base_link']/inertial"))
        wheel_macro = base.find(ns + "macro[@name='wheel']")
        self.assertEqual(properties["wheel_track"],
                         "${body_width + wheel_width + 2.0 * wheel_clearance}")
        wheel_origin = wheel_macro.find("joint/origin").get("xyz").split()
        self.assertEqual(wheel_origin[1], "${y}")
        self.assertEqual(wheel_macro.find("joint/origin").get("rpy"), "0 0 0")
        for joint in (base.find("joint[@name='caster_joint']"),
                      wheel_macro.find("joint"),
                      sensors.find("joint[@name='lidar_joint']"),
                      sensors.find("joint[@name='imu_joint']")):
            self.assertEqual(joint.find("parent").get("link"), "base_link")
        self.assertEqual(base.find("joint[@name='base_footprint_joint']/parent")
                         .get("link"), "base_footprint")
        for link, property_name in (
            (base.find("link[@name='base_link']"), "body_mass"),
            (wheel_macro.find("link"), "wheel_mass"),
            (base.find("link[@name='caster_link']"), "caster_mass"),
            (sensors.find("link[@name='lidar_link']"), "lidar_mass"),
            (sensors.find("link[@name='imu_link']"), "imu_mass"),
        ):
            self.assertEqual(link.find("inertial/mass").get("value"),
                             "${" + property_name + "}")
            if property_name != "body_mass":
                self.assertEqual(xyz(link.find("inertial")), (0, 0, 0))
        calls = base.findall(ns + "wheel")
        self.assertEqual([(n.get("side"), n.get("y")) for n in calls], [
            ("left", "${wheel_track / 2.0}"),
            ("right", "${-wheel_track / 2.0}"),
        ])
        track = (float(properties["body_width"]) + float(properties["wheel_width"])
                 + 2 * float(properties["wheel_clearance"]))
        wheel_x = float(wheel_origin[0])
        wheel_z = anchor[2] + float(wheel_origin[2])
        caster = xyz(base.find("joint[@name='caster_joint']"))
        lidar = xyz(sensors.find("joint[@name='lidar_joint']"))
        imu = xyz(sensors.find("joint[@name='imu_joint']"))
        coordinates = (
            tuple(a + b for a, b in zip(anchor, body)),
            (wheel_x, track / 2, wheel_z), (wheel_x, -track / 2, wheel_z),
            tuple(a + b for a, b in zip(anchor, caster)),
            tuple(a + b for a, b in zip(anchor, lidar)),
            tuple(a + b for a, b in zip(anchor, imu)),
        )
        mass_names = ("body_mass", "wheel_mass", "wheel_mass", "caster_mass",
                      "lidar_mass", "imu_mass")
        for point, mass_name, position in zip(P0_POINTS, mass_names, coordinates):
            self.assertEqual(point.mass_kg, float(properties[mass_name]))
            for actual, expected in zip((point.x_m, point.y_m, point.z_m), position):
                self.assertAlmostEqual(actual, expected)
        self.assertAlmostEqual(wheel_z, float(properties["wheel_radius"]))
        self.assertAlmostEqual(coordinates[3][2], float(properties["caster_radius"]))
        self.assertEqual(SUPPORT_M, tuple((p.x_m, p.y_m) for p in P0_POINTS[1:4]))


if __name__ == "__main__":
    unittest.main()
