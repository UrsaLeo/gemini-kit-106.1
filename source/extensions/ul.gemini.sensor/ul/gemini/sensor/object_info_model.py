from pxr import Tf
from pxr import Usd
from pxr import UsdGeom

from omni.ui import scene as sc
import omni.usd


class ObjInfoModel(sc.AbstractManipulatorModel):
    measurement = ""

    """
    The model tracks the position and info of the selected object.
    """

    class PositionItem(sc.AbstractManipulatorItem):
        """
        The Model Item represents the position. It doesn't contain anything
        because we take the position directly from USD when requesting.
        """

        def __init__(self) -> None:
            super().__init__()
            self.value = [0, 0, 0]

    def __init__(self) -> None:
        super().__init__()

        self.manipulator = None

        self.sensor_name = None
        self.kafka_message = None
        self.prim = None
        self.current_path = ""

        self.stage_listener = None
        self.all_prims = None

        self.position = ObjInfoModel.PositionItem()

        # Save the UsdContext name (we currently only work with a single Context)
        self.usd_context = omni.usd.get_context()

        # Track selection changes
        self.events = self.usd_context.get_stage_event_stream()
        self.stage_event_delegate = self.events.create_subscription_to_pop(
            self.on_stage_event, name="Object Info Selection Update"
        )

    def on_stage_event(self, event):
        """Called by stage_event_stream.  We only care about selection changes."""
        if event.type == int(omni.usd.StageEventType.SELECTION_CHANGED):
            self.all_prims = self.usd_context.get_selection().get_selected_prim_paths()

            stage = self.usd_context.get_stage()

            for prim_path in self.all_prims:
                prim = stage.GetPrimAtPath(prim_path)

                prim_pos = omni.usd.get_local_transform_SRT(prim)
                print("prim position1", prim_pos)

                if prim_path.split("/")[-1] == "Sensors":
                    try:
                        self.select_all_children(prim.GetAllChildren())
                    except Exception as e:
                        print(f"Exc2: {e}")

                try:
                    folder_path = prim.GetParent().GetName()
                except IndexError as e:
                    print("IndexError: ", e)
                    pass

                if not self.all_prims or folder_path != "Sensors":
                    self.current_path = ""
                    if self.manipulator:
                        self.manipulator.clear_manipulator()
                    return

                if not prim.IsA(UsdGeom.Imageable):
                    self.prim = None
                    if self.stage_listener:
                        self.stage_listener.Revoke()
                        self.stage_listener = None
                    return

                if not self.stage_listener:
                    self.stage_listener = Tf.Notice.Register(Usd.Notice.ObjectsChanged, self.notice_changed, stage)

                self.prim = prim

                self.data_gotten = self.prim.GetCustomData()
                self.current_path = prim_path

                # Position is changed because new selected object has a different position
                self._item_changed(self.position)

    def get_item(self, identifier):
        if identifier == "name":
            return self.current_path
        elif identifier == "position":
            return self.position
        elif identifier == "measurement":
            return self.measurement
        elif identifier == "sensor_name":
            return self.sensor_name
        elif identifier == "kafka_message":
            return self.kafka_message

        elif identifier == "all_prims":
            return self.all_prims

    def get_as_floats(self, item):
        if item == self.position:
            # Requesting position
            return self.get_position()
        if item:
            # Get the value directly from the item
            return item.value

        return []

    def get_position(self):
        """Returns position of currently selected object"""
        stage = self.usd_context.get_stage()
        if not stage or self.current_path == "":
            return [0, 0, 0]

        # Get position directly from USD
        prim = stage.GetPrimAtPath(self.current_path)
        box_cache = UsdGeom.BBoxCache(Usd.TimeCode.Default(), includedPurposes=[UsdGeom.Tokens.default_])
        bound = box_cache.ComputeWorldBound(prim)
        range = bound.ComputeAlignedBox()
        bboxMin = range.GetMin()
        bboxMax = range.GetMax()

        # Find the top center of the bounding box and add a small offset upward.
        x_Pos = (bboxMin[0] + bboxMax[0]) * 0.5
        y_Pos = bboxMax[1] + 5
        z_Pos = (bboxMin[2] + bboxMax[2]) * 0.5
        position = [x_Pos, y_Pos, z_Pos]
        return position

    # Loop through all notices that get passed along until we find selected
    def notice_changed(self, notice: Usd.Notice, stage: Usd.Stage) -> None:
        """Called by Tf.Notice.  Used when the current selected object changes in some way."""
        for p in notice.GetChangedInfoOnlyPaths():
            if self.current_path in str(p.GetPrimPath()):
                self._item_changed(self.position)

    def destroy(self):
        self.events = None
        self.stage_event_delegate.unsubscribe()

    def set_sensor_data(self, value):
        self.measurement = value
        self._item_changed(self.measurement)

    def set_sensor_name(self, sensor_name):
        self.sensor_name = sensor_name
        self._item_changed(self.sensor_name)

    def set_kafka_message(self, kafka_message):
        self.kafka_message = kafka_message
        # self._item_changed(self.kafka_message)

    def set_manipulator(self, manipulator):
        self.manipulator = manipulator

    def get_position_for_prim(self, prim):
        """Returns position of the given prim"""

        stage = self.usd_context.get_stage()
        if not stage or self.current_path == "":
            return [0, 0, 0]

        box_cache = UsdGeom.BBoxCache(Usd.TimeCode.Default(), includedPurposes=[UsdGeom.Tokens.default_])
        bound = box_cache.ComputeWorldBound(prim)
        range = bound.ComputeAlignedBox()
        bboxMin = range.GetMin()
        bboxMax = range.GetMax()

        x_Pos = (bboxMin[0] + bboxMax[0]) * 0.5
        y_Pos = bboxMax[1] + 5
        z_Pos = (bboxMin[2] + bboxMax[2]) * 0.5
        position = [x_Pos, y_Pos, z_Pos]
        return position

    def select_all_children(self, prims):
        """Selects all prims given a list of prim objects."""

        prim_paths = [prim.GetPath().pathString for prim in prims]
        selection = self.usd_context.get_selection()
        selection.set_selected_prim_paths(prim_paths, False)
