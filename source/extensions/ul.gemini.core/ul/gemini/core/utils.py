import omni.kit.commands
from omni.kit.viewport.utility import get_active_viewport, frame_viewport_selection
from omni.kit.notification_manager import post_notification, NotificationStatus
import omni.usd

from pxr import Gf, Usd, UsdGeom
from omni.kit.viewport.utility import get_active_viewport


def get_local_transform_xform(prim: Usd.Prim) -> tuple[Gf.Vec3d, Gf.Rotation, Gf.Vec3d]:
    """
    Get the local transformation of a prim using Xformable.
    See https://openusd.org/release/api/class_usd_geom_xformable.html
    Args:
        prim: The prim to calculate the local transformation.
    Returns:
        A tuple of:
        - Translation vector.
        - Rotation quaternion, i.e. 3d vector plus angle.
        - Scale vector.
    """
    xform = UsdGeom.Xformable(prim)
    local_transformation: Gf.Matrix4d = xform.GetLocalTransformation()
    translation: Gf.Vec3d = local_transformation.ExtractTranslation()
    rotation: Gf.Rotation = local_transformation.ExtractRotation()
    scale: Gf.Vec3d = Gf.Vec3d(*(v.GetLength() for v in local_transformation.ExtractRotationMatrix()))
    return translation, rotation, scale


def zoom_camera():
    viewport = get_active_viewport()
    ctx = omni.usd.get_context()

    selected_prims = ctx.get_selection().get_selected_prim_paths()

    if len(selected_prims) == 1:
        ctx.get_selection().set_selected_prim_paths([selected_prims[0]], True)
        frame_viewport_selection(viewport)
    else:
        post_notification(
            "Please select only one prim to zoom to",
            duration=2,
            status=NotificationStatus.WARNING,
        )
