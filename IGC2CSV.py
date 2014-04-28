import sys
import os
import datetime
import flightlog


# Adds a bunch of calculated fields to a flight dictionary
def crunch_flight(flight):
    flightdata = flight.flightdata
    for index, record in enumerate(flight.fixrecords):
        # thisdatetime = datetime.datetime.strptime(record['timestamp'], '')

        if index > 0:
            prevrecord = flight.fixrecords[index-1]

            record['time_delta'] = (record['datetime'] - prevrecord['datetime']).total_seconds()
            record['running_time'] = (record['datetime'] - flightdata['datetime_start']).total_seconds()
            flightdata['time_total'] = record['running_time']
            record['distance_delta'] = flightlog.haversine(record['longitude'], record['latitude'], prevrecord['longitude'], prevrecord['latitude'])
            flightdata['distance_total'] += record['distance_delta']
            record['distance_total'] = flightdata['distance_total']
            record['distance_from_start'] = flightlog.straight_line_distance(record['longitude'], record['latitude'], record['alt_gps'], flight.fixrecords[0]['longitude'], flight.fixrecords[0]['latitude'], flight.fixrecords[0]['alt_gps'])
            record['groundspeed'] = record['distance_delta'] / record['time_delta'] * 3600
            flightdata['groundspeed_peak'] = max(record['groundspeed'], flightdata['groundspeed_peak'])
            record['groundspeed_peak'] = flightdata['groundspeed_peak']
            record['alt_gps_delta'] = record['alt_gps'] - prevrecord['alt_gps']
            record['alt_pressure_delta'] = record['pressure'] - prevrecord['pressure']
            record['climb_speed'] = record['alt_gps_delta'] / record['time_delta']
            flightdata['climb_total'] += max(0, record['alt_gps_delta'])
            record['climb_total'] = flightdata['climb_total']
            flightdata['alt_peak'] = max(record['alt_gps'], flightdata['alt_peak'])
            flightdata['alt_floor'] = min(record['alt_gps'], flightdata['alt_floor'])
            if "tas" in flight.optfields:
                flightdata['tas_peak'] = max(record['optfields']['tas'], flightdata['tas_peak'])
                record['optfields']['tas_peak'] = flightdata['tas_peak']
        else:
            flightdata['time_start'] = record['datetime'].time()
            flightdata['datetime_start'] = datetime.datetime.combine(flight.date, flightdata['time_start'])
            flightdata['altitude_start'] = record['alt_gps']
            flightdata['distance_total'] = 0
            flightdata['climb_total'] = 0
            flightdata['alt_peak'] = record['alt_gps']
            flightdata['alt_floor'] = record['alt_gps']
            flightdata['groundspeed_peak'] = 0
            flightdata['time_total'] = 0

            record['running_time'] = 0
            record['time_delta'] = 0
            record['distance_delta'] = 0
            record['distance_total'] = 0
            record['groundspeed'] = 0
            record['groundspeed_peak'] = 0
            record['alt_gps_delta'] = 0
            record['alt_pressure_delta'] = 0
            record['climb_speed'] = 0
            record['climb_total'] = 0
            record['distance_from_start'] = 0

            if "tas" in flight.optfields:
                flightdata['tas_peak'] = record['optfields']['tas']
                record['optfields']['tas_peak'] = 0

    return flight


def crunch_logbook(logbook):
    logbook['flight_time'] = 0
    for flight in logbook['flights']:
        # TODO This is a HACK for the 6030 having 5 minutes of lead time before the flight
        logbook['flight_time'] += flight.flightdata['time_total'] - 300
        print "Total flight time: {:.2f} hours".format(logbook['flight_time']/60/60)


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
        ('Elapsed Time', 'record', 'running_time'),
        ('Latitude (Degrees)', 'record', 'latitude'),
        ('Longitude (Degrees)', 'record', 'longitude'),
        ('Altitude GPS', 'record', 'alt_gps'),
        ('Distance Delta', 'record', 'distance_delta'),
        ('Distance Total', 'record', 'distance_total'),
        ('Groundspeed', 'record', 'groundspeed'),
        ('Groundspeed Peak', 'record', 'groundspeed_peak'),
        ('Altitude Delta (GPS)', 'record', 'alt_gps_delta'),
        ('Altitude Delta (Pressure)', 'record', 'alt_pressure_delta'),
        ('Climb Speed', 'record', 'climb_speed'),
        ('Climb Total', 'record', 'climb_total'),
        ('Max Altitude (flight)', 'flight', 'alt_peak'),
        ('Min Altitude (flight)', 'flight', 'alt_floor'),
        ('Distance From Start (straight line)', 'record', 'distance_from_start')
        ]

    default_logbook_output_fields = [
        ('Datetime (UTC)', 'flight', 'datetime_start'),
        ('Distance', 'flight', 'distance_total'),
        ('Total Climb', 'flight', 'climb_total'),
        ('Max Altitude', 'flight', 'alt_peak'),
        ('Min Altitude', 'flight', 'alt_floor'),
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

    # Crunch the telemetry numbers on all of the flights
    for flight in logbook['flights']:
        crunch_flight(flight)

    crunch_logbook(logbook)

    # Output the logbook summary CSV file
    output = open('logbook.csv', 'w')
    outputfields = list(default_logbook_output_fields)

    header = ''
    for field in outputfields:
        header += field[0] + ','
    output.write(header[:-1] + '\n')

    for flight in logbook['flights']:
        recordline = ''
        for field in outputfields:
            if field[1] == 'flight':
                recordline += str(flight.flightdata[field[2]]) + ','
        output.write(recordline[:-1] + '\n')

    output.close()

    # Output the CSV file for all flights
    for flight in logbook['flights']:
        with open(get_output_filename(flight), 'w') as outputfile:

            outputfields = list(default_flight_output_fields)
            if 'tas' in flight.optfields:
                outputfields.append(('True Airspeed', 'optionalrecord', 'tas'))
                outputfields.append(('True Airspeed Peak', 'optionalrecord', 'tas_peak'))

            header = ''
            for field in outputfields:
                header += field[0] + ','
            outputfile.write(header[:-1] + '\n')

            for record in flight.fixrecords:
                recordline = ''
                for field in outputfields:
                    if field[1] == 'record':
                        recordline += str(record[field[2]]) + ','
                    elif field[1] == 'flight':
                        recordline += str(flight.flightdata[field[2]]) + ','
                    elif field[1] == 'optionalrecord':
                        recordline += str(record['optfields'][field[2]]) + ','
                outputfile.write(recordline[:-1] + '\n')


if __name__ == "__main__":
    main()
