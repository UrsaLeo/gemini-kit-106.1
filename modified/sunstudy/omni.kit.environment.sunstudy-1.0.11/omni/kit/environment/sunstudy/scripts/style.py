
from .utils import get_nominal_font_size


class SunstudyColors:
    Transparent = 0x0000000
    Disabled = 0xFF50504E
    Background = 0xFF23211F
    Text = 0xFFB7B2AF
    Slider = 0xFF555555
    Title = 0xFF23211F
    TitleHovered = 0xFF2B2927
    Panel = 0x30000000
    Border = Title
    BorderHovered = 0xFF33312F

    ButtonHovered = 0xFF33312F
    ButtonPressed = 0xFF33312F


SLIDER_STYLE = {
    "Rectangle::drag": {"background_color": SunstudyColors.Background, "border_width": 0, "border_radius": 2},
    "Label::drag": {"color": SunstudyColors.Text},
    "Triangle::drag": {"background_color": SunstudyColors.Text},
    "Circle::cursor": {"background_color": SunstudyColors.Text},
    "Seperator": {"color": SunstudyColors.Text},
    "Rectangle::start": {"background_color": SunstudyColors.Background},
    "Rectangle::end": {"background_color": SunstudyColors.Slider},
}


class PanelStyle:
    @staticmethod
    def get() -> dict:
        result = {
            "Rectangle::blank": {
                "background_color": SunstudyColors.Transparent,
                "border_width": 0,
            },

            "Label::title": {"font_size": 12},
            "Rectangle::title": {"background_color": SunstudyColors.Title, "border_width": 1, "border_color": SunstudyColors.Border},
            "Rectangle::title:selected": {"background_color": SunstudyColors.TitleHovered, "border_color": SunstudyColors.BorderHovered},

            "Rectangle::panel": {
                "background_color": SunstudyColors.Panel,
                "border_width": 1,
                "border_color": SunstudyColors.Border
            },
            "Rectangle::panel:hovered": {
                "background_color": SunstudyColors.Panel,
                "border_width": 1,
                "border_color": SunstudyColors.BorderHovered
            },
            "Rectangle::panel:pressed": {
                "background_color": SunstudyColors.Panel,
                "border_width": 1,
                "border_color": SunstudyColors.BorderHovered
            },
            "Label::time": {"font_size": get_nominal_font_size(16)},
            "Rectangle::button": {"background_color": SunstudyColors.Transparent, "border_radius": 2.0, "border_width": 0},
            "Rectangle::button:hovered": {"background_color": SunstudyColors.ButtonHovered},
            "Rectangle::button:pressed": {"background_color": SunstudyColors.ButtonHovered},
            "Rectangle:selected": {"background_color": SunstudyColors.Background},
            "Rectangle::round_button": {
                "background_color": SunstudyColors.Transparent,
                "border_radius": 10.0,
                "border_width": 0,
            },
            "Rectangle::round_button:hovered": {"background_color": SunstudyColors.ButtonHovered},
            "Rectangle::round_button:pressed": {"background_color": SunstudyColors.ButtonHovered},
        }

        return result