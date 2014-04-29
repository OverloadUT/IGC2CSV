"""Provides a Flight object which represents the log of a single flight"""
import datetime
from math import radians, sin, cos, asin, sqrt


def lat_to_degrees(lat):
    """Convert an IGC-spec latitude string to degrees

    IGC files store latitude as DDMMmmmN
    """
    direction = {'N': 1, 'S': -1}
    degrees = int(lat[0:2])
    minutes = int(lat[2:7])
    minutes /= 1000.
    directionmod = direction[lat[7]]
    return (degrees + minutes/60.) * directionmod


def lon_to_degrees(lon):
    """Convert an IGC-spec longitude string to degrees

    IGC files store longitude as DDDMMmmmN
    """
    direction = {'E': 1, 'W': -1}
    degrees = int(lon[0:3])
    minutes = int(lon[3:8])
    minutes /= 1000.
    directionmod = direction[lon[8]]
    return (degrees + minutes/60.) * directionmod


def haversine(fixone, fixtwo):
    """Calculate the great circle distance between two points
    on the earth (specified in decimal degrees)
    """
    try:
        lon1 = fixone['longitude']
        lat1 = fixone['latitude']
        lon2 = fixtwo['longitude']
        lat2 = fixtwo['latitude']
    except ValueError:
        raise TypeError("Requires 2 FixRecords")

    # convert decimal degrees to radians
    (lon1, lat1, lon2, lat2) = [radians(x) for x in [lon1, lat1, lon2, lat2]]
    # haversine formula
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a))
    # Earth's radius is 6367 km
    km = 6367 * c
    return km


def abs_distance(fixone, fixtwo):
    """Calculates the distance between two sets of latitude, longitude, and
    altitude, as a straight line"""
    try:
        alt1 = fixone['alt_gps']
        alt2 = fixtwo['alt_gps']
    except ValueError:
        raise TypeError("Requires 2 FixRecords")

    a = haversine(fixone, fixtwo)
    b = (alt1 - alt2) / 1000.  # convert meters to km
    c = sqrt(a**2. + b**2.)
    return c


class FixRecord(dict):
    """A single GPS fix record"""

    def __init__(self, *args, **kwargs):
        """Pass in a "prev" named parameter to define the record coming
        immediately before this one in a flight
        """
        dict.__init__(self, *args)
        self.prev = kwargs.get('prev')
        self.first = self.prev.first if self.prev is not None else self
        if self.prev:
            self.compute_deltas()

    def compute_deltas(self):
        """Compute the various delta values for convenient access"""
        prev = self.prev
        first = self.first

        # Time difference since previous record, in seconds
        self['time_delta'] = (self['datetime'] - prev['datetime']).seconds
        self['time_total'] = prev.get('time_total', 0) + self['time_delta']

        # Distance over the ground
        self['dist_delta'] = haversine(self, prev)
        self['dist_total'] = prev.get('dist_total', 0) + self['dist_delta']
        self['dist_from_start'] = haversine(self, first)

        # "True Distance" - the distance traveled through 3D space
        # relative to the Earth
        self['truedist_delta'] = abs_distance(self, prev)
        self['truedist_total'] = (
            prev.get('truedist_total', 0) + self['truedist_delta'])
        self['truedist_from_start'] = abs_distance(self, first)

        # Speed calculations
        self['groundspeed'] = self['dist_delta'] / self['time_delta']
        self['groundspeed_peak'] = max(
            self['groundspeed'],
            prev.get('groundspeed_peak', 0))
        self['truespeed'] = self['truedist_delta'] / self['time_delta']
        self['truespeed_peak'] = max(
            self['truespeed'],
            prev.get('truespeed_peak', 0))

        # Altitude and climb rates
        self['alt_delta'] = self['alt_gps'] - prev['alt_gps']
        self['climb_speed'] = self['alt_delta'] / self['time_delta']
        self['climb_total_abs'] = (
            prev.get('climb_total_abs', 0) + abs(self['alt_delta']))


