import sys
import os
import flightlog
import datetime


def crunch_logbook(logbook):
    logbook['flight_time'] = 0
    for flight in logbook['flights']:
        # TODO This is a HACK for the 6030 having 5 minutes of lead time before the flight
        print logbook['flight_time']
        logbook['flight_time'] += flight.flightinfo['time_total'] - 300
        print "Total flight time: {:.2f} hours".format(logbook['flight_time']/60./60.)


def get_output_filename(flight):
    inputfilename = flight.filename
    _, tail = os.path.split(inputfilename)
    filename, _ = os.path.splitext(tail)
    outputfilename = filename + '.csv'
    return outputfilename


def main():
    print "Number of arguments: {}".format(len(sys.argv))
    print "Argument List: {}".format(str(sys.argv))

    default_flight_output_fields = [
        ('Datetime (UTC)', 'record', 'datetime'),
        ('Elapsed Time', 'record', 'time_total'),
        ('Latitude (Degrees)', 'record', 'latitude'),
        ('Longitude (Degrees)', 'record', 'longitude'),
        ('Altitude GPS', 'record', 'alt_gps'),
        ('Distance Delta', 'record', 'dist_delta'),
        ('Distance Total', 'record', 'dist_total'),
        ('Groundspeed', 'record', 'groundspeed'),
        ('Groundspeed Peak', 'record', 'groundspeed_peak'),
        ('Altitude Delta (GPS)', 'record', 'alt_delta'),
        ('Climb Speed', 'record', 'climb_speed'),
        ('Climb Total', 'record', 'climb_total_abs'),
        # ('Max Altitude (flight)', 'flight', 'alt_peak'),
        # ('Min Altitude (flight)', 'flight', 'alt_floor'),
        ('Distance From Start (straight line)', 'record', 'dist_from_start')
        ]

    def logbook_output_datetime(flight):
        return flight.flightinfo['takeoff_datetime']

    def logbook_output_distance(flight):
        return flight.flightinfo['dist_total']

    def logbook_output_totalclimb(flight):
        return flight.flightinfo['climb_total_abs']

    def logbook_output_flighttime(flight):
        return flight.flightinfo['time_total'] - 240

    def logbook_output_filename(flight):
        _, filename = os.path.split(flight.filename)
        return filename

    default_logbook_output_fields = [
        ('Datetime (UTC)', logbook_output_datetime),
        ('Distance (km)', logbook_output_distance),
        ('Total Climb (m)', logbook_output_totalclimb),
        ('Flight Time (min)', logbook_output_flighttime),
        ('Track File', logbook_output_filename),
        # ('Max Altitude', 'flight', 'alt_peak'),
        # ('Min Altitude', 'flight', 'alt_floor'),
        ]

    logbook = {'flights': []}

    fileparam = sys.argv[1]

    if os.path.isfile(fileparam):
        logbook['flights'].append(flightlog.Flight(fileparam))
        print "Single IGC file supplied: {}".format(logbook['flights'][-1].filename)
        print 'Imported flight from {}'.format(logbook['flights'][-1].date)
    elif os.path.isdir(fileparam):
        for filename in os.listdir(fileparam):
            fileabs = os.path.join(fileparam, filename)
            if not os.path.isfile(fileabs):
                continue

            _, ext = os.path.splitext(fileabs)
            if ext.lower() == '.igc'.lower():
                logbook['flights'].append(flightlog.Flight(os.path.abspath(fileabs)))
                print 'Imported flight from {}'.format(logbook['flights'][-1].date)
    else:
        print 'Must indicate a file or directory to process'
        exit()

    print "{} flights ready to process...".format(len(logbook['flights']))
    crunch_logbook(logbook)

    # Output the logbook summary CSV file
    with open('logbook.csv', 'w') as output:
        outputfields = list(default_logbook_output_fields)

        header = ''
        for field in outputfields:
            header += field[0] + ','
        output.write(header[:-1] + '\n')

        for flight in logbook['flights']:
            recordlines = []
            for field in outputfields:
                recordlines.append(str(field[1](flight)))
            output.write(','.join(recordlines) + '\n')

    # Output the CSV file for all flights
    for flight in logbook['flights']:
        with open(get_output_filename(flight), 'w') as outputfile:

            outputfields = list(default_flight_output_fields)
            if 'tas' in flight.optfields:
                outputfields.append(('True Airspeed', 'optionalrecord', 'tas'))

            header = ''
            for field in outputfields:
                header += field[0] + ','
            outputfile.write(header[:-1] + '\n')

            for record in flight.fixrecords[1:]:
                recordline = ''
                for field in outputfields:
                    if field[1] == 'record':
                        recordline += str(record[field[2]]) + ','
                    elif field[1] == 'flight':
                        recordline += str(flight.flightinfo[field[2]]) + ','
                    elif field[1] == 'optionalrecord':
                        recordline += str(record['optfields'][field[2]]) + ','
                outputfile.write(recordline[:-1] + '\n')


if __name__ == "__main__":
    main()
