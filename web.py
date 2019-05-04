import datetime

from weather import CurrentWeather, DailyWeather, Forecast, HourlyWeather, \
                    News, Sunrise, Sunset, Weather

from flask import Flask, render_template
app = Flask(__name__)
app.debug = True

@app.route('/', methods=['GET'])
def index():
    f = Forecast(datetime.datetime.now())
    return render_template('weather.html', **f.asdict())
