import sys
import os
import datetime
from math import radians, cos, sin, asin, sqrt

# Reads the IGC file and returns a flight dictionary
def parse_igc(flight):
  flight['fixrecords'] = []
  flight['optional_records'] = {}

  file = open(flight['igcfile'], 'r')

  for line in file:
    line = line.rstrip()
    linetype = line[0]
    recordtypes[linetype](line, flight)

  file.close()
    
  return flight

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

def logline_A(line, flight):
  flight['manufacturer'] = line[1:]
  return

# H Records are headers that give one-time information
# http://carrier.csi.cam.ac.uk/forsterlewis/soaring/igc_file_format/igc_format_2008.html#link_3.3
def logline_H(line, flight):
  try:
    headertypes[line[1:5]](line[5:], flight)
  except KeyError:
    print "Header (not implemented): {}".format(line[1:])
  return

# Flight date header. This is the date that the FIRST B record was made on
# Date format: DDMMYY
# (did we learn nothing from Y2K?)
def logline_H_FDTE(line, flight):
  flight['flightdate'] = datetime.date(int(line[4:6])+2000, int(line[2:4]), int(line[0:2]))
  print "Flight date: {}".format(flight['flightdate'])


def logline_I(line, flight):
  num = int(line[1:3])
  for i in xrange(num):
    field = line[3+7*i:10+7*i]
    flight['optional_records'][field[4:7]] = (int(field[0:2])-1, int(field[2:4]))


def logline_B(line, flight):
  flight['fixrecords'].append({
    'timestamp' : line[1:7],
    'latitude'  : line[7:15],
    'longitude' : line[15:24],
    'AVflag'    : line[24:25] == "A",
    'pressure'  : int(line[25:30]),
    'alt-GPS'   : int(line[30:35]),
  })
  for key, record in flight['optional_records'].iteritems():
    flight['fixrecords'][-1]['opt_' +  key.lower()] = line[record[0]:record[1]]

  return

def logline_NotImplemented(line, flight):
  print "Record Type {} not implemented: {}".format(line[0:1], line[1:])
  return

  
recordtypes = {
  'A' : logline_A,
  'B' : logline_B,
  'C' : logline_NotImplemented,
  'D' : logline_NotImplemented,
  'E' : logline_NotImplemented,
  'F' : logline_NotImplemented,
  'G' : logline_NotImplemented,
  'H' : logline_H,
  'I' : logline_I,
  'J' : logline_NotImplemented,
  'K' : logline_NotImplemented,
  'L' : logline_NotImplemented,
}

headertypes = {
  'FDTE' : logline_H_FDTE,
}

# IGC files store latitude as DDMMmmmN
def lat_to_degrees(lat):
  direction = {'N':1, 'S':-1}
  degrees = int(lat[0:2])
  minutes = int(lat[2:7])
  minutes /= 1000.
  directionmod = direction[lat[7]]
  return (degrees + minutes/60.) * directionmod
  
# IGC files store longitude as DDDMMmmmN
def lon_to_degrees(lon):
  direction = {'E': 1, 'W':-1}
  degrees = int(lon[0:3])
  minutes = int(lon[3:8])
  minutes /= 1000.
  directionmod = direction[lon[8]]
  return (degrees + minutes/60.) * directionmod

# haversine calculates the distance between two pairs of latitude/longitude
def haversine(lon1, lat1, lon2, lat2):
  """
  Calculate the great circle distance between two points 
  on the earth (specified in decimal degrees)
  """
  # convert decimal degrees to radians 
  lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])
  # haversine formula 
  dlon = lon2 - lon1 
  dlat = lat2 - lat1 
  a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
  c = 2 * asin(sqrt(a)) 
  km = 6367 * c
  return km

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

  defaultoutputfields = [
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

  logbook = []

  fileparam = sys.argv[1]
  if os.path.isfile(fileparam):
    logbook.append({'igcfile': os.path.abspath(fileparam)})
    print "Single IGC file supplied: {}".format(logbook[-1]['igcfile'])
  elif os.path.isdir(fileparam):
    for filename in os.listdir(fileparam):
      fileabs = os.path.join(fileparam, filename)
      if not os.path.isfile(fileabs):
        continue

      root, ext = os.path.splitext(fileabs)
      if ext.lower() == '.igc'.lower():
        logbook.append({'igcfile': os.path.abspath(fileabs)})
  else:
    print 'Must indicate a file or directory to process'
    exit()

  print "{} flights ready to process...".format(len(logbook))

  # Parse all files
  for flight in logbook:
    flight = parse_igc(flight)

  # Crunch the telemetry numbers on all of the flights
  for flight in logbook:
    flight = crunch_flight(flight)

  # Output the CSV file for all flights
  for flight in logbook:
    flight['outputfilename'] = get_output_filename(flight['igcfile'])

    output = open(flight['outputfilename'], 'w')
    outputfields = list(defaultoutputfields)
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