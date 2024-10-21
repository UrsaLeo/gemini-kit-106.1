import os
import asyncio
import omni.kit.app
import carb.events
import carb.settings
import omni.ext
import omni.ui as ui
import carb.settings     #CR: Duplicate remove
from omni.ui import color as cl
import omni.usd
from pxr import Usd, UsdGeom, Sdf, Gf, Ar
from omni.usd import get_context
from omni.kit.viewport.utility import get_active_viewport
from omni.kit.markup.core.widgets.list_window import MarkupListWindow
from omni.kit.window.section.ui.section_tool_window import SectionToolWindow

# from omni.kit.tool.measure.interface.panel import MeasurePanel

import omni.kit.commands
from omni.kit.menu.utils import MenuLayout, MenuItemDescription
from .utils import zoom_camera


import subprocess
import asyncio   #CR: Duplicate
import time

import ul.gemini.services.gdn_services as gdn_services  # import get_partner_secure_data,get_integration_entity_type_list,get_rfi_details,get_submittals_details,get_procore_document_structure,get_source_list,should_open_artifact_window
import ul.gemini.services.artifact_services as artifact_services
import ul.gemini.services.core_services as core_services
import omni.kit.window.toolbar
from omni.kit.window.toolbar.builtin_tools.transform_button_group import (
    TransformButtonGroup,
)
import threading
from .camera import CameraChanger

from .toolbar import ExtensionVisibilityAction, Toolbar

from omni.kit.waypoint.core.widgets.list_window import WaypointListWindow
from omni.kit.variant.presenter.window import VariantPresenterWindow
from syntway.model_exploder.window import Window as ModelExploderWindow

import omni.appwindow
import carb.input
from carb.input import KeyboardEventType

import omni.timeline


# Any class derived from `omni.ext.IExt` in top level module (defined in `python.modules` of `extension.toml`) will be
# instantiated when extension gets enabled and `on_startup(ext_id)` will be called. Later when extension gets disabled
# on_shutdown() is called.


# Create a wrapper method to take in the inputs as (base_path, "../../../data/Nav_Loading.png")  and retern a relative path as self.getpath((base_path, "../../../data/Nav_Loading.png"))

base_path = os.path.dirname(__file__)
loading_screen_path = os.path.join(base_path, "../../../data/Nav_Loading.png")
partner_secure_data = None


class ULExtension(omni.ext.IExt):

    _camera_changer = CameraChanger() #CR: Remove
    _stage_subscription = None



    ########################################################################################

    #CR: Combine all start up UI settings

    _file_menu_list = [MenuItemDescription(name="UrsaLeo AI Assit - Comming Soon")]
    omni.kit.menu.utils.add_menu_items(_file_menu_list, "Help")
    _menu_layout = [
        MenuLayout.Menu("Help"),
        MenuLayout.Menu("Window", remove=True),
        MenuLayout.Menu("Edit", remove=True),
        MenuLayout.Menu("Create", remove=True),
        MenuLayout.Menu("Rendering", remove=True),
        MenuLayout.Menu("Tools", remove=True),
        MenuLayout.Menu("File", remove=True),
        MenuLayout.Menu("Layout", remove=True),
    ]
    omni.kit.menu.utils.add_layout(_menu_layout)

    #########################################################################################

    async def loading_screen(self):

            #CR: Combine all start up UI settings

        window_flags = ui.WINDOW_FLAGS_NO_RESIZE
        window_flags |= ui.WINDOW_FLAGS_NO_SCROLLBAR
        window_flags |= ui.WINDOW_FLAGS_MODAL
        window_flags |= ui.WINDOW_FLAGS_NO_CLOSE
        window_flags |= ui.WINDOW_FLAGS_NO_MOVE

#######################################################################
        self._window = ui.Window(
            "Rendering the Digital Twin",
            width=800,
            height=800,
            flags=window_flags,
            position_x=125,
            position_y=65,
        )
        with self._window.frame:
            with ui.VStack():
                self.image = ui.Image(loading_screen_path, fill_policy=ui.FillPolicy.STRETCH)
        self._window.visible = True


