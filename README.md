# Simple webui for visualizing motion detection on calendar widget


Client is a ESP8266 module with a PIR sensor running
[Sonoff-Tasmota](https://github.com/arendst/Sonoff-Tasmota), which is
configured to perform a HTTP GET whenever activity is detected by the
PIR sensor using a rule like:

```
Switchmode1 1
Switchtopic 0
Rule1 on switch1#state=1 do websend [<url>] /add/<id> endon
Rule1 1
```

See
[Wemos-D1-Mini-and-HC-SR501-PIR-Motion-Sensor](https://github.com/arendst/Sonoff-Tasmota/wiki/Wemos-D1-Mini-and-HC-SR501-PIR-Motion-Sensor)
for more info.


The server is written with [python-flask](http://flask.pocoo.org),
uses a sqlite database and [fullcalendar](https://fullcalendar.io) to
visualize the motion events on a calendar.

Lighttpd configuration looks something like:

```
  server.document-root = "/path/to/static"

  # fixup URLs for flask
  url.rewrite-once = (
    "^/static(.*)$" => "$1",
    "^/(events.*|add.*)$" => "/pirweb/$1"
  )

  fastcgi.server = ("/pirweb" =>
    ((
        "socket" => "/tmp/pirweb.sock",
        "bin-path" => "/path/to/pirweb.py",
        "check-local" => "disable",
        "max-procs" => 1
    ))
  )
```

Password protection (except for the /add endpoint as Tasmota doesn't support
authentication) can be done with something like:

```
  # auth required for everything except add
  auth.backend = "htdigest"
  auth.backend.htdigest.userfile = "/path/to/htdigest"

  $HTTP["url"] !~ "^/pirweb/add" {
    auth.require = ( "" =>
            (
            "method" => "basic",
            "realm" => "<realm>",
            "require" => "valid-user"
            )
    )
  }
```
