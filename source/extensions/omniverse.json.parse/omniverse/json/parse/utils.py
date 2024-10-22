room_mesh7342 = {
    "min_x": 2174.989501953125,
    "min_y": 2210.18505859375,
    "max_x": 4545.85009765625,
    "max_y": 4400.87353515625,
    "min_z": -10.0,
    "max_z": 10.0,
}

room_mesh7332 = {
    "min_x": -5878.865234375,
    "min_y": 863.9615478515625,
    "max_x": -5220.341796875,
    "max_y": 2702.464111328125,
    "min_z": -10.0,
    "max_z": 10.0,
}

def count_avatars_inside(avatars):
    # min_x, min_y = 2174.989501953125, 2210.18505859375
    # max_x, max_y = 4545.85009765625, 4400.87353515625
    # min_z, max_z = -20.0, 20.0

    # Check which avatars are inside the bounding box
    # avatars = self.get_json_manager().read_from_json(self.json_path)
    avatars_inside = []
    avatars_inside2 = []
    for avatar, details in avatars.items():
        # Split the spawn position and convert to float
        position = list(map(float, details["actions"][0]["finish_pos"].split()[:3]))
        x, y, z = position[0], position[1], position[2]

        # Check if inside bounding box
        if (
            room_mesh7342.get("min_x") <= x <= room_mesh7342.get("max_x")
            and room_mesh7342.get("min_y") <= y <= room_mesh7342.get("max_y")
            and room_mesh7342.get("min_z") <= z <= room_mesh7342.get("max_z")
        ):
            avatars_inside.append(avatar)

        if (
            room_mesh7332.get("min_x") <= x <= room_mesh7332.get("max_x")
            and room_mesh7332.get("min_y") <= y <= room_mesh7332.get("max_y")
            and room_mesh7332.get("min_z") <= z <= room_mesh7332.get("max_z")
        ):
            avatars_inside2.append(avatar)

    return avatars_inside, avatars_inside2