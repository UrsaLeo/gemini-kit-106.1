from datetime import datetime, date, time
from pxr import Sdf

from omni import ui
from omni.kit.widget.calendar import Calendar
from omni.kit.environment.core import UsdModelBuilder, EnvironmentProperties
from omni.kit.widgets.custom import UpdateEventHelper, COLORS

from .sunstudy_dialog import Clock
from .window_base import WindowBase


class DateTimeWindow(WindowBase):
    YEAR_MIN = 2000
    YEAR_MAX = 2051
    WINDOW_NAME = "Sun Study Date & Time"
    MENU_PATH = "Window/Set Date and Time"

    WINDOW_WIDTH = 500
    WINDOW_HEIGHT = 290

    LIGHT_WINDOW_STYLE = {
        **Clock.LIGHT_WINDOW_STYLE,
        "Rectangle::calendar": {"background_color": COLORS.TRANSPARENT, "border_radius": 2.0},
        "Rectangle::calendar:hovered": {"background_color": COLORS.CLR_B},
        "Rectangle::calendar:pressed": {"background_color": COLORS.CLR_A},
    }

    DARK_WINDOW_STYLE = {
        **Clock.DARK_WINDOW_STYLE,
        "Rectangle::calendar": {"background_color": COLORS.TRANSPARENT, "border_radius": 2.0},
        "Rectangle::calendar:hovered": {"background_color": COLORS.CLR_5},
        "Rectangle::calendar:pressed": {"background_color": COLORS.CLR_7},
    }

    WINDOW_STYLE = {"NvidiaLight": LIGHT_WINDOW_STYLE, "NvidiaDark": DARK_WINDOW_STYLE}

    def __init__(self):
        self._date_model = UsdModelBuilder().create_property_value_model(
            EnvironmentProperties.DATE, value_type=Sdf.ValueTypeNames.String, default="2021-11-24"
        )
        self._time_model = UsdModelBuilder().create_property_value_model(
            EnvironmentProperties.TIME_CURRENT, value_type=Sdf.ValueTypeNames.Float, default=0
        )

        super().__init__(
            DateTimeWindow.WINDOW_NAME,  # Title & window name
            ui.DockPreference.DISABLED,  # Dock
            DateTimeWindow.WINDOW_WIDTH,  # Width
            DateTimeWindow.WINDOW_HEIGHT,  # Height
            menu_path=DateTimeWindow.MENU_PATH,
            appear_after="Set Location",
            use_editor_menu=True,
        )

        self.set_visibility_changed_fn(self._on_visibility_changed)

    def destroy(self):
        self._update_event_helper.deregister_update(self._clock)
        self._update_event_helper = None
        super().destroy()

    def _get_content_style(self, ui_style):
        # overided base.
        return DateTimeWindow.WINDOW_STYLE[ui_style]

    # Override base class's implement
    def _build_content(self):
        date_time = datetime.now()

        # build calendar and clock
        with ui.HStack(height=200):
            self._calendar = Calendar(date_time.date(), width=210, height=200)
            # self._last_date = self._calendar.model.as_string
            # self._calendar.model.add_value_changed_fn(self._on_calendar_changed)

            ui.Spacer(width=5)
            with ui.VStack():
                ui.Spacer(height=50)
                self._clock = Clock(date_time.time())
                self._update_event_helper = UpdateEventHelper.get_instance()
                self._update_event_helper.register_update(self._clock)
                ui.Spacer()
            ui.Spacer()

        # Build control buttons
        with ui.HStack(height=28):
            ui.Spacer()
            with ui.HStack(width=ui.Percent(50)):
                ui.Spacer()
                ui.Button("Apply", height=0, clicked_fn=self._on_apply_clicked)
                ui.Spacer(width=8)
            with ui.HStack(width=ui.Percent(50)):
                ui.Spacer(width=8)
                ui.Button("Cancel", height=0, clicked_fn=self._on_cancel_clicked)
                ui.Spacer()
            ui.Spacer()

    def _on_apply_clicked(self):
        self._on_final_close(True)

    def _on_cancel_clicked(self):
        self._on_final_close(False)

    """
    def _on_help(self, btn):
        help_url = "https://docs.omniverse.nvidia.com/aec/text/AEC_View_UserManual.html#side-bar"
        webbrowser.open(help_url)
    """

    def _on_visibility_changed(self, visible):
        def __float_to_time(ft):
            hour = int(ft)
            ft = (ft - hour) * 60
            minute = int(ft)
            ft = (ft - minute) * 60
            second = int(ft)
            ft = (ft - second) * 1000000
            microsecond = int(ft)
            return time(hour, minute, second, microsecond)

        if visible:
            date_str = self._date_model.as_string
            (year, month, day) = date_str.split("-")
            date_value = date(int(year), int(month), int(day))
            self._calendar.set_date(date_value)
            time_of_day = self._time_model.as_float
            self._clock.set_time(__float_to_time(time_of_day))

    def _on_final_close(self, save):
        def __time_to_float(tm):
            return float(tm.hour) + tm.minute / 60.0 + tm.second / 3600.0 + tm.microsecond / (3600.0 * 1000000)

        self._window.visible = False
        if not save:
            return

        self._date_model.set_value(self._calendar.model.as_string)
        self._time_model.set_value(__time_to_float(self._clock.time))

    def _get_window_flags(self):
        flags = super()._get_window_flags()
        flags = flags | ui.WINDOW_FLAGS_NO_DOCKING
        return flags

    def show_align_to_right(self, right=0, top=0):
        # Call base
        if right > 0:
            left = right - DateTimeWindow.WINDOW_WIDTH
        else:
            left = 0
        self.show(True, left, top)

    def set_ui_style(self, style):
        super().set_ui_style(style)
        self._clock.set_ui_style(style)
        # self._calendar.set_ui_style(style)
