import astral
import csv
import datetime
import math
import random
import re
import statistics


def load_historical_data_headers():
    """Load the headers for historical weather data."""
    with open('../data/1711054.csv') as f:
        reader = csv.reader(f)
        return next(reader, None)


def load_historical_data():
    """Load historical weather data."""
    with open('../data/1711054.csv') as f:
        reader = csv.reader(f)
        next(reader, None)
        historical_data = []
        for row in reader:
            historical_data.append(row)
        return historical_data


class Forecast:
    """A class to hold the data for a speculative weather forecast display.

    This display shows a summary of fictional future weather by combining
    information from three different dates: first, it uses the current date to
    calcuate things like the days of the week and the hours of the day that
    should appear in daily and hourly forecasts. It also uses the current date
    to calculate upcoming sunrises and sunsets.

    It then looks through historical weather data from other locations, for the
    same date from a previous year. So, for example, it might display the
    weather from Austin Texas on May 1, 2010 in Chicago on May 1, 2019. 

    Finally, it chooses a year in the future where the current date has a
    matching day of the week.

    This object is designed to be instantiated once for each weather forecast
    display. A Forecast contains the current weather, hourly and daily weather
    predictions, events like sunrise, high tide, time of eclipse, etc., news,
    and advertisements.
    """

    def __init__(self, dt):
        """Object Constructor.

	Creating a new Forecast object instantiates Weather object subclasses
	for the current weather along with daily and hourly forecasts, as well
        as News and Advertisements objects.

        Args:
            dt (datetime.datetime)
        """
        self.dt = dt
        self.astral = astral.Astral()
        self.astral_city = 'Chicago'

        self.current_weather = CurrentWeather(dt)

        self.daily = []
        d = self.current_weather.dt.replace(hour=0, minute=0, second=0)
        for i in range(1, 7):
            self.daily.append(DailyWeather(d + datetime.timedelta(days=i)))

        self.hourly = []
        d = self.current_weather.dt.replace(minute=0, second=0)
        for i in range(1, 25):
            self.hourly.append(HourlyWeather(d + datetime.timedelta(hours=i)))

        self.news = News()

    def moon_phase(self):
        """Get the current moon phase.

        Returns:
            A string, one of four possible moon phases.
        """
        return (
            'New Moon',
            'First Quarter',
            'Full Moon',
            'Last Quarter',
            'New Moon'
        )[int(float(self.astral.moon_phase(date=self.dt) / 7.0))]

    def next_sunrise(self):
        """Get the next sunrise.

        Returns:
            A datetime.datetime object.
        """
        sun = self.astral_city.sun(date=self.dt)
        if self.sun['sunrise'] > self.dt:
            return self.sun['sunset']
        else:
            sun = self.astral_city.sun(
                date=self.dt + datetime.timedelta(days=1)
            )
            return self.sun['sunset']

    def next_sunset(self):
        """Get the next sunset.

        Returns:
            A datetime.datetime object.
        """
        sun = self.astral_city.sun(date=self.dt)
        if self.sun['sunset'] > self.dt:
            return self.sun['sunset']
        else:
            sun = self.astral_city.sun(
                date=self.dt + datetime.timedelta(days=1)
            )
            return self.sun['sunset']

    def asdict(self):
        """Return the forecast as a dict, for display in Jinja templates.

        Returns:
            A dict.
        """
        return {
            'current_weather': self.current_weather.asdict(),
            'daily':           [d.asdict() for d in self.daily],
            'hourly':          [h.asdict() for h in self.hourly],
            'news':            self.news.asdict()
        }


