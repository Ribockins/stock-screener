"""Decision rule for mql4/RotorProtocol.mq4.

V is the mean of the components that exist. A missing volume is left out,
not replaced with zero. Entry is a cross of +/- level on a closed bar.
"""

import unittest


def clip(value):
    return max(-1.0, min(1.0, value))


def vector(structure, momentum, volume):
    parts = [clip(value) for value in (structure, momentum, volume) if value is not None]
    if not parts:
        return None
    return sum(parts) / len(parts)


def cross_signal(previous, current, level=0.5):
    if previous is None or current is None:
        return 0
    if previous <= level and current > level:
        return 1
    if previous >= -level and current < -level:
        return -1
    return 0


def pressure_gone(side, previous, current):
    if side == 1 and previous >= 0.0 and current < 0.0:
        return True
    if side == -1 and previous <= 0.0 and current > 0.0:
        return True
    return False


class RotorProtocolTest(unittest.TestCase):
    def test_missing_volume_is_not_a_zero_vote(self):
        self.assertEqual(vector(1.0, 1.0, None), 1.0)
        self.assertAlmostEqual(vector(1.0, 1.0, 0.0), 2.0 / 3.0)

    def test_each_component_is_clipped_before_the_average(self):
        self.assertEqual(vector(2.0, -3.0, None), -0.0)
        self.assertEqual(vector(2.0, -3.0, None), (1.0 + -1.0) / 2.0)

    def test_long_cross_fires_once(self):
        self.assertEqual(cross_signal(0.4, 0.6), 1)
        self.assertEqual(cross_signal(0.5, 0.51), 1)
        self.assertEqual(cross_signal(0.6, 0.9), 0)
        self.assertEqual(cross_signal(0.4, 0.5), 0)

    def test_short_cross_fires_once(self):
        self.assertEqual(cross_signal(-0.4, -0.6), -1)
        self.assertEqual(cross_signal(-0.5, -0.51), -1)
        self.assertEqual(cross_signal(-0.6, -0.9), 0)

    def test_zero_cross_is_an_exit_and_not_an_entry(self):
        self.assertEqual(cross_signal(0.2, -0.2), 0)
        self.assertTrue(pressure_gone(1, 0.2, -0.2))
        self.assertTrue(pressure_gone(-1, -0.2, 0.2))
        self.assertFalse(pressure_gone(1, -0.1, -0.2))

    def test_source_has_one_entry_and_no_second_engine(self):
        with open("mql4/RotorProtocol.mq4", encoding="utf-8") as handle:
            source = handle.read()
        for call in ("iRSI", "iMACD", "iADX", "iStochastic", "iBands", "iCCI"):
            self.assertNotIn(call, source)
        self.assertIn("iMFI", source)
        self.assertIn("iMA", source)
        self.assertEqual(source.count("OrderSend"), 1)


if __name__ == "__main__":
    unittest.main()
