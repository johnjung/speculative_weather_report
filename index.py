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


class Forecast:
    def __init__(self, datetime):
        self.datetime = datetime
        self.astral = astral.Astral()
        self.astral_city = 'Chicago'

        self.current_weather = Weather(datetime)

        self.daily_forecast = []
        d = self.current_weather.datetime.replace(hour=0, minute=0, second=0)
        for i in range(1, 7):
            self.daily_forecast.append(Weather(d + datetime.timedelta(days=i)))

        self.hourly_forecast = []
        d = self.current_weather.datetime.replace(minute=0, second=0)
        for i in range(1, 25):
            self.daily_forecast.append(Weather(d + datetime.timedelta(hours=i)))

        self.news = News()

    def daily(self):
        '''daily forecast needs to include sunrise, sunset...other events?'''
        forecast = []
        w = self
        for i in range(7):
            w = w.get_next_day_weather()
            forecast.append(w.asdict())
        return forecast

    def hourly(self):
        forecast = []
        w = self
        for i in range(24):
            w = w.get_next_day_weather()
            forecast.append(w.asdict())
        return forecast

    def moon_phase(self):
        return (
            'New Moon',
            'First Quarter',
            'Full Moon',
            'Last Quarter',
            'New Moon'
        )[int(float(self.astral.moon_phase(date=self.datetime) / 7.0))]

    def next_sunrise(self):
        '''Get weather for the first future sunrise from this point.
        '''
        sun = self.astral_city.sun(date=self.datetime)
        if self.sun['sunrise'] > self.datetime:
            return self.sun['sunrise']
        else:
            sun = self.astral_city.sun(
                date=self.datetime + datetime.timedelta(days=1)
            )
            return self.sun['sunrise']

    def next_sunrise(self):
        '''Get weather for the first future sunrise from this point.
        '''
        sun = self.astral_city.sun(date=self.datetime)
        if self.sun['sunset'] > self.datetime:
            return self.sun['sunset']
        else:
            sun = self.astral_city.sun(
                date=self.datetime + datetime.timedelta(days=1)
            )
            return self.sun['sunset']

    def asdict(self):
        return {
            'current_weather': self.current_weather.asdict(),
            'daily_forecast':  self.daily_forecast(),
            'hourly_forecast': self.hourly_forecast(),
            'news':            self.news
        }