#######################################################################################

#CR: Is this needed, Remove or Put it in to KIT file
        settings = carb.settings.get_settings()
        settings.set("/app/viewport/content.emptyStageOnStart", True)
#########################################################################################

    def setup_viewport_settings(self):
        win = ui.Workspace.get_window("Main ToolBar")
        win.visible = False
        # print("persistent settings are stored in: {}".format(settings.get("/app/userConfigPath")))
        self.setup_viewport_select_op()

    def setup_viewport_select_op(self):

        print("Change selection")
        toolbar = omni.kit.window.toolbar.get_instance()
        print("Changing to select tool")
        button = toolbar.get_widget("select_op")
        button.model.set_value(True)
        settings = carb.settings.get_settings()
        # Changing the setting for whether to move in local or global mode.
        settings.set(TransformButtonGroup.TRANSFORM_MOVE_MODE_SETTING, "local")
        settings.set(TransformButtonGroup.TRANSFORM_MOVE_MODE_SETTING, "global")

    def create_new_toolbar(self):
        # def init_measure():
        # manager = omni.kit.app.get_app().get_extension_manager()
        # manager.set_extension_enabled_immediate("omni.kit.tool.measure", True)
        # MeasurePanel()

        with Toolbar() as tb:
            tb.extensionVisibilityAction(
                "Markups",
                "AnnotationIcon.png",
                "Collaborate with the Markup Tool",
                lambda: MarkupListWindow(),
                ["Markups"],
                [],
            )
            tb.extensionVisibilityAction(
                "Measure",
                "Measurement.png",
                "Take Measurements on the Digital Twin",
                None,
                ["Measure"],
                ["Property", "Attachment"],
                True,
            )
            tb.extensionVisibilityAction(
                "Sun Study",
                "Sun01.png",
                "View Effect of Sun Light by Time of Day",
                None,
                ["Sun Study"],
                [],
            )
            tb.extensionVisibilityAction(
                "Sensors",
                "Sensors_2.png",
                "View Sensor Data Panel",
                None,
                ["Sensors"],
                ["Attachment"],
            )
            # tb.simpleClickAction("Cameras", "Perspective.png", "Change Cameras", lambda : self._camera_changer.change_camera())
            tb.extensionVisibilityAction(
                "Waypoints",
                "Waypoint.png",
                "Waypoints",
                lambda: WaypointListWindow(),
                ["Waypoints"],
                [],
            )
            tb.extensionVisibilityAction(
                "Model Exploder",
                "ExpadingViewsIcon.png",
                "Model Exploder",
                lambda: ModelExploderWindow("Model Exploder", self._manager.get_enabled_extension_id("syntway.model_exploder")),
                ["Model Exploder"],
                [],
                True,
            )

            if partner_secure_data["twinVersionId"] == "1b75f4cf-4855-453a-ac8d-fab23f9923bb":
                # Used only for 1 twin now, so we just need to hard code it
                tb.extensionVisibilityAction(
                    "Variants",
                    "Variant.png",
                    "Variant Presenter Tool Tip",
                    lambda: VariantPresenterWindow(),
                    ["Variant Presenter"],
                    [],
                )
            tb.quitApplicationAction()

    def on_stage_event(self, event: carb.events.IEvent):
        def init_measure():
            self._manager.set_extension_enabled_immediate("omni.kit.tool.measure", True)

        # if (not self._window.visible):
        #     print("I am getting in to asset loading...")
        #     if  event.type == int(omni.usd.StageEventType.ASSETS_LOADING):
        #         self._stage_subscription.unsubscribe()

        #         self._window.visible = True
        #         self._stage_subscription = self.stage_stream.create_subscription_to_pop(
        #         self.on_stage_event, name="MyExtensionOnStageEvent"
        # )


        if event.type == int(omni.usd.StageEventType.ASSETS_LOADED):

            stage = omni.usd.get_context().get_stage()

            if stage.GetPrimAtPath("World/Characters"):
                print("yess")
                # omni.timeline.get_timeline_interface().play()

            print("I am clossing since asset is loaded !!")
            self._stage_subscription.unsubscribe()
            self._stage_subscription = None
            self._window.visible = False

            # Disables auto rebake on startp
            omni.kit.commands.execute(
                'ChangeSettingCommand',
                path="/persistent/exts/omni.anim.navigation.core/navMesh/autoRebakeOnChanges",
                value=False
            )
            omni.kit.commands.execute(
                'ChangeSettingCommand',
                path="/exts/omni.anim.navigation.core/navMesh/cache/enabled",
                value=False
            )
            omni.kit.commands.execute(
                'ChangeSettingCommand',
                path="/exts/omni.anim.navigation.core/navMesh/config/vizSurfaceEnable",
                value=False
            )

            # omni.kit.commands.execute(
            #     "ToggleVisibilitySelectedPrims",
            #     selected_paths=[Sdf.Path('/Environment')],
            #     stage=Usd.Stage.Open(
            #         rootlayer=Sdf.Find(r'C:/Anastasia/gemini-kit-106/source/apps/data/models/9332e77d-fb20-4221-8cf2-9a2c8ef80e22/Building.usd')

            #     )
            # )

            stage = omni.usd.get_context().get_stage()

            try:
                # omni.kit.commands.execute(
                #     "ToggleVisibilitySelectedPrims",
                #     selected_paths=[Sdf.Path('/Environment')],
                #     stage=stage
                # )

                environment_prim = stage.GetPrimAtPath('/Environment')
                paint_prim = stage.GetPrimAtPath('/World/Twins/Building/Geometry/Arch_CannonDesign/PaintTool')
                terrain_prim = stage.GetPrimAtPath('/World/Twins/Building/Geometry/Arch_CannonDesign/Terrain')

                if environment_prim:
                    env_visibility_attr = environment_prim.GetAttribute('visibility')
                    if env_visibility_attr and env_visibility_attr.Get() == "invisible":
                        env_visibility_attr.Set(UsdGeom.Tokens.visible)

                        # stage.GetRootLayer().Save()

                if paint_prim:
                    paint_visibility_attr = paint_prim.GetAttribute('visibility')
                    if paint_visibility_attr and paint_visibility_attr.Get() == "invisible":
                        paint_visibility_attr.Set(UsdGeom.Tokens.visible)
                        # current_visibility = paint_visibility_attr.Get()

                        # stage.GetRootLayer().Save()

                if terrain_prim:
                    terrain_visibility_attr = terrain_prim.GetAttribute('visibility')
                    if terrain_visibility_attr and terrain_visibility_attr.Get() == "invisible":
                        terrain_visibility_attr.Set(UsdGeom.Tokens.visible)

                        # stage.GetRootLayer().Save()

                    else:
                        print("Visibility attribute not found.")

                # for prim in stage.Traverse():
                #     print(prim.GetName(), prim.GetPath())
            except Exception as e:
                print(f"Error executing command: {e}")

            ###############
            # import omni.anim.navigation.core as nav
            # inav = nav.acquire_interface()
            # # inav.cancel_navmesh_baking()

            # valid = inav.validate_navmesh_point(carb.Float3(175.237, 7500.94, 5.39e-08))
            # print(f"Point is valid: {valid}")

            # for offset in [(-1, 0, 0), (1, 0, 0), (0, 0, -1), (0, 0, 1)]:
            #     adjusted_point = carb.Float3(
            #         175.237 + offset[0],
            #         7500.94 + offset[1],
            #         5.39e-08 + offset[2]
            #     )
            #     valid = inav.validate_navmesh_point(adjusted_point)
            #     print(f"Adjusted point {adjusted_point} is valid: {valid}")


            # volume_count = inav.get_navmesh_volume_count()
            # print(f"Navmesh volumes: {volume_count}")

            # nearest = carb.Float3()
            # found = inav.closest_navmesh_point(carb.Float3(175.237, 7500.94, 5.39e-08), nearest)
            # print(f"Nearest valid point: {nearest}, Found: {found}")



            ####################

            # we are doing this after asset is loaded to avoid the "render context changed" message
            init_measure()

            attachment_window = ui.Workspace.get_window("Attachment")
            avatar_window = ui.Workspace.get_window("Avatar configurations")
            stage_window = ui.Workspace.get_window("Stage")
            viewport_window = ui.Workspace.get_window("Viewport")

            if attachment_window and avatar_window:
                avatar_window.dock_in(attachment_window, ui.DockPosition.BOTTOM, 0.5)

            console_window = ui.Workspace.get_window("Console")
            if console_window:
                console_window.visible = False


    async def load_usd_to_viewport(self):
        # Asynchronously open the USD stage

        asyncio.ensure_future(self.loading_screen())
        # partner_secure_data = gdn_services.get_partner_secure_data()
        model_path = core_services.read_api_data_to_temp_file()
        file_path = f"{model_path}/Building.usd"

        print(f"Attempting to load USD file: {file_path}")

        success, error = await omni.usd.get_context().open_stage_async(
            file_path, omni.usd.UsdContextInitialLoadSet.LOAD_ALL
        )
        if not success:
            print(error)
            raise SystemExit("Coould not load USD file: {file_path}")

        # for i in range(35):
        #    await omni.kit.app.get_app().next_update_async()
        self.stage = omni.usd.get_context().get_stage()

        # await omni.kit.app.get_app().next_update_async()
        self.post_usd_load_operations()

    def post_usd_load_operations(self):
        # self.setup_viewport_settings()
        # Operations to execute after the USD has been loaded

        # self.initialize_camera_prim_paths ()
        self._camera_changer.initialize_camera_prim_paths()

        if not ui.Workspace.get_window("Markups"):
            print("Creating MarkUps")
            self._list_window_instance = ui.Workspace.get_window("Markups") or MarkupListWindow()

    def setup_hotkey(self):
        self.keyboard = omni.appwindow.get_default_app_window().get_keyboard()
        self.keyboard_sub_id = carb.input.acquire_input_interface().subscribe_to_keyboard_events(
            self.keyboard, self._on_keyboard_event
        )

    def _on_keyboard_event(self, event, *args, **kwargs):
        if event.input == carb.input.KeyboardInput.F:
            if event.type == KeyboardEventType.KEY_PRESS or event.type == KeyboardEventType.KEY_REPEAT:
                zoom_camera()

    def on_startup(self, ext_id):


        global partner_secure_data

        self._ext_id = ext_id
        self._count = 0
        self._manager = omni.kit.app.get_app().get_extension_manager()

        self.loading_stage = False  # Flag to indicate if a stage loading operation is in progress

        partner_secure_data = gdn_services.get_partner_secure_data()

        self.create_new_toolbar()
        self.stage_stream = omni.usd.get_context().get_stage_event_stream()
        # self.update_subscription = self.update_stream.create_subscription_to_pop(self.on_update_once, name="MyExtensionUpdateOnce")

        self._stage_subscription = self.stage_stream.create_subscription_to_pop(
            self.on_stage_event, name="MyExtensionOnStageEvent"
        )

        self.setup_viewport_settings()

        asyncio.ensure_future(self.load_usd_to_viewport())

        self.setup_hotkey()

        # self.setup_viewport_settings()
        # omni.kit.commands.execute(
        #     "CreateNavMeshVolumeCommand",
        #     parent_prim_path=Sdf.Path("/World"),
        #     layer=None,
        #     usd_context_name=""
        # )

    def on_shutdown(self):
        self._camera_changer = None
