# Copyright (c) 2018-2020, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#
__all__ = ["DefaultSelectionWatch"]

import carb.events
from pxr import Sdf, Trace
import omni.usd
from typing import Optional


class DefaultSelectionWatch(object):
    """ A watcher object that updates selections in TreeView when scene selections are updated, and vice versa. """

    def __init__(self, tree_view=None, usd_context=None):
        """
        Creates the selection watch instance associated with the given tree view and usd context.

        Keyword Args:
            tree_view (Optional[omni.ui.TreeView]): The treeview object to update selections from/to.
            usd_context (Optional[omni.usd.UsdContext]): The current UsdContext.
        """
        self._usd_context = usd_context or omni.usd.get_context()
        self._selection = None
        self._in_selection = False
        self._tree_view = None
        self._selection = self._usd_context.get_selection()
        self._events = self._usd_context.get_stage_event_stream()

        self.__stage_model_selection_sub = None
        self.set_tree_view(tree_view)

        self.__filter_string: Optional[str] = None
        # When True, SelectionWatch should consider filtering
        self.__filter_checking: bool = False

    def destroy(self):
        """Destroys the watcher object. Clears out event subscriptions."""
        self._usd_context = None
        self._selection = None
        self._stage_event_sub = None
        self._events = None
        if self._tree_view:
            self._tree_view.set_selection_changed_fn(None)
            self._tree_view = None
        self.__stage_model_selection_sub = None

    def set_tree_view(self, tree_view):
        """
        Replaces the TreeView that should show the selection with the given TreeView object if they are different.

        Args:
            tree_view (omni.ui.TreeView): The tree view object to update to.
        """
        if self._tree_view != tree_view:
            if self._tree_view:
                self._tree_view.set_selection_changed_fn(None)

            self._tree_view = tree_view
            self._tree_view.set_selection_changed_fn(self._on_widget_selection_changed)

        if self._tree_view:
            self.__on_stage_items_selection_changed()
            self.__stage_model_selection_sub = self._tree_view.model.subscribe_stage_items_selection_changed(
                self.__on_stage_items_selection_changed
            )

    def set_filtering(self, filter_string: Optional[str]):
        """
        Sets the filter string to the given string (all lower case).

        Args:
            filter_string (Optional[str]): The filter string, can be None.
        """
        if filter_string:
            self.__filter_string = filter_string.lower()
        else:
            self.__filter_string = filter_string

    def enable_filtering_checking(self, enable: bool):
        """
        When `enable` is True, SelectionWatch should consider filtering when changing Kit's selection.

        Args:
            enable (bool): Whether to enable filtering selections.
        """
        self.__filter_checking = enable


    #chandika - changes:When items in the viewport are selected, they can be at various levels including
    #levels that we have hidden from the tree view. If we include these levels that are excluded, the treeview
    #will not show the selection (since the leaf eg. Mesh is hidden). So we need to only include elements from
    #the path that are not excluded. Since the leaf nodes are only excluded based on the type (xform) we cut off
    #items that are not xforms so that tree view will select the visible leaf node properly

    @Trace.TraceFunction
    def __on_stage_items_selection_changed(self):
        if not self._tree_view or self._in_selection:
            return

        selected_items = self._tree_view.model.get_selected_stage_items()

        # Pump the changes to the model because to select something, TreeView should be updated.
        self._tree_view.model.update_dirty()

        # Expands all items in treeview
        selection = []
        for selected_item in selected_items:
            path = selected_item.path

            # Get the selected item and its parents. Expand all the parents of the new selection.
            full_chain = self._tree_view.model.find_full_chain(path)
            # When the new object is created, omni.usd sends the selection is changed before the object appears in the
            # stage and it means we can't select it. In this way it's better to return because we don't have the item
            # in the model yet.
            # TODO: Use UsdNotice to track if the object is created.
            if not full_chain or full_chain[-1].path != path:
                continue

            selection_chain=[]
            if full_chain:
                for item in full_chain[:-1]:
                    prim =item.prim
                    if (prim.GetTypeName() == "Xform"):
                        selection_chain.append(item)
                        self._tree_view.set_expanded(item, True, False)
                    #self._tree_view.set_expanded(item, True, False)
                selection.append(selection_chain[-1])

        # Send all of this to TreeView.
        self._in_selection = True
        self._tree_view.selection = selection
        self._in_selection = False

    @Trace.TraceFunction
    def _on_widget_selection_changed(self, selection):
        """Send the selection from TreeView to Kit"""
        if self._in_selection or not self._tree_view:
            return

        self._in_selection = True
        prim_paths = [item.path for item in selection if item]

        # Filter selection
        if self.__filter_string or self.__filter_checking:
            # Check if the selected prims are filtered and re-select filtered items only if necessary.
            filtered_paths = [item.path for item in selection if item and item.filtered]
            if filtered_paths != prim_paths:
                selection = [item for item in selection if item and item.path in filtered_paths]
                self._tree_view.selection = selection

        # Send the selection to Kit
        self._tree_view.model.set_selected_stage_items(selection, True)
        self._in_selection = False
