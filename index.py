#!/usr/bin/env python
"""Usage:
    index.py add
    index.py historical_headers
    index.py get_historical <field> [<yyyymmdd>]
    index.py weather [<YYYY-mm-ddTHH:MM:SS>]
"""

import csv
import datetime
import math
import sqlite3
import sys
from docopt import docopt

class Weather:
    def __init__(self):
        self.conn = sqlite3.connect('weather.db')

        with open('1711054.csv') as f:
            reader = csv.reader(f)
            self.historical_headers = next(reader, None)
            self.historical_data = []
            for row in reader:
                self.historical_data.append(row)

    def create_database(self):
        self.conn.execute('''CREATE TABLE local_climate_data
             (date text, trans text, symbol text, qty real, price real)''')

    def get_dew_point(self, dt_string):
        '''Get the dew point.

        :param str dt_string: a datetime string, e.g. "2019-04-23T09:30:00"

        :returns the dew point temperature as an integer in F. 
        '''
        return int(self.get_historical('HourlyDewPointTemperature', dt_string))

    def get_relative_humidity(self, dt_string):
        '''Get the relative humidity.

        :param str dt_string: a datetime string, e.g. "2019-04-23T09:30:00"

        :returns the relative humidity as an integer from 0 to 100. 
        '''
        return int(self.get_historical('HourlyRelativeHumidity', dt_string))

    def get_temperature(self, dt_string):
        '''Get the dry bulb temperature ("the temperature")

        :param str dt_string: a datetime string, e.g. "2019-04-23T09:30:00"

        :returns the temperature as an integer in F.
        '''
        return int(self.get_historical('HourlyDryBulbTemperature', dt_string))

    def get_h_temperature(self, dt_string):
        '''Get the high temperature for the day.

        :param str dt_string: a datetime string, e.g. "2019-04-23T09:30:00"

        :returns the high temperature as an integer in F.
        '''
        return max(
            filter(
                lambda t: t != '',
                self.get_historical_range(
                    'HourlyDryBulbTemperature',
                    dt_string.split('T')[0] + 'T00:00:00',
                    dt_string.split('T')[0] + 'T23:59:59'
                )
            )
        )

    def get_l_temperature(self, dt_string):
        '''Get the low temperature for the day.

        :param str dt_string: a datetime string, e.g. "2019-04-23T09:30:00"

        :returns the low temperature as an integer in F.
        '''
        return min(
            filter(
                lambda t: t != '',
                self.get_historical_range(
                    'HourlyDryBulbTemperature',
                    dt_string.split('T')[0] + 'T00:00:00',
                    dt_string.split('T')[0] + 'T23:59:59'
                )
            )
        )

    def get_time(self, dt_string):
        '''Get the closest past time in historical data for a specific
        date/time.

        :param str dt_string: a datetime string, e.g. "2019-04-23T09:30:00"

        :returns a datetime string.
        '''
        return self.get_historical('DATE', dt_string)

    def get_heat_index(self, dt_string):
        '''Calculate the heat index: see
        https://en.wikipedia.org/wiki/Heat_index.

        :param str dt_string: a datetime string, e.g. "2019-04-23T09:30:00"

        :returns a heat index temperature in F as an integer.
        '''
        t = self.get_temperature(dt_string)
        r = self.get_relative_humidity(dt_string)
        return int(
            sum(
                [-42.379,
                   2.04901523   * t,
                  10.14333127   * r,
                  -0.22475541   * t * r,
                  -6.83783e-03  * math.pow(t, 2),
                  -5.481717e-02 * math.pow(r, 2),
                   1.22874e-03  * math.pow(t, 2) * r,
                   8.5282e-04   * t * math.pow(r, 2),
                  -1.99e-06     * math.pow(t, 2) * math.pow(r, 2)]
            )
        )

    def get_closest_past_index(self, dt_string):
        '''Find the closest past index represented in historical data for a
        given date/time string.

        :param str dt_string: a datetime string, e.g. "2019-04-23T09:30:00"

        :returns an index (integer).
        '''
        d = self.historical_headers.index('DATE')
        r = len(self.historical_data) - 1
        while r >= 0:
            if self.historical_data[r][d] < dt_string:
                break
            r = r - 1
        return r

    def get_historical(self, field, dt_string):
        '''Get a single historical data point.

        :param str field: the field name.
        :param str dt_string: a datetime string, e.g. "2019-04-23T09:30:00"

        :returns the data as a string.
        '''
        r = self.get_closest_past_index(dt_string)
        f = self.historical_headers.index(field)
        return self.historical_data[r][f]

    def get_historical_range(self, field, dt_string_lo, dt_string_hi):
        '''Get a range of historical data points. 

        :param str field: the field name.
        :param str dt_string_lo: a datetime string, e.g. "2019-04-23T09:30:00"
        :param str dt_string_hi: a datetime string, e.g. "2019-04-23T09:30:00"

        :returns the data as a string.
        '''
        r_lo = self.get_closest_past_index(dt_string_lo)
        r_hi = self.get_closest_past_index(dt_string_hi)
        f = self.historical_headers.index(field)

        out = []
        r = r_lo
        while r <= r_hi:
            out.append(self.historical_data[r][f])
            r = r + 1
        return out


