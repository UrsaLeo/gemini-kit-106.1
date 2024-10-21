## Copyright (c) 2022, NVIDIA CORPORATION.  All rights reserved.
##
## NVIDIA CORPORATION and its licensors retain all intellectual property
## and proprietary rights in and to this software, related documentation
## and any modifications thereto.  Any use, reproduction, disclosure or
## distribution of this software and related documentation without an express
## license agreement from NVIDIA CORPORATION is strictly prohibited.
##
"""
Viewport context menu implementation with own styling
"""

__all__ = ['ViewportMenu']

import omni.kit
import omni.usd
import carb
import omni.kit.usd.layers as layers

from .context_menu import get_instance
from .style import MENU_STYLE
from omni.kit.widget.context_menu import DefaultMenuDelegate
from pxr import Usd, UsdShade, Sdf, Gf
from typing import Sequence
from omni import ui


class ViewportMenu:
    """
    Viewport context menu implementation with own styling
    """
    class MenuDelegate(DefaultMenuDelegate):
        TEXT_SIZE = 14
        ICON_SIZE = 14
        MARGIN_SIZE = [3, 3]

        def get_style(self):
            vp_style = MENU_STYLE.copy()
            vp_style["Label::Enabled"] = {"margin_width": self.MARGIN_SIZE[0],"margin_height": self.MARGIN_SIZE[1],"color": self.COLOR_LABEL_ENABLED}
            vp_style["Label::Disabled"] = {"margin_width": self.MARGIN_SIZE[0], "margin_height": self.MARGIN_SIZE[1], "color": self.COLOR_LABEL_DISABLED}
            return vp_style


    menu_delegate = MenuDelegate()

    @staticmethod
    def is_on_clipboard(objects, name):
        clipboard = objects["clipboard"]
        if not name in clipboard:
            return False
        return clipboard[name] != None

    @staticmethod
    def is_prim_on_clipboard(objects):
        return ViewportMenu.is_on_clipboard(objects, "prim_paths")

    @staticmethod
    async def can_show_clear_clipboard(objects, menu_item):
        return False

    @staticmethod
    def is_material_bindable(objects): # pragma: no cover
        if not "prim_list" in objects:
            return False
        for prim in objects["prim_list"]:
            if not omni.usd.is_prim_material_supported(prim):
                return False
        return True

    # ---------------------------------------------- menu onClick functions ----------------------------------------------

    @staticmethod
    def bind_material_to_prim_dialog(objects):
        import omni.kit.material.library

        if not "prim_list" in objects:
            return
        omni.kit.material.library.bind_material_to_prims_dialog(objects["stage"], objects["prim_list"])

    @staticmethod
    def set_prim_to_pos(path, new_pos):
        usd_context = omni.usd.get_context()
        stage = usd_context.get_stage()
        if stage:
            prim = stage.GetPrimAtPath(path)
            attr_position, attr_rotation, attr_scale, attr_order = omni.usd.TransformHelper().get_transform_attr(
                prim.GetAttributes()
            )
            if attr_position:
                if attr_position.GetName() == "xformOp:translate":
                    attr_position.Set(Gf.Vec3d(new_pos[0], new_pos[1], new_pos[2]))
                elif attr_position.GetName() == "xformOp:transform":
                    value = attr_position.Get()
                    if isinstance(value, Gf.Matrix4d):
                        matrix = value
                    else:
                        matrix = Gf.Matrix4d(*value)

                    eps_unused, scale_orient_mat_unused, abs_scale, rot_mat, abs_position, persp_mat_unused = (
                        matrix.Factor()
                    )
                    rot_mat.Orthonormalize(False)
                    abs_rotation = Gf.Rotation.DecomposeRotation3(
                        rot_mat, Gf.Vec3d.XAxis(), Gf.Vec3d.YAxis(), Gf.Vec3d.ZAxis(), 1.0
                    )
                    abs_rotation = [
                        Gf.RadiansToDegrees(abs_rotation[0]),
                        Gf.RadiansToDegrees(abs_rotation[1]),
                        Gf.RadiansToDegrees(abs_rotation[2]),
                    ]

                    # split matrix into rotation and translation/scale
                    matrix_pos = Gf.Matrix4d().SetIdentity()
                    matrix_rot = Gf.Matrix4d().SetIdentity()
                    matrix_pos.SetScale(abs_scale)
                    matrix_pos.SetTranslateOnly(Gf.Vec3d(new_pos[0], new_pos[1], new_pos[2]))
                    matrix_rot.SetRotate(
                        Gf.Rotation(Gf.Vec3d.XAxis(), abs_rotation[0])
                        * Gf.Rotation(Gf.Vec3d.YAxis(), abs_rotation[1])
                        * Gf.Rotation(Gf.Vec3d.ZAxis(), abs_rotation[2])
                    )

                    # build final matrix
                    attr_position.Set(matrix_rot * matrix_pos)
                else:
                    carb.log_error(f"unknown existing position type. {attr_position}")
            else:
                attr_position = prim.CreateAttribute("xformOp:translate", Sdf.ValueTypeNames.Float3, False)
                attr_position.Set(Gf.Vec3d(new_pos[0], new_pos[1], new_pos[2]))
                if attr_order:
                    attr_order = omni.usd.TransformHelper().add_to_attr_order(attr_order, attr_position.GetName())
                else:
                    attr_order = prim.CreateAttribute("xformOpOrder", Sdf.ValueTypeNames.String, False)
                    attr_order.Set(["xformOp:translate"])

    @staticmethod
    def copy_prim_to_clipboard(objects):
        objects["clipboard"]["prim_paths"] = []
        for prim in objects["prim_list"]:
            objects["clipboard"]["prim_paths"].append(prim.GetPath().pathString)

    def clear_clipboard(objects):
        if "clipboard" in objects:
            del objects["clipboard"]

    @staticmethod
    def paste_prim_from_clipboard(objects):
        clipboard = objects["clipboard"]
        set_pos = "mouse_pos" in objects and len(objects["clipboard"]["prim_paths"]) == 1
        usd_context = omni.usd.get_context()
        edit_mode = layers.get_layers(usd_context).get_edit_mode()
        is_auto_authoring = edit_mode == layers.LayerEditMode.AUTO_AUTHORING
        omni.kit.undo.begin_group()
        for prim_path in objects["clipboard"]["prim_paths"]:
            new_prim_path = omni.usd.get_stage_next_free_path(objects["stage"], prim_path, False)
            omni.kit.commands.execute(
                "CopyPrim", path_from=prim_path, path_to=new_prim_path, exclusive_select=True,
                copy_to_introducing_layer=is_auto_authoring
            )
            if set_pos:
                ViewportMenu.set_prim_to_pos(new_prim_path, objects["mouse_pos"])
        omni.kit.undo.end_group()

    @staticmethod
    def show_create_menu(objects):
        prim_list = None
        if "prim_list" in objects:
            prim_list = objects["prim_list"]

        get_instance().build_create_menu(
            objects,
            prim_list,
            omni.kit.context_menu.get_menu_dict("CREATE", "omni.kit.window.viewport"),
            delegate=ViewportMenu.menu_delegate
        )

        get_instance().build_add_menu(
            objects, prim_list, omni.kit.context_menu.get_menu_dict("ADD", "omni.kit.window.viewport")
        )

    @staticmethod
    def show_menu(usd_context_name: str, prim_path: str = None, world_pos: Sequence[float] = None, stage=None):
        return #chandika - disable context menu

        # get context menu core functionality & check its enabled
        if hasattr(omni.kit, "context_menu"):
            context_menu = get_instance()
        else:
            context_menu = None

        if context_menu is None:
            carb.log_info("context_menu is disabled!")
            return

        usd_context = omni.usd.get_context(usd_context_name)

        # get stage
        if stage is None:
            stage = usd_context.get_stage()
            if stage is None:
                carb.log_error("stage not avaliable")
                return None

        # setup objects, this is passed to all functions
        objects = {}
        objects["stage"] = stage
        objects["usd_context_name"] = usd_context_name
        prim_list = []

        paths = usd_context.get_selection().get_selected_prim_paths()
        if len(paths) > 0:
            for path in paths:
                prim = stage.GetPrimAtPath(path)
                if prim:
                    prim_list.append(prim)
        elif prim_path:
            prim = stage.GetPrimAtPath(prim_path)
            if prim:
                prim_list.append(prim)

        if prim_list:
            objects["prim_list"] = prim_list

        if world_pos is not None:
            # Legacy name 'mouse_pos'
            objects["mouse_pos"] = world_pos
            # But it's actually the world-space position
            objects["world_position"] = world_pos

        # setup menu
        menu_dict = [
            {"populate_fn": lambda o, d=ViewportMenu.menu_delegate: context_menu.show_selected_prims_names(o, d)},
            {"populate_fn": ViewportMenu.show_create_menu},
            {
                "name": "Find in Content Browser",
                "glyph": "menu_search.svg",
                "show_fn": [
                    context_menu.is_one_prim_selected,
                    context_menu.can_show_find_in_browser,
                ],
                "onclick_fn": context_menu.find_in_browser,
            },
            {"name": ""},
            {
                "name": "Group Selected",
                "glyph": "group_selected.svg",
                "show_fn": context_menu.is_prim_selected,
                "onclick_fn": context_menu.group_selected_prims,
            },
            {
                "name": "Ungroup Selected",
                "glyph": "group_selected.svg",
                "show_fn": [
                    context_menu.is_prim_selected,
                    context_menu.is_prim_in_group,
                ],
                "onclick_fn": context_menu.ungroup_selected_prims,
            },
            {
                "name": "Duplicate",
                "glyph": "menu_duplicate.svg",
                "show_fn": context_menu.can_be_copied,
                "onclick_fn": context_menu.duplicate_prim,
            },
            {
                "name": "Delete",
                "glyph": "menu_delete.svg",
                "show_fn": context_menu.can_delete,
                "onclick_fn": context_menu.delete_prim,
            },
            {"name": ""},
            {
                "name": "Copy",
                "glyph": "menu_duplicate.svg",
                "show_fn": context_menu.can_be_copied,
                "onclick_fn": ViewportMenu.copy_prim_to_clipboard,
            },
            {
                "name": "Paste Here",
                "glyph": "menu_paste.svg",
                "show_fn": ViewportMenu.is_prim_on_clipboard,
                "onclick_fn": ViewportMenu.paste_prim_from_clipboard,
            },
            # this will not be shown, used by tests to cleanup clipboard
            {
                "name": "Clear Clipboard",
                "glyph": "menu_duplicate.svg",
                "show_fn_async": ViewportMenu.can_show_clear_clipboard,
                "onclick_fn": ViewportMenu.clear_clipboard,
            },
            {"name": ""},
            {
                "name": "Refresh Reference",
                "glyph": "sync.svg",
                "name_fn": context_menu.refresh_reference_payload_name,
                "show_fn": [context_menu.is_prim_selected, context_menu.has_payload_or_reference],
                "onclick_fn": context_menu.refresh_payload_or_reference,
            },
            {"name": ""},
            {
                "name": "Select Bound Objects",
                "glyph": "menu_search.svg",
                "show_fn": context_menu.is_material,
                "onclick_fn": context_menu.select_prims_using_material,
            },
            {
                "name": "Assign Material",
                "glyph": "menu_material.svg",
                "show_fn_async": context_menu.can_assign_material_async,
                "onclick_fn": ViewportMenu.bind_material_to_prim_dialog,
            },
            {"name": "", "show_fn_async": context_menu.can_assign_material_async},
            {
                "name": "Copy URL Link",
                "glyph": "menu_link.svg",
                "show_fn": [
                    context_menu.is_prim_selected,
                    context_menu.is_one_prim_selected,
                    context_menu.can_show_find_in_browser,
                ],
                "onclick_fn": context_menu.copy_prim_url,
            },
            {
                "name": "Copy Prim Path",
                "glyph": "menu_link.svg",
                "show_fn": [
                    context_menu.is_prim_selected,
                    context_menu.is_one_prim_selected,
                    context_menu.can_show_find_in_browser,
                ],
                "onclick_fn": context_menu.copy_prim_path,
            },
        ]

        menu_dict += omni.kit.context_menu.get_menu_dict("MENU", "")
        menu_dict += omni.kit.context_menu.get_menu_dict("MENU", "omni.kit.window.viewport")
        omni.kit.context_menu.reorder_menu_dict(menu_dict)

        # show menu
        context_menu.show_context_menu("viewport", objects, menu_dict, delegate=ViewportMenu.menu_delegate)
