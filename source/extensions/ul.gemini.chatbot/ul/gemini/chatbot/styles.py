import omni.ui as ui
from omni.ui import color as cl


font_size = 16

bot_background=ui.color(0,0,0,255)

response_style_welcome = {
                        "Label": {
                            "font_size": font_size,
                            "color": "white",
                            "alignment": ui.Alignment.LEFT,
                            "margin":5
                        }
                }
bot_bubble_style_welcome = {
                    "background_color":bot_background,
                    "alignment": ui.Alignment.LEFT,
                    "padding":15
                }

send_button_style = {
    "Button": {
        "alignment": ui.Alignment.RIGHT_TOP,
        "background_color": cl("#252525"),
    },
    "Button.Image": {
        "image_width":ui.Percent(100),
        "fill_policy":ui.FillPolicy.PRESERVE_ASPECT_FIT, # Adjust as needed
        "alignment" :ui.Alignment.RIGHT_TOP,

    }
}