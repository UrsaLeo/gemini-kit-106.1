from . import gdn_services as gdn
import logging

import ul.gemini.services.utils as utils

logger = logging.getLogger(__name__)


partner_secure_data = gdn.get_partner_secure_data()


should_open_artifact_window = False
get_integration_entity_list_attempted = False
entity_type_list_data = None
rfi_details = None
rfi_get_details_attempted = False
submittals_details = None
submittals_details_attempted = None
document_data_attempted = False
document_file_data = None
source_list = None


def get_partner_secure_data():
    return partner_secure_data

#Returns the integration entity type list - not used currently?
def get_integration_entity_type_list():
    default_json = [
  {
    "id": "11111111-1111-1111-1111-111111111115",
    "type": "SUBMITTAL",
    "displayFields": "",
    "levels": "PROJECT"
  },
  {
    "id": "11111111-1111-1111-1111-111111111112",
    "type": "DOCUMENT",
    "displayFields": "",
    "levels": "COMPANY,PROJECT"
  },
  {
    "id": "11111111-1111-1111-1111-111111111113",
    "type": "RFI",
    "displayFields": "",
    "levels": "PROJECT"
  }
]
    global entity_type_list_data
    global get_integration_entity_list_attempted

    if get_integration_entity_list_attempted:
        return entity_type_list_data

    #response = make_get_secure_call(api_path
    # =f"/api/integration-entity-type/list", run_local=True)
    #loop = asyncio.getunning_loop()
    try:
            #response = await loop.run_in_executor(None, make_get_secure_call, "/api/integration-entity-type/list")
            response =  gdn.make_get_secure_call(api_path=f"/api/integration-entity-type/list")
            get_integration_entity_list_attempted = True

            if response is None:
                print("Received None from /api/integration-entity-type/list")
                return default_json
            try:
                entity_type_list_data = response.json()
            except :
                print ("error getting Jaon from /api/integration-entit-type/list")
                return default_json
            return entity_type_list_data
    except Exception as e:
        #logger.error(f"Error fetching integration entity type list: {e}")
        get_integration_entity_list_attempted = False
        return default_json


def get_rfi_details():
    global partner_secure_data
    if "authToken" not in partner_secure_data :
        return []

    global rfi_get_details_attempted
    global rfi_details
    client_id = partner_secure_data['clientId']
    source = 'PROCORE'
    twin_id = partner_secure_data['twinId']
    level = "PROJECT"
    entity_type = 'RFI'
    try:
        if rfi_get_details_attempted:
            return rfi_details

        response = gdn.make_get_secure_call(f"/api/integration-source/client/{client_id}/source/{source}/integration-entity-type/{entity_type}?twinId={twin_id}&level={level}&page=1&pageSize=50000")
        rfi_get_details_attempted = True
        if response is None:
            return []
        rfi_details = response.json()
        return rfi_details
    except Exception as e:
        print(f"Error fetching RFI details: {e}")
        rfi_get_details_attempted = False
        return []

def get_submittals_details():
    global partner_secure_data
    global submittals_details_attempted
    global submittals_details
    if "authToken" not in partner_secure_data :
        return []

    client_id = partner_secure_data['clientId']
    source = 'PROCORE'
    twin_id = partner_secure_data['twinId']
    level = "PROJECT"
    entity_type = 'SUBMITTAL'
    try:
        if submittals_details_attempted:
            return submittals_details

        response = gdn.make_get_secure_call(f"/api/integration-source/client/{client_id}/source/{source}/integration-entity-type/{entity_type}?twinId={twin_id}&level={level}&page=1&pageSize=50000")

        submittals_details_attempted = True
        if response is None:
            return []

        submittals_details = response.json()
        return submittals_details
    except Exception as e:
        print(f"Error getting submittals details {e}")
        submittals_details_attempted = False
        return []


