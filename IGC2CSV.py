import sys
import os
from math import radians, cos, sin, asin, sqrt

print('Number of arguments:', len(sys.argv), 'arguments.')
print('Argument List:', str(sys.argv))

fileparam = sys.argv[1]

if os.path.isfile(fileparam):
  igcfile = open(fileparam, 'r')
  print('IGC file:',igcfile.name)
else:
  print('Parsing direcories not yet supported')
  exit()


def parse_igc(file):
  flight = {'fixrecords': []}

  for line in file:
    line = line.rstrip()
    linetype = line[0]
    recordtypes[linetype](line, flight)
    
  return flight

def crunch_flight(flight):
  #TODO: All of the TAS stuff needs to be conditional based on if we actually have TAS data
  
  #TODO: Add Takeoff Distance
  #TODO: Add Altitude Above Landing
  #TODO: Add Date/Time
  
  for index, record in enumerate(flight['fixrecords']):
    record['latdegrees'] = lat_to_degrees(record['latitude'])
    record['londegrees'] = lon_to_degrees(record['longitude'])
    #TODO: This timeseconds calculation is terrible - completely breaks if we pass midnight
    record['timeseconds'] = int(record['timestamp'][0:2])*3600 + int(record['timestamp'][2:4])*60 + int(record['timestamp'][4:6])
    
    if index > 0:
      prevrecord = flight['fixrecords'][index-1]
      record['time_delta'] = int(record['timeseconds']) - int(prevrecord['timeseconds'])
      record['running_time'] = int(record['timeseconds']) - flight['time_start']
      record['distance_delta'] = haversine(record['londegrees'], record['latdegrees'], prevrecord['londegrees'], prevrecord['latdegrees'])
      flight['distance_total'] += record['distance_delta']
      record['distance_total'] = flight['distance_total']
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
      flight['tas_peak'] = max(record['tas'], flight['tas_peak'])
      record['tas_peak'] = flight['tas_peak']
    else:
      flight['time_start'] = record['timeseconds']
      flight['altitude_start'] = record['alt-GPS']
      flight['distance_total'] = 0
      flight['climb_total'] = 0
      flight['alt_peak'] = record['alt-GPS']
      flight['alt_floor'] = record['alt-GPS']
      flight['groundspeed_peak'] = 0
      flight['tas_peak'] = record['tas']
  
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
      record['tas_peak'] = 0
  
  return flight

def logline_A(line, flight):
  flight['manufacturer'] = line[1:]
  print('Manufacturer:',flight['manufacturer'])
  return

def logline_H(line, flight):
  print('Header (not implemented):',line[1:])
  return

def logline_B(line, flight):
  flight['fixrecords'].append({
    'timestamp' : line[1:7],
    'latitude'  : line[7:15],
    'longitude' : line[15:24],
    'AVflag'    : line[24:25] == "A",
    'pressure'  : int(line[25:30]),
    'alt-GPS'   : int(line[30:35]),
    'tas'       : int(line[35:38]), #TODO: THIS IS NOT STANDARD! FIXME TO BE BASED ON THE I RECORD IN THE IGC
  })
  return

def logline_NotImplemented(line, flight):
  print('Record Type ' + line[0:1] + ' Not implemented')
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
  'I' : logline_NotImplemented,
  'J' : logline_NotImplemented,
  'K' : logline_NotImplemented,
  'L' : logline_NotImplemented,
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

flight = parse_igc(igcfile)
flight = crunch_flight(flight)

def get_output_filename(inputfilename):
  head, tail = os.path.split(inputfilename)
  filename, ext = os.path.splitext(tail)
  outputfilename = filename + '.csv'
  return outputfilename

output = open(get_output_filename(fileparam), 'w')
output.write('Time,Latitude (Degrees),Longitude (Degrees),Altitude GPS,Distance Delta,Distance Total,Groundspeed,Groundspeed Peak,True Airspeed,True Airspeed Peak,Altitude Delta (GPS),Altitude Delta (Pressure),Climb Speed,Climb Total,Max Altitude (flight),Min Altitude (flight)\n')
for record in flight['fixrecords']:
  output.write("{},{},{},{},{},{},{},{},{},{},{},{},{},{},{},{}\n".format(
    record['running_time'],
    record['latdegrees'],
    record['londegrees'],
    record['alt-GPS'],
    record['distance_delta'],
    record['distance_total'],
    record['groundspeed'],
    record['groundspeed_peak'],
    record['tas'],
    record['tas_peak'],
    record['alt_gps_delta'],
    record['alt_pressure_delta'],
    record['climb_speed'],
    record['climb_total'],
    flight['alt_peak'],
    flight['alt_floor'],
  ))

#HACK to output everything except for the table of fixrecords
flight['fixrecords'] = []
print(flight)