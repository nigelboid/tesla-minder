#
# Import all necessary libraries
#

import requests
import json
import time

#
# Define some global constants
#

VERSION= '0.1.3'

# API request building blocks
API_VERSION= 'v1'
OWNERAPI_CLIENT_TOKENS_URL= 'http://pastebin.com/raw/0a8e0xTJ'
OWNERAPI_VERSION= '/api/1'

REQUEST_TOKEN= '/oauth/token'
REQUEST_VEHICLES= '/vehicles'
REQUEST_DATA_STATE_MOBILE_ACCESS= 'mobile_enabled'
REQUEST_DATA_STATE_VEHICLE= 'vehicle_state'
REQUEST_DATA_STATE_CLIMATE= 'climate_state'
REQUEST_DATA_STATE_CHARGE= 'charge_state'
REQUEST_DATA_STATE_DRIVE= 'drive_state'
REQUEST_DATA_STATE_GUI= 'gui_settings'
REQUEST_DATA_COMMANDS= {  REQUEST_DATA_STATE_MOBILE_ACCESS : '/',
                          REQUEST_DATA_STATE_VEHICLE : '/data_request/',
                          REQUEST_DATA_STATE_CLIMATE : '/data_request/',
                          REQUEST_DATA_STATE_CHARGE : '/data_request/',
                          REQUEST_DATA_STATE_DRIVE : '/data_request/',
                          REQUEST_DATA_STATE_GUI : '/data_request/',
}

CACHE_EXPIRATION_LIMIT= 300     # seconds

KEY_API_ID= 'id'
KEY_API_SECRET= 'secret'
KEY_API_BASEURL= 'baseurl'

KEY_TOKEN= 'access_token'
KEY_TOKEN_CREATION= 'created_at'
KEY_TOKEN_EXPIRATION= 'expires_in'
KEY_TOKEN_TYPE= 'token_type'
KEY_TOKEN_REFRESH= 'refresh_token'
KEY_TOKEN_URL= 'owner_url'

KEY_VEHICLES= 'response'
KEY_VEHICLE_COUNT= 'count'
KEY_VEHICLE_NAME= 'display_name'
KEY_VEHICLE_ID= 'id'

KEY_RESPONSE= 'response'
KEY_CACHE_EXPIRATION= 'cache_expiration'

KEY_STATE_VEHICLE_DOOR_DRIVER_FRONT= 'df'
KEY_STATE_VEHICLE_DOOR_DRIVER_REAR= 'dr'
KEY_STATE_VEHICLE_DOOR_PASSENGER_FRONT= 'pf'
KEY_STATE_VEHICLE_DOOR_PASSENGER_REAR= 'pr'
KEY_STATE_VEHICLE_DOOR_TRUNK_FRONT= 'ft'
KEY_STATE_VEHICLE_DOOR_TRUNK_REAR= 'rt'
KEY_STATE_VEHICLE_LOCKED= 'locked'

KEY_STATE_CHARGE_LEVEL= 'battery_level'
KEY_STATE_CHARGE_STATE= 'charging_state'


VALUE_STATE_CHARGE_CHARGING_READY= 'Connected'
VALUE_STATE_CHARGE_BATTERY_LEVEL= 'battery_level'


# API request result codes
STATUS_CODE_OK= 200


