import sys
import os
import datetime
from math import radians, cos, sin, asin, sqrt


# Adds a bunch of calculated fields to a flight dictionary
def crunch_flight(flight):
    for index, record in enumerate(flight['fixrecords']):
        #thisdatetime = datetime.datetime.strptime(record['timestamp'], '')
        record['latdegrees'] = lat_to_degrees(record['latitude'])
        record['londegrees'] = lon_to_degrees(record['longitude'])

        record['time'] = datetime.time(int(record['timestamp'][0:2]), int(record['timestamp'][2:4]), int(record['timestamp'][4:6]), 0, )

        if index > 0:
            prevrecord = flight['fixrecords'][index-1]

            # Because we only know the date of the FIRST B record, we have to do some shaky logic to determine when we cross the midnight barrier
            # There's a theoretical edge case here where two B records are separated by more than 24 hours causing the date to be incorrect
            # But that's a problem with the IGC spec and we can't do much about it
            if(record['time'] < prevrecord['time']):
                # We crossed the midnight barrier, so increment the date
                record['date'] = prevrecord['date'] + datetime.timedelta(days=1)
            else:
                record['date'] = prevrecord['date']

            record['datetime'] = datetime.datetime.combine(record['date'], record['time'])
            record['time_delta'] = (record['datetime'] - prevrecord['datetime']).total_seconds()
            record['running_time'] = (record['datetime'] - flight['datetime_start']).total_seconds()
            flight['time_total'] = record['running_time']
            record['distance_delta'] = haversine(record['londegrees'], record['latdegrees'], prevrecord['londegrees'], prevrecord['latdegrees'])
            flight['distance_total'] += record['distance_delta']
            record['distance_total'] = flight['distance_total']
            record['distance_from_start'] = straight_line_distance(record['londegrees'], record['latdegrees'], record['alt-GPS'], flight['fixrecords'][0]['londegrees'], flight['fixrecords'][0]['latdegrees'], flight['fixrecords'][0]['alt-GPS'])
            record['groundspeed'] = record['distance_delta'] / record['time_delta'] * 3600
            flight['groundspeed_peak'] = max(record['groundspeed'], flight['groundspeed_peak'])
            record['groundspeed_peak'] = flight['groundspeed_peak']
            record['alt_gps_delta'] = record['alt-GPS'] - prevrecord['alt-GPS']
            record['alt_pressure_delta'] = record['pressure'] - prevrecord['pressure']
            record['climb_speed'] = record['alt_gps_delta'] / record['time_delta']
            flight['climb_total'] += max(0, record['alt_gps_delta'])
            record['climb_total'] = flight['climb_total']
            flight['alt_peak'] = max(record['alt-GPS'], flight['alt_peak'])
            flight['alt_floor'] = min(record['alt-GPS'], flight['alt_floor'])
            if "TAS" in flight['optional_records']:
                flight['tas_peak'] = max(record['opt_tas'], flight['tas_peak'])
                record['tas_peak'] = flight['tas_peak']
        else:
            flight['time_start'] = record['time']
            flight['datetime_start'] = datetime.datetime.combine(flight['flightdate'], flight['time_start'])
            flight['altitude_start'] = record['alt-GPS']
            flight['distance_total'] = 0
            flight['climb_total'] = 0
            flight['alt_peak'] = record['alt-GPS']
            flight['alt_floor'] = record['alt-GPS']
            flight['groundspeed_peak'] = 0
            flight['time_total'] = 0
    
            record['date'] = flight['flightdate']
            record['datetime'] = datetime.datetime.combine(record['date'], record['time'])
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

            if "TAS" in flight['optional_records']:
                flight['tas_peak'] = record['opt_tas']
                record['tas_peak'] = 0
    
    return flight

def crunch_logbook(logbook):
    logbook['flight_time'] = 0
    for flight in logbook['flights']:
        # TODO This is a HACK for the 6030 having 5 minutes of lead time before the flight
        logbook['flight_time'] += flight['time_total'] - 300
        print "Total flight time: {:.2f} hours".format(logbook['flight_time']/60/60)


# Calculates the distance between two sets of latitude, longitude, and altitude, as a straight line
def straight_line_distance(lon1, lat1, alt1, lon2, lat2, alt2):
    a = haversine(lon1, lat1, lon2, lat2)
    b =  (alt1 - alt2) / 1000. #altitude is in meters, but we're working in km here
    c = sqrt(a**2. + b**2.)
    return c


def get_output_filename(inputfilename):
    head, tail = os.path.split(inputfilename)
    filename, ext = os.path.splitext(tail)
    outputfilename = filename + '.csv'
    return outputfilename

if __name__ == "__main__":
    print "Number of arguments: {}".format(len(sys.argv))
    print "Argument List: {}".format(str(sys.argv))

    default_flight_output_fields = [
        ('Datetime (UTC)', 'record', 'datetime'),
        ('Elapsed Time', 'record', 'running_time'),
        ('Latitude (Degrees)', 'record', 'latdegrees'),
        ('Longitude (Degrees)', 'record', 'londegrees'),
        ('Altitude GPS', 'record', 'alt-GPS'),
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
        logbook['flights'].append({'igcfile': os.path.abspath(fileparam)})
        print "Single IGC file supplied: {}".format(logbook['flights'][-1]['igcfile'])
    elif os.path.isdir(fileparam):
        for filename in os.listdir(fileparam):
            fileabs = os.path.join(fileparam, filename)
            if not os.path.isfile(fileabs):
                continue

            root, ext = os.path.splitext(fileabs)
            if ext.lower() == '.igc'.lower():
                logbook['flights'].append({'igcfile': os.path.abspath(fileabs)})
    else:
        print 'Must indicate a file or directory to process'
        exit()

    print "{} flights ready to process...".format(len(logbook['flights']))

    # Parse all files
    for flight in logbook['flights']:
        flight = parse_igc(flight)
        print 'Processed flight from {}'.format(flight['flightdate'])

    # Crunch the telemetry numbers on all of the flights
    for flight in logbook['flights']:
        flight = crunch_flight(flight)

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
                recordline += str(flight[field[2]]) + ','
        output.write(recordline[:-1] + '\n')

    output.close()


    # Output the CSV file for all flights
    for flight in logbook['flights']:
        flight['outputfilename'] = get_output_filename(flight['igcfile'])

        output = open(flight['outputfilename'], 'w')
        outputfields = list(default_flight_output_fields)
        if 'TAS' in flight['optional_records']:
            outputfields.append( ('True Airspeed', 'record', 'opt_tas') )
            outputfields.append( ('True Airspeed Peak', 'record', 'tas_peak') )

        header = ''
        for field in outputfields:
            header += field[0] + ','
        output.write(header[:-1] + '\n')

        for record in flight['fixrecords']:
            recordline = ''
            for field in outputfields:
                if field[1] == 'record':
                    recordline += str(record[field[2]]) + ','
                elif field[1] == 'flight':
                    recordline += str(flight[field[2]]) + ','
            output.write(recordline[:-1] + '\n')

        output.close()







