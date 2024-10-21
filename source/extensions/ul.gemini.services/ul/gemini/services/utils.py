import os

should_open_artifact_window = False

def manual_quote(text):
    # Define special characters and their percent-encoded equivalents
    specials = {'/': '%2F', '?': '%3F', '=': '%3D', '&': '%26', ':': '%3A', '#': '%23', '+': '%2B', '%': '%25', ' ': '%20'}
    # Replace special characters with their percent-encoded equivalents
    for special, encoded in specials.items():
        text = text.replace(special, encoded)
    return text

def get_file_extension(filename:str):
    file_extension = os.path.splitext(filename)[1]
    return file_extension.lstrip(".")


def has_selected_folders(selected_paths):
    for path in selected_paths:
        print("Checking for folder path: " + path)
        if len(get_file_extension(path)) == 0:
            return True
    return False

def get_file_name(path:str):
    print(f"Get file name path={path}")
    file_name = os.path.basename(path)
    print(f"file_name={file_name}")
    return file_name



#TBD - replace with urllib.parse.quote
def encode_url(text):
    # Define special characters and their percent-encoded equivalents
    specials = {'/': '%2F'}
    # Replace special characters with their percent-encoded equivalents
    for special, encoded in specials.items():
        text = text.replace(special, encoded)
    return text

def truncate_path(path:str, max_length):
    if len(path) > max_length:
        truncated_path = path[:max_length] + '...'
        return truncated_path
    else:
        return path

def has_clicked_staging_button(should_change_value=False):
    global should_open_artifact_window
    if should_change_value:
        should_open_artifact_window = not should_open_artifact_window
        value = not should_open_artifact_window
        return value
    return should_open_artifact_window

def define_entity_item(entity_datas, entity_type):    
    data = []
    for entity_data in entity_datas:
        name = None
        if entity_type == "SUBMITTAL":
            name = entity_data["title"]
            spec = "Not Defined" if entity_data["specification_section"] is None else entity_data["specification_section"]["label"]
            spec_number = None if entity_data["specification_section"] is None else entity_data["specification_section"]["number"]
            revision = None if entity_data["revision"] is None else entity_data["revision"]
            type = "Not Defined" if entity_data["type"] is None else entity_data["type"]['name']
            formatted_number = None if entity_data["formatted_number"] is None else entity_data["formatted_number"]
            number = None 
            if spec_number is None and formatted_number is None and revision is None:
                number = "Not Defined"
            elif (spec_number is not None or formatted_number is not None) and revision is not None:
                number = f"{formatted_number}.{revision}"
                
            data.append({
                "name": name,
                "spec": spec,
                "number": number,
                "revision": "Not Defined" if revision is None else revision,
                "id": str(entity_data["id"]),
                "type": type
            })
        else:
            name = entity_data["subject"]
            status = "Not Defined" if entity_data["status"] is None else entity_data["status"]
            number = "Not Defined" if entity_data["number"] is None else entity_data["number"]
            data.append({
                "id": str(entity_data["id"]),
                "name": name,
                "status": status,
                "number": number,
                "spec": "Not Defined",
            })
        
    return data
