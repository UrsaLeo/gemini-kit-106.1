import omni.ui as ui
from omni.kit.waypoint.core.widgets.list_window import WaypointListWindow as ListWindow

def open_waypoint():
    print("Opening waypoint")
    print("Entering way points")
    if not ui.Workspace.get_window("Waypoints"):
        ListWindow()
    waypoint_window = ui.Workspace.get_window("Waypoints")
    if waypoint_window:
        waypoint_window.visible = not waypoint_window.visible

def open_markup():
    print("Opening markuup")
    toggle_window_visibility("Markups")

def open_sensors():
    print("Opening sensors")
    toggle_window_visibility("Sensors")

def open_sun_study():
    print("Opening sensors")
    toggle_window_visibility("Sun Study")

def exit():
    print("Closing chatbot")

def toggle_window_visibility(window_name, hide_artifacts=False):
    win = ui.Workspace.get_window(window_name)
    if not win:
        print(f"Window {window_name} not found")
        return

    if hide_artifacts:
        artifact_win = ui.Workspace.get_window("Artifact")
        if artifact_win and artifact_win.visible:
            return

    win.visible = not win.visible


window_actions = {
    "open waypoint": open_waypoint,
    "open markup": open_markup,
    "open sensors": open_sensors,
    "open sun study" : open_sun_study,
    "exit":exit,
}

def open_windows(message):
    action = message.lower().strip()  # Normalize and strip any extra spaces
    print(f"Action: {action}")  # Debugging print statement

    try:
        # Directly access and call the function
        window_actions[action]()
    except KeyError:
        print("Unknown command")