#Returns the list of integration sources (eg. Procore, Internal etc.)
#This can be useful for example when you have documents coming form multiple integation sources
def get_source_list():
    global source_list
    if source_list is not None:
        return source_list
    try:
        response = gdn.make_get_secure_call(f"/api/integration-source/list")
        if response is None:
                return []

        list = response.json()
        source_list = list
        return source_list
    except Exception as e:
        logger.error(f"Error while getting the source list {e}")
        logger.error("Due to error occured returning an empty array")
        return []



def get_procore_document_structure():
    global partner_secure_data
    global document_file_data
    global document_data_attempted
    if partner_secure_data["authToken"] == None:
        return []

    client_id = partner_secure_data['clientId']
    twin_id = partner_secure_data['twinId']

    try:

        if document_data_attempted:
            return document_file_data
        # /api/integration-source/client/d090e8bd-2e70-4dcc-9162-9f9c0c4090d8/source/PROCORE/integration-entity-type/DOCUMENT?twinId=d4bd9c9c-fe70-407f-ae24-cc669de1f5ae&level=PROJECT
        #response = make_get_secure_call(api_path=f"/api/document/client/{client_id}/docs/list/all?pageSize=10000")
        response =  gdn.make_get_secure_call(api_path=f"/api/integration-source/client/{client_id}/source/PROCORE/integration-entity-type/DOCUMENT?twinId={twin_id}&level=PROJECT&page=1&pageSize=1000000")
        if response is None:
                return []

        #print(response)
        #print(partner_secure_data)
        response.raise_for_status()
        data = response.json()
        document_file_data = data["files"]
        document_data_attempted = True
        return document_file_data
    except Exception as e:
        print(f"Error while getting the document API {e}")
        print("Due to error occured returning an empty array")
        document_data_attempted = False
        return []

#TBD replace the check if a path is a file with this logic as docuemnt_file_data only has files
#while the current check - only checks if the filename has an extension or not
def is_a_file(path):
    return document_file_data.contains(path)

def search_for_documents(search_text:str):
    global partner_secure_data
    if "authToken" not in partner_secure_data :
        return []

    client_id = partner_secure_data['clientId']
    twin_id = partner_secure_data['twinId']
    try:

        if search_text:
            response = gdn.make_get_secure_call(api_path=f"/api/integration-source/client/{client_id}/source/PROCORE/integration-entity-type/DOCUMENT?twinId={twin_id}&level=PROJECT&page=1&pageSize=50000&searchText={search_text}")
            if response is None:
                return []

            data = response.json()
            document_file_data = data["files"]
            return document_file_data
        else:
            return get_procore_document_structure()
    except Exception as e:
        print(f"Error in searching for documents {e}")
        return []

def search_for_rfis(search_text:str):
    global partner_secure_data
    if "authToken" not in partner_secure_data :
        return []

    client_id = partner_secure_data['clientId']
    twin_id = partner_secure_data['twinId']
    try:
        if search_text:
            response =  gdn.make_get_secure_call(api_path=f"/api/integration-source/client/{client_id}/source/PROCORE/integration-entity-type/RFI?twinId={twin_id}&level=PROJECT&page=1&pageSize=50000&searchText={search_text}")
            if response is None:
                return []
            rfi_details = response.json()
            return rfi_details
        else:
            return get_rfi_details()
    except Exception as e:
        print(f"Error in searching for RFI {e}")
        return []

def search_for_submittals_locally(search_text:str):
    global submittals_details
    if search_text:
        search_text_lower = search_text.lower()
        submittals_filtered_data = [submittal for submittal in submittals_details['data'] if search_text_lower in submittal['title'].lower()]
        submittals = {'data': submittals_filtered_data}
        return submittals
    else:
        return get_submittals_details()

def search_for_rfis_locally(search_text:str):
    global rfi_details
    if search_text:
        search_text_lower = search_text.lower()
        rfis_filtered_data = [rfi for rfi in rfi_details['data'] if search_text_lower in rfi['subject'].lower()]
        rfis = {'data': rfis_filtered_data}
        return rfis
    else:
        return get_rfi_details()



