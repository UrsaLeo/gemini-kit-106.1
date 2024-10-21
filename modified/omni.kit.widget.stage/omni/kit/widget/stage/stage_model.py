# Copyright (c) 2018-2020, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#
__all__ = ["StageModel", "StageItemSortPolicy"]

from pxr import Sdf, Tf, Trace, Usd, UsdGeom
from typing import List, Optional, Dict, Callable, Union
from omni.kit.async_engine import run_coroutine
from .event import Event, EventSubscription
from .stage_item import StageItem
from .utils import handle_exception
from .stage_drag_and_drop_handler import StageDragAndDropHandler, AssetType
from enum import Enum

import carb
import carb.dictionary
import carb.settings
import omni.activity.core
import omni.client
import omni.ui as ui
import omni.usd
import omni.kit.usd.layers as layers


EXCLUSION_TYPES_SETTING = "ext/omni.kit.widget.stage/exclusion/types"
STAGE_ROOT="/World/Twins/Building"  #chandika

class StageItemSortPolicy(Enum):
    """Sort policy for stage items."""

    DEFAULT = 0
    """The default sort policy."""

    NAME_COLUMN_NEW_TO_OLD = 1
    """Sort by name from new to old."""

    NAME_COLUMN_OLD_TO_NEW = 2
    """Sort by name from old to new."""

    NAME_COLUMN_A_TO_Z = 3
    """Sort by name from A to Z."""

    NAME_COLUMN_Z_TO_A = 4
    """Sort by name from Z to A."""

    TYPE_COLUMN_A_TO_Z = 5
    """Sort by type from A to Z."""

    TYPE_COLUMN_Z_TO_A = 6
    """Sort by type from Z to A."""

    VISIBILITY_COLUMN_INVISIBLE_TO_VISIBLE = 7
    """Sort by visibility, invisible first."""

    VISIBILITY_COLUMN_VISIBLE_TO_INVISIBLE = 8
    """Sort by visibility, visible first."""


