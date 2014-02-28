IGC2CSV
=======
Reads an IGC file (a flight log used very commonly in hang gliding and paragliding) and spits out a CSV file with the flight data.

The intention is to make it much easier to look at the flight data in a program like Microsoft Excel without having to write your own parser.

The CSV output also has a bunch of data derived from the data, allowing quick and easy access to stats like distance traveled, per-second climb rate, total distance climbed, etc. Again, the idea here is to be able to pull this data in to Excel and start graphing it immediately without the need to do a bunch of formula work to get at the interesting statistics.


DashWare
========
Another purpose of this program is to put your flight logs in to a format that DashWare can understand, making it possible to create telemetry overlays on your flight videos.

[Example](http://www.youtube.com/watch?v=KKlZ1oOEYNI&hd=1)

DashWare supports a variety of formats natively, but IGC is not one of them. The included DashWare DataProfile works alongside the output of IGC2CSV to give you access to all of your flight data, *including True Airspeed if your variometer supports it.*
