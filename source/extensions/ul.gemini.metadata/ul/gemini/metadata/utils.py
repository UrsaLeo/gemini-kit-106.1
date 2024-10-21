from pxr import Usd
from pxr import Gf
import math
import omni.ui as ui
from omni.ui import color as cl


def screen_to_world(camera, screen_pos, viewport_width, viewport_height):
    """Calculates upper right corner position for a widget"""

    camera_transform = camera.ComputeLocalToWorldTransform(Usd.TimeCode.Default())

    fov_horiz = camera.GetHorizontalApertureAttr().Get()  # Horizontal aperture (in mm)
    focal_length = camera.GetFocalLengthAttr().Get()  # Focal length (in mm)
    aspect_ratio = viewport_width / viewport_height

    # Convert FOV from mm to radians
    fov_horiz_radians = 2 * math.atan(fov_horiz / (2 * focal_length))
    fov_vert_radians = fov_horiz_radians / aspect_ratio

    # Convert screen space coordinates to normalized device coordinates (-1 to 1)
    ndc_x = (screen_pos[0] / viewport_width) * 2 - 1
    ndc_y = 1 - (screen_pos[1] / viewport_height) * 2

    # Calculate the world space direction for this screen point
    direction = Gf.Vec3d(
        ndc_x * math.tan(fov_horiz_radians / 2),
        ndc_y * math.tan(fov_vert_radians / 2),
        -1.0  # Camera looks down -Z axis in its local space
    )
    direction.Normalize()

    # Transform the direction by the camera's world space orientation
    world_direction = camera_transform.TransformDir(direction)

    camera_pos = camera_transform.ExtractTranslation()

    # Project the point along the direction vector from the camera position
    distance = 2000
    world_pos = camera_pos + world_direction * distance

    return world_pos


def show_window_contents(names, values, prim_path):
    """Displays content for ui.Window with metadata"""

    with ui.ZStack():
        ui.Rectangle(
            style={
                "background_color": cl.black,
                "margin": 3,
            }
        )
        with ui.VStack(style={"font_size": 14, "margin": 5}):
            with ui.HStack():
                with ui.VStack():
                    with ui.HStack():
                        ui.Label(
                            "Prim Metadata:",
                            style={
                                "color": cl(1.0, 1.0, 1.0, 0.7), "font_size": 16, "font_style": "light"
                            },
                            alignment=ui.Alignment.LEFT
                        )
                        ui.Label(
                            f"{prim_path.split('/')[-1]}",
                            style={"color": cl.white, "font_size": 16, "font_style": "light"},
                            alignment=ui.Alignment.RIGHT
                        )
                    ui.Spacer(height=10)
                    for name, value in zip(names, values):
                        with ui.HStack():
                            ui.Label(
                                f"{name}:",
                                style={"color": cl(1.0, 1.0, 1.0, 0.7), "font_size": 16, "font_style": "light"},
                                alignment=ui.Alignment.LEFT
                            )

                            ui.Label(
                                value,
                                style={"color": cl.white, "font_size": 16, "font_style": "light"},
                                alignment=ui.Alignment.RIGHT
                            )
