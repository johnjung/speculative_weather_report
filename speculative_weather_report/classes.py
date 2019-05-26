import astral
import csv
import datetime
import math
import os
import random
import re
import statistics


def load_historical_data_headers():
    """Load the headers for historical weather data."""
    with open(os.path.dirname(os.path.realpath(__file__)) + '/../data/1711054.csv') as f:
        reader = csv.reader(f)
        return next(reader, None)


def load_historical_data():
    """Load historical weather data."""
    with open(os.path.dirname(os.path.realpath(__file__)) + '/../data/1711054.csv') as f:
        reader = csv.reader(f)
        next(reader, None)
        historical_data = []
        for row in reader:
            historical_data.append(row)
        return historical_data


class Forecast:
    """Contains the display elements of a speculative weather forecast.

    Notes:
        This display creates a fictional future weather forecast from historical
        weather data. It does this using three different dates and two different
        places. To start, the current date and location let us calculate the day
        of week, sunrise time, sunset time, and other events like high tides or
        eclipses.

        An alternate location allows the display to show historical weather data
        from a place with different climate. For example, on May 1st of this
        year in Chicago, Illinois, the forecast might display weather data from
        May 1st, 2010 in Austin, Texas. Using historical data gives us realistic
        looking data without having to do any weather modeling.

        Finally, the forecast displays a year in the future where the day of
        week (e.g. Tuesday) matches the current day of the week. The forecast
        also includes a news feed and advertisements, to explore the context
        around the weather. 

        This object is designed to be instantiated once for each weather
        forecast display.
    """

    def __init__(self, dt):
        """constructor.

        Creates a new Forecast object, and instantiates Weather objects to
        display the current weather along with daily and hourly forecasts, as
        well objects to display the news and advertisements.

        Args:
            dt (datetime.datetime): the current datetime, i.e.
            datetime.datetime.now()
        """
        self.dt = dt
        self.astral = astral.Astral()
        self.astral_city = 'Chicago'

        self.current_weather = CurrentWeather(dt)

        self.daily = []
        d = self.current_weather.dt.replace(hour=0, minute=0, second=0)
        for i in range(1, 7):
            self.daily.append(
                DailyWeather(
                    d + datetime.timedelta(days=i)
                )
            )

        self.hourly = []
        d = self.current_weather.dt.replace(minute=0, second=0)
        for i in range(1, 25):
            self.hourly.append(
                HourlyWeather(d + datetime.timedelta(hours=i))
            )

        self.news = News()

    def moon_phase(self):
        """Get the current moon phase.

        Returns:
            str: One of four possible moon phases.
        """
        return (
            'New Moon',
            'First Quarter',
            'Full Moon',
            'Last Quarter',
            'New Moon'
        )[int(float(self.astral.moon_phase(date=self.dt) / 7.0))]

    def next_sunrise(self):
        """sunrise.

        Returns:
            datetime.datetime: the time of the next sunrise.
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
        """sunset.

        Returns:
            datetime.datetime: the time of the next sunset.
        """
        sun = self.astral_city.sun(date=self.dt)
        if self.sun['sunset'] > self.dt:
            return self.sun['sunset']
        else:
            sun = self.astral_city.sun(
                date=self.dt + datetime.timedelta(days=1)
            )
            return self.sun['sunset']

    def next_high_tide(self):
        """high tide.

        Returns:
            datetime.datetime: the time of the next high tide.
        """
        raise NotImplementedError

    def next_low_tide(self):
        """low tide.

        Returns:
            datetime.datetime: the time of the next low tide.
        """
        raise NotImplementedError

    def next_partial_solar_eclipse(self):
        """partial solar eclipse.

        Returns:
            datetime.datetime: the time of the next partial solar eclipse.
        """
        raise NotImplementedError

    def next_total_solar_eclipse(self):
        """total solar eclipse.

        Returns:
            datetime.datetime: the time of the next total solar eclipse.
        """
        raise NotImplementedError

    def next_transit_of_mercury(self):
        """transit of mercury.

        Returns:
            datetime.datetime: the time of the next transit of Mercury.
        """
        raise NotImplementedError

    def next_transit_of_venus(self):
        """transit of Venus.

        Returns:
            datetime.datetime: the time of the next transit of Venus.
        """
        raise NotImplementedError

    def asdict(self):
        """get the forecast as a dict, for display in Jinja templates.

        Returns:
            dict: a dictionary containing the current weather, daily and hourly
            weather forecasts and astronomical events, news and advertisements.
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
            str: the date and time of the most recent weather data reading in
            YYYY-mm-ddTHH:MM:SS format. 
        """
        return datetime.datetime.strptime(
            self._get_historical('DATE'),
            '%Y-%m-%dT%H:%M:%S'
        ).strftime('%-I:%M%p')

    def carbon_count(self, temperature_increase):
        """Get an estimated carbon count for a given temperature increase.

        Args:
            temperature_increase (int): in Fahrenheit, starting from 0.

        Notes:
            This is a very rough estimate based on the following document:
            http://dels.nas.edu/resources/static-assets/
            materials-based-on-reports/booklets/warming_world_final.pdf

        Returns:
            int: the carbon count.
        """
        carbon_counts = (410, 480, 550, 630, 700, 800, 900, 1000, 1200, 1400)
        return carbon_counts[temperature_increase]

    def dew_point(self):
        """Get the dew point.

        Returns:
            int: the dew point temperature in Fahrenheit.
        """
        return int(self._get_historical('HourlyDewPointTemperature'))

    def heat_index(self):
        """Calculate the heat index: see
        https://en.wikipedia.org/wiki/Heat_index.

        Returns:
            int: a heat index temperature in Fahrenheit.
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
        """Get a human readable datetime string for this object.

        Raises:
            NotImplementedError: Implement this method in subclasses.
        """
        raise NotImplementedError

    def relative_humidity(self):
        """Get the relative humidity.

        Returns:
            int: the relative humidity from 0 to 100.
        """
        return int(self._get_historical('HourlyRelativeHumidity'))

    def sky_conditions(self):
        """Get sky conditions.

        Notes:
            These are recorded in the data in a string like:
            FEW:02 70 SCT:04 200 BKN:07 250
 
            Although this data field is often blank, very often zero or more
            data chunks in the following format will be included:
            [A-Z]{3}:[0-9]{2} [0-9]{2}

            The three letter sequence indicates cloud cover according to the
            dict below. The two digit sequence immediately following indicates
            the coverage of a layer in oktas (i.e. eigths) of sky covered. The
            final three digit sequence describes the height of the cloud layer,
            in hundreds of feet: e.g., 50 = 5000 feet. It is also possible for
            this string to include data that indicates that it was not possible
            to observe the sky because of obscuring phenomena like smoke or fog. 

            The last three-character chunk provides the best summary of current
            sky conditions.

        Returns:
            str: current sky conditions, e.g. 'clear sky'
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
            int: the temperature in Fahrenheit.
        """
        return int(self._get_historical('HourlyDryBulbTemperature'))

    def temperature_min(self):
        """Get the minimum daily temperature.

        Returns:
            int: the temperature in Fahrenheit.
        """
        return self._temperature_summary('min')

    def temperature_mean(self):
        """Get the mean daily temperature.

        Returns:
            int: the temperature in Fahrenheit.
        """
        return self._temperature_summary('mean')

    def temperature_max(self):
        """Get the maximum daily temperature.

        Returns:
            int: the temperature in Fahrenheit.
        """
        return self._temperature_summary('max')

    def visibility(self):
        """Get the visibility.

        Returns:
            int: visibility in miles.
        """
        return int(float(self._get_historical('HourlyVisibility')))

    def weather_type(self):
        """Get the type of weather.

        Returns: 
            str: a description of the current weather, e.g. 'fog'
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
        """Get the wind direction and speed.

        Returns:
            str: e.g., '13mph SW'
        """
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

        Args:
            dt (datetime.datetime): A datetime to look up other than self.dt.

        Returns:
            int: an index (record number) in the historical data.
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
        """Get a single historical data point. If the current data point is
        blank, the function searches backwards for the last available data.

        Args:
            field (str): the field name.

        Returns:
            str: the data.
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
            field (str): the field name.

        Returns:
            str: the data.
        """
        start_of_day = self.dt.replace(hour=0, minute=0, second=0)
        i1 = self._get_closest_past_index(start_of_day)
        i2 = self._get_closest_past_index(
            start_of_day + datetime.timedelta(days=1)
        )
        f = self.historical_headers.index(field)
        return [self.historical_data[i][f] for i in range(i1, i2 + 1)]

    def _temperature_summary(self, summary_type):
        """Get a temperature summary for the day.

        Args:
            summary_type (str): one of 'min', 'max', 'mean'

        Returns:
            int: the temperature summary in Fahrenheit.
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
        """Get a future year with the same weekday (e.g. "Tuesday") as self.dt.

        Args:
            min_future_year (int): year to start checking for matching weekdays.

        Returns:
            int: the future year. 
        """
        year = min_future_year
        while True:
            if self.dt.replace(year=year).weekday() == self.dt.weekday():
                return year
            year += 1

    def asdict(self):
        """Get this object as a dict, for rendering in Jinja templates.

        Returns:
            dict: template data.
        """
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
        """Get a human readable date and time for the current weather, e.g.
        'Tuesday, May 1.'

        Returns:
            str: the current time.
        """
        return self.dt.strftime('%A, %B %-d')

