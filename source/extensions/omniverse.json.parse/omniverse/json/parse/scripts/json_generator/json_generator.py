import json
import random


# def generate_position(max_coord_x, max_coord_y, max_coord_z):
#     return (
#         f"{random.randint(16100, 20400)} "
#         f"{random.randint(-5400, 9301)} "
#         f"{random.randint(-max_coord_z, max_coord_z)} "
#         f"{random.randint(0, 360)}"
#     )

def generate_position(max_coord_x, max_coord_y, max_coord_z):
    # X-Axis: Spawn at x < -18738.63 or x > 29189.49
    # Y-Axis: Spawn at y < -7738.77 or y > 13288.88
    # Z-Axis: Spawn at z < -4339.47 or z > 1844.67
    return (
        f"{random.randint(-300, 4500)} "
        f"{random.randint(2000, 10000)} "
        f"{random.randint(-max_coord_z, max_coord_z)} "
        f"{random.randint(0, 360)}"
    )

def generate_actions(prev_time, max_time, max_coord, duration=100):
    possible_commands = {
        "GoTo": {
            "start_time": lambda: None,
            "finish_time": lambda: None,
            "finish_pos": lambda: generate_position(max_coord, max_coord, 0),
        },
        "LookAround": {
            "duration": lambda: random.randint(10, duration),
            "start_time": lambda: None,
            "finish_time": lambda: None,
        },
        "Idle": {
            "duration": lambda: random.randint(10, duration),
            "start_time": lambda: None,
            "finish_time": lambda: None,
        },
    }

    weighted_keys = ["GoTo"] * 10 + list(possible_commands.keys())
    type_key = random.choice(weighted_keys)
    command_func_dict = possible_commands[type_key]
    new_dict = {"type": type_key}
    for arg, func in command_func_dict.items():
        new_dict[arg] = func()
    return new_dict


# def generate_actions(prev_time, max_time, max_coord, duration=100):
#     possible_commands = {
#         "GoTo": {
#             "start_time": lambda: None,
#             "finish_time": lambda: None,
#             "finish_pos": lambda: generate_position(max_coord, max_coord, 0),
#         },
#         "LookAround": {
#             "duration": lambda: random.randint(1, duration),
#             "start_time": lambda: None,
#             "finish_time": lambda: None,
#         },
#         "Idle": {
#             "duration": lambda: random.randint(1, duration),
#             "start_time": lambda: None,
#             "finish_time": lambda: None,
#         },
#     }

#     weighted_keys = ["GoTo"] * 10 + list(possible_commands.keys())
#     type_key = random.choice(weighted_keys)
#     command_func_dict = possible_commands[type_key]
#     new_dict = {"type": type_key}
#     for arg, func in command_func_dict.items():
#         new_dict[arg] = func()
#     return new_dict


def generate_character(
    max_number_actions=10, max_time=1500, max_coord=50, character_int_id=0
):
    max_duration = int(max_time / max_number_actions)
    character_id = f"avatar_{character_int_id}"
    spawn_position = generate_position(max_coord, max_coord, 0)
    actions = []
    j = 0
    prev_time = 0
    while j < max_number_actions:
        action_id = f"action_{character_int_id}_{j}"
        action = generate_actions(prev_time, max_time, max_coord, max_duration)
        actions.append(action)
        j += 1

    return {
        character_id: {
            "spawn_position": spawn_position,
            "actions": actions,
            "alarm_actions": [
            {
                "type": "GoTo",
                "start_time": 3,
                "finish_time": None,
                "finish_pos": spawn_position
            }
        ]
        }
    }


def generate_character_json(
    number_of_characters=50,
    max_number_actions=20,
    max_time=1500,
    max_coord=50,
    file_name="characters.json",
):
    characters = {}
    for i in range(number_of_characters):
        characters.update(
            generate_character(max_number_actions, max_time, max_coord, i)
        )
    print(characters)

    with open(file_name, "w") as outfile:
        json.dump(characters, outfile, indent=4)


if __name__ == "__main__":
    generate_character_json()