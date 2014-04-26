import datetime


class flight:
    def __init__(self, igcfile):
        self._crunched = False
        self.optionalrecords = {}
        self.parsewarnings = []
        self._parseigc(igcfile)
    
    def _parseigc(self, igcfile):
        """Parse an igc file to fill out this flight

        If the result is small enough to fit in an int, return an int.
        Else return a long.
        """
        if type(igcfile) is not file:
            import os
            if not os.path.isfile(igcfile):
                raise Exception('igcfile not found')
            f = open(igcfile)
        else:
            f = igcfile

        with f:
            for line in f:
                line = line.rstrip()
                linetype = line[0]
                self._recordtypes[linetype](self, line)

    def _logline_A((self, line)):
        """The manufacturer of the IGC recording device
        """
        flight.manufacturer = line[1:]
        return

    # H Records are headers that give one-time information
    # http://carrier.csi.cam.ac.uk/forsterlewis/soaring/igc_file_format/igc_format_2008.html#link_3.3
    def _logline_H((self, line)):
        """Header records contain all manner of information about the flight

        Perhaps most important is the flight date
        """
        try:
            self._headertypes[line[1:5]](line[5:], flight)
        except KeyError:
            self.parsewarnings.append('Header type not implemented: {type}'.format(type: line[1:5]))
        return

    # Flight date header. This is the date that the FIRST B record was made on
    # Date format: DDMMYY
    # (did we learn nothing from Y2K?)
    def _logline_H_FDTE((self, line)):
        flight.flightdate = datetime.date(int(line[4:6])+2000, int(line[2:4]), int(line[0:2]))

    def _logline_H_FGTY((self, line)):
        flight.glidertype = line[11:]


    def _logline_I((self, line)):
        num = int(line[1:3])
        for i in xrange(num):
            field = line[3+7*i:10+7*i]
            flight.optional_records[field[4:7]] = (int(field[0:2])-1, int(field[2:4]))


    def _logline_B((self, line)):
        flight.fixrecords.append({
            'timestamp' : line[1:7],
            'latitude'  : line[7:15],
            'longitude' : line[15:24],
            'AVflag'    : line[24:25] == "A",
            'pressure'  : int(line[25:30]),
            'alt-GPS'   : int(line[30:35]),
        })
        for key, record in flight.optional_records.iteritems():
            flight.fixrecords[-1]['opt_' +  key.lower()] = line[record[0]:record[1]]

        return

    # Catchall for line types that we don't care about, such as the "G" checksum records at the end
    def _logline_Ignore((self, line)):
        return


    def _logline_NotImplemented((self, line)):
        print "Record Type {} not implemented: {}".format(line[0:1], line[1:])
        return


    _recordtypes = {
        'A' : _logline_A,
        'B' : _logline_B,
        'C' : _logline_NotImplemented,
        'D' : _logline_NotImplemented,
        'E' : _logline_NotImplemented,
        'F' : _logline_NotImplemented,
        'G' : _logline_Ignore, #Checksum at end of file
        'H' : _logline_H,
        'I' : _logline_I,
        'J' : _logline_NotImplemented,
        'K' : _logline_NotImplemented,
        'L' : _logline_NotImplemented,
    }

    _headertypes = {
        'FDTE' : _logline_H_FDTE,
        'FGTY' : _logline_H_FGTY,
    }