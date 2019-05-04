import datetime

from weather import CurrentWeather, DailyWeather, Forecast, HourlyWeather, \
                    News, Sunrise, Sunset, Weather

f = Forecast(datetime.datetime.now()).asdict()
for k, v in f['current_weather'].items():
    print('{:>24}: {}'.format(k, v))

print('')
print('Your hourly forecast')
print('')

for h in f['hourly']:
    for k, v in h.items():
        print('{:>24}: {}'.format(k, v))
    print('')

print('Your daily forecast')
print('')

for d in f['daily']:
    for k, v in d.items():
        print('{:>24}: {}'.format(k, v))
    print('')

