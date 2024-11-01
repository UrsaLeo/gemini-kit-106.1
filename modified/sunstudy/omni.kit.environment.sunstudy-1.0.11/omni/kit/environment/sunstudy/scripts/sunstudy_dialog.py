import datetime

from omni.kit.widgets.custom import COLORS, MouseKey
from omni import ui

from .utils import get_nominal_font_size


class Spinner:
    LIGHT_WINDOW_STYLE = {
        "Triangle::spinner": {"background_color": COLORS.CLR_9, "border_width": 0},
        "Triangle::spinner:hovered": {"background_color": COLORS.CLR_7},
        "Triangle::spinner:pressed": {"background_color": COLORS.CLR_4},
    }

    DARK_WINDOW_STYLE = {
        "Triangle::spinner": {"background_color": COLORS.CLR_8, "border_width": 0},
        "Triangle::spinner:hovered": {"background_color": COLORS.CLR_B},
        "Triangle::spinner:pressed": {"background_color": COLORS.CLR_C},
    }

    WINDOW_STYLE = {"NvidiaLight": LIGHT_WINDOW_STYLE, "NvidiaDark": DARK_WINDOW_STYLE}

    REPEAT_DELAY = 0.500
    REPEAT_INTERVAL = 0.300

    def __init__(self, width, height, on_spin_fn, with_up=True, with_down=True, repeat=True):
        self._on_spin_fn = on_spin_fn
        self._repeat = repeat

        self._cur_time = 0.0
        self._action_time = 0.0
        # 1: Up pressed, 0: None, -1: Down pressed
        self._repeat_step = 0

        padding_x = width // 6
        padding_y = height // 9

        with ui.ZStack(width=width, height=height):
            with ui.Placer(offset_x=padding_x, offset_y=padding_y):
                self._spin_up = ui.Triangle(
                    name="spinner",
                    width=padding_x * 4,
                    height=padding_y * 3,
                    alignment=ui.Alignment.CENTER_TOP,
                    mouse_pressed_fn=(lambda x, y, key, m: self._on_spin_clicked(key, 1)),
                    mouse_released_fn=(lambda x, y, key, m: self._on_spin_released(key)),
                    visible=with_up,
                    opaque_for_mouse_events=True,
                )
            with ui.Placer(offset_x=padding_x, offset_y=padding_y * 5):
                self._spin_down = ui.Triangle(
                    name="spinner",
                    width=padding_x * 4,
                    height=padding_y * 3,
                    alignment=ui.Alignment.CENTER_BOTTOM,
                    mouse_pressed_fn=lambda x, y, key, m: self._on_spin_clicked(key, -1),
                    mouse_released_fn=(lambda x, y, key, m: self._on_spin_released(key)),
                    visible=with_down,
                    opaque_for_mouse_events=True,
                )

    def on_update(self, dt):
        self._cur_time += dt

        if not self._repeat or self._repeat_step == 0:
            return

        if self._cur_time > self._action_time:
            self._on_spin_fn(self._repeat_step)
            self._action_time += self.REPEAT_INTERVAL

    def _on_spin_clicked(self, key, step):
        # We only respond to left button
        if key != MouseKey.LEFT:
            return

        self._action_time = self._cur_time + self.REPEAT_DELAY
        self._repeat_step = step
        self._on_spin_fn(step)

    def _on_spin_released(self, key):
        if key != MouseKey.LEFT:
            return
        self._repeat_step = 0


class Number:
    """
    __img_map_light = {
        0: get_icon_path("0.png"),
        1: get_icon_path("1.png"),
        2: get_icon_path("2.png"),
        3: get_icon_path("3.png"),
        4: get_icon_path("4.png"),
        5: get_icon_path("5.png"),
        6: get_icon_path("6.png"),
        7: get_icon_path("7.png"),
        8: get_icon_path("8.png"),
        9: get_icon_path("9.png"),
    }
    __img_map_dark = {
        0: get_icon_path("0-dark.svg"),
        1: get_icon_path("1-dark.svg"),
        2: get_icon_path("2-dark.svg"),
        3: get_icon_path("3-dark.svg"),
        4: get_icon_path("4-dark.svg"),
        5: get_icon_path("5-dark.svg"),
        6: get_icon_path("6-dark.svg"),
        7: get_icon_path("7-dark.svg"),
        8: get_icon_path("8-dark.svg"),
        9: get_icon_path("9-dark.svg"),
    }
    __img_map = __img_map_dark
    """

    def __init__(self, width, height):
        self._value = 0
        # self._image = ui.Image(Number.__img_map[0], width=width, height=height)
        label_style = {"font_size": get_nominal_font_size(32)}
        self._label = ui.Label("0", width=width, height=height, name="number", style=label_style)

    def set_value(self, value, force=False):
        if value < 0:
            value = 0
        elif value > 9:
            value = 9
        if not force and self._value == value:
            return

        self._value = value
        # self._image.source_url = Number.__img_map[value]
        self._label.text = str(value)

    @staticmethod
    def set_ui_style(style):
        pass


