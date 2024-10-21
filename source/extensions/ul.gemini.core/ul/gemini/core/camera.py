import omni.kit.viewport.utility
import omni.usd
from omni.kit.window.popup_dialog import MessageDialog

from pxr import Usd, UsdGeom, Sdf, Gf
from omni.kit.viewport.utility import get_active_viewport

# CameraChanger takes all the cameras defined in the CAMERA_ROOT_PRIM_PATH
# and provides the camera_change functionality for the main ul.gemini extension


class CameraChanger:

    _camera_prim_paths = []
    _camera_properties = []
    _current_camera_index = -1
    _perspective_camera_path = "/OmniverseKit_Persp"
    _top_camera_index = -1
    # It picks up all the cameras direclty under this prim path for rotation

    # reads all the cameras defined under the given CAMERA_ROOT_PRIM PATHS and stores
    # also stores their properties to allow reset if user does WASD and stores the top camera
    # if one was provided
    def initialize_camera_prim_paths(self):
        CAMERA_ROOT_PRIM_PATH = "/World/Twins/Building"
        global _perspective_camera_path
        self._camera_prim_paths = []
        stage = omni.usd.get_context().get_stage()
        prim = stage.GetPrimAtPath(CAMERA_ROOT_PRIM_PATH)
        current_camera_path = omni.kit.viewport.utility.get_active_viewport().camera_path
        i = 0
        if prim and prim.GetChildren():
            for child_prim in prim.GetChildren():
                if child_prim.IsA(UsdGeom.Camera):
                    child_path = child_prim.GetPath()
                    child_path_str = f"{child_path}"
                    self._camera_prim_paths.append(child_path)

                    translate = child_prim.GetAttribute("xformOp:translate").Get()
                    scale = child_prim.GetAttribute("xformOp:scale").Get()
                    rotate = child_prim.GetAttribute("xformOp:rotateYXZ").Get()
                    props = [translate, scale, rotate]
                    print(props)

                    self._camera_properties.append(props)
                    # if there is a camera called "Top", we reset to that when calling section tool
                    # if not, no change
                    if child_path_str.endswith("/Top"):
                        self._top_camera_index = i
                    if current_camera_path and child_path == current_camera_path:
                        self._current_camera_index = i
                    i += 1
        else:
            self._camera_prim_paths = [self._perspective_camera_path]

        if self._current_camera_index == -1:
            raise SystemExit("Could not find a current camera in the USD at path " + CAMERA_ROOT_PRIM_PATH)

    def show_message_dialog(self):
        message = (
            "Camera position has changed. Resetting camera position. Use Waypoints if you want to save new positions."
        )

        def ok(dialog):
            dialog.hide()

        MessageDialog(
            title="Resettting camera position", width=400, message=message, ok_handler=ok, disable_cancel_button=True
        ).show()

    # cycle through the defined cameras
    def change_camera(self):

        # from ul.gemini.sensor.object_info_manipulator import ObjInfoManipulator

        # ObjInfoManipulator.clear_sensor()

        if len(self._camera_prim_paths) == 0:  ##no cameras!!
            return

        # before changing the camera, if camera position has changed,
        # reset the properties using saved values
        # as the user may have used WASD and got lost
        if self.reset_camera_properties():
            return

        if self._current_camera_index + 1 < len(self._camera_prim_paths):
            self.set_camera_to_index(self._current_camera_index + 1)
        else:
            self.set_camera_to_index(0)

        # settings = carb.settings.get_settings()_current_camera_index
        # settings.set("/rtx/sectionPlane/manipulator", False)

        # omni.usd.get_context().get_selection().set_selected_prim_paths([path], True)
        omni.usd.get_context().get_selection().clear_selected_prim_paths()  # 3TBD why do we have this??

    # Initializes _camera_prim_paths , _current_camera_index and  _top_camera_index

    def switch_to_top_camera(self):
        if self._top_camera_index != -1 and self._top_camera_index != self._current_camera_index:
            self.set_camera_to_index(self._top_camera_index)
        # sets the camear to the given path and sets the _current_camera_index accordingly

    def set_camera(self, camera_path):
        viewport = get_active_viewport()
        viewport.camera_path = camera_path
        camera_index = self._camera_prim_paths.index(camera_path)
        if camera_index != self._current_camera_index:
            self._current_camera_index = camera_index

    # sets the camera to the given index
    def set_camera_to_index(self, camera_index):
        self.set_camera(self._camera_prim_paths[camera_index])

    # checks if current camera position has changed and if so resets to saved values and returnns True
    def reset_camera_properties(self):
        # TBD check if the camera position changed and if so ask whether they want to reset the position

        if self._current_camera_index == -1:
            return

        stage = omni.usd.get_context().get_stage()
        if stage:
            prim = stage.GetPrimAtPath(self._camera_prim_paths[self._current_camera_index])
            props = self._camera_properties[self._current_camera_index]
            translate = props[0]
            scale = props[1]
            rotate = props[2]

            newTranslate = prim.GetAttribute("xformOp:translate").Get()
            newScale = prim.GetAttribute("xformOp:scale").Get()
            newRotate = prim.GetAttribute("xformOp:rotateYXZ").Get()
            if translate != newTranslate or scale != newScale or rotate != newRotate:
                self.show_message_dialog()
                prim.GetAttribute("xformOp:translate").Set(translate)
                prim.GetAttribute("xformOp:scale").Set(scale)
                prim.GetAttribute("xformOp:rotateYXZ").Set(rotate)
                return True
            return False