class DailyWeather(Weather):
    def human_readable_datetime(self):
        """Get a human readable date and time for each cell in a daily weather
        forecast, e.g. 'Tuesday'

        Returns:
            str: the weekday.
        """
        return self.dt.strftime('%a')

    def asdict(self):
        """Get information for an daily weather forecast cell.

        Returns:
            dict: forecast data.
        """
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
        """Get a human readable date and time for each cell in an hourly
        forecast, e.g. '2PM'

        Returns:
            str: the time.
        """
        return self.dt.strftime('%-I%p')

    def asdict(self):
        """Get information for an hourly weather forecast cell.

        Returns:
            dict: forecast data.
        """
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
        # short headline, source note.
        news = (("Troubling Trend Since 2020s for Great Lakes. Superior, Huron and Erie have seen the greatest declines.",
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

        # short headline, story body, source URL. 
        # stories are lightly modified, mostly changing the names of places. 
        news = [("""Two Killed as Tornado Strikes Stillwater, Oklahoma;
                    Apparent Tornado Leaves Swath of Damage in Norman.""",
                 """A tornado tore through Stillwater, Oklahoma last night,
                    touching down at approximately 10:20pm on the leading edge
                    of a squall line of severe thunderstorms. The Western Value
                    Inn at 51 and 177 was destroyed. Image from the scene
                    showed emergency crews sifting through rubble after part of
                    the motel's second story collapsed into a pile of debris
                    strewn about the first floor and parking lot. Two deaths
                    have been confirmed by county emergency management. Another
                    apparent tornado produced damage in the Norman area after
                    midnight.""",
                 "https://weather.com/news/news/2019-05-26-oklahoma-tornadoes-el-reno-sapulpa"),
                ("""Powerful 8.0 Magnitude Earthquake Strikes north-central
                    Bolivia.""",
                 """An 8.0 magnitude earthquake shook north-central Bolivia
                    yesterday morning, acording to the U.S. Geological Survey.
                    There were no immediate reports of deaths or major damage.
                    The quake, at a moderate depth of 71 miles, strike at 2:41
                    a.m., 50 miles southeast of Sorata. There were no immediate
                    reports of deaths. The mayor of Sorata told local radio
                    station RPP that the quake was felt very strongly there,
                    but it was not possible to move around the town because of
                    the darkness. A number of old houses collapsed, and the
                    electricity was cut, according to the National Emergency
                    Operations Center.""",
                 "https://weather.com/news/news/2019-05-26-earthquake-north-central-peru-may"),
                ("",
                 """Our primary journalistic mission is to report on breaking
                    weather news and the environment. This story does not
                    necessarily represent the position of our parent company.""",
                 ""),
                ("""Has Government Turned Us Into a Nation of Makers and
                    Takers?""",
                 """In a recent article produced by the Tax Policy Center, tax
                    analyst Smithson Roberts reports that 43% of Americans
                    won't pay federal income taxes this year. Roberts, a former
                    deputy assistant director for the Congressional Budget
                    Office, also states that "many commentators" have twisted
                    such statistics to suggest "that nearly half of all
                    households paid no tax at all when, in fact, nearly
                    everyone pays something." Roberts is correct that the
                    federal income tax is just one of many taxes, and hence, it
                    is misleading to ignore other taxes when discussing makers
                    and takers. However, he ignores another crucial aspect of
                    this issue, which is that the person who pays $1,000 in
                    taxes and receives $10,000 in government benefits is a
                    taker on the net. Even though this person pays
                    "something", as Roberts notes, he receives far more from
                    the government than he pays in taxes.""",
                 "https://www.justfactsdaily.com/has-government-turned-us-into-a-nation-of-makers-and-takers/"),
                ("",
                 """The Intergovernmental Panel on Climate Change (IPCC) is 
                    "the leading international body for the assessment of
                    climate change," and its "work serves as the key basis
                    for climate policy decisions made by governments throughout
                    the world. The IPCC states: "To determine whether current
                    warming is unusual, it is essential to place it in the
                    context of longer-term climate variability." The first
                    IPCC report stated that "some of the global warming since
                    1850 could be a recovery from the Little Ice Age rather
                    than a direct result of human activities. So it is
                    important to recognize the natural variations of climate
                    are appreciable and will modulate any future changes
                    induced by man." The second IPCC report stated that "data
                    prior to 1400 are too sparse to allow the reliable estimate
                    of global mean temperature" and show a graph of
                    proxy-derived temperatures for Earth's Northern Hemisphere
                    from 1400 onward." The third IPCC report stated that the
                    latest proxy studies indicate "the conventional terms of
                    'Little Ice Age' and 'Medieval Warm Period' appear to have
                    limited utility in describing...global mean temperature
                    change in the past centuries.""",
                  "https://www.justfacts.com/globalwarming.asp")]

        random.shuffle(news) 
        output = []
        for n in news:
            output.append(re.sub(r'\s+', ' ', n[1]).strip())
        return output

    def asdict(self):
        return {}