if __name__=='__main__':
    arguments = docopt(__doc__)

    w = Weather()

    if arguments['add']:
        pass
    if arguments['historical_headers']:
        sys.stdout.write('\n'.join(w.historical_headers + [""]))
        sys.exit()
    elif arguments['get_historical']:
        data = w.get_historical(arguments['<field>'], arguments['<yyyymmdd>'])
        if isinstance(data, str):
            sys.stdout.write(data + '\n')
        elif isinstance(data, list):
            sys.stdout.write('\n'.join(data + ['']))
    elif arguments['weather']:
        if not arguments['<YYYY-mm-ddTHH:MM:SS>']:
            now = datetime.datetime.now()
            arguments['<YYYY-mm-ddTHH:MM:SS>'] = '{}-{:02}-{:02}T{:02}:{:02}:{:02}'.format(
                2010, 
                now.month,
                now.day,
                now.hour,
                now.minute,
                now.second
            )

        sys.stdout.write("Chicago, IL\n")
        sys.stdout.write("as of {}\n".format( 
            datetime.datetime.strptime(
                w.get_time(arguments['<YYYY-mm-ddTHH:MM:SS>']),
                '%Y-%m-%dT%H:%M:%S'
            ).strftime('%-I:%M %p')
        ))
        sys.stdout.write("{} degrees\n".format(
            w.get_temperature(arguments['<YYYY-mm-ddTHH:MM:SS>'])
        ))
        sys.stdout.write("partly cloudy\n")
        sys.stdout.write("feels like {} degrees\n".format(
            w.get_heat_index(arguments['<YYYY-mm-ddTHH:MM:SS>'])
        ))
        sys.stdout.write("H {} degrees / L {} degrees\n".format(
            w.get_h_temperature(arguments['<YYYY-mm-ddTHH:MM:SS>']),
            w.get_l_temperature(arguments['<YYYY-mm-ddTHH:MM:SS>'])
        ))
        sys.stdout.write("UV index 5 of 10\n")
        sys.stdout.write("wind: S 18 mph\n")
        sys.stdout.write("humidity: {}%\n".format(
            w.get_relative_humidity(arguments['<YYYY-mm-ddTHH:MM:SS>'])
        ))
        sys.stdout.write("dew point: {} degrees\n".format(
            w.get_dew_point(arguments['<YYYY-mm-ddTHH:MM:SS>'])
        ))
        sys.stdout.write("pressure 29.95 down\n")
        sys.stdout.write("visibility 10.0 mi\n")
        sys.stdout.write("Mauna Loa Carbon Count: 410ppm\n")
        sys.exit()

    # TODO
    # 1. deal with sorting: because numbers are currently sorted as strings, 99 can
    # sort after 101. 
    # 2. add the db, check timings to be sure lookups are fast.
    # 3. deal with 'holes' in the data where a measurement wasn't available. 
    #    (i get these from the lo temperature function, check to see where they're
    #     coming from.)

    # self.local_climateology_data_fields = ('STATION', 'DATE',
    #     'HourlyDewPointTemperature', 'HourlyDryBulbTemperature',
    #     'HourlyPrecipitation', 'HourlyRelativeHumidity',
    #     'HourlySeaLevelPressure', 'HourlySkyConditions',
    #     'HourlyStationPressure', 'HourlyVisibility', 'HourlyWindDirection',
    #     'HourlyWindSpeed')
