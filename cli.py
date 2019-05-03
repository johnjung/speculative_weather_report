import datetime

from weather import CurrentWeather, DailyWeather, Forecast, HourlyWeather, \
                    News, Sunrise, Sunset, Weather

f = Forecast(datetime.datetime.now())
print(f.asdict())
