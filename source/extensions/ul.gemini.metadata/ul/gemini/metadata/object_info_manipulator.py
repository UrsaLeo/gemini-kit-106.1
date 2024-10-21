import os
import omni.usd
import omni.ui as ui
from omni.ui import scene as sc
from omni.ui import color as cl
from omni.kit.viewport.utility import get_active_viewport
from pxr import UsdGeom
from .utils import screen_to_world


class ObjInfoManipulator(sc.Manipulator):
    """Manipulator that displays the object path and material assignment
    with a leader line to the top of the object's bounding box.
    """
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._root = None
        self._widget = None
        self.tower_name = ""
        self.values = {}

    active_viewport = get_active_viewport()

    def destroy(self):
        omni.usd.get_context().get_selection().clear_selected_prim_paths()

    def _on_build_widgets(self):
        # Get names and values from attributes
        names = [item.GetName() for item in self.custom_attr.values()]
        values = [str(item.Get()) for item in self.custom_attr.values()]
        alignments = [ui.Alignment.LEFT, ui.Alignment.CENTER, ui.Alignment.RIGHT]

        style_system = {
            "Button": {
                "background_color": cl("#1e1e38"),
                "border_color": cl("#1e1e38"),
                "border_width": 2,
                "border_radius": 5,
                "padding": 5,
            },
            "font": "${fonts}/roboto_medium.ttf"
        }

        with ui.ZStack():
            ui.Rectangle(
                style={
                    "background_color": cl("#1e1e38"),
                    "border_color": cl(0.7),
                    "border_width": 4,
                    "border_radius": 12,
                }
            )
            with ui.VStack(style={"font_size": 30, "margin": 5}):
                with ui.HStack(style=style_system):
                    with ui.VStack():
                        ui.Label("Prim Metadata", style={"color": cl.white})
                        ui.Label(self.tower_name, style={"color": cl("#0afc7f"), "font_size": 50})
                    ui.Button(
                            image_url=os.path.join(os.path.dirname(__file__), "photo", "close.png"),
                            clicked_fn=lambda: self.destroy(),
                            tooltip="Close Details",
                            width=75,
                            height=75
                        )

                with ui.HStack(style=style_system):
                    with ui.VStack():
                        with ui.HStack():
                            for name, value, alignment in zip(names, values, alignments):
                                with ui.VStack():
                                    ui.Label(name, style={"color": cl.white, "font_size": 30}, alignment=alignment)
                                    ui.Label(value, style={"color": cl("#0afc7f"), "font_size": 40}, alignment=alignment)


        self.on_model_updated(None)

    def on_build(self):
        self._root = sc.Transform(visible=False)
        with self._root:
            with sc.Transform(look_at=sc.Transform.LookAt.CAMERA):
                pass
                # NOTE! This code will be needed if we choose to use Widget instead of Window to display metadata

                # self._widget = sc.Widget(700, 355, update_policy=sc.Widget.UpdatePolicy.ALWAYS)
                # self._widget.frame.set_build_fn(self._on_build_widgets)

                # self.window = ui.Window("Toggle Widget View", width=300, height=300)
                # # self.ext_id = ext_id
                # self.window.frame.set_build_fn(self._on_build_widgets)
                # # with self.window.frame:
                # #     self._on_build_widgets()
                #     # with ui.HStack(height=0):
                #     #     ui.Label("Prim Metadataa", alignment=ui.Alignment.CENTER_TOP, style={"margin": 5})


            # window = ui.Window("My Window", width=300, height=600)
            # with window.frame:
            #     self._on_build_widgets()

    def on_model_updated(self, _):
        active_viewport = get_active_viewport()
        self.stage = self.model.usd_context.get_stage()

        camera = UsdGeom.Camera(self.stage.GetPrimAtPath(get_active_viewport().camera_path))
        viewport_width, viewport_height = active_viewport.resolution[0], active_viewport.resolution[1]
        screen_pos = (viewport_width - 220, 100)
        upper_right_world_pos = screen_to_world(camera, screen_pos, viewport_width, viewport_height)

        self.path = self.model.get_item("name")

        if not self.model or not self.path:
            self._root.visible = False
            return

        custom_attr = self.model.get_item("attr")
        self.custom_attr = custom_attr
        if not custom_attr:
            self._root.visible = False
            return

        self.tower_name = self.path.split("/")[-1]

        if self._root:
            self._root.transform = sc.Matrix44.get_translation_matrix(*upper_right_world_pos)
            self._root.visible = True

        if self._widget:
            self._widget.frame.rebuild()
