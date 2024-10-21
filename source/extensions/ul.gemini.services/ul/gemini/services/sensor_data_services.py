from . import gdn_services as gdn
import requests
import json
import os

sensor_data_list_executed = False
sensor_data_list = None
warehouse_list = None
warehouse_sensor_list = None

id_sensor_list = [
            { "id": 1, "temperature": 2.5, "rotation": 22.5 },
            { "id": 2, "temperature": 23.5, "rotation": 27.5 },
            { "id": 3, "temperature": 93.5, "rotation": 28.5 },
            { "id": 4, "temperature": 43.5, "rotation": 29.5 },
            { "id": 5, "temperature": 63.5, "rotation": 22.5 },
            { "id": 6, "temperature": 13.5, "rotation": 67.5 },
            { "id": 7, "temperature": 87.9, "rotation": 90.5 },
            { "id": 8, "temperature": 77.2, "rotation": 44.5 },
            { "id": 9, "temperature": 11.0, "rotation": 22.5 },
            { "id": 10, "temperature": 13.0, "rotation": 28.5 },
            { "id": 11, "temperature": 16.0, "rotation": 24.5 },
]

def get_warehouse_list():
    global warehouse_list
    try:
        response = requests.get(f"http://localhost:3000/api/sensor-data/all")
        response.raise_for_status()
        if response.status_code == 200:
            warehouse_list = response.json()
            return warehouse_list
    except Exception as e:
        print("Persist data return")
        return [{"warehouse1":{"sensor1temperature":25.9705897614174,"sensor2humidity":45.869948216479166},"warehouse2":{"sensor1temperature":21.717074331208856,"sensor2humidity":33.251496691795175}}]


def get_warehouse_sensors(warehouse_id):
    global warehouse_sensor_list
    try:
        response = requests.get(f"http://localhost:3000/api/sensor-data/{warehouse_id}")
        response.raise_for_status()
        if response.status_code == 200:
            warehouse_sensor_list = response.json()
            return warehouse_sensor_list
    except Exception as e:
        return []


def get_sensor_data_by_id(warehouse_id,sensor_id):
    print(f"{sensor_id} {warehouse_id}")
    try:
        response = requests.get(f"http://localhost:3000/api/sensor-data/{warehouse_id}/{sensor_id}")
        response.raise_for_status()
        if response.status_code == 200:
            specific_sensor_data = response.json()
            print(f"RESPONSE {specific_sensor_data}")
            return specific_sensor_data
    except Exception as e:
        return []


def get_sensor_data():
    global sensor_data_list
    global sensor_data_list_executed

    if sensor_data_list_executed:
        return sensor_data_list
    else:
        sensor_data_list_executed = True
        sensor_data_list = [
            { "id": 1, "name": "Sensor one" },
            { "id": 2, "name": "Sensor two" },
            { "id": 3, "name": "Sensor three"},
            { "id": 4, "name": "Sensor four"},
            { "id": 5, "name": "Sensor five"},
            { "id": 6, "name": "Sensor six"},
            { "id": 7, "name": "Sensor seven"},
            { "id": 8, "name": "Sensor eight"},
            { "id": 9, "name": "Sensor nine"},
            { "id": 10, "name": "Sensor ten"},
            { "id": 11, "name": "Sensor eleven"}
        ]

        return sensor_data_list


# def add_or_update_sensor(sensor_list, sensor):
#     for item in sensor_list:
#         # Check if sensor keys are the same
#         if set(item.keys()) == set(sensor.keys()):
#             # Check if all values for keys are the same
#             if all(item[key] == sensor[key] for key in item):
#                 # Update the value if the sensor already exists
#                 item["value"] = sensor["value"]
#                 return
#     # Add a new sensor if it doesn't exist
#     sensor_list.append(sensor)

def add_or_update_sensor(sensor_list, sensor):
    # Get the key of the new sensor
    new_key = next(iter(sensor))
    # Check if the key already exists in the sensor list
    for item in sensor_list:
        if new_key in item:
            # Update the value for the existing key
            item[new_key] = sensor[new_key]
            return

    # If the key doesn't exist, add the new sensor to the list
    sensor_list.append(sensor)

def filter_current_reading_value(sensor_list,id):
    values = [sensor for sensor in sensor_list if id in sensor]
    if len(values) > 0 :
        return values[0]
    return None

def add_or_update_sensor_message(sensor_list: list,kafka_message: object):

    for sensor in sensor_list:
        if sensor['name'] == kafka_message['name']:
            # Update the existing record
            sensor['reading'] = kafka_message['reading']
            sensor['status'] = kafka_message['status']
            sensor['readingType'] = kafka_message['readingType']
            return
    # add the new message to the list
    sensor_list.append(kafka_message)


def add_or_update_sensor_message_update(sensor_list, kafka_messages: object):
    for kafka_message in kafka_messages:
        name_exists = any(sensor['name'] == kafka_message['name'] for sensor in sensor_list)
        if not name_exists:
            sensor_list.extend(kafka_message)
        else:
            for sensor in sensor_list:
                if sensor["name"] == kafka_message["name"]:
                    sensor['reading'] = kafka_message['reading']
                    sensor['status'] = kafka_message['status']
                    sensor['readingType'] = kafka_message['readingType']

def get_sensor_data_list():
    return  [
        {
            "name": "humidity",
            "type": "SOmething",
            "reading": 45.893749375893,
            "status": "SEVERE",
            "readingType": "%"
        },
        {
            "name": "temperature",
            "type": "temp",
            "reading": 25.893749375893,
            "status": "NORMAL",
            "readingType": "f"
        }
    ]


def get_equipment_names(data:any):
    if len(data) == 0: return []
    return [item["name"] for item in data]


def get_equipment_status(data:any):
    if len(data) == 0: return []
    return [item["status"] for item in data]


def get_equipment_type(data:any):
    if len(data) == 0: return []
    return [item["type"] for item in data]


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


def get_path_for_sensor(twin_version_id: str, sensor_name: str):
    path_mapping = load_mapping_file()

    if len(path_mapping) > 0:
        filtered_path = next((entry["path"] for entry in path_mapping if entry["twinVersionId"] == twin_version_id and entry["sensorName"] == sensor_name), None)
        return filtered_path
    else:
        return None


def get_default_camera_path_for_sensor(twin_version_id: str, sensor_name: str):
    path_mapping = load_mapping_file()

    if len(path_mapping) > 0:
        filtered_path = next(
            (entry["default_camera"] for entry in path_mapping
            if entry["twinVersionId"] == twin_version_id and entry["sensorName"] == sensor_name), None
        )
        return filtered_path
    else:
        return None


def get_sensor_camera_path(twin_version_id: str, sensor_name: str):
    path_mapping = load_mapping_file()
    if len(path_mapping) > 0:
        filtered_path = next(
            (entry.get("sensor_camera") for entry in path_mapping
             if entry["twinVersionId"] == twin_version_id
             and entry["sensorName"] == sensor_name
             and "sensor_camera" in entry),
            None
        )
        return filtered_path
    else:
        return None


def get_json_object(twin_version_id: str, sensor_name: str, path_mapping):
    if len(path_mapping) > 0:
        filtered_path = next((
            entry for entry in path_mapping
            if entry["twinVersionId"] == twin_version_id and entry["path"].split("/")[-1] == sensor_name
        ), None)
        return filtered_path
    else:
        return None


def get_all_json_objects_paths(twin_version_id: str, path_mapping):
    if len(path_mapping) > 0:
        filtered_objects = [
            entry["path"] for entry in path_mapping
            if entry["twinVersionId"] == twin_version_id]

        return filtered_objects
    else:
        return None