def search_for_submittals(search_text:str):
    global partner_secure_data
    if "authToken" not in partner_secure_data :
        return []

    client_id = partner_secure_data['clientId']
    twin_id = partner_secure_data['twinId']
    try:
        if search_text:
            response = gdn.make_get_secure_call(api_path=f"/api/integration-source/client/{client_id}/source/PROCORE/integration-entity-type/SUBMITTAL?twinId={twin_id}&level=PROJECT?page=1&pageSize=50000&searchText={search_text}")
            if response is None:
                return []
            submittals_details = response.json()
            return submittals_details
        else:
            return get_submittals_details()
    except Exception as e:
        print(f"Error in searching for submittals {e}")
        return []



def delete_integration_entity(asset_id: str, integration_entity_id: str,integration_entity_ids):
    delete_request_body = {}
    encode_asset_id = utils.encode_url(asset_id)
    twin_id = partner_secure_data['twinId']

    if integration_entity_id:
        delete_request_body['integrationEntityId'] = integration_entity_id
    else:
        delete_request_body['integrationEntityIds'] = integration_entity_ids

    print(delete_request_body)
    try:
        response = gdn.make_delete_secure_call(api_path=f"/api/twin-assets-integration-entity/twin/{twin_id}/asset/{encode_asset_id}",request_body=delete_request_body)
        if response is None:
                return []
        return response
    except Exception as e:
        print(f"Error in deleting the integration entity {e}")
        return []


def get_prim_path_submittals(prim_path):
    global partner_secure_data
    if "authToken" not in partner_secure_data :
        return []

    print(f"get_prim_path_submittals: {prim_path}")
    twin_id = partner_secure_data["twinId"]
    entityTypeList = get_integration_entity_type_list()
    submittal_id = next((item['id'] for item in entityTypeList if item['type'] == 'SUBMITTAL'), None)
    if submittal_id is None:
        print("Submittal Master Data is not configured")
        return []
    url_encoded = prim_path.replace("/", "%2F")
    print(url_encoded)
    response = gdn.make_get_secure_call(api_path=f"/api/twin-assets-integration-entity/twin/{twin_id}/asset/{url_encoded}", params={"entityTypeId": f"{submittal_id}", "level": "PROJECT"})
    if response is None:
        return []
    return response.json()

def get_prim_asset_documents(prim_path: str):
    client_id = partner_secure_data['clientId']
    twin_id = partner_secure_data['twinId']
    entityTypeList = get_integration_entity_type_list()
    document_id = next((item['id'] for item in entityTypeList if item['type'] == 'DOCUMENT'), None)
    if document_id is None:
        print("Document Master Data is not configured")
        return []
    url_encoded = prim_path.replace("/", "%2F")
    print(url_encoded)
    try:
        response = gdn.make_get_secure_call(api_path=f"/api/twin-assets-integration-entity/twin/{twin_id}/asset/{url_encoded}", params={"entityTypeId": f"{document_id}", "level": "PROJECT"})
        data = response.json()
        if len(data) == 0 : return []
        prim_asset_data = data
        return prim_asset_data
    except Exception as e:
        print(f"Error while getting the prim path documents {e}")
        print("Error caused while getting the relavnt documents")
        return []

def attach_submittals(prim_path,submittals: any):
    global partner_secure_data

    if "authToken" not in partner_secure_data :
        return []

    procore_id = get_source_id('PROCORE')
    entity_id = get_id_by_entity_type('SUBMITTAL')

    twin_id = partner_secure_data['twinId']
    asset_id = utils.encode_url(prim_path)
    print(f"Asset Id: {asset_id}")

    print(f"attach_submittals={prim_path}, {submittals}")
    submittals_request_body = {
        "clientId": partner_secure_data["clientId"],
        "integrationSourceId": procore_id,
        "integrationSource": "PROCORE",
        "level": "PROJECT"
    }
    if len(submittals) == 0:
        print("No Submittals to attach")
        return
    elif len(submittals) == 1:
        submittals_request_body['externalId']  =  submittals[0],
    else:
        submittals_request_body['externalIds']  =  submittals,
    try:
       response = gdn.make_post_secure_call(api_path=f"/api/twin-assets-integration-entity/twin/{twin_id}/asset/{asset_id}/entity-type-id/{entity_id}",request_body=submittals_request_body)
       print(f"attach_submittals: Response: {response}")
       return response
    except Exception as e:
        print(f"Error in attaching RFI: {e}")
        return []