class Clock:
    LIGHT_WINDOW_STYLE = {
        **Spinner.LIGHT_WINDOW_STYLE,
        "Circle::clock": {"background_color": COLORS.CLR_4, "border_width": 0},
        "Label::half_day": {"color": COLORS.CLR_5, "alignment": ui.Alignment.LEFT_CENTER},
        "Label::number": {"color": COLORS.CLR_5, "alignment": ui.Alignment.LEFT_CENTER},
    }

    DARK_WINDOW_STYLE = {
        **Spinner.DARK_WINDOW_STYLE,
        "Circle::clock": {"background_color": COLORS.CLR_8, "border_width": 0},
        "Label::half_day": {"color": COLORS.CLR_C, "alignment": ui.Alignment.LEFT_CENTER},
        "Label::number": {"color": COLORS.CLR_C, "alignment": ui.Alignment.LEFT_CENTER},
    }

    WINDOW_STYLE = {"NvidiaLight": LIGHT_WINDOW_STYLE, "NvidiaDark": DARK_WINDOW_STYLE}

    def __init__(self, time):
        self._time = time

        with ui.ZStack(height=54, width=0):
            # 2 digits for hour
            x = 10
            with ui.Placer(offset_x=x, offset_y=0):
                self._hour10x = Number(30, 54)
            with ui.Placer(offset_x=x + 20, offset_y=0):
                self._hour1x = Number(30, 54)
            x += 40

            # Spin for hour
            with ui.Placer(offset_x=x, offset_y=13):
                self._hour_spin = Spinner(15, 30, self._on_hour_spin)
            x += 20

            # Colon between hour and minute
            with ui.Placer(offset_x=x, offset_y=18):
                ui.Circle(name="clock", width=5, height=5)
            with ui.Placer(offset_x=x, offset_y=32):
                ui.Circle(name="clock", width=5, height=5)
            x += 15

            # 2 digits for minute
            with ui.Placer(offset_x=x, offset_y=0):
                self._minute10x = Number(30, 54)
            with ui.Placer(offset_x=x + 20, offset_y=0):
                self._minute1x = Number(30, 54)
            x += 40

            # Spin for minute
            with ui.Placer(offset_x=x, offset_y=13):
                self._minute_spin = Spinner(15, 30, self._on_minute_spin)
            x += 20

            # Lable for half-day
            with ui.Placer(offset_x=x, offset_y=0):
                self._half_day = ui.Label(
                    "PM", name="half_day", width=40, style={"font_size": get_nominal_font_size(26)}
                )
            x += 35

            # Spin for half-day
            with ui.Placer(offset_x=x, offset_y=12):
                self._half_day_spin = Spinner(15, 30, self._on_half_day_spin, False, True, False)
            x += 20

            self._update_hour()
            self._update_minute()

    def _update_hour(self, force=False):
        section = "PM"
        if self._time.hour < 1.0:
            section = "AM"
            hour = 12
        elif self._time.hour < 12.0:
            hour = int(self._time.hour)
            section = "AM"
        elif self._time.hour < 13.0:
            hour = int(self._time.hour)
        else:
            hour = int(self._time.hour) - 12

        self._half_day.text = section
        self._hour10x.set_value(hour // 10, force)
        self._hour1x.set_value(hour % 10, force)

    def _update_minute(self, force=False):
        self._minute10x.set_value(self._time.minute // 10, force)
        self._minute1x.set_value(self._time.minute % 10, force)

    def _on_hour_spin(self, step):
        hour = self._time.hour + step
        if hour < 0:
            hour = 23
        elif hour > 23:
            hour = 0

        self._time = datetime.time(hour, self._time.minute, self._time.second, self._time.microsecond)
        self._update_hour()

    def _on_minute_spin(self, step):
        minute = self._time.minute + step
        if minute < 0:
            minute = 59
        elif minute > 59:
            minute = 0

        self._time = datetime.time(self._time.hour, minute, self._time.second, self._time.microsecond)
        self._update_minute()

    def _on_half_day_spin(self, step):
        hour = self._time.hour
        if hour < 12:
            hour += 12
            self._half_day.text = "PM"
        else:
            hour -= 12
            self._half_day.text = "AM"

        self._time = datetime.time(hour, self._time.minute, self._time.second, self._time.microsecond)

    @property
    def hour(self):
        return self._time.hour

    @property
    def minute(self):
        return self._time.minute

    @property
    def time(self):
        return self._time

    def set_time(self, tm):
        self._time = tm
        self._update_hour()
        self._update_minute()

    def on_update(self, dt):
        self._hour_spin.on_update(dt)
        self._minute_spin.on_update(dt)
        return True

    def set_ui_style(self, style):
        self._style = style
        Number.set_ui_style(style)
        self._update_hour(True)
        self._update_minute(True)
