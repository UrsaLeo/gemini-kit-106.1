from pxr import Sdf

import carb
from omni.kit.widgets.custom import COLORS, MouseKey
from omni import ui
from omni.kit.environment.core import UsdModelBuilder, EnvironmentProperties, CityComboBox

from .window_base import WindowBase


ARROWS_ENTRY_NAME = "Compass"
AXIS_ENTRY_NAME = "Axis"
VISIBILITY_PATH = "/persistent/app/viewport/displayOptions"
VISIBILITY_MASK = {
    AXIS_ENTRY_NAME: 1 << 1,
    "Cameras": 1 << 5,
    "FPS": 1 << 0,
    "Grid": 1 << 6,
    "Lights": 1 << 8,
    # "Location": 1 << 3,  # there is no location in kit, guess it is resolution
    "Selection": 1 << 7,
    "Timeline": 1 << 4,
    ARROWS_ENTRY_NAME: 1 << 16,
}


class LocationWindow(WindowBase):
    WINDOW_NAME = "Sun Study Location"
    MENU_PATH = "Window/Set Location"

    WINDOW_WIDTH = 460
    WINDOW_HEIGHT = 0

    LIGHT_WINDOW_STYLE = {
        "Label::location": {"color": 0xFF656565},
        "Label::error": {"color": 0xFF0000FF},
        "Separator::location": {"color": COLORS.CLR_A, "border_width": 2},
    }

    DARK_WINDOW_STYLE = {
        "Label::location": {"color": 0xFFCCCCCC},
        "Label::error": {"color": 0xFF0000FF},
        "Separator::location": {"color": COLORS.CLR_3, "border_width": 2},
    }

    WINDOW_STYLE = {"NvidiaLight": LIGHT_WINDOW_STYLE, "NvidiaDark": DARK_WINDOW_STYLE}

    def __init__(self, player):
        self._player = player
        self._backup_data = [0, 0, 0]

        if self._player is None:
            carb.log_error("Create Set Data&Time window without sunstudy player!")

        self._city_combobox = None
        self._longitude_model = UsdModelBuilder().create_property_value_model(
            EnvironmentProperties.LONGITUDE, value_type=Sdf.ValueTypeNames.Float, default=0, min=-180, max=180
        )

        self._latitude_model = UsdModelBuilder().create_property_value_model(
            EnvironmentProperties.LATITUDE, value_type=Sdf.ValueTypeNames.Float, default=0, min=-90, max=90
        )

        self._longitude_model.add_value_changed_fn(self._reset_city)
        self._latitude_model.add_value_changed_fn(self._reset_city)

        self._north_orientation_model = UsdModelBuilder().create_property_value_model(
            EnvironmentProperties.NORTH_ORIENTATION, value_type=Sdf.ValueTypeNames.Float, default=0, min=0, max=360
        )

        super().__init__(
            LocationWindow.WINDOW_NAME,  # Title & window name
            ui.DockPreference.DISABLED,  # Dock
            LocationWindow.WINDOW_WIDTH,  # Width
            LocationWindow.WINDOW_HEIGHT,  # Height
            menu_path=LocationWindow.MENU_PATH,
            appear_after="Material Mapper",
            use_editor_menu=True,
        )

        self.set_visibility_changed_fn(self._on_visibility_changed)

    def _get_content_style(self, ui_style):
        # overided base.
        return LocationWindow.WINDOW_STYLE[ui_style]

    # Override base class's implement
    def _build_content(self):
        label_width = 130

        with ui.HStack(height=26):
            ui.Spacer(width=10)
            # ui.Label("Address", name="location", width=120, alignment=ui.Alignment.RIGHT)
            ui.Label("Preset", name="location", width=label_width, alignment=ui.Alignment.RIGHT_CENTER)
            ui.Spacer(width=5)
            self._city_combobox = CityComboBox()
            ui.Spacer(width=50)

        ui.Spacer(height=15)
        ui.Separator(height=0, name="location")
        ui.Spacer(height=15)

        with ui.HStack(height=0):
            ui.Spacer(width=10)
            ui.Label("Latitude", name="location", width=label_width, alignment=ui.Alignment.RIGHT_CENTER)

            ui.Spacer(width=5)
            ui.FloatDrag(self._latitude_model, name="ss-models", min=-90, max=90, step=0.3)
            ui.Spacer(width=50)

        ui.Spacer(height=15)
        with ui.HStack(height=0):
            ui.Spacer(width=10)
            ui.Label("Longitude", name="location", width=label_width, alignment=ui.Alignment.RIGHT_CENTER)

            ui.Spacer(width=5, height=0)
            ui.FloatDrag(self._longitude_model, name="ss-models", min=-180, max=180, step=0.3)
            ui.Spacer(width=50)

        ui.Spacer(height=15)
        with ui.HStack(height=0):
            ui.Spacer(width=10)
            ui.Label("North Orientation", name="location", width=label_width, alignment=ui.Alignment.RIGHT_CENTER)
            ui.Spacer(width=5)
            ui.FloatDrag(self._north_orientation_model, name="ss-models", min=0, max=360, step=0.5)
            ui.Spacer(width=50)

        ui.Spacer(height=15)
        with ui.HStack(height=0):
            ui.Spacer(width=10, height=0)
            self.errorlabel = ui.Label(
                "", name="error", height=0, alignment=ui.Alignment.H_CENTER, style={"color": 0xFF0000FF}
            )

        ui.Spacer(height=15)
        with ui.HStack(height=28):
            ui.Spacer()
            with ui.HStack(width=ui.Percent(50)):
                ui.Spacer()
                ui.Button("Close", height=0, clicked_fn=lambda: self._on_close(MouseKey.LEFT))
                ui.Spacer(width=8)
            with ui.HStack(width=ui.Percent(50)):
                ui.Spacer(width=8)
                ui.Button("Cancel", height=0, clicked_fn=self._on_cancel)
                ui.Spacer()
            ui.Spacer()
        ui.Spacer(height=20)

        self._city_combobox.model.set_location(self._longitude_model.as_float, self._latitude_model.as_float)
        self._city_combobox.model.add_item_changed_fn(self._on_city_changed)

    def _on_city_changed(self, model: ui.AbstractItemModel, item: ui.AbstractItem):
        idx = model.get_item_value_model().as_int
        if idx == 0:
            # Custom, keep longitude and latitude without changes
            if self._player is not None:
                self._player.update_fix_timezone(False)
            return

        location_item = model.get_item_children(item)[idx]
        longitude = model.get_item_value_model(location_item, column_id=1).as_float
        latitude = model.get_item_value_model(location_item, column_id=2).as_float

        if abs(latitude - self._latitude_model.as_float) >= 0.00001:
            self._latitude_model.set_value(latitude)
        if abs(longitude - self._longitude_model.as_float) >= 0.00001:
            self._longitude_model.set_value(longitude)

        if self._player is not None:
            self._player.update_fix_timezone(True)

    def _reset_city(self, *_):
        if self._city_combobox is not None:
            latitude = self._latitude_model.as_float
            longitude = self._longitude_model.as_float
            self._city_combobox.model.set_location(longitude, latitude)

    def _on_cancel(self):
        self._latitude_model.set_value(self._backup_data[0])
        self._longitude_model.set_value(self._backup_data[1])
        self._north_orientation_model.set_value(self._backup_data[2])

        self._on_close(MouseKey.LEFT)

    def _on_visibility_changed(self, visible):
        if visible:
            self._show_compass()
            self.init_data()
        else:
            self._restore_compass()
            self.errorlabel.text = ""

    def _on_close(self, btn):
        if btn == MouseKey.LEFT:
            self.show(False)
            self.errorlabel.text = ""

    def _get_window_flags(self):
        flags = super()._get_window_flags()
        flags = flags | ui.WINDOW_FLAGS_NO_DOCKING
        return flags

    def init_data(self):
        self._backup_data[0] = self._latitude_model.as_float
        self._backup_data[1] = self._longitude_model.as_float
        self._backup_data[2] = self._north_orientation_model.as_float

    def show_align_to_right(self, right=0, top=0):
        # Call base
        if right > 0:
            left = right - LocationWindow.WINDOW_WIDTH
        else:
            left = 0
        super().show(True, left, top)

    def destroy(self):
        self._player = None
        self.set_visibility_changed_fn(None)
        super().destroy()

    def _show_compass(self):
        setting = carb.settings.get_settings()
        visibility_value = setting.get(VISIBILITY_PATH) or 0
        self._origin_state = visibility_value
        visibility_value = visibility_value | VISIBILITY_MASK[ARROWS_ENTRY_NAME]
        visibility_value = visibility_value & ~VISIBILITY_MASK[AXIS_ENTRY_NAME]
        setting.set(VISIBILITY_PATH, visibility_value)

    def _restore_compass(self):
        setting = carb.settings.get_settings()
        visibility_value = setting.get(VISIBILITY_PATH) or 0

        if self._origin_state & VISIBILITY_MASK[ARROWS_ENTRY_NAME]:
            visibility_value = visibility_value | VISIBILITY_MASK[ARROWS_ENTRY_NAME]
        else:
            visibility_value = visibility_value & ~VISIBILITY_MASK[ARROWS_ENTRY_NAME]

        if self._origin_state & VISIBILITY_MASK[AXIS_ENTRY_NAME]:
            visibility_value = visibility_value | VISIBILITY_MASK[AXIS_ENTRY_NAME]
        else:
            visibility_value = visibility_value & ~VISIBILITY_MASK[AXIS_ENTRY_NAME]

        setting.set(VISIBILITY_PATH, visibility_value)
