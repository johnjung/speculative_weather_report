#!/usr/bin/env python
"""Usage:
    index.py add
    index.py historical_headers
    index.py help
    index.py get_historical <field> [<yyyymmdd>]
    index.py get_normal <field> [<month>]
    index.py normal_headers
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

        self.local_climateology_data_fields = ('STATION', 'DATE',
            'HourlyDewPointTemperature', 'HourlyDryBulbTemperature',
            'HourlyPrecipitation', 'HourlyRelativeHumidity',
            'HourlySeaLevelPressure', 'HourlySkyConditions',
            'HourlyStationPressure', 'HourlyVisibility', 'HourlyWindDirection',
            'HourlyWindSpeed')

        # normals.
        with open('1709000.csv') as f:
            reader = csv.reader(f)
            self.normal_headers = next(reader, None)
            self.normal_data = []
            for row in reader:
                self.normal_data.append(row)

        # historical data.
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
        return int(self.get_historical('HourlyDewPointTemperature', dt_string))

    def get_relative_humidity(self, dt_string):
        return int(self.get_historical('HourlyRelativeHumidity', dt_string))

    def get_temperature(self, dt_string):
        return int(self.get_historical('HourlyDryBulbTemperature', dt_string))

    def get_h_temperature(self, dt_string):
        # TODO: debug
        r1 = self.get_closest_past_index(dt_string.split('T')[0] + 'T00:00:00')
        r2 = self.get_closest_past_index(dt_string.split('T')[0] + 'T23:59:59')
        f = self.historical_headers.index('HourlyDryBulbTemperature')
        temps = []
        r = r1
        while r <= r2:
            temps.append(self.historical_data[r][f])
            r = r + 1
        return max(temps)

    def get_l_temperature(self, dt_string):
        # TODO: debug
        r1 = self.get_closest_past_index(dt_string.split('T')[0] + 'T00:00:00')
        r2 = self.get_closest_past_index(dt_string.split('T')[0] + 'T23:59:59')
        f = self.historical_headers.index('HourlyDryBulbTemperature')
        temps = []
        r = r1
        while r <= r2:
            temps.append(self.historical_data[r][f])
            r = r + 1
        return min(temps)

    def get_time(self, dt_string):
        return self.get_historical('DATE', dt_string)

    def get_heat_index(self, dt_string):
        t = self.get_temperature(dt_string)
        r = self.get_relative_humidity(dt_string)
        # see https://en.wikipedia.org/wiki/Heat_index
        return int(
            sum([
                -42.379,
                  2.04901523   * t,
                 10.14333127   * r,
                 -0.22475541   * t * r,
                 -6.83783e-03  * math.pow(t, 2),
                 -5.481717e-02 * math.pow(r, 2),
                  1.22874e-03  * math.pow(t, 2) * r,
                  8.5282e-04   * t * math.pow(r, 2),
                 -1.99e-06     * math.pow(t, 2) * math.pow(r, 2)
            ])
        )

    def get_closest_past_index(self, dt_string):
        d = self.historical_headers.index('DATE')
        r = len(self.historical_data) - 1
        while r >= 0:
            if self.historical_data[r][d] < dt_string:
                break
            r = r - 1
        return r

    def get_historical(self, field, dt_string):
        r = self.get_closest_past_index(dt_string)
        f = self.historical_headers.index(field)
        return self.historical_data[r][f]

    def get_normal(self, field, month=None):
        i = self.normal_headers.index(field)
        if month:
            return self.normal_data[int(month) - 1][i]
        else:
            return [d[i] for d in self.normal_data]

    def add_local_climateology_data(self, csv_filename):
        with open(csv_filename) as f:
            reader = csv.reader(f)
            headers = next(reader)

            headers.index(f)
    

if __name__=='__main__':
    arguments = docopt(__doc__)

    w = Weather()

    if arguments['add']:
        pass
    if arguments['historical_headers']:
        sys.stdout.write('\n'.join(w.historical_headers + [""]))
        sys.exit()
    if arguments['normal_headers']:
        sys.stdout.write('\n'.join(w.normal_headers + [""]))
        sys.exit()
    elif arguments['help']:
        raise NotImplementedError
    elif arguments['get_historical']:
        data = w.get_historical(arguments['<field>'], arguments['<yyyymmdd>'])
        if isinstance(data, str):
            sys.stdout.write(data + '\n')
        elif isinstance(data, list):
            sys.stdout.write('\n'.join(data + ['']))
    elif arguments['get_normal']:
        data = w.get_normal(arguments['<field>'], arguments['<month>'])
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
