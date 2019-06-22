#!/usr/bin/env python

import datetime
import dateutil.parser
import itertools
import os
import sqlite3
import sys
from flask import Flask, json, g, redirect, request, Response, url_for
from flup.server.fcgi import WSGIServer

project_dir = os.path.dirname(os.path.abspath(__file__))

# number of minutes in each event "block"
BLOCK_MINUTES = 30

# valid IDs
IDS = {
    'spain': 1,
    'denmark': 2
    }

app = Flask(__name__)


def init_db():
    with app.app_context():
        with get_db() as db:
            db.execute('create table if not exists events '
                       '(ts datetime not null, count integer not null, '
                       ' id integer, primary key (ts), unique (ts))')


def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(os.path.join(project_dir,
                                                        'db/pirweb.db'))
    db.row_factory = sqlite3.Row
    return db


@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()


def query_db(query, args=(), one=False):
    cur = get_db().execute(query, args)
    rv = cur.fetchall()
    cur.close()
    return (rv[0] if rv else None) if one else rv


def to_iso8601(d):
    """Convert datetime to is8601 UTC timeformat for fullcalendar"""
    return d.isoformat() + 'Z'


def to_color(count):
    colors = ['#fdf2f2', '#fbe2e1', '#f9d1cf', '#f6c0be', '#f4afad',
              '#f29e9b', '#f08d8a', '#ed7c79', '#eb6b67', '#e95b56',
              '#e74a45', '#e43933', '#e22822']
    return colors[min(max(count, 0), len(colors) - 1)]


def hour_entry(count, start):
    end = start + datetime.timedelta(minutes=BLOCK_MINUTES)
    return {
        'title': str(count),
        'start': to_iso8601(start),
        'end': to_iso8601(end),
        'color': to_color(count)
        }


def day_entry(count, start):
    day = datetime.datetime.combine(start, datetime.time.min)
    return {
        'title': str(count),
        'allDay': True,
        'rendering': 'background',
        'start': to_iso8601(day),
        'end': to_iso8601(day),
        'color': to_color(count)
        }


def to_day(row):
    """Return date (as dateutil.date) of row"""
    return dateutil.parser.parse(row['ts']).date()


def to_events(rows):
    """Convert db rows to fullcalendar events. Also calculate an
    'allday' event with the sum of all events for each day"""
    for day, events in itertools.groupby(rows, to_day):
        total = 0
        for e in events:
            start = dateutil.parser.parse(e['ts'])
            count = e['count']
            total += count
            yield hour_entry(count, start)

        yield day_entry(total, day)


@app.route("/")
def root():
    return redirect(url_for('static', filename='index.html'))


@app.route("/add/<id>")
def add(id):
    id = IDS[id]
    now = datetime.datetime.utcnow()
    block = now.minute - (now.minute % BLOCK_MINUTES)
    now = now.replace(minute=block, second=0, microsecond=0)
    try:
        with get_db() as db:
            db.execute('insert into events (ts,count,id) values (?, 1, ?)', [now, id])
    except sqlite3.IntegrityError:
        with get_db() as db:
            db.execute('update events set count=count+1 where "ts"=? and id=?', [now, id])

    return "Added"


@app.route("/events")
def events():
    id = IDS[request.args.get('id')]
    start = request.args.get('start', '')
    end = request.args.get('end', '')
    events = query_db('select * from events where ts >= datetime(?) '
                      'and ts < datetime(?) and id=? order by ts',
                      [start, end, id])
    return Response(json.dumps(list(to_events(events))),
                    mimetype='application/json')


if __name__ == "__main__":
    init_db()
    if 'debug' in sys.argv:
        app.run(debug=True)
    else:
        WSGIServer(app).run()
