import omni.kit.viewport.window
from pxr import Tf
from pxr import Usd
from pxr import UsdGeom

from omni.ui import scene as sc
import omni.usd
from omni.kit.viewport.utility import get_active_viewport
import omni.ui as ui
from .utils import show_window_contents
import omni.kit.viewport


class ObjInfoModel(sc.AbstractManipulatorModel):
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

        self.prim = None
        self.window = None
        self.current_path = ""

        self.stage_listener = None
        self.position = ObjInfoModel.PositionItem()
        self.usd_context = omni.usd.get_context()

        self.events = self.usd_context.get_stage_event_stream()
        self.stage_event_delegate = self.events.create_subscription_to_pop(
            self.on_stage_event, name="Object Info Selection Update"
        )

        self._attr = {}

    def on_stage_event(self, event):
        """Called by stage_event_stream.  We only care about selection changes."""
        if event.type == int(omni.usd.StageEventType.SELECTION_CHANGED):
            # Reset dict with attrs to display only current prim attrs
            self._attr = {}
            prim_paths = self.usd_context.get_selection().get_selected_prim_paths()

            if not prim_paths:
                self.current_path = ""
                self._item_changed(self.position)
                return
            stage = self.usd_context.get_stage()

            prim_attrs = []

            for path in prim_paths:
                prim = stage.GetPrimAtPath(path)

                if not prim.IsA(UsdGeom.Imageable):
                    self.prim = None
                    if self.stage_listener:
                        self.stage_listener.Revoke()
                        self.stage_listener = None
                    return

                if not self.stage_listener:
                    self.stage_listener = Tf.Notice.Register(Usd.Notice.ObjectsChanged, self.notice_changed, stage)

                self.prim = prim
                self.current_path = prim_paths[0]

                # Get all custom attributes and write them to self._attr dict
                all_attrs = prim.GetAttributes()
                current_attrs = {}

                for attr in all_attrs:
                    if (
                        attr.IsCustom()
                        and attr.GetName() != "refinementEnableOverride"
                        and attr.GetName() != "refinementLevel"
                        and not attr.GetName().startswith("userProperties:")
                        and not attr.GetName().startswith("blender")
                        and not attr.GetName().startswith("omni:kit:")
                    ):
                        current_attrs[attr.GetName()] = attr

                if current_attrs not in prim_attrs:
                    prim_attrs.append(current_attrs)

            if not len(prim_attrs):
                self.window.visible = False
                return

            # Create window for metadata
            self.window = ui.Window(" ", width=230, height=400, resizable=False)

            vp = get_active_viewport()
            width, _ = vp.resolution

            self.window.setPosition(width - 460, 90)
            self.window.visible = True

            with self.window.frame:
                with ui.VStack():
                    for prim_path, attrs in zip(prim_paths, prim_attrs):
                        prim = stage.GetPrimAtPath(prim_path)
                        all_attrs = [attr for attr in prim.GetAttributes() if (
                                attr.IsCustom()
                                and attr.GetName() != "refinementEnableOverride"
                                and attr.GetName() != "refinementLevel"
                                and not attr.GetName().startswith("userProperties:")
                                and not attr.GetName().startswith("blender")
                                and not attr.GetName().startswith("omni:kit:")
                            )]

                        names = [item.GetName() for item in attrs.values()]
                        values = [str(item.Get()) for item in attrs.values()]

                        if not len(all_attrs):
                            self.window.visible = False
                            return

                        show_window_contents(names, values, prim_path)

            self._item_changed(self.position)

    def get_item(self, identifier):
        if identifier == "name":
            return self.current_path
        elif identifier == "position":
            return self.position
        elif identifier == "attr":
            return self._attr

    def get_as_floats(self, item):
        if item == self.position:
            return self.get_position()
        if item:
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
