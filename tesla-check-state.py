#!/usr/bin/env python


#
# Import all necessary libraries
#

import argparse
import json
import datetime
from teslarequest import TeslaRequest
#from operator import itemgetter


#
# Define some global constants
#

VERSION= '0.0.4'

MINIMUM_CHARGING_LEVEL= 50
DEFAULT_CHARGING_LIMIT= 80


#
# Define our functions
#

# Collect all expected and detected arguments from the command line
#
def GetArguments():
  argumentParser= argparse.ArgumentParser()

  argumentParser.add_argument('-t', '--token', '--token-file',
    nargs=1, dest='token_file', required=True, action='store',
    help='Tesla Owner API authorization token file')

  argumentParser.add_argument('-b', '--level', '--battery-level',
    nargs=1, dest='min_battery_level', type=int, required=False, action='store',
    default=[MINIMUM_CHARGING_LEVEL],
    help='Minimum battery level to trigger an alert')

  argumentParser.add_argument('-c', '--limit', '--charging-limit',
    nargs=1, dest='charging_limit', type=int, required=False, action='store',
    default=[DEFAULT_CHARGING_LIMIT],
    help='Battery charging limit')


  argumentParser.add_argument('-d', '--debug', dest='debug', required=False,
    action='store_true', default=False, help='Turn on verbose diagnostics')
  argumentParser.add_argument('-q', '--quiet', dest='quiet', required=False,
    action='store_true', default=False, help='Suppress non-critical messages')

  argumentParser.add_argument('-v', '--version', action='version',
    version='%(prog)s '+VERSION)

  return argumentParser.parse_args()


# Validate and normalize some of the obtained arguments and pass the rest along
#
def NormalizeArguments(options):
  # convert lists of single values into integer values
  options.min_battery_level= int(options.min_battery_level.pop())
  options.charging_limit= int(options.charging_limit.pop())

  # convert lists of single strings into strings
  options.token_file = str(options.token_file.pop())

  return options


# Read and validate our token from the specified file
#
def GetToken(options):
  input_file= open(options.token_file)
  options.token= json.loads(input_file.read())

  return options


# Should there be an 's' at the end?
#
def PluralS(number):
  if int(number) == 1:
    return ''
  else:
    return 's'



# Main entry point
#
def main():
  try:
    # instantiate our Tesla API and initialize from command line arguments
    options= NormalizeArguments(GetArguments())
    options= GetToken(options)
    request= TeslaRequest(options)

    # figure out what we have
    vehicle_count= request.get_vehicle_count()
    if options.debug:
      print
      print '{:>14}: {}'.format('Count', vehicle_count)

    for counter in xrange(0, vehicle_count):
      try:
        name= request.get_vehicle_name(counter)
        vehicle_id= request.get_vehicle_id(counter)
        if options.debug:
          print '{:>14}: {}'.format(name, vehicle_id)
  
        open_doors= request.get_vehicle_open_doors_and_trunks(counter)
        if (len(open_doors) > 0):
          if options.debug:
            print '{:>18}: {}'.format('open door' + PluralS(len(open_doors)),
              open_doors)
          else:
            print 'Open door{}! {}: {}'.format(PluralS(len(open_doors)), name, open_doors)
        else:
          if options.debug:
            print '{:>18}: {}'.format('open door' + PluralS(len(open_doors)),
              'all doors closed')
  
        if request.is_vehicle_locked(counter):
          if options.debug:
            print '{:>18}: locked'.format('lock state')
        else:
          if options.debug:
            print '{:>18}: unlocked'.format('lock state')
          else:
            print '{} is unlocked!'.format(name)
  
        if request.get_charging_limit(counter) != options.charging_limit:
          if options.debug:
            print '{:>18}: set to {}% instead of {}%'.format(
              'charging limit', request.get_charging_limit(counter), options.charging_limit)
          else:
            print '{} charging limit set to {}% instead of {}%'.format(
              name, request.get_charging_limit(counter), options.charging_limit)
  
          if request.set_charging_limit(counter, options.charging_limit):
            if options.debug:
              print '{:>18}: reset to {}%'.format('charging limit', options.charging_limit)
            else:
              print '{} charging limit reset to {}%'.format(name, options.charging_limit)
          else:
            if options.debug:
              print '{:>18}: failed reset!'.format('charging limit')
            else:
              print '{} failed charging limit reset!'.format(name)
        else:
          if options.debug:
            print '{:>18}: already set to {}'.format(
              'charging limit', options.charging_limit)
  
        if request.is_ready_to_charge(counter):
          if options.debug:
            print '{:>18}: ready'.format('charging state')
        elif (request.get_battery_level(counter) < options.min_battery_level):
          if options.debug:
            print '{:>18}: not ready but should be charging (level= {}%)!'.format(
              'charging state', request.get_battery_level(counter))
          else:
            print '{} is not ready to charge and is running low (level= {}%)!'.format(
              name, request.get_battery_level(counter))
        else:
          if options.debug:
            print '{:>18}: not ready'.format('charging state')
  
  
        if options.debug:
          print
          print json.dumps(request.get_vehicle_state(counter),
            sort_keys=True, indent=4, separators=(',', ': '))
          print
          print json.dumps(request.get_charge_state(counter),
            sort_keys=True, indent=4, separators=(',', ': '))
          print
          
          
      except Exception as error:
        # problems accessing a vehicle
        if options.debug:
          print type(error)
          print error.args[0]
          for counter in xrange(1, len(error.args)):
            print '\t' + str(error.args[counter])
          
        # skip to the next vehicle
        continue
        

  except Exception as error:
    print type(error)
    print error.args[0]
    for counter in xrange(1, len(error.args)):
      print '\t' + str(error.args[counter])

  else:
    if options.debug:
      print
      print 'All done!'
      print


#
# Execute if we were run as a program
#

if __name__ == '__main__':
  main()
