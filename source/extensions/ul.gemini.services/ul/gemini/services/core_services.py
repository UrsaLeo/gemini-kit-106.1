import os
import requests
import json
import zipfile
import logging

from ul.gemini.services.gdn_services import get_partner_secure_data, make_get_secure_call

# Any class derived from `omni.ext.IExt` in top level module (defined in `python.modules` of `extension.toml`) will be
# instantiated when extension gets enabled and `on_startup(ext_id)` will be called. Later when extension gets disabled
# on_shutdown() is called.

extract_dir = os.path.abspath(os.path.join(os.path.dirname(__file__),"..","..","..","..","..","apps","data","models"))
print (f"models directory {extract_dir} \n before getting partnersecure data")
model_path = ""

partner_secure_data = get_partner_secure_data()

def read_api_data_to_temp_file():
    global partner_secure_data
    global model_path
    global extract_dir
    base_url = partner_secure_data['baseUrl']
    twin_version_id = partner_secure_data['twinVersionId']
    if (base_url == None or twin_version_id == None):
        raise SystemExit("baseUrl and twinVersionId must be provided")

    # Initially creating the model folder
    #extract_dir = os.path.join(model_path, 'model')
    #os.makedirs(extract_dir, exist_ok=True)

    model_path = os.path.join(extract_dir, twin_version_id)
    print("Existing file path", model_path)
    model_path = model_path.replace("\\", "/")
    print(f'existing_file_path={model_path}')
    print(model_path)
    if os.path.exists(model_path):
        print(f"File '{twin_version_id}' already exists in the 'models' folder.")
        return model_path
    else:
        print(f"Its going to call the API")
        try:
            response =  make_get_secure_call(f"{base_url}/api/document/{twin_version_id}/building/download")
            response_data = response.json()
            print(f"RESPONSE: {response_data}")
            if response_data['url']:
                try:
                    file_response = requests.get(response_data['url'])
                    file_response.raise_for_status()
                    if file_response.status_code == 200:
                        # Create a "models" folder if it doesn't exist
                        file_path = os.path.join(extract_dir, response_data['filename'])
                        file_path = file_path.replace("\\", "/")
                        print(f"File path for zip={file_path}")
                        # Save the content to the local zip file

                        with open(file_path, 'wb') as file:
                            file.write(file_response.content)

                        print(f"Zip file saved to: {file_path}")

                        # Unzip the file
                        with zipfile.ZipFile(file_path, 'r') as zip_ref:
                                # Extract all contents into the "models" folder
                            #extracted_file = os.path.join(extract_dir, twin_version_id)
                            zip_ref.extractall(model_path)

                        #print(f"Zip file extracted to: {extracted_file}")

                            # Optionally, remove the original zip file if you don't need it
                        os.remove(file_path)
                        print(f"Original zip file removed.")
                    else:
                        raise SystemExit(f"AWS downloadable API failed: {file_response.status_code}")
                except requests.exceptions.RequestException as e:
                    raise SystemExit(f"Error fetching AWS downloadable API: {e}") from e
            else:
                raise SystemExit(f"No URL data found from the request")
        except requests.exceptions.RequestException as e:
            raise SystemExit(f"Error fetching data from API: {e}") from e
    return model_path
