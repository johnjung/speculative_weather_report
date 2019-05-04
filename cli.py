import datetime

from weather import CurrentWeather, DailyWeather, Forecast, HourlyWeather, \
                    News, Sunrise, Sunset, Weather

f = Forecast(datetime.datetime.now())
for k, v in f.asdict().items():
    if type(v) == dict:
        for k2, v2 in v.items():
            print('{}: {}'.format(k2, v2))
    elif type(v) == str:
        print('{}: {}'.format(k, v))
