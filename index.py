import astral
import csv
import datetime
import math
import random
import re
import sqlite3
import statistics
import sys
import textwrap
from docopt import docopt

from flask import Flask, render_template
app = Flask(__name__)
app.debug = True

class Weather:
    def __init__(self, datetime, fdt):
        self.datetime = datetime
        self.fdt = fdt
        with open('1721388.csv') as f:
            reader = csv.reader(f)
            self.historical_headers = next(reader, None)
            self.historical_data = []
            for row in reader:
                self.historical_data.append(row)
        self.i = self.get_closest_past_index(datetime)

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

    def get_present_weather_type(self):
        '''Get a description of the current weather. 

        :returns a string.
        '''
        weather_strings = {
            'FG':   'fog',
            'TS':   'thunder',
            'PL':   'sleet',
            'GR':   'hail',
            'GL':   'ice sheeting',
            'DU':   'dust',
            'HZ':   'haze',
            'BLSN': 'drifing snow',
            'FC':   'funnel cloud',
            'WIND': 'high winds',
            'BLPY': 'blowing spray',
            'BR':   'mist',
            'DZ':   'drizzle',
            'FZDZ': 'freezing drizzle',
            'RA':   'rain',
            'FZRA': 'freezing rain',
            'SN':   'snow',
            'UP':   'precipitation',
            'MIFG': 'ground fog',
            'FZFG': 'freezing fog'
        }
        types = set()
        present_weather = self.get_historical('HourlyPresentWeatherType')
        for p in present_weather.split('|'):
            m = re.search('[A-Z]+', p)
            if m:
                types.add(weather_strings[m.group(0)])
        return ', '.join(list(types))

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

    def get_time(self):
        '''Get the closest past time in historical data for a specific
        date/time.

        :returns a datetime string.
        '''
        return self.get_historical('DATE')

    def get_visibility(self):
        return int(float(self.get_historical('HourlyVisibility')))

    def get_wind_direction_and_speed(self):
        d = int(self.get_historical('HourlyWindDirection'))
        if d == 0:
            return 'still'

        directions = ('N', 'NNE', 'NE', 'ENE', 'E', 'ESE', 'SE', 'SSE', 'S',
                      'SSW', 'SW', 'WSW', 'W', 'WNW', 'NW', 'NNW', 'N')
        i = int(round(float(d) / 22.5))
        direction = directions[i % 16]

        s = self.get_historical('HourlyWindSpeed')
        return '{}mph {}'.format(s, direction)

    def get_temperature_summary(self, summary_type):
        '''Get the high temperature for the day.

        :param str summary_type: one of 'min', 'max', 'mean'

        :returns the high temperature as an integer in F.
        '''
        if dt_string == None:
            dt_string = self.dt_string

        temperatures = map(
            int,
            filter(
                bool,
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

    def is_beginning_of_day(self):
        '''Check to see if the current time is 00:00:00.

        :rtype bool
        '''
        return (
            self.datetime.hour,
            self.datetime.minute,
            self.datetime.second
        ) == (0, 0, 0)

    def get_beginning_of_day_weather(self):
	'''Factory for a new Weather() object with its datetime set at the
	beginning of the current object's day. (i.e., midnight of the current
        day.)

        :rtype Weather instance.
        '''
        if self.is_beginning_of_day():
            return self
        else:
            return Weather(
                datetime.datetime(
                    self.datetime.year,
                    self.datetime.month,
                    self.datetime.day
                )
            )

    def get_next_day_weather(self):
	'''Factory for a new Weather() object with its datetime set at the
	beginning of tomorrow (i.e. midnight), relative to the current
        instance. 

        :rtype Weather instance.
        '''
        d = self.datetime + datetime.timedelta(days=1)
        return Weather(
            datetime.datetime(
                d.year,
                d.month,
                d.day
            )
        )

    def get_previous_day_weather(self):
	'''Factory for a new Weather() object. If the current instance's
	datetime is at the beginning of the day, this method returns an object
	for the previous calendar day. Otherwise it returns an object for the
        beginning of the current day.

        :rtype Weather instance.
        '''
        if self.is_beginning_of_day():
            d = self.datetime - datetime.timedelta(days=1)
            return Weather(
                datetime.datetime(
                    d.year,
                    d.month,
                    d.day
                )
            )
        else:
            return self.get_beginning_of_day_weather()

    def is_beginning_of_hour(self):
	'''Check to see if the current object's datetime is set to the
        beginning of the hour, e.g. 00:00. 

        :rtype bool
        '''
        return (
            self.datetime.minute,
            self.datetime.second
        ) == (0, 0)

    def get_beginning_of_hour_weather(self):
	'''Factory for a new Weather() object. If the current instance's
	datetime is at the beginning of the hour, return the current object.
        Otherwise return a new instance whose datetime is set to 00:00.

        :rtype Weather instance.
        '''
        if self.is_beginning_of_hour():
            return self
        else:
            return Weather(
                datetime.datetime(
                    self.datetime.year,
                    self.datetime.month,
                    self.datetime.day,
                    self.datetime.hour
                )
            )
     
    def get_next_hour_weather(self):
	'''Factory for a new Weather() object with it's datetime set to the
        next hour.

        :rtype Weather instance.
        '''
        d = self.datetime + datetime.timedelta(hours=1)
        return Weather(
            datetime.datetime(
                d.year,
                d.month,
                d.day,
                d.hour
            )
        )

    def get_previous_hour_weather(self):
	'''Factory for a new Weather() object with it's datetime set to the
        beginning of the current hour or the previous hour. 

        :rtype Weather instance.
        '''
        if self.is_beginning_of_hour():
            d = self.datetime - datetime.timedelta(hours=1)
            return Weather(
                datetime.datetime(
                    d.year,
                    d.month,
                    d.day,
                    d.hour
                )
            )
        else:
            return self.get_beginning_of_hour_weather()

    def get_daily_forecast(self, dt_string=None):
        timestrings = self.get_daily_forecast_timestrings(dt_string)
        future_timestrings = self.get_daily_forecast_timestrings(future_dt_string)
        forecast = [] 
        for t in range(len(timestrings)):
            forecast.append({
                'ts':   timestrings[t],
                'low':  self.get_temperature_summary('min', timestrings[t]),
                'high': self.get_temperature_summary('max', timestrings[t]),
                'day':  datetime.datetime.strptime(
                            future_timestrings[t],
                            '%Y-%m-%dT%H:%M:%S'
                        ).strftime('%a')
            })
        return forecast

    def get_hourly_forecast(self, dt_string=None):
        if not dt_string:
            dt_string = self.dt_string
        timestrings = self.get_hourly_forecast_timestrings(dt_string)
        forecast = []
        for ts in timestrings:
            forecast.append({
                'ts':   ts,
                'temp': self.get_temperature(ts),
                'time': datetime.datetime.strptime(
                            ts,
                            '%Y-%m-%dT%H:%M:%S'
                        ).strftime('%-I%p')
            })
        return forecast

    def get_closest_past_index(self, dt_string=None):
        '''Find the closest past index represented in historical data for a
        given date/time string.

        :returns an index (integer).
        '''
        if not dt_string:
            dt_string = self.dt_string
        f = self.historical_headers.index('DATE')
        i = len(self.historical_data) - 1
        while i >= 0:
            if self.historical_data[i][f] < dt_string:
                break
            i = i - 1
        return i

    def get_historical(self, field, dt_string=None):
        '''Get a single historical data point.

        :param str field: the field name.

        :returns the data as a string.
        '''
        if dt_string:
            i = self.get_closest_past_index(dt_string)
        else:
            i = self.i
        f = self.historical_headers.index(field)

        while i > 0:
            if self.historical_data[i][f]:
                return self.historical_data[i][f]
            i = i - 1
        return ''

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

    def get_advertisement(self):
        ads = (("Skirts, blouses and accessories. Up to 45% off. Shop Now.", "Noracora"),
               ("Your future's looking up with our new student loan. Competitive interest rates. Multiple repayment options. No origination fee. Get started now.", "Sallie Mae"),
               ("Shop non-traditional jewelry designs.", "Brilliant Earth"),
               ("Khakis for all seasons. All season tech.", "Dockers"))
        return random.choice(ads)[0]

    def get_news(self):
        news = (("Troubling Trend Since 2020s for Great Lakes. Superior, Huron and Erie have seen the greatest declines. See more.",
                 "weather.com 2019/04/28 (modified date)"),
                ("Freeze in May? Here's Who Is Likely to See One.",
                 "weather.com 2019/04/28 (verbatim)"),
                ("Incoming Severe Threat This Week",
                 "weather.com 2019/04/28 (verbatim)"),
                ("Winter Storm Central: Blizzard Conditions Likely; Travel Nearly Impossible",
                 "weather.com 2019/04/28 (verbatim)"),
                ("Allergy: Tips for An Allergy-Free Spring Road Trip",
                 "weather.com 2019/04/28 (verbatim)"),
                ("Allergy: Worst Plants for Spring Allergies",
                 "weather.com 2019/04/28 (verbatim)"),
                ("Tornado Safety and Preparedness: Safest Places to Wait Out A Tornado",
                 "weather.com 2019/04/28 (verbatim)"),
                ("Allergy: Spring Allergy Capitals: Which City Ranks the Worst",
                 "weather.com 2019/04/28 (verbatim)"))
        return [n[0] for n in random.sample(news, 3)]

    def get_future_years_with_same_weekday(self):
        years = []
        for y in range(1, 100):
            future_d = self.datetime + datetime.timedelta(year=y)
            if future_d.weekday() == self.datetime.weekday():
                years.append(y)
        return years


now = datetime.datetime.now()
w = Weather('{}-{:02}-{:02}T{:02}:{:02}:{:02}'.format(
    2010, 
    now.month,
    now.day,
    now.hour,
    now.minute,
    now.second
))


@app.route('/', methods=['GET'])
def index():
    now = datetime.datetime.now()

    historical_weather_datetime = datetime.datetime(
        2010,
        now.month,
        now.day,
        now.hour,
        now.minute,
        now.second
    )

    future_year = min(
        filter(
            lambda y: y > 2069,
            w.get_future_years_with_same_weekday(now_dt_string)
        )
    )

    w = Weather(historical_weather_datetime)

    future_dtstring = datetime.datetime.strptime(
        '{}-{:02}-{:02}T00:00:00'.format(
            future_year,
            now.month,
            now.day
        ),
        '%Y-%m-%dT%H:%M:%S'
    ).strftime('%Y-%m-%dT%H:%M:%S')    
    future_datetime = datetime.datetime.strptime(
        '{}-{:02}-{:02}T00:00:00'.format(
            future_year,
            now.month,
            now.day
        ),
        '%Y-%m-%dT%H:%M:%S'
    ).strftime('%A, %B, %-d %Y')

    a = astral.Astral() 
    city = a['Chicago']
    sun = city.sun(date=datetime.datetime.now())
    "Sunrise: {}<br/>".format(sun['sunrise'].strftime('%-I:%m%p'))
    "Sunset: {}<br/>".format(sun['sunset'].strftime('%-I:%m%p'))

    moon_phases = ('New Moon', 'First Quarter', 'Full Moon', 'Last Quarter', 'New Moon')
    i = int(float(a.moon_phase(date=datetime.datetime.now())) / 7.0)
    "Moon phase: {}<br/>".format(moon_phases[i])

    return render_template('weather.html', **{
        'place':             'Chicago',
        'weather_data_date': future_datetime,
        'weather_data_time': datetime.datetime.strptime(
                                 w.get_time(),
                                 '%Y-%m-%dT%H:%M:%S'
                             ).strftime('%-I:%M%p'),
        'present_weather':   w.get_present_weather_type(),
        'sky_conditions':    w.get_sky_conditions(),
        'temperature':       w.get_temperature(),
        'daily_forecast':    w.get_daily_forecast(w.dt_string, future_dtstring),
        'hourly_forecast':   w.get_hourly_forecast(),
        'news':              ' '.join(w.get_news()) + ' ' + w.get_advertisement()
    })