#
# Define our Tesla API class
#
class TeslaRequest:

  # Constructor
  def __init__(self, arguments):
    # First, validate our debug flag
    if hasattr(arguments, 'debug'):
      self.debug= arguments.debug
    else:
      self.debug= False

    # Instantiate internal cache
    self.cache= {}

    # Validate required values
    if hasattr(arguments, 'token'):
      self.token= arguments.token
    else:
      self.token= None

    if hasattr(arguments, 'e_mail'):
      self.e_mail= arguments.e_mail
    else:
      self.e_mail= None
    if hasattr(arguments, 'password'):
      self.password= arguments.password
    else:
      self.password= None

    if hasattr(arguments, 'cache_expiration_limit'):
      self.cache_expiration_limit= arguments.cache_expiration_limit
    else:
      self.cache_expiration_limit= CACHE_EXPIRATION_LIMIT

    # Bootstrap value discovery
    if self.token:
      if self.__is_token_valid():
        self.__cache_vehicles()
      elif self.e_mail and self.password:
        self.__cache_token()
        self.__cache_vehicles()
      else:
        self.vehicles= None
        raise Exception(
          'Could not validate existing token (no credentials to obtain a new one)!', self)
    elif self.e_mail and self.password:
      self.__cache_token()
      self.__cache_vehicles()
    else:
      self.vehicles= None
      raise Exception(
        'Could not obtain a token (no credentials to obtain a new one)!', self)


  # Obtain Owner API parameters from our special place
  def __get_owner_api_parameters(self):
    owner_api= requests.get(OWNERAPI_CLIENT_TOKENS_URL)

    if owner_api.status_code == STATUS_CODE_OK:
      return owner_api.json()
    else:
      if self.debug:
        raise Exception('Could not obtain Owner API parameters (status code {})'.format(owner_api.status_code), self)
      else:
        raise Exception('Could not obtain Owner API parameters (status code {})'.format(owner_api.status_code))


  # Obtain access token from Tesla
  def __cache_token(self):
    owner_api= self.__get_owner_api_parameters()

    try:
      owner_url= owner_api[API_VERSION][KEY_API_BASEURL]
      client_id= owner_api[API_VERSION][KEY_API_ID]
      client_secret= owner_api[API_VERSION][KEY_API_SECRET]
    except Exception as error:
      if self.debug:
        print 'Failed to obtain expected Owner API parameters'
        print json.dumps(owner_api, sort_keys=True, indent=4, separators=(',', ': '))
      raise error

    try:
      request= owner_url + REQUEST_TOKEN
      payload= {
        'grant_type' : 'password',
  			'client_id' : client_id,
  			'client_secret' : client_secret,
  			'email' : self.e_mail,
  			'password' : self.password,
      }
    except Exception as error:
      if self.debug:
        print 'Failed to formulate token request'
      raise error

    response= requests.post(request, json= payload)

    if response.status_code == STATUS_CODE_OK:
      self.token= response.json()
      self.token[KEY_TOKEN_URL]= owner_url
      return True
    else:
      if self.debug:
        raise Exception('Failed to obtain token (status code {})'.format(
          response.status_code), self, request, payload)
      else:
        raise Exception('Failed to obtain token (status code {})'.format(
          response.status_code))


  # Validate our current token
  def __is_token_valid(self):
    return (
      time.time() < (self.token[KEY_TOKEN_CREATION] + self.token[KEY_TOKEN_EXPIRATION])
      )


  # Obtain owned vehicles
  def __cache_vehicles(self):
    request= self.get_url() + OWNERAPI_VERSION + REQUEST_VEHICLES

    response= requests.get(request, headers= self.get_headers())

    if response.status_code == STATUS_CODE_OK:
      self.vehicles= response.json()
      return True
    else:
      if self.debug:
        raise Exception('Failed to obtain owned vehicles (status code {})'.format(
          response.status_code), self, request)
      else:
        raise Exception('Failed to obtain owned vehicles (status code {})'.format(
          response.status_code))


  # Obtain and cache indicated state of the specified vehicle
  def __cache_state(self, vehicle_index, state_type):
    try:
      headers= self.get_headers()
      request= self.get_url() + OWNERAPI_VERSION + REQUEST_VEHICLES \
        + '/' + str(self.get_vehicle_id(vehicle_index)) \
        + REQUEST_DATA_COMMANDS[state_type] + state_type

      response= requests.get(request, headers= headers)

    except Exception as error:
      if self.debug:
        print 'Could not obtain state of vehicle named "{}"'.format(
          self.get_vehicle_name(vehicle_index))
        if request:
          print 'URL: {}'.format(request)
        if headers:
          print "Headers:"
          print json.dumps(headers, sort_keys=True, indent=4, separators=(',', ': '))
      raise error

    else:
      if response.status_code == STATUS_CODE_OK:
        state= response.json()[KEY_RESPONSE]
        state[KEY_CACHE_EXPIRATION]= time.time() + self.cache_expiration_limit

        if vehicle_index not in self.cache:
          self.cache[vehicle_index]= {}
        self.cache[vehicle_index][state_type]= state
      else:
        if self.debug:
          raise Exception('Could not obtain state of vehicle'
            + ' named "{}" (status code {})'.format(
              self.get_vehicle_name(vehicle_index), response.status_code),
            self, request, headers)
        else:
          raise Exception('Could not obtain state of vehicle'
            + ' named "{}" (status code {})'.format(
              self.get_vehicle_name(vehicle_index), response.status_code))


  # Return state for the specified vehicle
  def __get_state(self, vehicle_index, state_type):
    try:
      if ((vehicle_index not in self.cache)
        or (state_type not in self.cache[vehicle_index])
        or (self.cache[vehicle_index][state_type][KEY_CACHE_EXPIRATION] < time.time())):
          self.__cache_state(vehicle_index, state_type)

      return self.cache[vehicle_index][state_type]

    except Exception as error:
      if self.debug:
        print 'Could not obtain state of vehicle named "{}" from cache'.format(
          self.get_vehicle_name(vehicle_index))
      raise error


  # Formulate and return stored token parameters
  def get_token(self):
    try:
      return self.token
    except Exception as error:
      if self.debug:
        print 'No token parameters set!'
      raise error


  # Formulate and return stored Owner API URL
  def get_url(self):
    try:
      return self.token[KEY_TOKEN_URL]
    except Exception as error:
      if self.debug:
        print 'No Owner API URL set!'
      raise error


  # Formulate and return stored Owner API request headers
  def get_headers(self):
    try:
      return {
        'Authorization' : self.token[KEY_TOKEN_TYPE] + ' ' + self.token[KEY_TOKEN],
        }
    except Exception as error:
      if self.debug:
        print 'Failed to formulate Owner API request headers!'
      raise error


  # Return count of stored vehicles
  def get_vehicle_count(self):
    try:
      return self.vehicles[KEY_VEHICLE_COUNT]
    except Exception as error:
      if self.debug:
        print 'No vehicles stored!'
      raise error


  # Return the name of the specified vehicle
  def get_vehicle_name(self, vehicle_index):
    try:
      return self.vehicles[KEY_VEHICLES][vehicle_index][KEY_VEHICLE_NAME]
    except Exception as error:
      if self.debug:
        print 'Could not access the name of vehicle #{}'.format(vehicle_index)
      raise error


  # Return the ID of the specified vehicle
  def get_vehicle_id(self, vehicle_index):
    try:
      return self.vehicles[KEY_VEHICLES][vehicle_index][KEY_VEHICLE_ID]
    except Exception as error:
      if self.debug:
        print 'Could not access the ID of vehicle #{}'.format(vehicle_index)
      raise error


  # Return full vehicle state dump for the specified vehicle
  def get_vehicle_state(self, vehicle_index):
    try:
      return self.__get_state(vehicle_index, REQUEST_DATA_STATE_VEHICLE)
    except Exception as error:
      if self.debug:
        print 'Could not access general state for vehicle #{}'.format(vehicle_index)
      raise error


  # Return full vehicle state dump for the specified vehicle
  def get_charge_state(self, vehicle_index):
    try:
      return self.__get_state(vehicle_index, REQUEST_DATA_STATE_CHARGE)
    except Exception as error:
      if self.debug:
        print 'Could not access charge state for vehicle #{}'.format(vehicle_index)
      raise error


  # Return a list of open doors and trunks for the specified vehicle
  def get_vehicle_open_doors_and_trunks(self, vehicle_index):
    try:
      doors= {
        KEY_STATE_VEHICLE_DOOR_DRIVER_FRONT : 'Driver Side Front Door',
        KEY_STATE_VEHICLE_DOOR_DRIVER_REAR : 'Driver Side Rear Door',
        KEY_STATE_VEHICLE_DOOR_PASSENGER_FRONT : 'Passenger Side Front Door',
        KEY_STATE_VEHICLE_DOOR_PASSENGER_REAR : 'Passenger Side Rear Door',
        KEY_STATE_VEHICLE_DOOR_TRUNK_FRONT : 'Front Trunk',
        KEY_STATE_VEHICLE_DOOR_TRUNK_REAR : 'Rear Trunk',
      }

      open_doors= []
      state= self.__get_state(vehicle_index, REQUEST_DATA_STATE_VEHICLE)
      for door in doors.keys():
        if (state[door] != 0):
          open_doors.append(doors[door])

      return open_doors

    except Exception as error:
      if self.debug:
        print 'Could not obtain open doors and trunks for vehicle named "{}"'.format(
          self.get_vehicle_name(vehicle_index))
      raise error


  # Return a boolean indicating the locked state for the specified vehicle
  def is_vehicle_locked(self, vehicle_index):
    try:
      return self.__get_state(
        vehicle_index, REQUEST_DATA_STATE_VEHICLE)[KEY_STATE_VEHICLE_LOCKED]
    except Exception as error:
      if self.debug:
        print 'Could not obtain locked state for vehicle named "{}"'.format(
          self.get_vehicle_name(vehicle_index))
      raise error


  # Return a boolean indicating charging readiness for the specified vehicle
  def is_ready_to_charge(self, vehicle_index):
    try:
      return (
        self.__get_state(vehicle_index, REQUEST_DATA_STATE_CHARGE)[KEY_STATE_CHARGE_STATE]
        == VALUE_STATE_CHARGE_CHARGING_READY)
    except Exception as error:
      if self.debug:
        print 'Could not obtain charging state for vehicle named "{}"'.format(
          self.get_vehicle_name(vehicle_index))
      raise error


  # Return current battery level % for the specified vehicle
  def get_battery_level(self, vehicle_index):
    try:
      return (self.__get_state(
        vehicle_index, REQUEST_DATA_STATE_CHARGE)[VALUE_STATE_CHARGE_BATTERY_LEVEL])
    except Exception as error:
      if self.debug:
        print 'Could not obtain charging state for vehicle named "{}"'.format(
          self.get_vehicle_name(vehicle_index))
      raise error