def attach_rfi(prim_path,rfis: any):
    global partner_secure_data

    if "authToken" not in partner_secure_data :
        return []


    print(f"attach_rfi={prim_path}, {rfis}")
    procore_id = get_source_id('PROCORE')
    entity_id = get_id_by_entity_type('RFI')

    twin_id = partner_secure_data['twinId']
    asset_id = utils.encode_url(prim_path)
    print(f"Asset Id: {asset_id}")
    rfi_request_body = {
        "clientId": partner_secure_data["clientId"],
        "integrationSourceId": procore_id,
        "integrationSource": "PROCORE",
        "level": "PROJECT"
    }

    if len(rfis) == 0:
        print("No RFI to attach")
        return
    elif len(rfis) == 1:
        rfi_request_body["externalId"] = rfis[0]
    else:
        rfi_request_body["externalIds"] = rfis

    try:
       response =  gdn.make_post_secure_call(api_path=f"/api/twin-assets-integration-entity/twin/{twin_id}/asset/{asset_id}/entity-type-id/{entity_id}",request_body=rfi_request_body)
       print(f"attach_rfi: Response: {response}")
       return response
    except Exception as e:
        print(f"Error in attaching RFI: {e}")
        return []

def get_rfi_for_selected_prim(prim_path:str):
    global partner_secure_data
    if "authToken" not in partner_secure_data :
        return []

    print(f"get_rfi_for_selected_prim: {prim_path}")
    twin_id = partner_secure_data["twinId"]
    entityTypeList = get_integration_entity_type_list()
    print(f"Integration EntityType list: ",entityTypeList)
    rfi_id = next((item['id'] for item in entityTypeList if item['type'] == 'RFI'), None)
    if rfi_id is None:
        print("RFI Master Data is not configured")
        return
    url_encoded = utils.encode_url(prim_path)
    print(url_encoded)
    response = gdn.make_get_secure_call(api_path=f"/api/twin-assets-integration-entity/twin/{twin_id}/asset/{url_encoded}", params={"entityTypeId": f"{rfi_id}", "level": "PROJECT"})
    if response is None:
        return []
    return response.json()


def get_source_id(source: str):
    data = get_source_list()
    source_id = next((item["id"] for item in data if item["source"] == source), None)
    logger.info(f"Source ID: {source_id}")
    return source_id

def get_id_by_entity_type(type):
    global entity_type_list_data
    id =  next((item["id"] for item in entity_type_list_data if item["type"] == type), None)
    print(f"Entity type Id : {id}")
    return id

def attach_a_document(prim_path: str, procore_paths: str):
    client_id = partner_secure_data['clientId']
    twin_id = partner_secure_data['twinId']
    source_id = get_source_id('PROCORE')
    entity_id = get_id_by_entity_type('DOCUMENT')
    # external_ids = []
    data = {
        "clientId": client_id,
        "integrationSourceId": source_id,
        "integrationSource": "PROCORE",
        "level": "PROJECT"
    }
    if len(procore_paths) == 0:
        print("No Attchment to attach")
        return

    if len(procore_paths) == 1:
        # external_ids.append(procore_paths[0])
        data["externalId"] = procore_paths[0]
    else:
        # for path in procore_paths:
        #     external_ids.append(path)
        data["externalIds"] = procore_paths
    print(f"Data={data}")
    asset_id = utils.encode_url(prim_path)
    try:
        response  = gdn.make_post_secure_call(api_path=f"/api/twin-assets-integration-entity/twin/{twin_id}/asset/{asset_id}/entity-type-id/{entity_id}",request_body=data)
        return response
    except Exception as e:
        print(f"Error in attaching Dpocument: {e}")
        return []



