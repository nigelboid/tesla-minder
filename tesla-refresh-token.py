#!/usr/bin/env python3


#
# Import all necessary libraries
#

import argparse
import json
import sys
import datetime
from teslarequest import TeslaRequest

#
# Define some global constants
#

VERSION= '0.0.1'

KEY_TOKEN= 'access_token'
KEY_TOKEN_CREATION= 'created_at'
KEY_TOKEN_EXPIRATION= 'expires_in'
KEY_TOKEN_TYPE= 'token_type'
KEY_TOKEN_REFRESH= 'refresh_token'

MINIMUM_DAYS_REMAINING= 5


#
# Define our functions
#

# Collect all expected and detected arguments from the command line
#
def GetArguments():
  argumentParser= argparse.ArgumentParser()

  argumentParser.add_argument('-t', '--token', '--token-file',
    dest='token_file', required=True, action='store',
    help='Tesla Owner API authorization token file')

  argumentParser.add_argument('--days',
    dest='min_expiration_days', type=int, required=False, action='store',
    default=MINIMUM_DAYS_REMAINING,
    help='Minimum days remaining before expiration to trigger a refresh')

  diagnostics= argumentParser.add_mutually_exclusive_group()
  diagnostics.add_argument('-d', '--debug', dest='debug', required=False,
    action='store_true', default=False, help='Activate verbose diagnostics')
  diagnostics.add_argument('-q', '--quiet', dest='quiet', required=False,
    action='store_true', default=False, help='Suppress non-critical messages')

  argumentParser.add_argument('-v', '--version', action='version',
    version='%(prog)s '+VERSION)

  return argumentParser.parse_args()


# Read and validate our token from the specified file
#
def GetToken(options):
  input_file= open(options.token_file)
  token= json.loads(input_file.read())
  token_creation= datetime.datetime.fromtimestamp(token[KEY_TOKEN_CREATION])
  token_expiration= datetime.datetime.fromtimestamp(token[KEY_TOKEN_CREATION]
                    + token[KEY_TOKEN_EXPIRATION])

  time_remaining= token_expiration - datetime.datetime.now()

  if options.debug:
    print()
    print('{:>23}: {}'.format('Token (access)', token[KEY_TOKEN]))
    print('{:>23}: {}'.format('Token (refresh)', token[KEY_TOKEN_REFRESH]))
    print('{:>23}: {}'.format('Token type', token[KEY_TOKEN_TYPE]))
    print('{:>23}: {}'.format('Token created', token_creation))
    print('{:>23}: {}'.format('Token expires', token_expiration))
    print('{:>23}: {}'.format('Token life remaining', time_remaining))

  options.token= token
  
  return time_remaining.days


# Should there be an 's' at the end?
#
def PluralS(number):
  if float(number) == 1:
    return ''
  else:
    return 's'


# Main entry point
#
def main():
  try:
    # instantiate our Tesla API and initialize from command line arguments
    options= GetArguments()
    days_remaining= GetToken(options)
    request= TeslaRequest(options)

    # figure out what we have
    if options.debug:
      print('')
      print('{:>18}: {}'.format('URL', request.get_url()))
      
    request.force_token_refresh()
    
    # write it out to our designated output file (or STDOUT if none)
    with open(options.token_file, 'w') as token_file:
      json.dump(request.get_token(), token_file, sort_keys=True, indent=4, separators=(',', ': '))
      
    if options.debug:
      print('')
      print(json.dumps(request.get_token(), sort_keys=True, indent=4, separators=(',', ': ')))

  except Exception as error:
    print(type(error))
    print(error.args[0])
    for counter in range(1, len(error.args)):
      print('\t' + str(error.args[counter]))

  else:
    if options.debug:
      print('')
      print('All done!')
      print('')


#
# Execute if we were run as a program
#

if __name__ == '__main__':
  main()
