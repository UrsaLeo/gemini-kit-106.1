from omni.ui import scene as sc

from .object_info_manipulator import ObjInfoManipulator
from .object_info_model import ObjInfoModel


class ObjectInfoScene():
    """The Object Info Manupulator, placed into a Viewport"""

    def __init__(self, viewport_window, ext_id: str):
        self._scene_view = None
        self._viewport_window = viewport_window

        with self._viewport_window.get_frame(ext_id):
            self._scene_view = sc.SceneView()
            with self._scene_view.scene:
                ObjInfoManipulator(model=ObjInfoModel())

            self._viewport_window.viewport_api.add_scene_view(self._scene_view)

    def __del__(self):
        self.destroy()

    def destroy(self):
        if self._scene_view:
            self._scene_view.scene.clear()
            if self._viewport_window:
                self._viewport_window.viewport_api.remove_scene_view(self._scene_view)

        self._viewport_window = None
        self._scene_view = None