def create_document_event(api_path,document_event_body):
    try:
        print(f"document_event_body={document_event_body}")
        response = gdn.make_post_secure_call(api_path=api_path,request_body=document_event_body)
        print(response)
        print(partner_secure_data)
        response.raise_for_status()
        print(f"Sucessfully creted the document event {response.json()}")
        return response
    except Exception as e:
        print(f"Error When creating document event {e}")
        return []


def custom_sort(data:any, key:str,attribute_key:str,reverse:bool=False):
    sorted_data = []
    none_type_element = []
    other_elements = []
    print("DATATA")
    print(data)

    for i in data:
        if i[key] is None:
            none_type_element.append(i)
        else:
            other_elements.append(i)

    other_elements.sort(key=lambda x:x.get(key,{}).get(attribute_key) or "",reverse=reverse)
    sorted_data.extend(none_type_element)
    sorted_data.extend(other_elements)
    return sorted_data


def sort_data(entity_type:str,loaded_data:any,sort_by:str, is_sort_selected: bool, type_of_sort:str = "ASC"):
    if entity_type == "SUBMITTAL":
        if is_sort_selected and type_of_sort == "ASC":
            if sort_by == "TITLE":
                sorted_data = sorted(loaded_data,key=lambda x:x["title"])
                return {"data": sorted_data}
            elif sort_by == "NUMBER":
                sorted_data = sorted(loaded_data,key=lambda x:x["formatted_number"])
                return {"data": sorted_data}
            elif sort_by == "TYPE":
                sorted_data = custom_sort(loaded_data,"type","name")
                return {"data": sorted_data}
            elif sort_by == "REVISION":
                sorted_data = sorted(loaded_data,key=lambda x: x["revision"])
                return {"data": sorted_data}
            elif sort_by == "SPEC":
                sorted_data = custom_sort(loaded_data,"specification_section","label")
                return {"data": sorted_data}
        elif is_sort_selected and type_of_sort == "DESC":
            if sort_by == "TITLE":
                sorted_data = sorted(loaded_data, key=lambda x:x["title"], reverse=True)
                return {"data": sorted_data}
            elif sort_by == "NUMBER":
                sorted_data = sorted(loaded_data,key=lambda x:x["formatted_number"], reverse=True)
                return {"data": sorted_data}
            elif sort_by == "TYPE":
                sorted_data = custom_sort(loaded_data,"type","name",True)
                return {"data": sorted_data}
            elif sort_by == "REVISION":
                sorted_data = sorted(loaded_data,key=lambda x: x["revision"], reverse=True)
                return {"data": sorted_data}
            elif sort_by == "SPEC":
                sorted_data = custom_sort(loaded_data,"specification_section","label",True)
                return {"data": sorted_data}
        else:
            return get_submittals_details()
    else:
        if is_sort_selected and type_of_sort == "ASC":
            if sort_by == "TITLE":
                sorted_data = sorted(loaded_data,key=lambda x:x["subject"])
                return {"data": sorted_data}
            elif sort_by == "NUMBER":
                sorted_data = sorted(loaded_data,key=lambda x:x["full_number"])
                return {"data": sorted_data}
        elif is_sort_selected and type_of_sort == "DESC":
            if sort_by == "TITLE":
                sorted_data = sorted(loaded_data, key=lambda x:x["subject"], reverse=True)
                return {"data": sorted_data}
            elif sort_by == "NUMBER":
                sorted_data = sorted(loaded_data,key=lambda x:x["full_number"], reverse=True)
                return {"data": sorted_data}
        else:
            return get_rfi_details()
