# Copyright (c) 2018-2020, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#
__all__ = ["StageWidgetExtension"]


from typing import Any

import omni.ext

from .stage_column_delegate_registry import StageColumnDelegateRegistry
from .delegates import *
from .drag_and_drop_registry import DragAndDropRegistry
from .stage_actions import *
from .export_utils import _get_stage_open_sub
from .stage_item import StageItem
from .stage_style import Styles as StageStyles

class StageWidgetExtension(omni.ext.IExt):
    """The entry point for Stage Widget."""

    def on_startup(self, ext_id):
        """
        Startup handler for the stage widget extension.

        Args:
            ext_id (str): The extension id.
        """
        # Register column delegates
        self._name_column_sub = StageColumnDelegateRegistry().register_column_delegate("Name", NameColumnDelegate)
        #self._type_column_sub = StageColumnDelegateRegistry().register_column_delegate("Type", TypeColumnDelegate)
        self._visibility_column_sub = StageColumnDelegateRegistry().register_column_delegate("Visibility", VisibilityColumnDelegate)
        self._ext_name = omni.ext.get_extension_name(ext_id)
        StageStyles.on_startup()
        self._action_manager = ActionManager()
        self._action_manager.on_startup()
        self._stage_open_sub = _get_stage_open_sub()

        # TODO: these special cases -- env::, SimReady:: -- should be registered by their respective extensions,
        # omni.kit.window.environment and omni.simready.explorer.
        def simready_filter(source: Any) -> bool:
            return isinstance(source, str) and source.startswith("SimReady::")

        def simready_handler(source: Any, target_item: Any) -> None:
            # Drop from SimReady explorer
            action_registry = omni.kit.actions.core.get_action_registry()
            action = action_registry.get_action("omni.simready.explorer", "add_asset_from_drag")
            if action:
                if isinstance(target_item, StageItem):
                    if not target_item:
                        target_item = stage_model.root
                    path_to = target_item.path
                else:
                    path_to = None
                action.execute(source, path_to=path_to)
                return

        def env_filter(source: Any) -> bool:
            return isinstance(source, str) and source.startswith("env::")

        def env_handler(source: Any, target_item: Any) -> None:
            # Drop from environment window
            action_registry = omni.kit.actions.core.get_action_registry()
            action = action_registry.get_action("omni.kit.window.environment", "drop")
            if action:
                action.execute(source)
                return

        DragAndDropRegistry().register_drop_handler("simready", simready_filter, simready_handler)
        DragAndDropRegistry().register_drop_handler("env", env_filter, env_handler)

    def on_shutdown(self):
        """Shutdown handler for the stage widget extension."""
        DragAndDropRegistry().deregister_drop_handler("env")
        DragAndDropRegistry().deregister_drop_handler("simready")
        self._name_column_sub = None
        self._visibility_column_sub = None
        self._type_column_sub = None
        self._stage_open_sub = None
        self._action_manager.on_shutdown()
