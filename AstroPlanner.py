from flask import Flask, render_template, request
from astropy.coordinates import SkyCoord, EarthLocation
from astropy.time import Time
from astroplan import Observer, FixedTarget, AltitudeConstraint, AirmassConstraint, AtNightConstraint
from astroplan.utils import time_grid_from_range
from astroplan.scheduling import Schedule, Transitioner, SequentialScheduler
import datetime
import numpy as np
import pytz
from pytz import timezone
from datetime.timezone import TimezoneInfo

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/schedule', methods=['POST'])
def schedule():
    # Get input data from form
    latitude = request.form['latitude']
    longitude = request.form['longitude']
    elevation = request.form['elevation']
    objects = request.form['objects'].split(',')
    start_date = request.form['start_date']
    end_date = request.form['end_date']
    start_time = request.form['start_time']
    end_time = request.form['end_time']
    alt_range_min = request.form['alt_range_min']
    alt_range_max = request.form['alt_range_max']
    az_range_min = request.form['az_range_min']
    az_range_max = request.form['az_range_max']

    print(start_date)
    print(end_date)

    start_date = datetime.datetime.strptime(start_date, '%Y-%m-%d').date()
    end_date = datetime.datetime.strptime(end_date, '%Y-%m-%d').date()

    # # Define observer location
    observer = Observer(latitude=latitude, longitude=longitude)

    print(observer)

    # Define observer location
    location = EarthLocation.from_geodetic(longitude, latitude, elevation)

    # Get timezone info from latitude and longitude
    tzinfo = TimezoneInfo.from_latitude_and_longitude(latitude, longitude)

    # Define observer with timezone info
    observer = Observer(location=location, timezone=tzinfo)

    # Define observing constraints
    constraints = [AltitudeConstraint(min=alt_range_min, max=alt_range_max),
                   AirmassConstraint(max=2),
                   AtNightConstraint.twilight_civil()]

    # Define targets
    targets = [FixedTarget.from_name(name) for name in objects]

    # Define time range
    time_range = Time([str(start_date), str(end_date)])

    # Get the EarthLocation object based on the user's input
    location = EarthLocation.from_geodetic(longitude, latitude, elevation)

    # Get the timezone at that location using timezone_at method
    timezone = location.timezone_name()

    # Create the pytz timezone object
    tz = pytz.timezone(timezone)

    # Define time grid
    time_resolution = datetime.timedelta(hours=1)
    observer_tz = timezone(observer.timezone)
    start_datetime = observer_tz.localize(
        datetime.datetime.combine(start_date, datetime.datetime.strptime(start_time, '%H:%M').time()))
    end_datetime = observer_tz.localize(
        datetime.datetime.combine(end_date, datetime.datetime.strptime(end_time, '%H:%M').time()))
    observing_time_range = (datetime.time(hour=start_datetime.hour, minute=start_datetime.minute),
                            datetime.time(hour=end_datetime.hour, minute=end_datetime.minute))
    observing_time_grid = time_grid_from_range(time_range, time_resolution=time_resolution,
                                               observer=observer,
                                               constraints=constraints,
                                               time_of_night=observing_time_range)

    # Get the observability table
    table = observer.constraint_table(targets, time_range=time_range, time_grid=observing_time_grid)

    # Get the visible and non-visible targets
    visible_objects = []
    nonvisible_objects = []

    for row in table:
        if row['ever observable']:
            visible_objects.append(row['target name'])
        else:
            nonvisible_objects.append(row['target name'])


    # Generate observing schedule
    observing_schedule = []
    for observation in SequentialScheduler(constraints).schedule(observer, targets, time_range,
                                                                time_grid=observing_time_grid):
        observing_schedule.append(observation)

    # Group observing schedule by date
    observing_schedule_by_date = {}
    for observation in observing_schedule:
        observing_date = observation['start_time'].datetime.date()
        if observing_date in observing_schedule_by_date:
            observing_schedule_by_date[observing_date].append(observation)
        else:
            observing_schedule_by_date[observing_date] = [observation]

    # Format observing schedule for display
    observing_schedule_display = []
    for observing_date, observations in observing_schedule_by_date.items():
        for observation in observations:
            observing_schedule_display.append({
                'date': observing_date,
                'name': observation['target'].name,
                'start_time': observation['start_time'].datetime.time(),
                'end_time': observation['end_time'].datetime.time(),
                'alt_range': f"{observation['target_altaz'].alt.deg:.1f} - {observation['target_altaz'].alt.deg + observation['target'].size.to('deg').value:.1f}",
                'az_range': f"{observation['target_altaz'].az.deg:.1f} - {(observation['target_altaz'].az.deg + 180) % 360:.1f}",
                'mag': observation['target'].magnitude,
            })

    # Render template with observing schedule data
    return render_template('schedule.html', observing_schedule=observing_schedule_display)




if __name__ == '__main__':
    app.run(debug=True)