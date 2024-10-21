from omni.ui import scene as sc
from .object_info_manipulator import ObjInfoManipulator
from .object_info_model import ObjInfoModel


class ViewportSceneInfo:
    manipulator = None

    """The Object Info Manipulator, placed into a Viewport"""

    def __init__(self, viewport_window, ext_id) -> None:
        self.scene_view = None
        self.viewport_window = viewport_window

        with self.viewport_window.get_frame(ext_id):
            self.scene_view = sc.SceneView()

            with self.scene_view.scene:
                self.manipulator = ObjInfoManipulator(model=ObjInfoModel())

            self.viewport_window.viewport_api.add_scene_view(self.scene_view)

    def __del__(self):
        self.destroy()

    def set_sensor_data(self, measurement):
        self.manipulator.model.set_sensor_data(measurement)

    def set_sensor_name(self, sensor_name):
        self.manipulator.model.set_sensor_name(sensor_name)

    def set_kafka_message(self, kafka_message):
        self.manipulator.model.set_kafka_message(kafka_message)

    def destroy(self):
        if self.scene_view:
            # Empty the SceneView of any elements it may have
            self.scene_view.scene.clear()
            # un-register the SceneView from Viewport updates
            if self.viewport_window:
                self.viewport_window.viewport_api.remove_scene_view(self.scene_view)
        # Remove our references to these objects
        self.viewport_window = None
        self.scene_view = None
