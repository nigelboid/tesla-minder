#
# Import all necessary libraries
#

import requests
import json
import time

#
# Define some global constants
#

VERSION= '0.2.2'
MAX_ATTEMPTS= 20

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


COMMAND_WAKE_UP= 'wake_up'


CACHE_EXPIRATION_LIMIT= 300     # seconds
ATTEMPT_RETRY_DELAY= 5          # seconds

KEY_API_ID= 'id'
KEY_API_SECRET= 'secret'
KEY_API_BASEURL= 'baseurl'

KEY_TOKEN= 'access_token'
KEY_TOKEN_CREATION= 'created_at'
KEY_TOKEN_EXPIRATION= 'expires_in'
KEY_TOKEN_TYPE= 'token_type'
KEY_TOKEN_REFRESH= 'refresh_token'
KEY_TOKEN_URL= KEY_API_BASEURL
KEY_TOKEN_ID= KEY_API_ID
KEY_TOKEN_SECRET= KEY_API_SECRET

KEY_VEHICLES= 'response'
KEY_VEHICLE_COUNT= 'count'
KEY_VEHICLE_NAME= 'display_name'
KEY_VEHICLE_ID= 'id'
KEY_VEHICLE_ONLINE_STATE= 'state'
KEY_VEHICLE_INSERVICE_STATE= 'in_service'

KEY_RESPONSE= 'response'
KEY_RESULT= 'result'
KEY_CACHE_EXPIRATION= 'cache_expiration'

KEY_STATE_VEHICLE_DOOR_DRIVER_FRONT= 'df'
KEY_STATE_VEHICLE_DOOR_DRIVER_REAR= 'dr'
KEY_STATE_VEHICLE_DOOR_PASSENGER_FRONT= 'pf'
KEY_STATE_VEHICLE_DOOR_PASSENGER_REAR= 'pr'
KEY_STATE_VEHICLE_DOOR_TRUNK_FRONT= 'ft'
KEY_STATE_VEHICLE_DOOR_TRUNK_REAR= 'rt'
KEY_STATE_VEHICLE_LOCKED= 'locked'
KEY_STATE_VEHICLE_HOMELINK= 'homelink_nearby'
KEY_STATE_VEHICLE_SENTRY= 'sentry_mode'

KEY_STATE_CHARGE_LEVEL= 'battery_level'
KEY_STATE_CHARGE_STATE= 'charging_state'
KEY_STATE_CHARGE_PENDING= 'scheduled_charging_pending'
KEY_STATE_CHARGE_LIMIT= 'charge_limit_soc'

KEY_STATE_DRIVE_SHIFT= 'shift_state'


VALUE_STATE_CHARGE_CHARGING_READY= ['Connected', 'Stopped']
VALUE_STATE_CHARGE_CHARGING_NOW= ['Charging']
VALUE_STATE_CHARGE_BATTERY_LEVEL= 'battery_level'
VALUE_STATE_ONLINE_ASLEEP= 'asleep'
VALUE_STATE_ONLINE_ONLINE= 'online'
VALUE_STATE_ONLINE_OFFLINE= 'offline'
VALUE_STATE_PARKED= 'P'
VALUE_STATE_UNKNOWN= 'unknown'



# API request result codes
STATUS_CODE_OK= 200
STATUS_CODE_REQUEST_TIMEOUT= 408
STATUS_RESPONSE= 'response'
STATUS_RESPONSE_RESULT= 'result'
STATUS_RESPONSE_REASON= 'reason'


