from weather import CurrentWeather, DailyWeather, Forecast, HourlyWeather, \
                    News, Sunrise, Sunset, Weather

from flask import Flask, render_template
app = Flask(__name__)
app.debug = True
