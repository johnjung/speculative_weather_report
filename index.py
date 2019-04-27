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
import re
import sqlite3
import statistics
import sys
from docopt import docopt

class Weather:
    def __init__(self, dt_string):
        self.dt_string = dt_string
        with open('1711054.csv') as f:
            reader = csv.reader(f)
            self.historical_headers = next(reader, None)
            self.historical_data = []
            for row in reader:
                self.historical_data.append(row)
        self.i = self.get_closest_past_index(dt_string)

    def get_carbon_count(self, temperature_increase):
        '''Get an estimated carbon count in ppm for a temperature increase
        given in F, compared to current levels:
        http://dels.nas.edu/resources/static-assets/materials-based-on-reports/booklets/warming_world_final.pdf
        '''
        carbon_counts = (410, 480, 550, 630, 700, 800, 900, 1000, 1200, 1400)
        return carbon_counts[temperature_increase]

    def get_dew_point(self):
        '''Get the dew point.

        :returns the dew point temperature as an integer in F. 
        '''
        return int(self.get_historical('HourlyDewPointTemperature'))

    def get_relative_humidity(self):
        '''Get the relative humidity.

        :returns the relative humidity as an integer from 0 to 100. 
        '''
        return int(self.get_historical('HourlyRelativeHumidity'))

    def get_sky_conditions(self):
        '''Get sky conditions. These are recorded in the data in a string like:

        FEW:02 70 SCT:04 200 BKN:07 250
 
        Although this data field is often blank, very often zero or more data
        chunks in the following format will be included:

        [A-Z]{3}:[0-9]{2} [0-9]{2}

        The three letter sequence indicates cloud cover according to the dict
        below. The two digit sequence immediately following indicates the
        coverage of a layer in oktas (i.e. eigths) of sky covered. The final 
        three digit sequence describes the height of the cloud layer, in 
        hundreds of feet: e.g., 50 = 5000 feet. It is also possible for this
        string to include data that indicates that it was not possible to 
        observe the sky because of obscuring phenomena like smoke or fog. 

        The last three-character chunk provides the best summary of 
        current sky conditions.
        '''
        conditions = {
           'CLR': 'clear sky',
           'FEW': 'few clouds',
           'SCT': 'scattered clouds',
           'BKN': 'broken clouds',
           'OVC': 'overcast'
        }

        matches = re.search(
            '([A-Z]{3}):[0-9]{2} [0-9]{3}$',
            self.get_historical('HourlySkyConditions')
        )
        try:
            return conditions[matches.group(1)]
        except AttributeError:
            return ''

    def get_temperature(self):
        '''Get the dry bulb temperature ("the temperature")

        :returns the temperature as an integer in F.
        '''
        return int(self.get_historical('HourlyDryBulbTemperature'))

    def get_temperature_summary(self, summary_type):
        '''Get the high temperature for the day.

        :param str summary_type: one of 'min', 'max', 'mean'

        :returns the high temperature as an integer in F.
        '''
        temperatures = map(
            lambda t: int(t),
            filter(
                lambda t: t != '',
                self.get_historical_range(
                    'HourlyDryBulbTemperature',
                    *self.get_daily_timestring_range()
                )
            )
        )
        if summary_type == 'min':
            return min(temperatures)
        elif summary_type == 'max':
            return max(temperatures)
        elif summary_type == 'mean':
            return int(statistics.mean(temperatures))
        else:
            raise ValueError

    def get_time(self):
        '''Get the closest past time in historical data for a specific
        date/time.

        :returns a datetime string.
        '''
        return self.get_historical('DATE')

    def get_future_hourly_timestrings(self):
        '''Get 23 hours worth of future time strings- each timestring starts
        from the beginning of the hour.
        '''
        m = re.match('^([0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}).*$', self.dt_string)
        dt = datetime.datetime.strptime(
            '{}:00:00'.format(m.group(1)),
            '%Y-%m-%dT%H:%M:%S'
        )

        dt_strings = []
        for h in range(1, 24):
            dt_strings.append(
                (dt + datetime.timedelta(hours=h)).strftime(
                    '%Y-%m-%dT%H:%M:%S'
                )
            )
        return dt_strings

    def get_future_daily_timestrings(self):
        '''Get 6 days worth of future time strings- each timestring starts
        from the beginning of the day.
        '''
        m = re.match('^([0-9]{4}-[0-9]{2}-[0-9]{2}).*$', self.dt_string)
        dt = datetime.datetime.strptime(
            '{}T00:00:00'.format(m.group(1)),
            '%Y-%m-%dT%H:%M:%S'
        )

        dt_strings = []
        for d in range(1, 7):
            dt_strings.append(
                (dt + datetime.timedelta(days=d)).strftime(
                    '%Y-%m-%dT%H:%M:%S'
                )
            )
        return dt_strings

    def get_daily_timestring_range(self):
        '''For a given datetime string, get the earliest and latest timestrings
        for the day.
        '''
        return (
            self.dt_string.split('T')[0] + 'T00:00:00',
            self.dt_string.split('T')[0] + 'T23:59:59'
        )

    def get_visibility(self):
        return int(float(self.get_historical('HourlyVisibility')))

    def get_wind_direction_and_speed(self):
        d = self.get_historical('HourlyWindDirection')
        if d == '0':
            return 'still'

        directions = ('N', 'NNE', 'NE', 'ENE', 'E', 'ESE', 'SE', 'SSE', 'S',
                      'SSW', 'SW', 'WSW', 'W', 'WNW', 'NW', 'NNW', 'N')
        i = int(round(float(d) / 22.5))
        direction = directions[i % 16]

        s = self.get_historical('HourlyWindSpeed')
        return '{}mph {}'.format(s, direction)

    def get_heat_index(self):
        '''Calculate the heat index: see
        https://en.wikipedia.org/wiki/Heat_index.

        :returns a heat index temperature in F as an integer.
        '''
        t = self.get_temperature()
        if t < 80:
            return None
        r = self.get_relative_humidity()
        if r < 40:
            return None
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

        :returns an index (integer).
        '''
        d = self.historical_headers.index('DATE')
        r = len(self.historical_data) - 1
        while r >= 0:
            if self.historical_data[r][d] < dt_string:
                break
            r = r - 1
        return r

    def get_historical(self, field):
        '''Get a single historical data point.

        :param str field: the field name.

        :returns the data as a string.
        '''
        f = self.historical_headers.index(field)
        return self.historical_data[self.i][f]

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

    w = Weather(arguments['<YYYY-mm-ddTHH:MM:SS>'])
    temperature_increase = 0

    if arguments['add']:
        pass
    if arguments['historical_headers']:
        sys.stdout.write('\n'.join(w.historical_headers + [""]))
        sys.exit()
    elif arguments['get_historical']:
        data = w.get_historical(arguments['<field>'])
        if isinstance(data, str):
            sys.stdout.write(data + '\n')
        elif isinstance(data, list):
            sys.stdout.write('\n'.join(data + ['']))
    elif arguments['weather']:
        sys.stdout.write("Chicago, IL\n")

        sys.stdout.write("as of {}\n".format( 
            datetime.datetime.strptime(
                w.get_time(),
                '%Y-%m-%dT%H:%M:%S'
            ).strftime('%-I:%M %p')
        ))
        sys.stdout.write("{} degrees\n".format(
            w.get_temperature()
        ))

        sky_conditions =  w.get_sky_conditions()
        if sky_conditions:
            sys.stdout.write('{}\n'.format(
                sky_conditions
            ))
     
        heat_index =  w.get_heat_index()
        if heat_index:
            sys.stdout.write("feels like {} degrees\n".format(heat_index))

        sys.stdout.write("H {} degrees / L {} degrees\n".format(
            w.get_temperature_summary('max'),
            w.get_temperature_summary('min')
        ))
        sys.stdout.write("wind: {}\n".format(
            w.get_wind_direction_and_speed()
        ))
        sys.stdout.write("humidity: {}%\n".format(
            w.get_relative_humidity()
        ))
        sys.stdout.write("dew point: {} degrees\n".format(
            w.get_dew_point()
        ))
        sys.stdout.write("visibility {} mi\n".format(
            w.get_visibility()
        ))
        sys.stdout.write("Mauna Loa Carbon Count: {}ppm\n".format(
            w.get_carbon_count(temperature_increase)
        ))
        sys.exit()

    # TODO
    # 2. add the db, check timings to be sure lookups are fast.
    # 3. deal with 'holes' in the data where a measurement wasn't available. 
    #    (i get these from the lo temperature function, check to see where they're
    #     coming from.)

    # self.local_climateology_data_fields = ('STATION', 'DATE',
    #     
    #     'HourlyPrecipitation'
    #     'HourlySeaLevelPressure', 'HourlySkyConditions',
    #     'HourlyStationPressure', 'HourlyVisibility', 'HourlyWindDirection',
    #     'HourlyWindSpeed')
    #
    # there can be multiple records with the same timestamp. See:
    # 2010-04-27T01:51:00
    #
    # some data doesn't always appear- see sky conditions for an example. 
    # add a feature to search backwards for the last observation from a point
    # in time.
    #
    # always uses LST- no adjustments are made for daylight savings time. 