class Weather:
    def __init__(self, datetime):
        '''Constructor

	      :param datetime datetime: current date.
        '''
        self.datetime = datetime
        with open('1721388.csv') as f:
            reader = csv.reader(f)
            self.historical_headers = next(reader, None)
            self.historical_data = []
            for row in reader:
                self.historical_data.append(row)

    def as_of(self):
        '''Get the most recent reading time from historical data.

        :returns a datetime string.
        '''
        return self.get_historical('DATE')

    def carbon_count(self, temperature_increase):
        '''Get an estimated carbon count in ppm for a temperature increase
        given in F, compared to current levels:
        http://dels.nas.edu/resources/static-assets/materials-based-on-reports/booklets/warming_world_final.pdf
        '''
        carbon_counts = (410, 480, 550, 630, 700, 800, 900, 1000, 1200, 1400)
        return carbon_counts[temperature_increase]

    def dew_point(self):
        '''Get the dew point.

        :returns the dew point temperature as an integer in F. 
        '''
        return int(self.get_historical('HourlyDewPointTemperature'))

    def heat_index(self):
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

    def relative_humidity(self):
        '''Get the relative humidity.

        :returns the relative humidity as an integer from 0 to 100. 
        '''
        return int(self.get_historical('HourlyRelativeHumidity'))

    def sky_conditions(self):
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

    def temperature(self):
        '''Get the dry bulb temperature ("the temperature")

        :returns the temperature as an integer in F.
        '''
        return int(self.get_historical('HourlyDryBulbTemperature'))

    def temperature_min(self):
        return self._temperature_summary('min')

    def temperature_mean(self):
        return self._temperature_summary('mean')

    def temperature_max(self):
        return self._temperature_summary('max')

    def visibility(self):
        return int(float(self.get_historical('HourlyVisibility')))

    def weather_type(self):
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

    def wind_direction_and_speed(self):
        d = int(self.get_historical('HourlyWindDirection'))
        if d == 0:
            return 'still'

        directions = ('N', 'NNE', 'NE', 'ENE', 'E', 'ESE', 'SE', 'SSE', 'S',
                      'SSW', 'SW', 'WSW', 'W', 'WNW', 'NW', 'NNW', 'N')
        i = int(round(float(d) / 22.5))
        direction = directions[i % 16]

        s = self.get_historical('HourlyWindSpeed')
        return '{}mph {}'.format(s, direction)

    def _get_closest_past_index(self, datetime=None):
        '''Find the closest past index represented in historical data for a
        given date/time string.

        :returns an index (integer).
        '''
        if not datetime:
            datetime = self.datetime
        dt_string = datetime.strftime('%Y-%m-%dT%H:%M:%S')
        f = self.historical_headers.index('DATE')
        i = len(self.historical_data) - 1
        while i >= 0:
            if self.historical_data[i][f] < dt_string:
                break
            i = i - 1
        return i

    def _get_historical(self, field):
        '''Get a single historical data point.

        :param str field: the field name.

        :returns the data as a string.
        '''
        i = self.get_closest_past_index()
        f = self.historical_headers.index(field)
        while i > 0:
            if self.historical_data[i][f]:
                return self.historical_data[i][f]
            i = i - 1
        return ''

    def _get_historical_daily_range(self, field):
        '''Get a range of historical data points. 

        :param str field: the field name.

        :returns the data as a string.
        '''
        start_of_day = self.datetime.replace(hour=0, minute=0, second=0)
        i1 = self.get_closest_past_index(start_of_day)
        i2 = self.get_closest_past_index(
            start_of_day + datetime.timedelta(days=1)
        )
        f = self.historical_headers.index(field)
        return [self.historical_data[i][f] for i in range(i1, i2 + 1)]

    def _temperature_summary(self, summary_type):
        '''Get the high temperature for the day.

        :param str summary_type: one of 'min', 'max', 'mean'

        :returns the high temperature as an integer in F.
        '''
        temperatures = map(
            int,
            filter(
                bool,
                self.get_historical_daily_range('HourlyDryBulbTemperature')
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

    def future_year_with_same_weekday(self, min_future_year):
        year = min_future_year:
        while True:
            if self.datetime.replace(year=year).weekday() = self.cdt.weekday():
                return year
            year += 1

    def asdict(self):
        return {
            'as_of':                    self.as_of,
            'carbon_count':             self.carbon_count,
            'dew_point':                self.dew_point,
            'heat_index':               self.heat_index,
            'relative_humidity':        self.relative_humidity,
            'sky_conditions':           self.sky_conditions,
            'temperature':              self.temperature,
            'temperature_min':          self.temperature,
            'temperature_mean':         self.temperature,
            'temperature_max':          self.temperature,
            'visibility':               self.visibility,
            'weather_type':             self.weather_type,
            'wind_direction_and_speed': self.wind_direction_and_speed
        }

class CurrentWeather(Weather):
    def __init__(self):
        raise NotImplementedError

    def human_readable_time():
        raise NotImplementedError


class DailyWeather(Weather):
    def __init__(self):
        raise NotImplementedError

    def human_readable_time():
        raise NotImplementedError


class HourlyWeather(Weather):
    def __init__(self):
        raise NotImplementedError

    def human_readable_time():
        raise NotImplementedError


class Sunrise(Weather):
    def __init__(self):
        raise NotImplementedError

    def human_readable_time():
        raise NotImplementedError


class Sunset(Weather):
    def __init__(self):
        raise NotImplementedError

    def human_readable_time():
        raise NotImplementedError


class News:
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


@app.route('/', methods=['GET'])
def index():
    return render_template(
        'weather.html', 
        Forecast(datetime.datetime.now()).asdict()
    )
