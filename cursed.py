import curses
import datetime
import time
from speculative_weather_report import Forecast, News

def main(stdscr):
    curses.start_color()
    curses.use_default_colors()
    curses.init_pair(1, 15, 0)

    f = Forecast(datetime.datetime.now()).asdict()

    # Simulation date.
    sim_date_str = '\n{:^60}\n'.format(
        '{}, {}'.format(
            f['current_weather']['human_readable_datetime'],
            f['current_weather']['simulation_year']
        )
    )
    #sim_date_win = curses.newwin(1, curses.COLS, curses.LINES - 1, 0)
    #stdscr.addstr(curses.LINES - 1, 0, sim_date_str, curses.color_pair(1))
    stdscr.addstr(5, 0, 'hello', curses.color_pair(1))

    # news ticker.
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
