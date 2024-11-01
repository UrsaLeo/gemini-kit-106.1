from datetime import datetime
from pxr import Sdf
import carb
import carb.settings

from omni import ui
from omni.kit.environment.core import (
    PlayButton,
    PlayRateButton,
    PlayLoopButton,
    SunstudyTimeSlider,
    UsdModelBuilder,
    EnvironmentProperties,
)
from omni.kit.environment.core import get_sunstudy_player
import omni.kit.app
from .style import SLIDER_STYLE, PanelStyle, SunstudyColors

import asyncio
import pathlib


EXTENSION_FOLDER_PATH = pathlib.Path(
    omni.kit.app.get_app().get_extension_manager().get_extension_path_by_module(__name__)
)
COLORS_SETTING_PATH = "/exts/omni.kit.environment.sunstudy/colors"
WIDTH_SETTING_PATH = "/exts/omni.kit.environment.sunstudy/window/width"


class SunstudyWindowLayer:
    WINDOW_NAME = "Sun Study"
    MENU_PATH = f"Window/{WINDOW_NAME}"
    WIDTH = 880
    HEADER_HEIGHT = 14

    PADDING = 10

    __instance = None
    __init_visible = True

    @staticmethod
    def set_init_visible(visible: bool):
        SunstudyWindowLayer.__init_visible = visible

    def __init__(self, factory_args, *ui_args, **ui_kwargs):
        super().__init__()

        settings = carb.settings.get_settings()
        panel_color = settings.get(f"{COLORS_SETTING_PATH}/panel")
        if panel_color:
            SunstudyColors.Panel = panel_color
        window_width = settings.get(WIDTH_SETTING_PATH)
        if window_width:
            SunstudyWindowLayer.WIDTH = window_width

        self._time_slider = None

        ui_kwargs["build_fn"] = self._build_fn
        ui_kwargs["visible"] = True
        ui_kwargs["vertical_clipping"] = True
        ui_kwargs["herizontal_clipping"] = True
        ui_kwargs["visible"] = SunstudyWindowLayer.__init_visible

        self.__ui_frame = ui.Frame(*ui_args, **ui_kwargs)

        self._player = get_sunstudy_player()

        self._date_model = UsdModelBuilder().create_property_value_model(
            # EnvironmentProperties.DATE, value_type=Sdf.ValueTypeNames.String, default="2021-11-24"
            EnvironmentProperties.DATE, value_type=Sdf.ValueTypeNames.String, default=datetime.today().isoformat()
        )
        self._time_model = UsdModelBuilder().create_property_value_model(
            EnvironmentProperties.TIME_CURRENT, value_type=Sdf.ValueTypeNames.Float, default=0
        )
        self._date_model.add_value_changed_fn(self._on_date_time_changed)
        self._time_model.add_value_changed_fn(self._on_date_time_changed)

        SunstudyWindowLayer.__instance = self

    def destroy(self):
        if self.__ui_frame:
            self.__ui_frame.destroy()
            self.__ui_frame = None

        self._player = None
        SunstudyWindowLayer.__instance = None
        # self._menu_action = None

    @staticmethod
    def get_instance():
        return SunstudyWindowLayer.__instance

    @property
    def name(self):
        return "Sunstudy Layer"

    @property
    def categories(self):
        return ("sunstudy", "utility")

    @property
    def layers(self):
        return tuple()

    @property
    def visible(self):
        return self.__ui_frame.visible if self.__ui_frame else False

    @visible.setter
    def visible(self, visible: bool):
        if self.__ui_frame:
            self.__ui_frame.visible = bool(visible)

    '''
    def _on_menu_action(self):
        if self.__ui_frame:
            self.__ui_frame.visible = not self.__ui_frame.visible
    def _create_menu(self, menu_path, hotkey=None, appear_after=""):
        paths = menu_path.split("/")
        if len(paths) == 1:
            menu_title = menu_path
            self._parent_menu_title = "Window"
        else:
            menu_title = paths[-1]
            self._parent_menu_title = paths[0]
        # Add menu
        self._menu_list = [
            MenuItemDescription(
                name=menu_title,
                # glyph="cog.svg",
                appear_after=appear_after,
                ticked=True,
                ticked_fn=self._on_tick,
                onclick_fn=self._on_click,
                hotkey=hotkey,
            )
        ]
        omni.kit.menu.utils.add_menu_items(self._menu_list, self._parent_menu_title, -1)

    '''

    def _build_fn(self):
        with ui.ZStack(width=ui.Percent(100), height=ui.Percent(100), spacing=0, style=PanelStyle.get()):
            # The window header
            self._header_placer = ui.Placer(
                offset_x=0, offset_y=0, height=0, width=0, draggable=True, drag_axis=ui.Axis.XY
            )
            self._header_placer.set_offset_x_changed_fn(self._check_pos_x)
            self._header_placer.set_offset_y_changed_fn(self._check_pos_y)

            self._panel_placer = ui.Placer(offset_x=0, offset_y=0, height=0, width=0, draggable=False)

        with self._header_placer:
            ui.Rectangle(name="blank", width=SunstudyWindowLayer.WIDTH, height=SunstudyWindowLayer.HEADER_HEIGHT)

        with self._panel_placer:
            self._panel_stack = ui.ZStack(width=0, height=0, spacing=0)
        with self._panel_stack:
            self._build_content()

        self.__ui_frame.set_computed_content_size_changed_fn(self._on_viewport_size_changed)
        self._on_viewport_size_changed()

    def _check_pos_x(self, x_len):
        x = float(x_len)
        if x < 0:
            x = 0
            self._header_placer.offset_x = x
        elif x + self._panel_stack.computed_width > self.__ui_frame.computed_width:
            x = max(self.__ui_frame.computed_width - self._header_stack.computed_width, 0)
            self._header_placer.offset_x = x

        async def __delay_change_offset_x(placer, value):
            await omni.kit.app.get_app().next_update_async()
            placer.offset_x = value

        asyncio.ensure_future(__delay_change_offset_x(self._panel_placer, x))

    def _check_pos_y(self, y_len):
        y = float(y_len)
        if y < 0:
            y = 0
            self._header_placer.offset_y = y
        else:
            if y + self._panel_stack.computed_height > self.__ui_frame.computed_height:
                y = max(self.__ui_frame.computed_height - self._panel_stack.computed_height, 0)
                self._header_placer.offset_y = y

        async def __delay_change_offset_y(placer, value):
            await omni.kit.app.get_app().next_update_async()
            placer.offset_y = value

        asyncio.ensure_future(__delay_change_offset_y(self._panel_placer, y))

    async def __delay_reset_offset(self):
        if not self._panel_stack:
            return

        await omni.kit.app.get_app().next_update_async()

        offset_x = max(0, (self.__ui_frame.computed_width - SunstudyWindowLayer.WIDTH) / 2)
        if offset_x != self._header_placer.offset_x:
            self._header_placer.offset_x = offset_x
        offset_y = max(0, self.__ui_frame .computed_height - self._panel_stack.computed_height - 5)
        if offset_y != self._header_placer.offset_y:
            self._header_placer.offset_y = offset_y

    def _on_viewport_size_changed(self):
        asyncio.ensure_future(self.__delay_reset_offset())

    def _on_dragging_slider(self, dragging):
        if dragging:
            self._panel_placer.draggable = False
        else:
            self._panel_placer.draggable = True

    def _build_content(self):
        ui.Rectangle(name="panel", width=SunstudyWindowLayer.WIDTH, mouse_hovered_fn=self._on_panel_hovered)
        with ui.VStack(height=0, spacking=0):
            with ui.ZStack(width=0, height=0):
                self._title_rect = ui.Rectangle(name="title", width=SunstudyWindowLayer.WIDTH, height=SunstudyWindowLayer.HEADER_HEIGHT)
                with ui.VStack(width=SunstudyWindowLayer.WIDTH, height=SunstudyWindowLayer.HEADER_HEIGHT):
                    ui.Spacer(height=1)
                    with ui.HStack():
                        size = SunstudyWindowLayer.HEADER_HEIGHT - 4
                        ui.Spacer(width=size + 5)
                        ui.Spacer()
                        ui.Label(SunstudyWindowLayer.WINDOW_NAME, width=0, name="title")
                        ui.Spacer()
                        with ui.ZStack(width=size, height=size):
                            def __on_close_pressed(x, y, key, m):
                                if key == 0:  # left button
                                    ui.Workspace.show_window(SunstudyWindowLayer.WINDOW_NAME, False)

                            ui.Rectangle(name="button", mouse_pressed_fn=__on_close_pressed)
                            ui.Image(f"{EXTENSION_FOLDER_PATH}/icons/close.svg", width=size, height=size)
                        ui.Spacer(width=5)
                    ui.Spacer()

            ui.Spacer(height=5)
            self._time_slider = SunstudyTimeSlider(
                on_datetime_changed_fn=self._on_date_time_changed,
                style=SLIDER_STYLE,
            )

            ui.Spacer(height=5)
            with ui.ZStack():
                with ui.HStack(height=24):
                    ui.Spacer(width=24)
                    self._rate_button = PlayRateButton(width=16, height=16, image_width=14, image_height=14)
                    self._loop_button = PlayLoopButton(width=16, height=16, image_width=14, image_height=14)
                    ui.Spacer()

                    label_width = 192
                    with ui.ZStack(height=20, width=label_width + 4):
                        with ui.Placer(offset_x=0, offset_y=0):
                            ui.Rectangle(
                                name="button",
                                width=label_width + 4,
                                height=20,
                                mouse_pressed_fn=lambda x, y, key, m: self._on_date_time_clicked(key),
                                tooltip="Set Date & Time",
                            )
                        with ui.Placer(offset_x=2, offset_y=2):
                            self._current_time_label = ui.Label(
                                "", name="time", width=label_width, alignment=ui.Alignment.H_CENTER
                            )
                    ui.Spacer(width=24)

                with ui.HStack(height=16):
                    ui.Spacer()
                    self._play_button = PlayButton(self._player, width=16, height=16, image_width=14, image_height=14)
                    ui.Spacer()

            ui.Spacer(height=2)

        self._time_slider.current_time_model.add_value_changed_fn(self._on_date_time_changed)
        self._update_date_time()

    def _on_panel_hovered(self, hovered: bool):
        self._title_rect.selected = hovered

    def _on_date_time_changed(self, mode: ui.AbstractValueModel) -> None:
        self._update_date_time()

    # When data in background are changed, update the visiual elements to reflect the changes
    def _update_date_time(self):
        def _time_float_to_string(value: float) -> str:
            value = max(value, 0)
            value = min(value, 24)

            hour = int(value)
            total_seconds = int((value - hour) * 3600)
            minute = int(total_seconds / 60)
            second = total_seconds % 60

            return "{}:{:02d}:{:02d}".format(hour, minute, second)

        if self._time_slider is None or self._current_time_label is None:
            return

        time = _time_float_to_string(self._time_slider.current_time_model.as_float)
        self._current_time_label.text = datetime.strptime(
            f"{self._date_model.as_string} {time}", "%Y-%m-%d %H:%M:%S"
        ).strftime("%I:%M %p %B %d, %Y")

    # Called when the date-time label in the window is clicked
    def _on_date_time_clicked(self, key):
        if key != 0:  # Left button
            return

        date_time_window = ui.Workspace.get_window("Sun Study Date & Time")
        if date_time_window is None:
            return
        if date_time_window.visible:
            date_time_window.visible = False
        else:
            date_time_window.visible = True
            # width_delta = self._window.width - date_time_window.width
            # date_time_window.position_x = self._window.position_x + width_delta
            # date_time_window.position_y = self._window.position_y - date_time_window.height - 5
