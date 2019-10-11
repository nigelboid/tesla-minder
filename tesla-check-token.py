#!/usr/bin/env python3


#
# Import all necessary libraries
#

import argparse
import json
import datetime
#from operator import itemgetter


#
# Define some global constants
#

VERSION= '0.0.4'

KEY_TOKEN= 'access_token'
KEY_TOKEN_CREATION= 'created_at'
KEY_TOKEN_EXPIRATION= 'expires_in'
KEY_TOKEN_TYPE= 'token_type'
#KEY_TOKEN_REFRESH= 'refresh_token'

MINIMUM_DAYS_REMAINING= 5


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

  argumentParser.add_argument('-d', '--days',
    nargs=1, dest='min_expiration_days', type=int, required=False, action='store',
    default=[MINIMUM_DAYS_REMAINING],
    help='Minimum days remaining before expiration to trigger an alert')

  argumentParser.add_argument('--debug', dest='debug', required=False,
    action='store_true', default=False, help='Turn on verbose diagnostics')

  argumentParser.add_argument('-v', '--version', action='version',
    version='%(prog)s '+VERSION)

  return argumentParser.parse_args()


# Validate and normalize some of the obtained arguments and pass the rest along
#
def NormalizeArguments(options):
  # convert lists of single values into integer values
  options.min_expiration_days= int(options.min_expiration_days.pop())

  # convert lists of single strings into strings
  options.token_file = str(options.token_file.pop())

  return options


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
    print('{:>23}: {}'.format('Token', token[KEY_TOKEN]))
    print('{:>23}: {}'.format('Token type', token[KEY_TOKEN_TYPE]))
    print('{:>23}: {}'.format('Token created', token_creation))
    print('{:>23}: {}'.format('Token expires', token_expiration))
    print('{:>23}: {}'.format('Token life remaining', time_remaining))

  return time_remaining.days



# Main entry point
#
def main():
  try:
    # instantiate our Tesla API and initialize from command line arguments
    options= NormalizeArguments(GetArguments())
    days= GetToken(options)

    # figure out what we have
    if (days > options.min_expiration_days):
      if options.debug:
        print('')
        print('Token expires in {} days ({} days threshold).'.format(days, options.min_expiration_days))
    else:
        print('Time to refresh the token ({} days remaining)!'.format(days))


  except Exception as error:
    print(type(error))
    print(error.args[0])
    for counter in range(1, len(error.args)):
      print('\t' + str(error.args[counter]))

  else:
    if options.debug:
      print('All done!')


#
# Execute if we were run as a program
#

if __name__ == '__main__':
  main()
