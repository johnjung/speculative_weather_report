import curses
import datetime
import time
from speculative_weather_report import Forecast, News

def main(stdscr):
    f = Forecast(datetime.datetime.now()).asdict()

    # Hide cursor, set up color. 
    curses.curs_set(0)
    curses.start_color()
    curses.use_default_colors()
    curses.init_pair(1, 15, 0)

    # Simulation date.
    sim_date_str = '{}, {}'.format(
        f['current_weather']['human_readable_datetime'],
        f['current_weather']['simulation_year']
    ).center(curses.COLS)
    stdscr.addstr(1, 0, sim_date_str, curses.color_pair(1))

    # Current weather as-of.
    weather_as_of_str = '-CURRENT WEATHER AS OF {}-'.format(
        f['current_weather']['as_of']
    ).center(curses.COLS)
    stdscr.addstr(3, 0, weather_as_of_str, curses.color_pair(1))

    # Sky conditions.
    sky_conditions_str = '{}, {}. Wind {}.'.format(
        f['current_weather']['sky_conditions'],
        f['current_weather']['weather_type'],
        f['current_weather']['wind_direction_and_speed']
    ).center(curses.COLS)
    stdscr.addstr(5, 0, sky_conditions_str, curses.color_pair(1))

    # Your hourly forecast.
    str = '-YOUR HOURLY FORECAST-'.center(curses.COLS)
    stdscr.addstr(11, 0, str, curses.color_pair(1))

    str = ''.join([' 73   75   76   77   77   77   74   71   68   66   65   65'.center(curses.COLS),
                   '4PM  5PM  6PM  7PM  8PM  9PM 10PM 11PM 12AM  1AM  2AM  3AM'.center(curses.COLS),
                   ''.center(curses.COLS),
                   ' 64   65   67   69   69   72   76   72   76   76   76   77'.center(curses.COLS),
                   '4AM  5AM  6AM  7AM  8AM  9AM 10AM 11AM 12PM  1PM  2PM  3PM'.center(curses.COLS)])
    stdscr.addstr(13, 0, str, curses.color_pair(1))

    # Your daily forecast.
    str = '-YOUR DAILY FORECAST-'.center(curses.COLS)
    stdscr.addstr(19, 0, str, curses.color_pair(1))

    str = ''.join(['       low temperature:    62    58    62    61    66    63'.center(curses.COLS),
                   '      mean temperature:    69    67    72    78    71    73'.center(curses.COLS),
                   '      high temperature:    77    78    86    90    80    84'.center(curses.COLS),
                   '                          Mon   Tue   Wed   Thu   Fri   Sat'.center(curses.COLS)])
    stdscr.addstr(21, 0, str, curses.color_pair(1))
    stdscr.refresh()

    # News ticker.
    news_str = (' ' * curses.COLS).join([''] + News().get_news())
    news_pad = curses.newpad(1, len(news_str) + curses.COLS)
    news_pad.addstr(news_str, curses.color_pair(1))

    x = 0
    while True:
        news_pad.refresh(0, x, curses.LINES-1, 0, curses.LINES, curses.COLS-1) 
        time.sleep(0.08)
        x += 1
        if x >= len(news_str):
          x = 0

curses.wrapper(main)
