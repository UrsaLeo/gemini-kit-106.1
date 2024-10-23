import requests
import json
import os
import zipfile
import logging
from ctypes import CDLL
import ctypes
import asyncio

logger = logging.getLogger(__name__)

#NOTE: if you're looking to set the secure_token data or twin_version_id please look at the user-data.json file
# and app-data.json file in the source/apps/data folder

app_data_loaded = False
user_data_loaded = False

partner_secure_data = ""

def get_auth_token(api_path, refresh_token):
  try:
    base_url = partner_secure_data['baseUrl']
    token_api = f"{base_url}{api_path}?refreshToken={refresh_token}"
   # print(f"Refresh token API: {token_api}")
    token_response = requests.get(token_api)
    token_response.raise_for_status()
    token = json.loads(token_response.text)
    #print(f"new token:{token}")
    return token
  except Exception as e:
    print("Error Fetching the refresh token")
    raise SystemExit(f"Get auth token API failed: {token_response.status_code}\n error: {e}")


def get_partner_secure_data():
    global partner_secure_data
    global user_data_loaded

    if user_data_loaded:
        return partner_secure_data

    try:
        load_local_secure_data()
        #partner_secure_data = json.loads(default_secure_data)
        return partner_secure_data

        sdklib_path = os.path.join(os.path.dirname(__file__) , "../../../lib/x64/GfnRuntimeSdk.dll")
        print (f"loading sdk from path {sdklib_path}")
        gfnsdk_library  =  CDLL(sdklib_path)

        #print("DLL IS LOADED")
        logger.info("DLL is LOADED")

        gfnsdk_library.gfnInitializeRuntimeSdk(0)
        logger.info("GFN Sdk initialized")

        # Checking if the GFN SDK is activated in cloud env
        # TBD: load partnersecuredata from local file if not running in cloud
        is_running_in_cloud = gfnsdk_library.gfnIsRunningInCloud()
        logger.info(f"is GFN in cloud={is_running_in_cloud}")

        if not is_running_in_cloud:
            #print("Not running in cloud")
            load_local_secure_data()
            #partner_secure_data = json.loads(default_secure_data)
            return partner_secure_data

        gfnsdk_library.gfnGetPartnerSecureData.restype = ctypes.c_int
        gfnsdk_library.gfnGetPartnerSecureData.argtypes = [ctypes.POINTER(ctypes.c_char_p)]

        secure_data_ptr = ctypes.c_char_p()  # Allocate a char pointer directly
        error_code = gfnsdk_library.gfnGetPartnerSecureData(ctypes.byref(secure_data_ptr))

        if error_code == 0:
            partner_secure_data_string = secure_data_ptr.value.decode('utf-8')  # Dereference and decode
            partner_secure_data = json.loads(partner_secure_data_string)

        #elif error_code == -29:
        #    partner_secure_data = json.loads(default_secure_data)
        #    logger.info(f"error code from gfnGetPartnerSecureData [{error_code}] - using default_seure_data")


        else:
            logger.error(f"Could not load partner secure data - error code = {error_code} ")
            raise SystemExit(f"Could not load partner secure data - error code = {error_code} ")
        #logger.info(f"partnerSecureData={partner_secure_data_string}")

        user_data_loaded = True
        return partner_secure_data
    except Exception as e:
        logger.info("Exception: {}".format(e))
        #print(f"Error loading DLL: {e}")
        raise SystemExit(f"Could not load partner secure data - error code = {error_code} ")

# Note when running locally, load_local_secure_data will be called
# app_data.json is  mandatory, user_data is optional and in our
# custom remote solution, these may be created at two different points
# app data when the application is started, and user-data when user is
# connected to the web-rtc connection

def load_local_secure_data():
    global app_data_loaded, user_data_loaded, partner_secure_data
    # Read the app-data JSON file
    data_root_path = os.path.join(os.path.dirname(__file__) , "..","..","..","..","..","apps","data")
    app_data_path = os.path.join(data_root_path,"app_data.json")
    user_data_path = os.path.join(data_root_path,"user_data.json")
    if (os.path.exists(app_data_path)):
        with open(app_data_path, 'r') as file:
            partner_secure_data = json.load(file)
            app_data_loaded = True
    else:
        raise SystemExit(f"could not find <app-root>/app-data/app_data.json when running locally")

    #load user_data if it exists
    if (os.path.exists(user_data_path)):
        with open(user_data_path, 'r') as file:
            user_data = json.load(file)
            user_data_loaded = True
            partner_secure_data = {**partner_secure_data, **user_data}



