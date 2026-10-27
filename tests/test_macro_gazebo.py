"""Pure description/freshness checks; installed simulator assets stay untouched."""
import unittest
from rosa_reliability.gazebo_demo import home_description, require_home, MARKER
from rosa_reliability.ros_arm import HOME_POSE


class MacroGazeboTests(unittest.TestCase):
    def test_description_only_adds_explicit_initial_positions(self):
        source = '<xacro:ur_robot ' + MARKER + '/>'
        expected = '${dict(' + ','.join(k + '=' + repr(v) for k, v in HOME_POSE.items()) + ')}'
        self.assertEqual(home_description(source), source.replace(MARKER,
            MARKER + '\n    initial_positions="' + expected + '"'))

    def test_unknown_or_duplicated_template_is_rejected(self):
        for source in ('unknown', MARKER + MARKER):
            with self.assertRaises(RuntimeError): home_description(source)

    def test_home_requires_finite_complete_observations(self):
        require_home(HOME_POSE)
        for value in (None, float('nan'), float('inf'), True, 1.0):
            with self.assertRaises(RuntimeError): require_home({**HOME_POSE, 'shoulder_pan_joint': value})
        with self.assertRaises(RuntimeError): require_home({})


if __name__ == '__main__': unittest.main()
