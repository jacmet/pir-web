#!/usr/bin/env python

import datetime
import dateutil.parser
import email.message
import json
import os.path
import requests
import smtplib
import string
import sys

from requests.auth import HTTPDigestAuth

# minimum amount of activity before a day is considered "active"
MIN_ACTIVITY = 3

# email template for when activity has been detected
ACT_SUBJECT = '${date}: Activity in ${place}'
ACT_BODY = """
Hi,

Activity has been detected ${today} times today in ${place}.

For details, see ${url}

--
Motion
"""

# and when no more
IDLE_SUBJECT = '${date}: No more activity in ${place}'
IDLE_BODY = """
Hi,

No more activity has been detected in ${place} (yesterday ${yesterday} times).

For details, see ${url}

---
Motion
"""


def to_iso8601(d):
    """ Convert date to is8601 UTC timeformat """
    return datetime.datetime.combine(d, datetime.time.min).isoformat() + 'Z'


def has_activity(d):
    """ Does day have motion activity? """
    return d >= MIN_ACTIVITY


def send_email(from_addr, to_addr, subject, body):
    """ Send email """
    msg = email.message.Message()
    msg['From'] = from_addr
    msg['To'] = to_addr
    msg['Subject'] = subject
    msg.set_payload(body)

    smtp = smtplib.SMTP('localhost')
    smtp.sendmail(msg['From'], [msg['To']], msg.as_string())
    smtp.quit()
    print str(msg)


if len(sys.argv) != 2:
    sys.stderr.write('Usage: %s <place>\n' % sys.argv[0])
    sys.exit(1)

place = sys.argv[1]

try:
    config_file = os.path.expanduser('~/.pirweb.conf')
    config = json.loads(open(config_file).read())
except Exception:
    sys.stderr.write('Error reading config, check %s\n' % config_file)
    sys.exit(1)

for key in ['url', 'auth_user', 'auth_password', 'mail_from', 'mail_to']:
    if key not in config:
        sys.stderr.write('"%s" key not found in config, check %s\n' %
                         (key, config_file))
        sys.exit(2)

delta = datetime.timedelta(days=1)
today = datetime.date.today()
yesterday = today - delta
tomorrow = today + delta

auth = HTTPDigestAuth(config['auth_user'], config['auth_password'])
params = {
    'id': place,
    'start': to_iso8601(yesterday),
    'end': to_iso8601(tomorrow)
    }

motion = {}

req = requests.get(config['url'] + '/events', params=params,
                   auth=auth, timeout=10)
for e in req.json():
    if e.get('allDay'):
        day = dateutil.parser.parse(e.get('start', '')).date()
        count = int(e.get('title', 0))
        motion[day] = count

vals = {
    'place': place,
    'yesterday': motion.get(yesterday, 0),
    'today': motion.get(today, 0),
    'url': config['url'],
    'date': today
    }

# new activity?
if not has_activity(vals['yesterday']) and has_activity(vals['today']):
    send_email(config['mail_from'], config['mail_to'],
               string.Template(ACT_SUBJECT).substitute(vals),
               string.Template(ACT_BODY).substitute(vals))

# no longer activity?
if has_activity(vals['yesterday']) and not has_activity(vals['today']):
    send_email(config['mail_from'], config['mail_to'],
               string.Template(IDLE_SUBJECT).substitute(vals),
               string.Template(IDLE_BODY).substitute(vals))
