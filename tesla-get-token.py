#!/usr/bin/env python3


#
# Import all necessary libraries
#

import argparse
import json
import sys
from teslarequest import TeslaRequest

#
# Define some global constants
#

VERSION= '0.0.5'

KEY_EMAIL= 'e-mail'
KEY_PASSWORD= 'password'


#
# Define our functions
#

# Collect all expected and detected arguments from the command line
#
def GetArguments():
  argumentParser= argparse.ArgumentParser()

  argumentParser.add_argument('-o', '--output', '--output-file',
    nargs=1, dest='output', required=False, action='store',
    help='File to store Tesla Owner API authorization token')

  argumentParser.add_argument('-d', '--debug', dest='debug', required=False,
    action='store_true', default=False, help='Turn on verbose diagnostics')
  argumentParser.add_argument('-q', '--quiet', dest='quiet', required=False,
    action='store_true', default=False, help='Suppress non-critical messages')

  argumentParser.add_argument('-v', '--version', action='version',
    version='%(prog)s '+VERSION)

  return argumentParser.parse_args()


# Validate and normalize some of the obtained arguments and pass the rest along
#
def NormalizeArguments(options, e_mail, password):
  if options.debug and options.quiet:
    # cannot have it both ways -- debug trumps quiet
    options.quiet= False

  # convert lists of single strings into strings
  options.output = str(options.output.pop())

  # instantiate secret e-mail and password parameters
  if e_mail:
    options.e_mail= e_mail

  if password:
    options.password= password

  return options


# Main entry point
#
def main():
  try:
    # soak up secret information from STDIN
    secret= ''
    for line in sys.stdin:
      secret+= line
    secret= json.loads(secret)
  except:
    print('Failed to provide properly formatted (JSON) login information as input.')
    print('Treminating...')
  else:
    try:
      # instantiate our Tesla API and initialize from command line arguments
      options= NormalizeArguments(GetArguments(), secret[KEY_EMAIL], secret[KEY_PASSWORD])
      request= TeslaRequest(options)

      # figure out what we have
      if options.debug:
        print('')
        print('{:>18}: {}'.format('URL', request.get_url()))

      # write it out to our designated output file (or STDOUT if none)
      if options.output:
        with open(options.output, 'w') as output_file:
          json.dump(request.get_token(), output_file)
      else:
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
