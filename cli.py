#!/usr/bin/env python
'''Usage:
    ./cli.py weather
    ./cli.py load_data <csv_file>
    ./cli.py get_field <field>
'''

import datetime
import sqlite3
import sys

from docopt import docopt
from speculative_weather_report import CurrentWeather, DailyWeather, \
                                       Forecast, HourlyWeather, News, \
                                       Sunrise, Sunset, Weather

def print_weather(f):
    sys.stdout.write(
        '\n{:^60}\n'.format(
            '{}, {}'.format(
                f['current_weather']['human_readable_datetime'],
                f['current_weather']['simulation_year']
            )
        )
    )
    
    sys.stdout.write(
        '\n{:^60}\n'.format(
            '-CURRENT WEATHER AS OF {}-'.format(
                f['current_weather']['as_of']
            )
        )
    )
    
    sys.stdout.write(
        '\n{:^60}\n\n'.format(
            '{}, {}. Wind {}.'.format(
                f['current_weather']['sky_conditions'],
                f['current_weather']['weather_type'],
                f['current_weather']['wind_direction_and_speed']
            )
        )
    )
    
    sys.stdout.write(
        '{:>20}: {:<7}\n'.format(
            'Current Temp',
            f['current_weather']['temperature']
        )
    )
    
    sys.stdout.write(
        '{:>20}: {:<7} {:>20}: {:<7}\n'.format(
            'High',
            f['current_weather']['temperature_max'],
            'Rel. Humidity',
            f['current_weather']['relative_humidity']
        )
    )
    
    sys.stdout.write(
        '{:>20}: {:<7} {:>20}: {:<7}\n'.format(
            'Low',
            f['current_weather']['temperature_min'],
            'Carbon Count',
            f['current_weather']['carbon_count']
        )
    )
    
    sys.stdout.write('\n{:^60}\n\n'.format('-YOUR HOURLY FORECAST-'))
    
    for h in f['hourly'][:12]:
        sys.stdout.write('{:>4} '.format(h['temperature']))
    sys.stdout.write('\n')
    for h in f['hourly'][:12]:
        sys.stdout.write('{:>4} '.format(h['human_readable_datetime']))
    sys.stdout.write('\n\n')
    
    for h in f['hourly'][12:]:
        sys.stdout.write('{:>4} '.format(h['temperature']))
    sys.stdout.write('\n')
    for h in f['hourly'][12:]:
        sys.stdout.write('{:>4} '.format(h['human_readable_datetime']))
    sys.stdout.write('\n')
    
    sys.stdout.write('\n{:^60}\n\n'.format('-YOUR DAILY FORECAST-'))
    
    sys.stdout.write('{:>23}'.format('low temperature:'))
    for d in f['daily']:
        sys.stdout.write('{:>6}'.format(d['temperature_min']))
    sys.stdout.write('\n')
    sys.stdout.write('{:>23}'.format('mean temperature:'))
    for d in f['daily']:
        sys.stdout.write('{:>6}'.format(d['temperature_mean']))
    sys.stdout.write('\n')
    sys.stdout.write('{:>23}'.format('high temperature:'))
    for d in f['daily']:
        sys.stdout.write('{:>6}'.format(d['temperature_max']))
    sys.stdout.write('\n')
    sys.stdout.write('{:>23}'.format(''))
    for d in f['daily']:
        sys.stdout.write('{:>6}'.format(d['human_readable_datetime']))
    sys.stdout.write('\n\n')

if __name__=='__main__':
    arguments = docopt(__doc__)

    f = Forecast(datetime.datetime.now()).asdict()
    if arguments['load_data']:
        conn = sqlite3.connect('weather.db')
        c = conn.cursor()
        '''
        STATION - always a number. 
        DATE    - alwys same format. 
        '''
        pass
    elif arguments['get_field']:
        pass
    elif arguments['weather']:
        print_weather(f)