class StageModel(ui.AbstractItemModel):
    """The item model that watches the stage."""

    def __init__(self, stage: Usd.Stage, flat=False, load_payloads=False, check_missing_references=False, **kwargs):
        """
        StageModel provides the model for TreeView of Stage Widget, which also manages all StageItems.

        Args:
            stage (Usd.Stage): USD stage handle.

        Keyword Args:
            flat (bool): If True, all StageItems will be children of the root node. This option only applies to
                filtering mode.
            load_payloads (bool): Whether payloads should be loaded automatically during stage traversal.
            check_missing_references (bool): Deprecated.
            children_reorder_supported (bool): Whether to enable children reordering for drag and drop. False by default.
            show_prim_displayname (bool): Whether to show prim's displayName from metadata or path name. False by default.
            show_undefined_prims (bool): Whether to show prims that have no def. False by default.
        """

        super().__init__()

        self.__flat_search = flat
        self.load_payloads = load_payloads

        # Stage item cache for quick access
        self.__stage_item_cache: Dict[Sdf.Path, StageItem] = {}

        self.__stage_item_builder = kwargs.get("stage_item_builder", StageItem)

        self.__stage = stage
        if self.__stage:
            # Internal access that can be overrided.
            self._root = self.__stage_item_builder(self._get_path_converter().absoluteRootPath, self.stage, self)
            default_prim = self.__stage.GetDefaultPrim()
            if default_prim:
                self.__default_prim_name = default_prim.GetName()
            else:
                self.__default_prim_name = ""
        else:
            self.__default_prim_name = ""
            self._root = None

        # Stage watching
        if self.__stage:
            self.__stage_listener = Tf.Notice.Register(Usd.Notice.ObjectsChanged, self._on_objects_changed, self.__stage)
            self.__layer_listener = Tf.Notice.Register(
                Sdf.Notice.LayerInfoDidChange, self._on_layer_info_change, self.__stage.GetRootLayer()
            )
        else:
            self.__stage_listener = None
            self.__layer_listener = None

        # Delayed paths to be refreshed.
        self.__dirty_prim_paths = set()
        self.__prim_changed_task_or_future = None

        # The string that the shown objects should have.
        self.__filter_name_text = None
        # The dict of form {"type_name_string", lambda prim: True}. When lambda is True, the prim will be shown.
        self.__filters = {}

        self.__stage_item_value_model_count = 1

        # Exclusion list allows to hide prims of specific types silently
        settings = carb.settings.get_settings()
        self.__exclusion_types: Optional[List[str]] = settings.get(EXCLUSION_TYPES_SETTING)
        self.__setting_sub = omni.kit.app.SettingChangeSubscription(
            EXCLUSION_TYPES_SETTING, self.__on_exclusion_types_changed
        )

        self.layers_state_interface = None
        self.__usd_context = None
        self.__stage_event_subscription = None
        self.__layers_event_subs = []

        # It's possible that stage is not attached to any context.
        if self.__stage:
            self.__usd_context = omni.usd.get_context_from_stage(self.__stage)

            detect_outdate_state_changes = kwargs.get("detect_outdate_state_changes", True)

            if self.__usd_context and detect_outdate_state_changes:
                layers_interface = layers.get_layers(self.__usd_context)
                self.layers_state_interface = layers_interface.get_layers_state()

                for event in [
                    layers.LayerEventType.OUTDATE_STATE_CHANGED, layers.LayerEventType.AUTO_RELOAD_LAYERS_CHANGED
                ]:
                    layers_event_sub = layers_interface.get_event_stream().create_subscription_to_pop_by_type(
                        event, self.__on_layer_event, name=f"omni.kit.widget.stage {str(event)}"
                    )
                    self.__layers_event_subs.append(layers_event_sub)

                self.__stage_event_subscription = self.__usd_context.get_stage_event_stream().create_subscription_to_pop(
                    self.__on_stage_event, name="omni.kit.widget.stage listener"
                )

        # Notifies when stage items are destroyed.
        self.__on_stage_items_destroyed = Event()

        self.__drag_and_drop_handler = kwargs.get(
            "drag_and_drop_handler", StageDragAndDropHandler(self)
        )
        self.__drag_and_drop_handler.children_reorder_supported = kwargs.get("children_reorder_supported", False)

        # If it's in progress of renaming prim.
        self.__renaming_prim = False

        self.__show_prim_displayname = kwargs.get("show_prim_displayname", False)

        self.__show_undefined_prims = kwargs.get("show_undefined_prims", False)

        # The sorting strategy to use. Only builtin columns (name, type, and visibility) support to
        # change the sorting policy directly through StageModel.
        self.__items_builtin_sort_policy = StageItemSortPolicy.DEFAULT
        self.__settings_builtin_sort_policy = False
        self.__items_sort_func = None
        self.__items_sort_reversed = False

        # Notifies when stage items are selected. This event is unlike the one
        # released from event stream of UsdContext.
        self.__on_stage_items_selection_changed = Event()

        self.__selected_items = set()
        self.__set_usd_selection = False

    def __on_stage_event(self, event: carb.events.IEvent):
        if self.__set_usd_selection:
            self.__set_usd_selection = False
            return

        if event.type == int(omni.usd.StageEventType.SELECTION_CHANGED):
            self.__on_selection_changed()

    def __on_selection_changed(self):
        selection_paths = self.__usd_context.get_selection().get_selected_prim_paths()
        selected_items = set()
        for path in selection_paths:
            stage_item = self._get_stage_item_from_cache(path, True)
            if stage_item:
                selected_items.add(stage_item)

        if selected_items != self.__selected_items:
            self.__set_selected_stage_items(selected_items)

    def __on_layer_event(self, event):
        payload = layers.get_layer_event_payload(event)
        if (
            payload.event_type != layers.LayerEventType.OUTDATE_STATE_CHANGED and
            payload.event_type != layers.LayerEventType.AUTO_RELOAD_LAYERS_CHANGED
        ):
            return

        all_stage_items = self._get_all_stage_items_from_cache()
        to_refresh_items = [item for item in all_stage_items if item.payrefs]

        # Notify all items to refresh its live and outdate status
        self._refresh_stage_items(to_refresh_items, [])

    def _clear_stage_item_cache(self):
        if self.__stage_item_cache:
            all_items = list(self.__stage_item_cache.items())
            if all_items:
                self._refresh_stage_items([], destroyed_items=all_items)
                for _, item in self.__stage_item_cache.items():
                    item.destroy()
            self.__stage_item_cache = {}

    def _cache_stage_item(self, item: StageItem):
        if item == self._root:
            return

        if item.path not in self.__stage_item_cache:
            self.__stage_item_cache[item.path] = item

    def _get_stage_item_from_cache(self, path: Sdf.Path, create_if_not_existed=False):
        """Gets or creates stage item."""
        if not self.stage:
            return None

        path = self._get_path_converter()(path)
        if path == self._get_path_converter().absoluteRootPath:
            return self._root

        stage_item = self.__stage_item_cache.get(path, None)
        if not stage_item and create_if_not_existed:
            prim = self.stage.GetPrimAtPath(path)
            if self._should_prim_be_excluded_from_tree_view(prim):
                return None

            stage_item = self.__stage_item_builder(path, self.stage, self)
            self._cache_stage_item(stage_item)

        return stage_item

    def _get_all_stage_items_from_cache(self):
        return list(self.__stage_item_cache.values())

    @Trace.TraceFunction
    def _get_stage_item_children(self, path: Sdf.Path):
        """
        Gets all children stage items of path. If those stage items are not
        created, they will be created. This optimization is used to implement
        lazy loading that only paths that are accessed will create corresponding
        stage items.
        """

        if path == self._get_path_converter().absoluteRootPath:
            stage_item = self._root
        else:
            stage_item = self.__stage_item_cache.get(path, None)

        if not stage_item or not stage_item.prim:
            return []

        prim = stage_item.prim
        if self.load_payloads and not prim.IsLoaded():
            # Lazy load payloads
            prim.Load(Usd.LoadWithoutDescendants)

        # This appears to be working fastly after testing with 10k nodes under a single parent.
        # It does not need to cache all the prent-children relationship to save memory.
        children = []
        display_predicate = Usd.TraverseInstanceProxies(Usd.PrimAllPrimsPredicate)
        children_iterator = prim.GetFilteredChildren(display_predicate)
        for child_prim in children_iterator:
            if (self._should_prim_be_excluded_from_tree_view(child_prim, True)):   #chandika
                continue
            child_path = child_prim.GetPath()
            child = self._get_stage_item_from_cache(child_path, True)
            if child:
                children.append(child)

        return children

    def _remove_stage_item_from_cache(self, prim_path: Sdf.Path):
        item = self.__stage_item_cache.pop(prim_path, None)
        if item:
            item.destroy()

            return True

        return False

    def _pop_stage_item_from_cache(self, prim_path: Sdf.Path):
        return self.__stage_item_cache.pop(prim_path, None)


    #def _should_prim_be_excluded_from_tree_view(self, prim):
    #    if (
    #        not prim or prim.GetMetadata("hide_in_stage_window") or
    #        (self.__exclusion_types and prim.GetTypeName() in self.__exclusion_types) or
    #        (not self.__show_undefined_prims and not prim.IsDefined())
    #    ):
    #        return True
    #
     #   return False

    #chandika

    def _should_prim_be_excluded_from_tree_view(self, prim, filter_stage_root=False):
        if (str(prim.GetPath()).strip() in  ["/World", "/World/Twins", "/World/Twins/Building", "/World/Twins/Building/Geometry","/World/Twins/Building/Geometry/Arch_CannonDesign"]) :
            return False
        if (
            not prim or prim.GetMetadata("hide_in_stage_window") or
            (self.__exclusion_types and prim.GetTypeName() in self.__exclusion_types) or
            (not self.__show_undefined_prims and not prim.IsDefined()) or
            (filter_stage_root and prim.GetTypeName() != "Xform")
            # (filter_stage_root and prim.GetTypeName() not in ["Xform", "Scope"]) or


        ):
            return True

        #if str(prim.GetPath()).strip() == "/World":
        #    return False

        #either the prim path has to be part of our root path or a child of it
        prim_path = str(prim.GetPath()).strip()
        if (filter_stage_root and (not STAGE_ROOT.startswith(prim_path) and
            not prim_path.startswith(STAGE_ROOT))):
            return True


        #either the prim path has to be part of our root path or a child of it
        prim_path = str(prim.GetPath()).strip()
        if (filter_stage_root and (not STAGE_ROOT.startswith(prim_path) and
            not prim_path.startswith(STAGE_ROOT))):
            return True

        return False

    @staticmethod
    def _get_path_converter() -> Callable:
        """
        The Path conversion function to use for prim paths.

        Returns:
            Callable: The path conversion function.
        """
        return Sdf.Path

    @property
    def usd_context(self) -> omni.usd.UsdContext:
        """
        Gets the usd context for the model.

        Returns:
            omni.usd.UsdContext: The underlying usd context for the model.
        """
        return self.__usd_context

    @property
    def stage(self) -> Usd.Stage:
        """
        Gets the stage for the model.

        Returns:
            Usd.Stage: The underlying usd stage for the model.
        """
        return self.__stage

    @property
    def root(self) -> StageItem:
        """
        Gets the item that represents the absolute root.

        Returns:
            StageItem: The root item.
        """
        return self._root

    @property
    def exclusion_types(self) -> Optional[List[str]]:
        """
        Gets the exclusion types.

        Returns:
            Optional[List[str]]: The exclusion types if set, else None.
        """
        return self.__exclusion_types

    @property
    def flat(self) -> bool:
        """
        Whether the model is in flat mode or not.
        When in flat mode, all items will be the children of the root item, and empty children for other items.

        It will return False when show_prim_displayname is True, or when model has not filter text, even if this
        property is set to True. That means flat mode is currently used for searching only and show_prim_displayname is
        False.
        """
        return self.__flat_search and self._has_filters() and not self.show_prim_displayname

    @flat.setter
    def flat(self, value):
        """
        Sets search mode.

        Args:
            value (bool): Value to set.
        """

        if self.__flat_search != value:
            self.__flat_search = value
            if not self.show_prim_displayname:
                for item in self.__stage_item_cache.values():
                    item.is_flat = value

    def find(self, path: Sdf.Path) -> StageItem:
        """
        Finds the item with the given path if it's populated already.

        Args:
            path (Sdf.Path): Path to find item of.

        Returns:
            StageItem: The found item
        """

        path = self._get_path_converter()(path)
        if path == self._get_path_converter().absoluteRootPath:
            return self._root

        return self._get_stage_item_from_cache(path)

    @Trace.TraceFunction
    def find_full_chain(self, path: Optional[Union[Sdf.Path, str]]) -> Optional[List[StageItem]]:
        """
        Returns the list of all the parent nodes and the node representing the given path.
        If path is empty or there's no root item, returns None.

        Args:
            path (Optional[Union[Sdf.Path, str]]): Path to find item of.
        Returns:
            List[StageItem]: Found items.
        """
        if not self._root:
            return None

        if not path:
            return None

        if isinstance(path, str) and path[-1] == "/":
            path = path[:-1]

        path = self._get_path_converter()(path)
        if path == self._get_path_converter().absoluteRootPath:
            return None

        result = [self._root]

        # Finds the full chain and creates stage item on demand to avoid expanding whole tree.
        prefixes = path.GetPrefixes()
        for child_path in prefixes:
            child_item = self._get_stage_item_from_cache(child_path, True)
            if child_item:
                result.append(child_item)
            else:
                break

        return result

    @Trace.TraceFunction
    def update_dirty(self):
        """
        Create/remove dirty items that was collected from TfNotice. Can be called at any time to pump changes.
        """
        if not self.__dirty_prim_paths:
            return

        stage_update_activity = "Stage|Update|Stage Widget Model"
        omni.activity.core.began(stage_update_activity)

        dirty_prim_paths = list(self.__dirty_prim_paths)
        self.__dirty_prim_paths = set()

        # Updates the common root as refreshing subtree will filter
        # all cache items to find the old stage items. So iterating each
        # single prim path is not efficient as it needs to traverse
        # whole cache each time. Even it's possible that dirty prim paths
        # are not close to each other that results more stage traverse,
        # the time is still acceptable after testing stage over 100k prims.
        common_prefix = dirty_prim_paths[0]
        for path in dirty_prim_paths[1:]:
            common_prefix = self._get_path_converter().GetCommonPrefix(common_prefix, path)

        (
            info_changed_stage_items,
            children_refreshed_items,
            destroyed_items
        ) = self._refresh_prim_subtree(common_prefix)
        self._refresh_stage_items(
            info_changed_stage_items, children_refreshed_items, destroyed_items
        )

        omni.activity.core.ended(stage_update_activity)

    def _refresh_stage_items(
        self, info_changed_items=[], children_refreshed_items=[], destroyed_items=[]
    ):
        """
        `info_changed_items` includes only items that have flags/attributes updated.
        `children_refreshed_items` includes only items that have children updated.
        `destroyed_items` includes only items that are removed from stage.
        """

        if info_changed_items:
            for item in info_changed_items:
                item.update_flags()

                # Refresh whole item for now to maintain back-compatibility
                if self._root == item:
                    self._item_changed(None)
                else:
                    self._item_changed(item)

        if children_refreshed_items:
            if self.flat:
                self._item_changed(None)
            else:
                for stage_item in children_refreshed_items:
                    if self._root == stage_item:
                        self._item_changed(None)
                    else:
                        self._item_changed(stage_item)

        if destroyed_items:
            for item in destroyed_items:
                self.__selected_items.discard(item)

            self.__on_stage_items_destroyed(destroyed_items)

    @Trace.TraceFunction
    def _refresh_prim_subtree(self, prim_path):
        """
        Refresh prim subtree in lazy way. It will only refresh those
        stage items that are populated already to not load them beforehand
        to improve perf, except the absolute root node.
        """
        carb.log_verbose(f"Refresh prim tree rooted from {prim_path}")

        old_stage_items = []
        refreshed_stage_items = set([])
        children_updated_stage_items = set([])

        item = self._get_stage_item_from_cache(prim_path)

        # This is new item, returning and refreshing it immediately if its parent is existed.
        if not item:
            if self._has_filters():
                self._prefilter(prim_path)

            parent = self._get_stage_item_from_cache(prim_path.GetParentPath())
            if parent:
                children_updated_stage_items.add(parent)

            return refreshed_stage_items, children_updated_stage_items, []

        # If it's to refresh whole stage, it should always refresh absolute root
        # as new root prim should always be populated.
        if prim_path == self._get_path_converter().absoluteRootPath:
            children_updated_stage_items.add(self._root)
            if self._has_filters():
                # OM-84576: Filtering all as it's possible that new sublayers are inserted.
                should_update_items = self._prefilter(prim_path)
                children_updated_stage_items.update(should_update_items)
            old_stage_items = list(self.__stage_item_cache.values())
        else:
            for path, item in self.__stage_item_cache.items():
                if path.HasPrefix(prim_path):
                    old_stage_items.append(item)

            # If no cached items, and it's the root prims refresh, it should
            # alwasy populate root prims if they are not populated yet.
            if not old_stage_items:
                children_updated_stage_items.add(self._root)

        all_removed_items = []
        for stage_item in old_stage_items:
            if stage_item.path == self._get_path_converter().absoluteRootPath:
                continue

            prim = self.stage.GetPrimAtPath(stage_item.path)
            if prim:
                if prim.IsActive():
                    refreshed_stage_items.add(stage_item)
                else:
                    children_updated_stage_items.add(stage_item)
            else:
                parent = self._get_stage_item_from_cache(stage_item.path.GetParentPath())
                if parent:
                    children_updated_stage_items.add(parent)

                # Removes it from filter list.
                if self.flat and (stage_item.filtered or stage_item.child_filtered):
                    children_updated_stage_items.add(self._root)

                if self._remove_stage_item_from_cache(stage_item.path):
                    all_removed_items.append(stage_item)

        return refreshed_stage_items, children_updated_stage_items, all_removed_items

    @Trace.TraceFunction
    def _on_objects_changed(self, notice, stage):
        """Called by Usd.Notice.ObjectsChanged"""
        if not stage or stage != self.stage or self.__drag_and_drop_handler.is_reordering_prim:
            return

        if self.__renaming_prim:
            return

        dirty_prims_paths = []

        for p in notice.GetResyncedPaths():
            if p.IsAbsoluteRootOrPrimPath():
                dirty_prims_paths.append(p)

        for p in notice.GetChangedInfoOnlyPaths():
            if not p.IsAbsoluteRootOrPrimPath():
                if p.name == UsdGeom.Tokens.visibility:
                    dirty_prims_paths.append(p.GetPrimPath())

                continue

            for field in notice.GetChangedFields(p):
                if field == omni.usd.editor.HIDE_IN_STAGE_WINDOW or field == omni.usd.editor.DISPLAY_NAME:
                    dirty_prims_paths.append(p)
                    break

        if not dirty_prims_paths:
            return

        self.__dirty_prim_paths.update(dirty_prims_paths)

        # Update in the next frame. We need it because we want to accumulate the affected prims
        if self.__prim_changed_task_or_future is None or self.__prim_changed_task_or_future.done():
            self.__prim_changed_task_or_future = run_coroutine(self.__delayed_prim_changed())

    @Trace.TraceFunction
    def _on_layer_info_change(self, notice, sender):
        """Called by Sdf.Notice.LayerInfoDidChange when the metadata of the root layer is changed"""
        if not sender or notice.key() != "defaultPrim":
            return

        new_default_prim = sender.defaultPrim
        if new_default_prim == self.__default_prim_name:
            return

        # Unmark the old default
        items_refreshed = []
        if self.__default_prim_name:
            found = self.find(self._get_path_converter().absoluteRootPath.AppendChild(self.__default_prim_name))
            if found:
                items_refreshed.append(found)

        # Mark the old default
        if new_default_prim:
            found = self.find(self._get_path_converter().absoluteRootPath.AppendChild(new_default_prim))
            if found:
                items_refreshed.append(found)

        self._refresh_stage_items(items_refreshed)
        self.__default_prim_name = new_default_prim

    @handle_exception
    @Trace.TraceFunction
    async def __delayed_prim_changed(self):
        await omni.kit.app.get_app().next_update_async()

        # It's possible that stage is closed before coroutine
        # is handled.
        if not self.__stage:
            return

        # Pump the changes to the model.
        self.update_dirty()
        self.__prim_changed_task_or_future = None

    @carb.profiler.profile
    @Trace.TraceFunction
    def get_item_children(self, item: Optional[StageItem]) -> Union[List[StageItem], StageItem]:
        """
        Gets the sorted children of the given item. Returns the root item when item is None.
        If filtering is on, will return a filtered list of child items.

        Args:
            item (Optional[StageItem]): Item to find children of.
        Returns:
            Union[List[StageItem], StageItem]: The child items.
        """
        if item is None:
            item = self._root

        if not item:
            return []

        if self.flat:
            # In flat mode, all stage items will be the children of root.
            if item == self._root:
                children = self._get_all_stage_items_from_cache()
            else:
                children = []
        else:
            children = self._get_stage_item_children(item.path)

        if self._has_filters():
            children = [child for child in children if (child.filtered or child.child_filtered)]

        # Sort children
        if self.__items_sort_func:
            children.sort(key=self.__items_sort_func, reverse=self.__items_sort_reversed)
        elif self.__items_sort_reversed:
            children.reverse()

        return children

    @carb.profiler.profile
    @Trace.TraceFunction
    def can_item_have_children(self, item: Optional[StageItem]) -> bool:
        """
        Checks if the given item can have children.
        By default, if can_item_have_children is not provided, it will call get_item_children to get the count of
        children, so implementing this function to make sure we do lazy load for all items.

        Args:
            item (Optional[StageItem]): The item to check.

        Returns:
            bool: The result.
        """

        if item is None:
            item = self._root

        if not item or not item.prim:
            return False

        # Non-root item in flat mode has no children.
        if self.flat and item != self._root:
            return False

        prim = item.prim
        if self.load_payloads and not prim.IsLoaded():
            # Lazy load payloads
            prim.Load(Usd.LoadWithoutDescendants)

        display_predicate = Usd.TraverseInstanceProxies(Usd.PrimAllPrimsPredicate)
        children_iterator = prim.GetFilteredChildren(display_predicate)
        for child_prim in children_iterator:
            if self._should_prim_be_excluded_from_tree_view(child_prim, True):  #chandika
                continue

            if self._has_filters():
                child_item = self._get_stage_item_from_cache(child_prim.GetPath(), False)
                if child_item and (child_item.filtered or child_item.child_filtered):
                    return True
            else:
                return True

        return False

    def get_item_value_model_count(self, item: Optional[StageItem]) -> int:
        """
        Gets item value model count.

        Args:
            item (Optional[StageItem]): Unused.

        Returns:
            int: The item value model count.
        """
        return self.__stage_item_value_model_count

    def set_item_value_model_count(self, count: int):
        """
        Internal method to set column count.

        Args:
            count (int): Count value to set.
        """
        self.__stage_item_value_model_count = count
        self._item_changed(None)

    def drop_accepted(self, target_item, source, drop_location=-1) -> bool:
        """
        Called to highlight the target when drag and dropping.

        Args:
            target_item (StageItem): Drop target.
            source (StageItem): Drop source.
            drop_location (int): The drop location, default to -1.

        Returns:
            bool: Drop accepted.
        """
        return self.__drag_and_drop_handler.drop_accepted(target_item, source, drop_location)

    def drop(self, target_item, source, drop_location=-1):
        """
        Drop handler called when dropping something to the item.
        When drop_location is -1, it means to drop the source item on top of the target item. When drop_location is not
        -1, it means to drop the source item between items.

        Args:
            target_item (StageItem): Drop target.
            source (StageItem): Drop source.
            drop_location (int): The drop location, default to -1.
        """
        return self.__drag_and_drop_handler.drop(target_item, source, drop_location)

    def get_drag_mime_data(self, item: StageItem) -> str:
        """
        Returns MIME (Multipurpose Internet Mail Extensions) data for dropping this item elsewhere.

        Args:
            item (StageItem): The source item.

        Returns:
            str: The MIME data constructed of item paths.
        """

        # OM-107738: Supports drag and drop for multiple items to other window.
        selected_paths = self.__usd_context.get_selection().get_selected_prim_paths()
        paths = []
        for path in selected_paths:
            if not self._get_stage_item_from_cache(path):
                continue

            paths.append(path)

        if paths:
            return "\n".join(paths)

        # As we don't do Drag and Drop to the operating system, we return the string.
        return str(item.path) if item else "/"

    def _has_filters(self):
        return self.__filter_name_text or self.__filters

    def filter_by_text(self, filter_name_text):
        """
        Filter stage model items by text.
        Currently, only single word that's case-insensitive or prim path are supported.

        Args:
            filter_name_text (str): The filter text.
        """
        if not self._root:
            return

        # Specify the filter string that is used to reduce the model
        if self.__filter_name_text == filter_name_text:
            return

        self.__filter_name_text = filter_name_text.strip() if filter_name_text else None
        should_update_items = self._prefilter(self._get_path_converter().absoluteRootPath)
        self._refresh_stage_items([], should_update_items)

    def filter(self, add=None, remove=None, clear=None) -> bool:
        """
        Updates the filter type names and refreshes the stage items with the new filter types.
        In most cases we need to filter by several types, so this method allows to add, remove and set the list of types
        to filter and updates the items if necessary.

        Keyword Args:
            add (Optional[Dict]): A dictionary of this form: {"type_name_string", lambda prim: True}. When lambda is
                True, the prim will be shown.
            remove (Optional[Union[str, Dict, list, set]]): Removes filters by name if the filter name is in "remove".
            clear: Removes all existing filters. When used with `add`, it will remove existing filters first and then
                add the newly given ones.

        Returns:
            True if the model has filters. False otherwise.
        """
        if not self._root:
            return

        changed = False

        if clear:
            if self.__filters:
                self.__filters.clear()
                changed = True

        if remove:
            if isinstance(remove, str):
                remove = [remove]

            for key in remove:
                if key in self.__filters:
                    self.__filters.pop(key, None)
                    changed = True

        if add:
            self.__filters.update(add)
            changed = True

        if changed:
            should_update_items = self._prefilter(self._get_path_converter().absoluteRootPath)
            self._refresh_stage_items([], should_update_items)

        return not not self.__filters

    def get_filters(self) -> Dict:
        """
        Return dict of filters.

        Returns:
            Dict: The filters dictionary.
        """
        return self.__filters

    def reset(self):
        """Forces a full update of items."""
        if self._root:
            self._clear_stage_item_cache()
        self._item_changed(None)

    def destroy(self):
        """Destroys the instance, notifies column delegates and clear all subs and resources."""
        self.__drag_and_drop_handler = None
        # Notify column delegates to release related resources
        all_stage_items = self._get_all_stage_items_from_cache()
        self._refresh_stage_items(destroyed_items=all_stage_items)
        self.__on_stage_items_destroyed.clear()
        self.__on_stage_items_selection_changed.clear()
        self.__selected_items.clear()

        self.__stage = None
        if self._root:
            self._root.destroy()
        self._root = None
        self.__layers_event_subs = []
        self.__stage_event_subscription = None

        if self.__stage_listener:
            self.__stage_listener.Revoke()
            self.__stage_listener = None

        if self.__layer_listener:
            self.__layer_listener.Revoke()
            self.__layer_listener = None

        self.__dirty_prim_paths = set()
        if self.__prim_changed_task_or_future:
            self.__prim_changed_task_or_future.cancel()
            self.__prim_changed_task_or_future = None

        self.__setting_sub = None
        self._clear_stage_item_cache()
        self.layers_state_interface = None

        self.__items_builtin_sort_policy = StageItemSortPolicy.DEFAULT
        self.__items_sort_func = None
        self.__items_sort_reversed = False

    def _clear_filter_states(self, prim_path=None):
        should_update_items = []
        should_update_items.append(self.root)
        for stage_item in self.__stage_item_cache.values():
            if prim_path and not stage_item.path.HasPrefix(prim_path):
                continue

            if stage_item.filtered or stage_item.child_filtered:
                should_update_items.append(stage_item)
                stage_item.filtered = False
                stage_item.child_filtered = False

        return should_update_items

    def _filter_prim(self, prim: Usd.Prim):
        if not prim:
            return False

        # Don't search it as prim path if it shows displayName.
        if (
            self.__filter_name_text
            and Sdf.Path.IsValidPathString(self.__filter_name_text)
            and self._get_path_converter().IsAbsolutePath(self._get_path_converter()(self.__filter_name_text))
        ):
            filter_text_is_prim_path = True
            filter_path = self._get_path_converter()(self.__filter_name_text)
            if not prim.GetPath().HasPrefix(filter_path):
                return False

            filter_prim = self.stage.GetPrimAtPath(filter_path)
            if not filter_prim:
                return False
        else:
            filter_text_is_prim_path = False
            filter_path = self.__filter_name_text.lower() if self.__filter_name_text else ""

        # Has the search string in the name
        if filter_text_is_prim_path:
            # If it's non-flat serach, the search path should match the prim path exactly.
            filtered_with_string = self.flat or prim.GetPath() == filter_path
        else:
            if self.show_prim_displayname:
                name = omni.usd.editor.get_display_name(prim) or prim.GetName()
            else:
                name = prim.GetName()
            name = name.lower()
            filtered_with_string = filter_path in name if filter_path else True

        if not filtered_with_string:
            return False

        # Has the given type
        if self.__filters:
            filtered_with_lambda = False
            for _, fn in self.__filters.items():
                if fn(prim):
                    filtered_with_lambda = True
                    break
        else:
            filtered_with_lambda = True

        return filtered_with_lambda

    def _prefilter(self, prim_path: Sdf.Path):
        """Recursively mark items that meet the filtering rule"""
        prim_path = Sdf.Path(prim_path)
        prim = self.stage.GetPrimAtPath(prim_path)
        if not prim:
            return set()

        # Clears all filter states.
        old_filtered_items = set(self._clear_filter_states(prim_path))
        should_update_items = set()

        if self._has_filters():
            # Root should be refreshed always
            should_update_items.add(self.root)

            # and then creates stage items on demand when they are filtered to avoid
            # perf issue to create stage items for whole stage.
            display_predicate = Usd.TraverseInstanceProxies(Usd.PrimAllPrimsPredicate)
            children_iterator = iter(Usd.PrimRange(prim, display_predicate))
            for child_prim in children_iterator:
                if self._should_prim_be_excluded_from_tree_view(child_prim):
                    children_iterator.PruneChildren()
                    continue

                if self.load_payloads and not prim.IsLoaded():
                    # Lazy load payloads
                    prim.Load(Usd.LoadWithoutDescendants)

                filtered = self._filter_prim(child_prim)
                if not filtered:
                    continue

                # Optimization: only prim path that's filtered will create corresponding
                # stage item instead of whole subtree.
                child_prim_path = child_prim.GetPath()
                stage_item = self._get_stage_item_from_cache(child_prim_path, True)
                if not stage_item:
                    continue

                stage_item.filtered = True
                stage_item.child_filtered = False
                if not self.flat:
                    should_update_items.add(stage_item)
                    old_filtered_items.discard(stage_item)
                    parent_path = child_prim_path.GetParentPath()
                    # Creates all parents if they are not there and mark their children filtered.
                    while parent_path:
                        parent_item = self._get_stage_item_from_cache(parent_path, True)
                        if not parent_item or parent_item.child_filtered:
                            break

                        should_update_items.add(parent_item)
                        old_filtered_items.discard(parent_item)
                        parent_item.child_filtered = True
                        parent_path = parent_path.GetParentPath()
                else:
                    self.root.child_filtered = True

        should_update_items.update(old_filtered_items)

        return should_update_items

    def __on_exclusion_types_changed(self, item: carb.dictionary.Item, event_type: carb.settings.ChangeEventType):
        """Called when the exclusion list is changed"""
        if event_type == carb.settings.ChangeEventType.CHANGED:
            settings = carb.settings.get_settings()
            self.__exclusion_types = settings.get(EXCLUSION_TYPES_SETTING)
        elif event_type == carb.settings.ChangeEventType.DESTROYED:
            self.__exclusion_types = None
        else:
            return

        self.reset()

    @property
    def children_reorder_supported(self) -> bool:
        """
        Whether to support reorder children by drag and dropping.

        Returns:
            bool: The setting value.
        """
        return self.__drag_and_drop_handler.children_reorder_supported

    @children_reorder_supported.setter
    def children_reorder_supported(self, value: bool):
        """
        Sets whether children re-ordering should be supported.

        Args:
            enabled (bool): Value to set.
        """
        self.__drag_and_drop_handler.children_reorder_supported = value

    @property
    def show_prim_displayname(self) -> bool:
        """
        Instructs stage delegate to show prim's displayName from USD or path name.

        Returns:
            bool
        """
        return self.__show_prim_displayname

    @show_prim_displayname.setter
    def show_prim_displayname(self, value):
        """
        Sets whether to show display names for prims.

        Args:
            show (bool): Value to set.
        """
        if value != self.__show_prim_displayname:
            self.__show_prim_displayname = value

            all_stage_items = self._get_all_stage_items_from_cache()
            self._refresh_stage_items(all_stage_items)

    @property
    def show_undefined_prims(self) -> bool:
        """
        Whether to show prims that have no def.

        Returns:
            bool
        """
        return self.__show_undefined_prims

    @show_undefined_prims.setter
    def show_undefined_prims(self, value):
        """
        Sets whether to show undefined prims.

        Args:
            value (bool): Value to set.
        """
        if value != self.__show_undefined_prims:
            self.__show_undefined_prims = value

            all_stage_items = self._get_all_stage_items_from_cache()
            all_stage_items.append(self._root)
            self._refresh_stage_items(all_stage_items)

    def subscribe_stage_items_destroyed(self, fn: Callable[[List[StageItem]], None]) -> EventSubscription:
        """
        Subscribe to changes when stage items are destroyed with fn.
        Return the object that will automatically unsubscribe when destroyed.

        Args:
            fn (Callable[[List[StageItem]], None]): The event handler.
        Returns:
            EventSubscription: The subscription object.
        """
        return EventSubscription(self.__on_stage_items_destroyed, fn)

    def rename_prim(self, prim_path: Sdf.Path, new_name: str) -> bool:
        """
        Renames a prim to the new name given.

        Args:
            prim_path (Sdf.Path): The prim path to rename.
            new_name (str): The new name to rename to.

        Returns:
            bool: Whether the ranme is performed successfully.
        """
        if not self.stage or not self.stage.GetPrimAtPath(prim_path):
            return False

        stage_item = self._get_stage_item_from_cache(prim_path)

        # Move the prim to the new name
        try:
            self.__renaming_prim = True

            if self.__show_prim_displayname:
                omni.kit.commands.execute(
                    "ChangePrimDisplayName", stage=self.stage,
                    prim_path=prim_path,
                    new_display_name=new_name
                )

                if stage_item:
                    self._refresh_stage_items([stage_item])
            else:
                if not Tf.IsValidIdentifier(new_name):
                    carb.log_error(f"Cannot rename prim {prim_path} to name {new_name} as new name is invalid.")
                    return False

                if prim_path.name == new_name:
                    return True

                parent_path = prim_path.GetParentPath()
                created_path = parent_path.AppendElementString(new_name)
                if self.stage.GetPrimAtPath(created_path):
                    carb.log_error(f"Cannot rename prim {prim_path} to name {new_name} as new prim exists already.")
                    return False

                def prim_renamed(old_prim_name: Sdf.Path, new_prim_name: Sdf.Path):
                    async def select_prim(prim_path):
                        # Waits for two frames until stage item is created
                        app = omni.kit.app.get_app()
                        await app.next_update_async()
                        await app.next_update_async()

                        if self.__usd_context:
                            self.__usd_context.get_selection().set_selected_prim_paths(
                                [prim_path.pathString], True
                            )

                    run_coroutine(select_prim(new_prim_name))

                on_move_fn = prim_renamed if stage_item else None

                # OM-97047: Previously the prim will rename regardless of the result of calling MovePrims. Adding a return
                # value from the command call so we can operate post the move allows us to determine if the move encountered
                # an error during the move. If it does, we need to undo the move command executed and return. @gamato
                success, result = omni.kit.commands.execute(
                    "MovePrim",
                    path_from=prim_path,
                    path_to=created_path,
                    on_move_fn=on_move_fn,
                    destructive=False,
                    stage_or_context=self.stage
                )

                if success and not result:
                    # Need to undo the move prim command
                    omni.kit.undo.undo()
                    return False

                # If stage item exists.
                if stage_item:
                    self.__stage_item_cache.pop(stage_item.path, None)
                    # Change internal path and refresh old path.
                    stage_item._path = created_path
                    stage_item.update_flags()
                    # Cache new path
                    self._cache_stage_item(stage_item)

                    # Refreshes search list
                    if (
                        self._has_filters() and not stage_item.child_filtered and
                        stage_item.filtered and not self._filter_prim(stage_item.prim)
                    ):
                        stage_item.filtered = False
                        if self.flat:
                            self._item_changed(None)
                        else:
                            parent_path = prim_path.GetParentPath()
                            parent_item = self._get_stage_item_from_cache(parent_path)
                            if parent_item:
                                self._refresh_stage_items([], children_refreshed_items=[parent_item])
                    else:
                        self._refresh_stage_items([], children_refreshed_items=[stage_item])
        except Exception as e:
            import traceback
            carb.log_error(traceback.format_exc())
            carb.log_error(f"Failed to rename prim {prim_path}: {str(e)}")
            return False
        finally:
            self.__renaming_prim = False

        return True

    def set_items_sort_key_func(self, key_fn: Callable[[StageItem], None], reverse=False):
        """
        Sets the key function to sort item children.

        Args:
            key_fn (Callable[[StageItem], None]): The function that's used to sort children of item, which
                be passed to list.sort as key function, for example, `lambda item: item.name`. If `key_fn` is
                None and `reverse` is True, it will reverse items only. Or if `key_fn` is None and `reverse` is
                False, it will clear sort function.
            reverse (bool): By default, it's ascending order to sort with key_fn. If this flag is True,
                it will sort children in reverse order.
        """

        notify = False
        if not self.__settings_builtin_sort_policy and self.__items_builtin_sort_policy != StageItemSortPolicy.DEFAULT:
            self.__items_builtin_sort_policy = StageItemSortPolicy.DEFAULT
            if self.__items_sort_func:
                self.__items_sort_func = None
                notify = True

        if self.__items_sort_func or self.__items_sort_reversed:
            self.__items_sort_func = None
            self.__items_sort_reversed = False
            notify = True

        if key_fn or reverse:
            self.__items_sort_func = key_fn
            self.__items_sort_reversed = reverse
            notify = True

        # Refresh all items to sort their children
        if notify:
            all_stage_items = self._get_all_stage_items_from_cache()
            all_stage_items.append(self.root)
            self._refresh_stage_items([], all_stage_items)

    def set_items_sort_policy(self, items_sort_policy: StageItemSortPolicy):
        """
        This is the old way to sort builtin columns (name, type, and visibility), which can only sort one builtin column
        at a time, and it will clear all existing sort functions customized by `append_column_sort_key_func` and only
        sort column specified by `items_sort_policy`. For more advanced sorting, see function
        `append_column_sort_key_func`, which supports chaining sort for multiple columns.

        Args:
            items_sort_policy (StageItemSortPolicy): The sort policy to set.
        """

        try:
            self.__settings_builtin_sort_policy = True
            if self.__items_builtin_sort_policy != items_sort_policy:
                self.__items_builtin_sort_policy = items_sort_policy
                if self.__items_builtin_sort_policy == StageItemSortPolicy.NAME_COLUMN_NEW_TO_OLD:
                    self.set_items_sort_key_func(None, True)
                elif self.__items_builtin_sort_policy == StageItemSortPolicy.NAME_COLUMN_A_TO_Z:
                    self.set_items_sort_key_func(lambda item: (item.name_model._name_prefix, item.name_model._suffix_order), False)
                elif self.__items_builtin_sort_policy == StageItemSortPolicy.NAME_COLUMN_Z_TO_A:
                    self.set_items_sort_key_func(lambda item: (item.name_model._name_prefix, item.name_model._suffix_order), True)
                elif self.__items_builtin_sort_policy == StageItemSortPolicy.TYPE_COLUMN_A_TO_Z:
                    self.set_items_sort_key_func(lambda item: item.type_name.lower(), False)
                elif self.__items_builtin_sort_policy == StageItemSortPolicy.TYPE_COLUMN_Z_TO_A:
                    self.set_items_sort_key_func(lambda item: item.type_name.lower(), True)
                elif self.__items_builtin_sort_policy == StageItemSortPolicy.VISIBILITY_COLUMN_INVISIBLE_TO_VISIBLE:
                    self.set_items_sort_key_func(lambda item: 1 if item.visible else 0, False)
                elif self.__items_builtin_sort_policy == StageItemSortPolicy.VISIBILITY_COLUMN_VISIBLE_TO_INVISIBLE:
                    self.set_items_sort_key_func(lambda item: 0 if item.visible else 1, False)
                else:
                    self.set_items_sort_key_func(None, False)
        finally:
            self.__settings_builtin_sort_policy = False

    def get_items_sort_policy(self) -> StageItemSortPolicy:
        """
        Gets the sort policy for builtin columns.

        Returns:
            StageItemSortPolicy: The sort policy.
        """

        return self.__items_builtin_sort_policy

    def subscribe_stage_items_selection_changed(self, fn: Callable[[], None]) -> EventSubscription:
        """
        Subscribe to changes when stage items are selected or unselected.
        Return the object that will automatically unsubscribe when destroyed.

        Why StageModel manages its own selection list is because omni.kit.selection only manages those selections
        that are valid prims. Valid prims are those ones that exist in the stage and active. We also need to support
        UX for those items that are inactive to do batch operations with them. Therefore, StageModel maintains its own
        selection list that is iosolated with omni.kit.selection, and it also keeps up with the omni.kit.selection
        events if necessary.

        Args:
            fn (Callable[[], None]): The event handler to notify when selections are changed.
        Returns:
            EventSubscription: The subscription object.
        """
        return EventSubscription(self.__on_stage_items_selection_changed, fn)

    def get_selected_stage_items(self) -> List[StageItem]:
        """Gets a list of current selected stage items.

        Returns:
            List[StageItem]: A list of stage items.
        """

        return list(self.__selected_items)

    def __set_selected_stage_items(self, selections):
        self.__selected_items = set(selections)
        self.__on_stage_items_selection_changed()

    def set_selected_stage_items(self, selections: List[StageItem], undo=False):
        """Sets a list of selections.

        It also sets selections for omni.kit.selection if this stage model manages the stage
        from a UsdContext.

        Args:
            selections (List[StageItem]): Non-empty selection list to be set.
            undo (bool): If the selection for omni.kit.selection can be undo. Defaults to False.
        """

        all_items = set([item for item in selections if item and item.path in self.__stage_item_cache])
        if all_items != self.__selected_items:
            if self.__usd_context:
                new_paths = [item.path.pathString for item in selections if item]
                self.__set_usd_selection = True
                if not undo:
                    self.__usd_context.get_selection().set_selected_prim_paths(new_paths, True)
                else:
                    old_paths = [item.path.pathString for item in self.__selected_items if item]
                    omni.kit.commands.execute(
                        "SelectPrims", old_selected_paths=old_paths,
                        new_selected_paths=new_paths, expand_in_stage=True
                    )

            self.__set_selected_stage_items(all_items)

    # Deprecated APIs
    def refresh_item_names(self):  # pragma: no cover
        """Deprecated."""

        for item in self.__stage_item_cache.values():
            item.name_model.rebuild()
            self._item_changed(item)

    @property
    def check_missing_references(self):  # pragma: no cover
        """Deprecated: It will always check missing references now."""

        return True

    @check_missing_references.setter
    def check_missing_references(self, value):  # pragma: no cover
        """Deprecated."""
        pass