#
# Define our Tesla API class
#
class TeslaRequest:

  # Constructor
  def __init__(self, arguments):
    # First, validate our debug and quiet flags
    if hasattr(arguments, 'debug'):
      self.__debug= arguments.debug
    else:
      self.__debug= False
      
    if hasattr(arguments, 'quiet'):
      self.__quiet= arguments.quiet
    else:
      self.__quiet= False


    # Instantiate internal cache
    self.__cache= {}

    # Validate required values
    self.__token_refreshed= False
    if hasattr(arguments, 'token'):
      self.__token= arguments.token
    else:
      self.__token= None

    if hasattr(arguments, 'e_mail'):
      self.__e_mail= arguments.e_mail
    else:
      self.__e_mail= None
    if hasattr(arguments, 'password'):
      self.__password= arguments.password
    else:
      self.__password= None

    if hasattr(arguments, 'cache_expiration_limit'):
      self.__cache_expiration_limit= arguments.cache_expiration_limit
    else:
      self.__cache_expiration_limit= CACHE_EXPIRATION_LIMIT
      
    self.__cache_token()
    self.__cache_vehicles()


  # Obtain Owner API parameters from our special place
  def __get_owner_api_parameters(self):
    try:
      owner_api_response= requests.get(OWNERAPI_CLIENT_TOKENS_URL)

      if owner_api_response.status_code == STATUS_CODE_OK:
        owner_api= owner_api_response.json()
        
        # URL validation code from SethRobertson https://github.com/gglockner/teslajson/pull/12/files
        prefix='https://'
        owner_url= owner_api[API_VERSION][KEY_API_BASEURL]
        if (not owner_url.startswith(prefix) or '/' in owner_url[len(prefix):]
          or not owner_url.endswith(('.teslamotors.com', '.tesla.com'))):
            raise IOError('Unexpected token source URL <{}>'.format(owner_url))
        
        return owner_api
      else:
        if self.__debug:
          raise Exception('Could not obtain Owner API parameters (status code {})'.format(
            owner_api_response.status_code), self)
        else:
          raise Exception('Could not obtain Owner API parameters (status code {})'.format(
            owner_api_response.status_code))
            
    except Exception as error:
      if self.__debug:
        print('Failed to obtain expected Owner API parameters')
        print(owner_api_response)
      raise error


  # Validate current access token or obtain and cache a refreshed or a new one
  def __cache_token(self):
    if self.__token:
      if not self.__is_token_valid():
        self.__refresh_token()
        
    else:
      if self.__e_mail and self.__password:
        self.__get_token()
      else:
        raise Exception('Could not obtain a token (no credentials to obtain a new one)!', self)


  # Refresh access token
  def __refresh_token(self):
    try:
      owner_api= {}
      owner_api[API_VERSION]= {}
      
      owner_api[API_VERSION][KEY_API_BASEURL]= self.__token[KEY_TOKEN_URL]
      owner_api[API_VERSION][KEY_API_ID]= self.__token[KEY_TOKEN_ID]
      owner_api[API_VERSION][KEY_API_SECRET]= self.__token[KEY_TOKEN_SECRET]
      
      request= self.__token[KEY_TOKEN_URL] + REQUEST_TOKEN
      payload= {
        'grant_type' : 'refresh_token',
  			'client_id' : self.__token[KEY_TOKEN_ID],
  			'client_secret' : self.__token[KEY_TOKEN_SECRET],
  			'refresh_token' : self.__token[KEY_TOKEN_REFRESH]
      }
    except Exception as error:
      if self.__debug:
        print('Failed to formulate refresh token request')
      raise error

    response= requests.post(request, json= payload)

    if response.status_code == STATUS_CODE_OK:
      self.__token= response.json()
      self.__token[KEY_TOKEN_URL]= owner_api[API_VERSION][KEY_API_BASEURL]
      self.__token[KEY_TOKEN_ID]= owner_api[API_VERSION][KEY_API_ID]
      self.__token[KEY_TOKEN_SECRET]= owner_api[API_VERSION][KEY_API_SECRET]
      self.__token_refreshed= True
      
      return self.__token_refreshed
    else:
      if self.__debug:
        raise Exception('Failed to obtain token (status code {})'.format(
          response.status_code), self, request, payload)
      else:
        raise Exception('Failed to obtain token (status code {})'.format(
          response.status_code))




  # Obtain new access token
  def __get_token(self):
    try:
      owner_api= self.__get_owner_api_parameters()
      
      request= owner_api[API_VERSION][KEY_API_BASEURL] + REQUEST_TOKEN
      payload= {
        'grant_type' : 'password',
  			'client_id' : owner_api[API_VERSION][KEY_API_ID],
  			'client_secret' : owner_api[API_VERSION][KEY_API_SECRET],
  			'email' : self.__e_mail,
  			'password' : self.__password,
      }
    except Exception as error:
      if self.__debug:
        print('Failed to formulate new token request')
      raise error

    response= requests.post(request, json= payload)

    if response.status_code == STATUS_CODE_OK:
      self.__token= response.json()
      self.__token[KEY_TOKEN_URL]= owner_api[API_VERSION][KEY_API_BASEURL]
      self.__token[KEY_TOKEN_ID]= owner_api[API_VERSION][KEY_API_ID]
      self.__token[KEY_TOKEN_SECRET]= owner_api[API_VERSION][KEY_API_SECRET]
      self.__token_refreshed= True
      
      return self.__token_refreshed
    else:
      if self.__debug:
        raise Exception('Failed to obtain token (status code {})'.format(
          response.status_code), self, request, payload)
      else:
        raise Exception('Failed to obtain token (status code {})'.format(
          response.status_code))


  # Validate our current token
  def __is_token_valid(self):
    return (
      time.time() < (self.__token[KEY_TOKEN_CREATION] + self.__token[KEY_TOKEN_EXPIRATION])
      )


  # Obtain owned vehicles
  def __cache_vehicles(self):
    request= self.get_url() + OWNERAPI_VERSION + REQUEST_VEHICLES

    response= requests.get(request, headers= self.get_headers())

    if response.status_code == STATUS_CODE_OK:
      self.__vehicles= response.json()
      return True
    else:
      if self.__debug:
        raise Exception('Failed to obtain owned vehicles (status code {})'.format(
          response.status_code), self, request)
      else:
        raise Exception('Failed to obtain owned vehicles (status code {})'.format(
          response.status_code))


  # Obtain and cache indicated state of the specified vehicle
  def __cache_state(self, vehicle_index, state_type):
    attempts= self.__wake_up(vehicle_index)
      
    if self.get_vehicle_online_state(vehicle_index) == VALUE_STATE_ONLINE_ONLINE:
      headers= self.get_headers()
      request= self.get_url() + OWNERAPI_VERSION + REQUEST_VEHICLES \
        + '/' + str(self.get_vehicle_id(vehicle_index)) \
        + REQUEST_DATA_COMMANDS[state_type] + state_type
  
      response= requests.get(request, headers= headers)
      
      if response.status_code == STATUS_CODE_OK:
        state= response.json()[KEY_RESPONSE]
        state[KEY_CACHE_EXPIRATION]= time.time() + self.__cache_expiration_limit
  
        if vehicle_index not in self.__cache:
          self.__cache[vehicle_index]= {}
        self.__cache[vehicle_index][state_type]= state
          
      else:
        if self.__debug:
          if (attempts > 1):
            plural_s= "s"
          else:
            plural_s= ""
            
          raise Exception('Could not obtain state of vehicle'
            + ' named "{}" (status code {}) after {} attempt{}'.format(
              self.get_vehicle_name(vehicle_index), response.status_code, attempts, plural_s),
            self, request, headers)
        else:
          raise Exception('Could not obtain state of vehicle'
            + ' named "{}" (status code {})'.format(
              self.get_vehicle_name(vehicle_index), response.status_code))


  # Return state for the specified vehicle
  def __get_state(self, vehicle_index, state_type):
    try:
      if ((vehicle_index not in self.__cache)
        or (state_type not in self.__cache[vehicle_index])
        or (self.__cache[vehicle_index][state_type][KEY_CACHE_EXPIRATION] < time.time())):
          self.__cache_state(vehicle_index, state_type)

      return self.__cache[vehicle_index][state_type]

    except Exception as error:
      if self.__debug:
        print('Could not obtain state of vehicle named "{}" from cache'.format(
          self.get_vehicle_name(vehicle_index)))
      raise error


  # Wake up specified vehicle
  def __wake_up(self, vehicle_index):
    headers= self.get_headers()
    request= self.get_url() + OWNERAPI_VERSION + REQUEST_VEHICLES \
      + '/' + str(self.get_vehicle_id(vehicle_index)) \
      + '/' + COMMAND_WAKE_UP
      
    awake= False
    attempts= 0
    while attempts < MAX_ATTEMPTS:
      attempts+= 1
      response= requests.post(request, headers= headers)
      time.sleep(ATTEMPT_RETRY_DELAY)
    
      if response.status_code == STATUS_CODE_OK:
        if response.json()[STATUS_RESPONSE][KEY_VEHICLE_ONLINE_STATE] == VALUE_STATE_ONLINE_ONLINE:
          awake= True
          self.__vehicles[KEY_VEHICLES][vehicle_index][KEY_VEHICLE_ONLINE_STATE]= VALUE_STATE_ONLINE_ONLINE
          break

    if not awake:
      if self.__debug:
        raise Exception('Could not wake up vehicle'
          + ' named "{}" (response code {}, status is {})'.format(
            self.get_vehicle_name(vehicle_index), response.status_code,
            response.json()[STATUS_RESPONSE][KEY_VEHICLE_ONLINE_STATE]),
          self, request, headers)
      else:
        raise Exception('Could not wake up vehicle'
          + ' named "{}" (response code {}, status is {})'.format(
            self.get_vehicle_name(vehicle_index), response.status_code,
            response.json()[STATUS_RESPONSE][KEY_VEHICLE_ONLINE_STATE]))
    else:
      return attempts


  # Expire indicated state cache
  def __expire_cache(self, vehicle_index, state_type):
    self.__cache[vehicle_index][state_type][KEY_CACHE_EXPIRATION]= 0
              

  # Formulate and return stored token parameters
  def get_token(self):
    try:
      return self.__token
    except Exception as error:
      if self.__debug:
        print('No token parameters set!')
      raise error


  # Force refresh of our access token
  def force_token_refresh(self):
    self.__refresh_token()


  # Do we have a refreshed token (make sure to save it!)
  def is_token_refreshed(self):
    return self.__token_refreshed


  # Formulate and return stored Owner API URL
  def get_url(self):
    try:
      return self.__token[KEY_TOKEN_URL]
    except Exception as error:
      if self.__debug:
        print('No Owner API URL set!')
      raise error


  # Formulate and return stored Owner API request headers
  def get_headers(self):
    try:
      return {
        'Authorization' : self.__token[KEY_TOKEN_TYPE] + ' ' + self.__token[KEY_TOKEN],
        'User-Agent' : 'teslarequest.py'
        }
    except Exception as error:
      if self.__debug:
        print('Failed to formulate Owner API request headers!')
      raise error


  # Return count of stored vehicles
  def get_vehicle_count(self):
    try:
      return self.__vehicles[KEY_VEHICLE_COUNT]
    except Exception as error:
      if self.__debug:
        print('No vehicles stored!')
      raise error


  # Return the name of the specified vehicle
  def get_vehicle_name(self, vehicle_index):
    try:
      return self.__vehicles[KEY_VEHICLES][vehicle_index][KEY_VEHICLE_NAME]
    except Exception as error:
      if self.__debug:
        print('Could not access the name of vehicle #{}'.format(vehicle_index))
      raise error


  # Return the ID of the specified vehicle
  def get_vehicle_id(self, vehicle_index):
    try:
      return self.__vehicles[KEY_VEHICLES][vehicle_index][KEY_VEHICLE_ID]
    except Exception as error:
      if self.__debug:
        print('Could not access the ID of vehicle #{}'.format(vehicle_index))
      raise error


  # Return the online state of the specified vehicle
  def get_vehicle_online_state(self, vehicle_index):
    try:
      return self.__vehicles[KEY_VEHICLES][vehicle_index][KEY_VEHICLE_ONLINE_STATE]
    except Exception as error:
      if self.__debug:
        print('Could not access the online state of vehicle #{}'.format(vehicle_index))
      raise error


  # Return the in-service state of the specified vehicle
  def is_vehicle_in_service(self, vehicle_index):
    try:
      return self.__vehicles[KEY_VEHICLES][vehicle_index][KEY_VEHICLE_INSERVICE_STATE]
    except Exception as error:
      if self.__debug:
        print('Could not access the in-service state of vehicle #{}'.format(vehicle_index))
      raise error


  # Return full vehicle state dump for the specified vehicle
  def get_vehicle_state(self, vehicle_index):
    try:
      return self.__get_state(vehicle_index, REQUEST_DATA_STATE_VEHICLE)
    except Exception as error:
      if self.__debug:
        print('Could not access general state for vehicle #{}'.format(vehicle_index))
      raise error


  # Return charge state for the specified vehicle
  def get_drive_state(self, vehicle_index):
    try:
      return self.__get_state(vehicle_index, REQUEST_DATA_STATE_DRIVE)
    except Exception as error:
      if self.__debug:
        print('Could not access drive state for vehicle #{}'.format(vehicle_index))
      raise error


  # Return charge state for the specified vehicle
  def get_charge_state(self, vehicle_index):
    try:
      return self.__get_state(vehicle_index, REQUEST_DATA_STATE_CHARGE)
    except Exception as error:
      if self.__debug:
        print('Could not access charge state for vehicle #{}'.format(vehicle_index))
      raise error


  # Return charging limit for the specified vehicle
  def get_charging_limit(self, vehicle_index):
    return self.get_charge_state(vehicle_index)[KEY_STATE_CHARGE_LIMIT]


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
      state= self.get_vehicle_state(vehicle_index)
      for door in doors.keys():
        if (state[door] != 0):
          open_doors.append(doors[door])

      return open_doors

    except Exception as error:
      if self.__debug:
        print('Could not obtain open doors and trunks for vehicle named "{}"'.format(
          self.get_vehicle_name(vehicle_index)))
      raise error


  # Return a list of open doors and trunks for the specified vehicle
  def get_vehicle_location(self, vehicle_index):
    try:
      state= self.get_drive_state(vehicle_index)

      return (state['latitude'], state['longitude'])

    except Exception as error:
      if self.__debug:
        print('Could not obtain location for vehicle named "{}"'.format(
          self.get_vehicle_name(vehicle_index)))
      raise error


  # Return a boolean indicating the locked state for the specified vehicle
  def is_vehicle_locked(self, vehicle_index):
    try:
      return self.__get_state(
        vehicle_index, REQUEST_DATA_STATE_VEHICLE)[KEY_STATE_VEHICLE_LOCKED]
    except Exception as error:
      if self.__debug:
        print('Could not obtain locked state for vehicle named "{}"'.format(
          self.get_vehicle_name(vehicle_index)))
      raise error


  # Return a boolean indicating proximity to a programmed HomeLink location ("unknown" string for absent indicator)
  def is_vehicle_near_homelink(self, vehicle_index):
    try:
      state= self.__get_state(vehicle_index, REQUEST_DATA_STATE_VEHICLE)
      
      if (KEY_STATE_VEHICLE_HOMELINK in state):
        return state[KEY_STATE_VEHICLE_HOMELINK]
      else:
        return VALUE_STATE_UNKNOWN
    except Exception as error:
      if self.__debug:
        print('Could not obtain HomeLink state for vehicle named "{}"'.format(
          self.get_vehicle_name(vehicle_index)))
      raise error


  # Return a boolean indicating Sentry Mode activation state ("unknown" string for absent indicator)
  def is_vehicle_sentry_mode_active(self, vehicle_index):
    try:
      state= self.__get_state(vehicle_index, REQUEST_DATA_STATE_VEHICLE)
      
      if (KEY_STATE_VEHICLE_SENTRY in state):
        return state[KEY_STATE_VEHICLE_SENTRY]
      else:
        return VALUE_STATE_UNKNOWN
    except Exception as error:
      if self.__debug:
        print('Could not obtain Sentry Mode state for vehicle named "{}"'.format(
          self.get_vehicle_name(vehicle_index)))
      raise error


  # Return a boolean indicating the parked state for the specified vehicle
  def is_vehicle_parked(self, vehicle_index):
    try:
      state= self.__get_state(vehicle_index, REQUEST_DATA_STATE_DRIVE)
      
      if (KEY_STATE_DRIVE_SHIFT in state):
        return (state[KEY_STATE_DRIVE_SHIFT] == VALUE_STATE_PARKED)
      else:
        return False
    except Exception as error:
      if self.__debug:
        print('Could not obtain parked state for vehicle named "{}"'.format(
          self.get_vehicle_name(vehicle_index)))
      raise error


  # Return a boolean indicating charging readiness for the specified vehicle
  def is_vehicle_ready_to_charge(self, vehicle_index):
    try:
      return (
        ((self.__get_state(vehicle_index, REQUEST_DATA_STATE_CHARGE)[KEY_STATE_CHARGE_STATE]
          in VALUE_STATE_CHARGE_CHARGING_READY)
        and
        (self.__get_state(vehicle_index, REQUEST_DATA_STATE_CHARGE)[KEY_STATE_CHARGE_PENDING]
          == True))
          
        or self.is_vehicle_charging(vehicle_index))
    except Exception as error:
      if self.__debug:
        print('Could not obtain charging state for vehicle named "{}"'.format(
          self.get_vehicle_name(vehicle_index)))
      raise error


  # Return a boolean indicating charging readiness for the specified vehicle
  def is_vehicle_charging(self, vehicle_index):
    try:
      return (self.__get_state(vehicle_index, REQUEST_DATA_STATE_CHARGE)[KEY_STATE_CHARGE_STATE]
          in VALUE_STATE_CHARGE_CHARGING_NOW)
    except Exception as error:
      if self.__debug:
        print('Could not obtain charging state for vehicle named "{}"'.format(
          self.get_vehicle_name(vehicle_index)))
      raise error


  # Return current battery level % for the specified vehicle
  def get_battery_level(self, vehicle_index):
    try:
      return (self.__get_state(
        vehicle_index, REQUEST_DATA_STATE_CHARGE)[VALUE_STATE_CHARGE_BATTERY_LEVEL])
    except Exception as error:
      if self.__debug:
        print('Could not obtain charging state for vehicle named "{}"'.format(
          self.get_vehicle_name(vehicle_index)))
      raise error


  # Issue a command to the specified vehicle
  def issue_command(self, vehicle_index, command, payload):
    headers= self.get_headers()
    request= self.get_url() + OWNERAPI_VERSION + REQUEST_VEHICLES \
      + '/' + str(self.get_vehicle_id(vehicle_index)) \
      + '/command/' + command

    response= requests.post(request, headers= headers, json= payload)

    if response.status_code == STATUS_CODE_OK:
      return response.json()[STATUS_RESPONSE][STATUS_RESPONSE_RESULT]
    else:
      if self.__debug:
        raise Exception('Failed to issue command "{}" to vehicle named "{}" (status code {})'.format(command, self.get_vehicle_name(vehicle_index), response.status_code), self, request, response.json())
      else:
        raise Exception('Failed to issue command "{}" to vehicle named "{}" (status code {})'.format(command, self.get_vehicle_name(vehicle_index), response.status_code))


  # Issue a command to the specified vehicle to set its charging limit
  def set_charging_limit(self, vehicle_index, limit):
    payload= {'percent' : limit}
    self.__expire_cache(vehicle_index, REQUEST_DATA_STATE_CHARGE)
    return self.issue_command(vehicle_index, 'set_charge_limit', payload)


  # Issue a command to the specified vehicle to set maximum range charging limit
  def set_charging_limit_max(self, vehicle_index):
    payload= {}
    self.__expire_cache(vehicle_index, REQUEST_DATA_STATE_CHARGE)
    return self.issue_command(vehicle_index, 'charge_max_range', payload)


  # Issue a command to the specified vehicle to set standard charging limit
  def set_charging_limit_standard(self, vehicle_index):
    payload= {}
    self.__expire_cache(vehicle_index, REQUEST_DATA_STATE_CHARGE)
    return self.issue_command(vehicle_index, 'charge_standard', payload)


  # Issue a command to the specified vehicle to set its charging limit
  def set_sentry_mode_on(self, vehicle_index):
    payload= {'on' : True}
    self.__expire_cache(vehicle_index, REQUEST_DATA_STATE_VEHICLE)
    return self.issue_command(vehicle_index, 'set_sentry_mode', payload)


  # Issue a command to the specified vehicle to set its charging limit
  def set_sentry_mode_off(self, vehicle_index):
    payload= {'on' : False}
    self.__expire_cache(vehicle_index, REQUEST_DATA_STATE_VEHICLE)
    return self.issue_command(vehicle_index, 'set_sentry_mode', payload)