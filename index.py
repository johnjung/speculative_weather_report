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

    def get_carbon_count(self, temperature_increase):
        '''Get an estimated carbon count in ppm for a temperature increase
        given in F, compared to current levels:
        http://dels.nas.edu/resources/static-assets/materials-based-on-reports/booklets/warming_world_final.pdf
        '''
        carbon_counts = (410, 480, 550, 630, 700, 800, 900, 1000, 1200, 1400)
        return carbon_counts[temperature_increase]

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

    def get_sky_conditions(self, dt_string):
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
            self.get_historical('HourlySkyConditions', dt_string)
        )
        try:
            return conditions[matches.group(1)]
        except AttributeError:
            return ''

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
            map(
                lambda t: int(t),
                filter(
                    lambda t: t != '',
                    self.get_historical_range(
                        'HourlyDryBulbTemperature',
                        dt_string.split('T')[0] + 'T00:00:00',
                        dt_string.split('T')[0] + 'T23:59:59'
                    )
                )
            )
        )

    def get_l_temperature(self, dt_string):
        '''Get the low temperature for the day.

        :param str dt_string: a datetime string, e.g. "2019-04-23T09:30:00"

        :returns the low temperature as an integer in F.
        '''
        return min(
            map(
                lambda t: int(t),
                filter(
                    lambda t: t != '',
                    self.get_historical_range(
                        'HourlyDryBulbTemperature',
                        dt_string.split('T')[0] + 'T00:00:00',
                        dt_string.split('T')[0] + 'T23:59:59'
                    )
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

    def get_visibility(self, dt_string):
        return int(float(self.get_historical('HourlyVisibility', dt_string)))

    def get_wind_direction_and_speed(self, dt_string):
        d = self.get_historical('HourlyWindDirection', dt_string)
        if d == '0':
            return 'still'

        directions = ('N', 'NNE', 'NE', 'ENE', 'E', 'ESE', 'SE', 'SSE', 'S',
                      'SSW', 'SW', 'WSW', 'W', 'WNW', 'NW', 'NNW', 'N')
        direction = directions[int(float(d) / 22.5)]

        s = self.get_historical('HourlyWindSpeed', dt_string)
        return '{}mph {}'.format(s, direction)

    def get_heat_index(self, dt_string):
        '''Calculate the heat index: see
        https://en.wikipedia.org/wiki/Heat_index.

        :param str dt_string: a datetime string, e.g. "2019-04-23T09:30:00"

        :returns a heat index temperature in F as an integer.
        '''
        t = self.get_temperature(dt_string)
        if t < 80:
            return None
        r = self.get_relative_humidity(dt_string)
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
    temperature_increase = 0

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
            sys.stdout.write("Using {}\n".format(arguments['<YYYY-mm-ddTHH:MM:SS>']))

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

        sky_conditions =  w.get_sky_conditions(arguments['<YYYY-mm-ddTHH:MM:SS>'])
        if sky_conditions:
            sys.stdout.write('{}\n'.format(
                sky_conditions
            ))
     
        heat_index =  w.get_heat_index(arguments['<YYYY-mm-ddTHH:MM:SS>'])
        if heat_index:
            sys.stdout.write("feels like {} degrees\n".format(heat_index))

        sys.stdout.write("H {} degrees / L {} degrees\n".format(
            w.get_h_temperature(arguments['<YYYY-mm-ddTHH:MM:SS>']),
            w.get_l_temperature(arguments['<YYYY-mm-ddTHH:MM:SS>'])
        ))
        sys.stdout.write("wind: {}\n".format(
            w.get_wind_direction_and_speed(arguments['<YYYY-mm-ddTHH:MM:SS>'])
        ))
        sys.stdout.write("humidity: {}%\n".format(
            w.get_relative_humidity(arguments['<YYYY-mm-ddTHH:MM:SS>'])
        ))
        sys.stdout.write("dew point: {} degrees\n".format(
            w.get_dew_point(arguments['<YYYY-mm-ddTHH:MM:SS>'])
        ))
        sys.stdout.write("visibility {} mi\n".format(
            w.get_visibility(arguments['<YYYY-mm-ddTHH:MM:SS>'])
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
