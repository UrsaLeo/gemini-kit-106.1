import carb


def get_nominal_font_size(real_size):
    settings = carb.settings.get_settings()
    app_font_size = 14.0
    app_font_size_str = settings.get("/app/font/size")
    if app_font_size_str is not None:
        app_font_size = float(app_font_size_str)
    nominal_size = round(14.0 * real_size / app_font_size)
    # print(f"Font size change: {real_size} => {nominal_size}, at {app_font_size}")
    return nominal_size
