import random
import copy
import math
from collections import Counter


def get_kafka_topic(partner_secure_data: dict) -> str:
    """
    This function maps the twinVersionId to a topic.
    Args:
        partner_secure_data(dict)

    Returns:
        topic(string)

    """
    topic_map = {
        # Stage twins
        "b7586e58-9a07-47f6-8049-43d6d6f2c5e5": "b7586e58-9a07-47f6-8049-43d6d6f2c5e5",  # Glass Factory
        "ed02afb1-ac52-4275-a1dd-c072487d9d16": "ed02afb1-ac52-4275-a1dd-c072487d9d16",  # Oil and Gas
        "bb9da2c6-4a1d-4efa-8c0f-222b44bbf136": "ed02afb1-ac52-4275-a1dd-c072487d9d16",  # Water Plant
        "afc3e440-0798-4ac3-bfcf-206bc3eef3f3": "ed02afb1-ac52-4275-a1dd-c072487d9d16",  # Mock data For Esamur(Water plant)


        # Production twins
        "463b9b40-6343-4bce-b364-b99cbef355e7": "ed02afb1-ac52-4275-a1dd-c072487d9d16", # Esamur client
    }

    return topic_map.get(
        partner_secure_data["twinVersionId"], "my_topic1"
    )  # if not in topic map - return default topic


def get_real_data_twin(twin: str) -> bool:
    """
    This function checks if the twin is a real data twin(contains real data from kharon/iot devices).
    Args:
        twin:

    Returns:

    """
    return twin in (
        "b7586e58-9a07-47f6-8049-43d6d6f2c5e5",
        "ed02afb1-ac52-4275-a1dd-c072487d9d16",
        "bb9da2c6-4a1d-4efa-8c0f-222b44bbf136",
        "afc3e440-0798-4ac3-bfcf-206bc3eef3f3", #  This is mocked, not real actually
    )


equipment_map = None
equipment_copy = {}
initial_distance = None


def create_random_equipment(data):
    """Creates equipment map with random equipment using kafka data"""

    global equipment_copy
    if equipment_copy is not None and data["device_name"] in equipment_copy:
        return equipment_copy

    data_copy = copy.deepcopy(data)
    data_device = data_copy["device_name"]

    equipment_copy[data_device] = random.choice(
        ["Equipment1", "Equipment2", "Equipment3"]
    )

    return equipment_copy


def create_equipment_map(stage):
    """Creates equipment map with random equipment using prim data"""

    global equipment_map

    if equipment_map is not None:
        return equipment_map

    folder = stage.GetPrimAtPath("/World/Twins/Building/Sensors")

    if folder:
        children = folder.GetAllChildren()
        child_list = [child.GetPath().pathString.split("/")[-1] for child in children]

        device_assignment = {}
        equipment = ["Equipment1", "Equipment2", "Equipment3"]

        for device in child_list:
            assigned_equipment = random.choice(equipment)
            device_assignment[device] = assigned_equipment

        equipment_map = device_assignment

        return device_assignment


def get_distance(prim_pos, camera_pos):
    """Calculates distance from sensors to camera"""

    camera_position = camera_pos[3]
    distance = math.sqrt(
        (prim_pos[0] - camera_position[0]) ** 2 +
        (prim_pos[1] - camera_position[1]) ** 2 +
        (prim_pos[2] - camera_position[2]) ** 2
    )

    return distance


def get_changed_size(distance):
    """Calculates text size when we zoom"""

    size_map = [
        (1000, 35),
        (1200, 30),
        (1300, 27),
        (1465, 25),
        (1700, 23),
        (2000, 20),
        (2200, 17),
        (2500, 15),
        (3500, 12),
        (4500, 11),
        (5100, 10),
        (5500, 9),
        (6000, 7),
        (10040, 5),
        (14040, 3)
    ]

    for max_distance, size in size_map:
        if distance < max_distance:
            return size

    return 1


def get_unique_value_keys(input_dict):
    """Gets sensor names for which equipment type has only one sensor"""

    value_count = Counter(input_dict.values())
    unique_keys = [
        key for key, value in input_dict.items() if value_count[value] == 1
    ]

    return unique_keys


def safe_eval(expression, reading):
    """Safely evaluates a mathematical comparison expression with a reading value.
       Used for search_by_reading func"""

    safe_globals = {"__builtins__": None}
    safe_locals = {"reading": reading}

    try:
        return eval(expression, safe_globals, safe_locals)
    except Exception:
        return False
