import random
import carb
import carb.events
import omni.ext
import omni.usd
import omni.ext
import omni.kit.ui
from pxr import Sdf
from .object_info_scene import ObjectInfoScene
from omni.kit.viewport.utility import get_active_viewport_window


class MyExtension(omni.ext.IExt):
    def __init__(self):
        super().__init__()
        self.custom_attrs = {}

        self.stage_stream = omni.usd.get_context().get_stage_event_stream()
        self._stage_subscription = self.stage_stream.create_subscription_to_pop(
            self.on_data_load, name="OnLoadEvent"
        )

    def on_startup(self, ext_id):
        viewport_window = get_active_viewport_window()

        if not viewport_window:
            carb.log_warn(f"No Viewport Window to add {ext_id} scene to")
            self._widget_info_viewport = None
            return

        self._widget_info_viewport = ObjectInfoScene(viewport_window, ext_id)

    def on_shutdown(self):
        if self._widget_info_viewport:
            self._widget_info_viewport.destroy()
            self._widget_info_viewport = None

    def on_data_load(self, event: carb.events.IEvent):
        if event.type == int(omni.usd.StageEventType.ASSETS_LOADED):
            pass

            # NOTE! This code is for testing - it sets attrs to prims, so they could be read

            # stage = omni.usd.get_context().get_stage()
            # all_prims = [prim for prim in stage.Traverse()]
            # prim_paths = [prim.GetPath().pathString for prim in all_prims]

            # for path in prim_paths:
            #     if path.split("/")[-1].startswith("Mesh"):
            #         prim = stage.GetPrimAtPath(path)

            #         if not prim.IsValid():
            #             continue

            #         if not prim.GetAttribute("GUID"):
            #             attr1 = prim.CreateAttribute("GUID", Sdf.ValueTypeNames.String)
            #             attr1.Set(random.choice([
            #                 "0360e59a",
            #                 "67efcfb5",
            #                 "00a4619a"
            #             ]))

            #         if not prim.GetAttribute("Asset_Name"):
            #             attr2 = prim.CreateAttribute("Asset_Name", Sdf.ValueTypeNames.String)
            #             attr2.Set(f"Asset {random.randint(1, 20)}")

            #         if not prim.GetAttribute("Service_Date"):
            #             attr3 = prim.CreateAttribute("Service_Date", Sdf.ValueTypeNames.String)
            #             attr3.Set(random.choice(["18.09.2024", "10.08.2024", "22.07.2024"]))

            #         if not prim.GetAttribute("One_more_attr"):
            #             attr3 = prim.CreateAttribute("One_more_attr", Sdf.ValueTypeNames.String)
            #             attr3.Set(random.choice(["Value1", "Value2", "Value3"]))