class Flight(object):
    """A single flight"""
    def __init__(self, igcfile=None):
        self.optfields = {}
        self.parsewarnings = []
        self.fixrecords = []
        self.flightinfo = {}
        self.date = None
        self.filename = None

        if igcfile is not None:
            self.load_igc(igcfile)

    def load_igc(self, igcfile):
        """Parse an igc file to fill out this flight"""
        if type(igcfile) is not file:
            import os
            if not os.path.isfile(igcfile):
                raise IOError('igcfile not found')
            fileobj = open(igcfile, 'r')
        else:
            fileobj = igcfile

        self.filename = fileobj.name
        with fileobj:
            for line in fileobj:
                self._parseline(line)

    def _parseline(self, line):
        """Parse a single line of an IGC file and add its data"""
        line = line.strip()
        # The first character in an IGC file determines the type of record
        linetype = line[0]
        self._recordtypes[linetype](self, line)

    def _logline_a(self, line):
        """A RECORD - FR ID NUMBER

        The unique identifier of the flight recorder"""
        self.flightinfo['flightrecorder'] = line[1:]

    # H Records are headers that give one-time information
    # http://carrier.csi.cam.ac.uk/forsterlewis/soaring/igc_file_format/igc_format_2008.html#link_3.3
    def _logline_h(self, line):
        """Header records contain all manner of information about the flight

        Perhaps most important is the flight date
        """
        try:
            self._headertypes[line[1:5]](self, line[5:])
        except KeyError:
            self.parsewarnings.append(
                'Header type not implemented: {headertype} Full line: {line}'
                .format(headertype=line[1:5], line=line))

    def _logline_h_flightdate(self, line):
        """Flight date of the first B record
        Date format: DDMMYY
        """
        try:
            flightdate = datetime.date(
                int(line[4:6])+2000,
                int(line[2:4]),
                int(line[0:2]))
        except ValueError:
            raise IGCError(line_text=line, msg="Bad date")

        self.date = flightdate

    def _logline_h_glidertype(self, line):
        """The glider type"""
        self.flightinfo['glidertype'] = line[11:]

    def _logline_i(self, line):
        """I RECORD - EXTENSIONS TO THE FIX B RECORD

        Defines which optional records will be contained in each B record

        The record defines exactly how many bytes each optional field will take
        """
        num = int(line[1:3])
        for i in xrange(num):
            # Each optional record definition is 7 bytes
            field = line[3+7*i:10+7*i]
            opt_record_name = field[4:7].lower()
            startbyte = int(field[0:2])-1
            endbyte = int(field[2:4])
            self.optfields[opt_record_name] = (startbyte, endbyte)

    def _logline_b(self, line):
        """B RECORD - FIX

        The actual during-flight meat and potatoes: a GPS fix record.
        Also contains any optional fields defined in the I record
        """

        if self.date is None:
            errormsg = ("Reached a B record without the flight date "
                        "being declared")
            raise IGCError(msg=errormsg, line_text=line)

        timestamp = line[1:7]
        time = datetime.time(
            int(timestamp[0:2]),
            int(timestamp[2:4]),
            int(timestamp[4:6]),
            0, None)

        try:
            date = self.fixrecords[-1]['datetime'].date()
            if self.fixrecords[-1]['datetime'].time() > time:
                # If this record's time is seemingly earlier than the previous
                # record's, it means we've moved to the next day.
                date += datetime.timedelta(days=1)
        except IndexError:
            # There is no previous record, so this record's date is the
            # flight start date
            date = self.date

        mydatetime = datetime.datetime.combine(date, time)

        newrecord = {
            'datetime':       mydatetime,
            'latitude':       lat_to_degrees(line[7:15]),
            'longitude':      lon_to_degrees(line[15:24]),
            'avflag':         line[24:25] == "A",
            'pressure':       int(line[25:30]),
            'alt_gps':        int(line[30:35]),
            'optfields': {},
        }

        for key, record in self.optfields.iteritems():
            # Grab all of the optional fields as defined by the I record
            optionalfield = line[record[0]:record[1]]
            newrecord['optfields'][key.lower()] = optionalfield

        try:
            prevrecord = self.fixrecords[-1]
        except IndexError:
            prevrecord = None

        self.fixrecords.append(FixRecord(newrecord, prev=prevrecord))

    def _logline_ignore(self, line):
        """An ingnored IGC record, such as the "G" checksum records"""
        pass

    def _logline_not_implemented(self, line):
        """An IGC record that is not yet implemented"""
        self.parsewarnings.append(
            "Record Type {recordtype} not implemented: {fullline}"
            .format(recordtype=line[0:1], fullline=line))

    _recordtypes = {
        'A': _logline_a,
        'B': _logline_b,
        'C': _logline_not_implemented,
        'D': _logline_not_implemented,
        'E': _logline_not_implemented,
        'F': _logline_not_implemented,
        'G': _logline_ignore,  # Checksum at end of file
        'H': _logline_h,
        'I': _logline_i,
        'J': _logline_not_implemented,
        'K': _logline_not_implemented,
        'L': _logline_not_implemented,
    }

    _headertypes = {
        'FDTE': _logline_h_flightdate,
        'FGTY': _logline_h_glidertype,
    }


class Error(Exception):
    """Base class for exceptions in this module."""
    pass


class IGCError(Error):
    """Raised when an error occurs while parsing an IGC file

    Attributes:
        line_text -- The line itself that caused the error
        msg  -- explanation of the error
        line_num -- The line number of the igc file where the error occurred
    """
    def __init__(self, line_text="", msg="", line_num=0):
        super(IGCError, self).__init__()
        self.line_text = line_text
        self.msg = msg
        self.line_num = line_num

    def __str__(self):
        msg = "Error parsing IGC file at line {line_num}: \"{msg}\""
        return msg.format(
            line_num=self.line_num, msg=self.msg, line_text=self.line_text)
