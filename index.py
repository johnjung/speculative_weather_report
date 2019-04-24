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

    def get_time(self, dt_string):
        d = self.historical_headers.index('DATE')
        if dt_string:
            r = len(self.historical_data) - 1
            while r >= 0:
                if r == 0 or self.historical_data[r][d] < dt_string:
                    closest_dt_string = self.historical_data[r][d]
                    break
                r = r - 1
        dt = datetime.datetime.strptime(closest_dt_string, "%Y-%m-%dT%H:%M:%S")
        return dt.strftime("%-I:%M %p")

    def get_temperature(self, dt_string):
        return self.get_historical('HourlyDryBulbTemperature', dt_string)

    def get_heat_index(self, dt_string):
        # see https://en.wikipedia.org/wiki/Heat_index
        raise NotImplementedError

    def get_historical(self, field, dt_string=None):
        i = self.historical_headers.index(field)
        d = self.historical_headers.index('DATE')
        if dt_string:
            if self.historical_data[-1][d] <= dt_string:
                return self.historical_data[-1][i]
            else:
                for r in self.historical_data:
                    if r[d] > dt_string:
                        return r[i]
        else:
            return [r[i] for r in self.historical_data]

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
        sys.stdout.write((
            'SAMPLE HISTORICAL HEADERS\n\n'
            'ACMH\n'
            'Average cloudiness midnight to midnight from manual observations (percent)\n\n'
            'ACSH\n'
            'Average cloudiness sunrise to sunset from manual observations (percent)\n\n'
            'AWDR\n'
            'Average daily wind direction (degrees)\n\n'
            'AWND\n'
            'Average daily wind speed (tenths of meters per second)\n\n'
            'PRCP\n'
            'Precipitation (tenths of mm)\n\n'
   	    'SNOW\n'
            'Snowfall (mm)\n\n'
	    'SNWD\n'
            'Snow depth (mm)\n\n'
            'TAVG\n'
            'Average temperature (tenths of degrees C)\n\n'
            'TMAX\n'
            'Maximum temperature (tenths of degrees C)\n\n'
            'TMIN\n'
            'Minimum temperature (tenths of degrees C)\n\n'
  	    'WT** = Weather Type where ** has one of the following values:\n'
            '01 = Fog, ice fog, or freezing fog (may include heavy fog)\n'
            '02 = Heavy fog or heaving freezing fog (not always distinquished from fog)\n'
            '03 = Thunder\n'
            '04 = Ice pellets, sleet, snow pellets, or small hail\n'
            '05 = Hail (may include small hail)\n'
            '06 = Glaze or rime\n'
            '07 = Dust, volcanic ash, blowing dust, blowing sand, or blowing obstruction\n'
            '08 = Smoke or haze\n'
            '09 = Blowing or drifting snow\n'
            '10 = Tornado, waterspout, or funnel cloud\n'
            '11 = High or damaging winds\n'
            '12 = Blowing spray\n'
            '13 = Mist\n'
            '14 = Drizzle\n'
            '15 = Freezing drizzle\n'
            '16 = Rain (may include freezing rain, drizzle, and freezing drizzle)\n'
            '17 = Freezing rain\n'
            '18 = Snow, snow pellets, snow grains, or ice crystals\n'
            '19 = Unknown source of precipitation\n'
            '21 = Ground fog\n'
            '22 = Ice fog or freezing fog\n\n'
            'WV** = Weather in the Vicinity where ** has one of the following values:\n'
            '01 = Fog, ice fog, or freezing fog (may include heavy fog)\n'
            '03 = Thunder\n'
            '07 = Ash, dust, sand, or other blowing obstruction\n'
            '18 = Snow or ice crystals\n'
            '20 = Rain or snow shower\n\n'
            'SAMPLE NORMAL HEADERS\n\n'
            'MLY-TMIN-NORMAL\n'
            'Long-term averages of annual minimum temperature\n\n'
            'MLY-TMIN-STDDEV\n'
            'Long-term standard deviations of annual minimum temperature\n\n'
            'MLY-TAVG-NORMAL\n'
            'Long-term averages of annual average temperature\n\n'
            'MLY-TAVG-STDDEV\n'
            'Long-term standard deviations of annual average temperature\n\n'
            'MLY-TMAX-NORMAL\n'
            'Long-term averages of monthly maximum temperature\n\n'
            'MLY-TMAX-STDDEV\n'
            'Long-term standard deviations of monthly maximum temperature\n\n'
            'MLY-PRCP-NORMAL\n\n'
            'MLY-SNOW-NORMAL\n'))
        sys.exit()
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
        sys.stdout.write("as of {}\n".format(w.get_time(arguments['<YYYY-mm-ddTHH:MM:SS>'])))
        sys.stdout.write("{} degrees\n".format(w.get_temperature(arguments['<YYYY-mm-ddTHH:MM:SS>'])))
        sys.stdout.write("partly cloudy\n")
        sys.stdout.write("feels like 79 degrees\n")
        sys.stdout.write("H 78 degrees / L 50 degrees\n")
        sys.stdout.write("UV index 5 of 10\n")
        sys.stdout.write("wind: S 18 mph\n")
        sys.stdout.write("humidity: 33%\n")
        sys.stdout.write("dew point: 48 degrees\n")
        sys.stdout.write("pressure 29.95 down\n")
        sys.stdout.write("visibility 10.0 mi\n")
        sys.stdout.write("Mauna Loa Carbon Count: 410ppm\n")
        sys.exit()
