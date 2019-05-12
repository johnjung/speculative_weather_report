import datetime
import unittest
from speculative_weather_report import Weather


class TestWeather(unittest.TestCase):
    def test_get_previous_hour_timestring(self):
        w = Weather('2019-05-01T20:00:00')
        self.assertEqual(
            w.get_previous_hour_timestring(),
            '2019-05-01T19:00:00'
        )


if __name__ == '__main__':
    unittest.main()
