"""Provides a Flight object which represents the log of a single flight"""
import datetime
from math import radians, sin, cos, asin, sqrt


def lat_to_degrees(lat):
    """Convert an IGC-spec lattitude string to degrees

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


def haversine(lon1, lat1, lon2, lat2):
    """
    Calculate the great circle distance between two points
    on the earth (specified in decimal degrees)
    """
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


class Flight(object):
    """A single flight"""
    def __init__(self, igcfile=None):
        self._crunched = False
        self.optionalrecords = {}
        self.parsewarnings = []
        self.fixrecords = []
        self.auxdata = {}
        self.date = None

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
        self.auxdata['flightrecorder'] = line[1:]

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
        self.auxdata['glidertype'] = line[11:]

    def _logline_i(self, line):
        """I RECORD - EXTENSIONS TO THE FIX B RECORD

        Defines which optional records will be contained in each B record

        The record defines exactly how many bytes each optional field will take
        """
        num = int(line[1:3])
        for i in xrange(num):
            # Each optional record definition is 7 bytes
            field = line[3+7*i:10+7*i]
            opt_record_name = field[4:7]
            startbyte = int(field[0:2])-1
            endbyte = int(field[2:4])
            self.optionalrecords[opt_record_name] = (startbyte, endbyte)

    def _logline_b(self, line):
        """B RECORD - FIX

        The actual during-flight meat and potatoes: a GPS fix record.
        Also contains any optional fields defined in the I record
        """
        timestamp = line[1:7]
        time = datetime.time(
            int(timestamp[0:2]),
            int(timestamp[2:4]),
            int(timestamp[4:6]),
            0, None)

        # TODO WIP

        raise Exception("Work in progress")

        try:
            date = self.fixrecords[-1].datetime.date
        except IndexError:
            date = self.datetime

        self.fixrecords.append({
            'timestamp': line[1:7],
            'latitude':  lat_to_degrees(line[7:15]),
            'longitude': lon_to_degrees(line[15:24]),
            'avflag':    line[24:25] == "A",
            'pressure':  int(line[25:30]),
            'alt_gps':   int(line[30:35]),
        })
        # Grab all of the optional fields as defined by the I record
        for key, record in self.optionalrecords.iteritems():
            optionalfield = line[record[0]:record[1]]
            self.fixrecords[-1]['opt_' + key.lower()] = optionalfield

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
    def __init__(self, line_text, msg="", line_num=0):
        super(IGCError, self).__init__()
        self.line_text = line_text
        self.msg = msg
        self.line_num = line_num

    def __str__(self):
        msg = "Error parsing IGC file at line {line_num}: \"{msg}\""
        return msg.format(
            line_num=self.line_num, msg=self.msg, line_text=self.line_text)