def expose_new_token_or_continue(response:any=None,type_of_secure_call:str="GET", api_path:str=None, request_body:any={},params={}):
    global partner_secure_data
    global refresh_token
    if 'html' in response.text.lower() or response.status_code == 403:
        #print("IT GOT HTML")
        refresh_token = partner_secure_data['refreshToken']
        token = get_auth_token(refresh_token_api,refresh_token)
        partner_secure_data['authToken'] = token['authToken']
        partner_secure_data['refreshToken'] = token['refreshToken']
        type_of_secure_call = type_of_secure_call.upper()
        if type_of_secure_call == "GET":
            return  make_get_secure_call(api_path,params)
        elif type_of_secure_call == "POST":
            return  make_post_secure_call(api_path,request_body,params)
        elif type_of_secure_call == "DELETE":
            return  make_delete_secure_call(api_path=api_path,params=params)
        elif type_of_secure_call == "PUT":
            return  make_put_secure_call(api_path=api_path,request_body=request_body,params=params)
        else:
            raise SystemExit(f"Invalid type of secure call: {type_of_secure_call}")

    else:
        return response

def make_get_secure_call(api_path,params={}):
    global partner_secure_data
    global refresh_token_api
    base_url = partner_secure_data['baseUrl']
    #print(f"make_get_secure_call: Partner Secure Data: {partner_secure_data}")
    #print(f"URL: {api_path}")
    try:
        response =  requests.get(f"{base_url}{api_path}", headers={'Authorization': f"Bearer {partner_secure_data['authToken']}"},params=params)
        response.raise_for_status()
        #print(f"RESPONSE FROM BE: {response.text}")
        return expose_new_token_or_continue(response=response,api_path=api_path,type_of_secure_call="GET",params=params)
    except requests.exceptions.RequestException as e:
        print(f"Error GET data from API: {e}")
        #raise SystemExit(f"Error GET data from API: {e}") from e
        return None

def make_post_secure_call(api_path,request_body,params={}):
    global partner_secure_data
    global refresh_token_api
    base_url = partner_secure_data['baseUrl']
    try:
        #print(f"make_post_secure_call: Partner Secure Data: {partner_secure_data}")
        #print(f"make_post_secure_call: Request Body: {request_body}")
        response =  requests.post(f"{base_url}{api_path}",data=request_body,headers={'Authorization': f"Bearer {partner_secure_data['authToken']}"},params=params)
        response.raise_for_status()
        logger.info(f"RESPONSE FROM BE: {response.text}")
        return expose_new_token_or_continue(response=response,api_path=api_path,request_body=request_body,type_of_secure_call="POST",params=params)
    except requests.exceptions.RequestException as e:
        # raise SystemExit(f"Error POST data from API: {e}") from e
        logger.error(f"make_post_secure_call: error: {e}")
        return None

def make_delete_secure_call(api_path,request_body,params={}):
    global partner_secure_data
    global refresh_token_api
    base_url = partner_secure_data['baseUrl']
    #print(f"make_delete_secure_call: Partner Secure Data: {partner_secure_data}")
    try:
        response =  requests.delete(f"{base_url}{api_path}", headers={'Authorization': f"Bearer {partner_secure_data['authToken']}"},params=params,data=request_body)
        response.raise_for_status()
        #print(f"RESPONSE FROM BE: {response.text}")
        return expose_new_token_or_continue(response=response,api_path=api_path,type_of_secure_call="DELETE",params=params)
    except requests.exceptions.RequestException as e:
        print(f"Error DELETE data from API: {e}")
        return None

def make_put_secure_call(api_path,request_body,params={}):
    global partner_secure_data
    global refresh_token_api
    base_url = partner_secure_data['baseUrl']
    try:
        #print(f"make_post_secure_call: Partner Secure Data: {partner_secure_data}")
        response =  requests.put(f"{base_url}{api_path}",request_body,headers={'Authorization': f"Bearer {partner_secure_data['authToken']}"},params=params)
        response.raise_for_status()
        #print(f"RESPONSE FROM BE: {response.text}")
        return expose_new_token_or_continue(response=response,api_path=api_path,request_body=request_body,type_of_secure_call="PUT",params=params)
    except requests.exceptions.RequestException as e:
        logger.error(f"Error PUT data from API: {e}")
        return None

def load_mapping_file():
    base_path = os.path.join(os.path.dirname(__file__), "sensor_path_mapping")
    print(os.path.join(base_path, "sensor_path_mapping.json"))
    file_path = os.path.join(base_path, "sensor_path_mapping.json")

    try:
        with open(file_path, "r") as json_file:
            data = json.load(json_file)
        print("File loaded!")
        return data
    except Exception as e:
        print(e)
        print("Failed to read the MAP file")
        return []

def get_default_camera_path(twin_version_id:str):
    path_mapping = load_mapping_file()
    if len(path_mapping) > 0:
        filtered_path = next((entry["default_camera"] for entry in path_mapping if entry["twinVersionId"] == twin_version_id), None)
        print(f"filtered path = {filtered_path}")
        return filtered_path
    else:
        return None