class Weather:
    historical_headers = load_historical_data_headers()
    historical_data = load_historical_data()

    def __init__(self, dt):
        """Constructor

        Args:
            dt (datetime.datetime)
        """
        self.dt = dt

    def as_of(self):
        """Get the most recent reading time from historical data.

        Returns:
            a string in YYYY-mm-ddTHH:MM:SS format. 
        """
        return datetime.datetime.strptime(
            self._get_historical('DATE'),
            '%Y-%m-%dT%H:%M:%S'
        ).strftime('%-I:%M%p')

    def carbon_count(self, temperature_increase):
        """Get an estimated carbon count in ppm for a temperature increase
        given in F, compared to current levels:
        http://dels.nas.edu/resources/static-assets/materials-based-on-reports/booklets/warming_world_final.pdf
        """
        carbon_counts = (410, 480, 550, 630, 700, 800, 900, 1000, 1200, 1400)
        return carbon_counts[temperature_increase]

    def dew_point(self):
        """Get the dew point.

        Returns:
            the dew point temperature as an integer in F. 
        """
        return int(self._get_historical('HourlyDewPointTemperature'))

    def heat_index(self):
        """Calculate the heat index: see
        https://en.wikipedia.org/wiki/Heat_index.

        Returns:
            a heat index temperature in F as an integer.
        """
        t = self.temperature()
        if t < 80:
            return None
        r = self.relative_humidity()
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

    def human_readable_datetime(self):
        raise NotImplementedError

    def relative_humidity(self):
        """Get the relative humidity.

        Returns:
            the relative humidity as an integer from 0 to 100. 
        """
        return int(self._get_historical('HourlyRelativeHumidity'))

    def sky_conditions(self):
        """Get sky conditions.

        These are recorded in the data in a string like:

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
        """
        conditions = {
           'CLR': 'clear sky',
           'FEW': 'few clouds',
           'SCT': 'scattered clouds',
           'BKN': 'broken clouds',
           'OVC': 'overcast'
        }
        matches = re.search(
            '([A-Z]{3}).*$',
            self._get_historical('HourlySkyConditions')
        )
        try:
            return conditions[matches.group(1)]
        except AttributeError:
            return self._get_historical('HourlySkyConditions')

    def temperature(self):
        """Get the dry bulb temperature ("the temperature")

        Returns:
            the temperature as an integer in F.
        """
        return int(self._get_historical('HourlyDryBulbTemperature'))

    def temperature_min(self):
        return self._temperature_summary('min')

    def temperature_mean(self):
        return self._temperature_summary('mean')

    def temperature_max(self):
        return self._temperature_summary('max')

    def visibility(self):
        return int(float(self._get_historical('HourlyVisibility')))

    def weather_type(self):
        """Get a description of the current weather. 

        Returns: 
            a string.
        """
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
        present_weather = self._get_historical('HourlyPresentWeatherType')
        for p in present_weather.split('|'):
            m = re.search('[A-Z]+', p)
            if m:
                types.add(weather_strings[m.group(0)])
        return ', '.join(list(types))

    def wind_direction_and_speed(self):
        d = int(self._get_historical('HourlyWindDirection'))
        if d == 0:
            return 'still'

        directions = ('N', 'NNE', 'NE', 'ENE', 'E', 'ESE', 'SE', 'SSE', 'S',
                      'SSW', 'SW', 'WSW', 'W', 'WNW', 'NW', 'NNW', 'N')
        i = int(round(float(d) / 22.5))
        direction = directions[i % 16]

        s = self._get_historical('HourlyWindSpeed')
        return '{}mph {}'.format(s, direction)

    def _get_closest_past_index(self, dt=None):
        """Find the closest past index represented in historical data for a
        given date/time string.

        Returns:
            an index (integer).
        """
        if not dt:
            dt = self.dt
        dt_string = dt.replace(year=2010).strftime('%Y-%m-%dT%H:%M:%S')
        f = self.historical_headers.index('DATE')
        i = len(self.historical_data) - 1
        while i >= 0:
            if self.historical_data[i][f] < dt_string:
                break
            i -= 1
        return i

    def _get_historical(self, field):
        """Get a single historical data point.

        Args:
            str field: the field name.

        Returns:
            the data as a string.
        """
        i = self._get_closest_past_index()
        f = self.historical_headers.index(field)
        while i > 0:
            if self.historical_data[i][f]:
                return self.historical_data[i][f]
            i -= 1
        return ''

    def _get_historical_daily_range(self, field):
        """Get a range of historical data points. 

        Args:
            str field: the field name.

        Returns:
            the data as a string.
        """
        start_of_day = self.dt.replace(hour=0, minute=0, second=0)
        i1 = self._get_closest_past_index(start_of_day)
        i2 = self._get_closest_past_index(
            start_of_day + datetime.timedelta(days=1)
        )
        f = self.historical_headers.index(field)
        return [self.historical_data[i][f] for i in range(i1, i2 + 1)]

    def _temperature_summary(self, summary_type):
        """Get the high temperature for the day.

        Args:
            str summary_type: one of 'min', 'max', 'mean'

        Returns:
            the high temperature as an integer in F.
        """
        temperatures = map(
            int,
            filter(
                bool,
                self._get_historical_daily_range('HourlyDryBulbTemperature')
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
        year = min_future_year
        while True:
            if self.dt.replace(year=year).weekday() == self.dt.weekday():
                return year
            year += 1

    def asdict(self):
        return {
            'as_of':                    self.as_of(),
            'human_readable_datetime':  self.human_readable_datetime(),
            'simulation_year':          self.future_year_with_same_weekday(2060),
            'carbon_count':             self.carbon_count(0),
            'dew_point':                self.dew_point(),
            'heat_index':               self.heat_index(),
            'relative_humidity':        self.relative_humidity(),
            'sky_conditions':           self.sky_conditions(),
            'temperature':              self.temperature(),
            'temperature_min':          self.temperature_min(),
            'temperature_mean':         self.temperature_mean(),
            'temperature_max':          self.temperature_max(),
            'visibility':               self.visibility(),
            'weather_type':             self.weather_type(),
            'wind_direction_and_speed': self.wind_direction_and_speed()
        }


class CurrentWeather(Weather):
    def human_readable_datetime(self):
        return self.dt.strftime('%A, %B %-d')

class DailyWeather(Weather):
    def human_readable_datetime(self):
        return self.dt.strftime('%a')

    def asdict(self):
        return {
            'as_of':                    self.as_of(),
            'dt':                       self.dt,
            'human_readable_datetime':  self.human_readable_datetime(),
            'temperature_min':          self.temperature_min(),
            'temperature_mean':         self.temperature_mean(),
            'temperature_max':          self.temperature_max(),
        }

class HourlyWeather(Weather):
    def human_readable_datetime(self):
        return self.dt.strftime('%-I%p')

    def asdict(self):
        return {
            'as_of':                    self.as_of(),
            'dt':                       self.dt,
            'human_readable_datetime':  self.human_readable_datetime(),
            'temperature':              self.temperature(),
        }

class Sunrise(Weather):
    def human_readable_datetime(self):
        raise NotImplementedError


class Sunset(Weather):
    def human_readable_datetime(self):
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

    def asdict(self):
        return {}
