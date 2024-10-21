"""
omni.kit.window.property PropertyWindow class
"""
# Copyright (c) 2020, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#

__all__ = ["PropertyWindow"]

import asyncio
import sys
import copy
from typing import Any, List, Optional

import carb
import carb.settings
import omni.ui as ui
from omni.kit.widget.searchfield import SearchField

from .property_filter import PropertyFilter
from .property_scheme_delegate import PropertySchemeDelegate
from .property_widget import PropertyWidget
from .templates.simple_property_widget import LABEL_HEIGHT


class PropertyWindow:
    """
    Property Window framework.
    """
    def __init__(self, window_kwargs=None, properties_frame_kwargs=None):
        """
        Create a PropertyWindow.

        Args:
            window_kwargs (dict): Additional kwargs to pass to ui.Window.
            properties_frame_kwargs (dict): Additional kwargs to pass to ui.ScrollingFrame.
        """
        window_flags = ui.WINDOW_FLAGS_NO_SCROLLBAR
        self._settings = carb.settings.get_settings()
        self._visibility_changed_listener = None
        self._window_kwargs = {
            "title": "Property",
            "width": 600,
            "height": 800,
            "flags": window_flags,
            "dockPreference": ui.DockPreference.RIGHT_BOTTOM,
        }
        if window_kwargs:
            self._window_kwargs.update(window_kwargs)
        self._properties_frame_kwargs = {
            "name": "canvas",
            "horizontal_scrollbar_policy": ui.ScrollBarPolicy.SCROLLBAR_ALWAYS_OFF,
            "vertical_scrollbar_policy": ui.ScrollBarPolicy.SCROLLBAR_AS_NEEDED,
        }
        if properties_frame_kwargs:
            self._properties_frame_kwargs.update(properties_frame_kwargs)
        self._window = ui.Window(**self._window_kwargs)
        self._window.set_visibility_changed_fn(self._visibility_changed_fn)
        self._docked = True
        self._selected_in_dock = True
        self._window.set_selected_in_dock_changed_fn(self.__selected_in_dock_changed)
        self._window.set_docked_changed_fn(self.__dock_changed)
        self._window.frame.set_build_fn(self._rebuild_window)

        # Dock it to the same space where Layers is docked, make it the first tab and the active tab.
        self._window.deferred_dock_in("Details", ui.DockPolicy.CURRENT_WINDOW_IS_ACTIVE)
        self._window.dock_order = 0

        self._scheme = ""
        self._payload = None
        self._scheme_delegates = {}
        self._scheme_delegates_layout = {}
        self._widgets_top = {}
        self._widgets_bottom = {}
        self._built_widgets = set()
        self._notification_paused = False
        self._notifications_while_paused = []
        self._filter = PropertyFilter()
        self._window_frame = None  # for compatibility with clients that look for this to modify ScrollingFrame
        self.__old_scroll_pos = None

    def destroy(self):
        """Destroy function. Class cleanup function
        """
        self._visibility_changed_listener = None
        self._window = None

    def set_visible(self, visible: bool):
        """Set window visibility state.

        Args:
            visible (bool): Visible state of the window.
        """
        if self._window:
            self._window.visible = visible

    def _on_search(self, search_words: Optional[List[str]]) -> None:
        self._filter.name = "" if search_words is None else " ".join(search_words)

    def __selected_in_dock_changed(self, is_selected):
        self._selected_in_dock = is_selected
        self.pause = not (is_selected if self._docked else True)

    def __dock_changed(self, is_docked):
        self._docked = is_docked
        self.pause = not (self._selected_in_dock if is_docked else True)

    def _rebuild_window(self):
        # We should only rebuild the properties ScrollingFrame on payload change, but that doesn't work
        # reliably so as a workaround we rebuild the entire window including static searchfield.
        use_default_style = (
            carb.settings.get_settings().get_as_string("/persistent/app/window/useDefaultStyle") or False
        )
        if use_default_style:
            style = {}
        else:
            from .style import get_style

            style = get_style()
        with ui.VStack(style=style):
            if carb.settings.get_settings().get_as_bool("/ext/omni.kit.window.property/enableSearch"):
                with ui.HStack(height=0):
                    ui.Spacer(width=8)
                    self._searchfield = SearchField(
                        on_search_fn=self._on_search,
                        subscribe_edit_changed=True,
                        show_tokens=False,
                        height=LABEL_HEIGHT,
                        style=style,
                    )
                    # Workaround for needing to rebuild SearchField: fill with existing filter text
                    if self._filter.name:
                        self._searchfield._search_field.model.as_string = self._filter.name
                        self._searchfield._set_in_searching(True)
                    ui.Spacer(width=5 + 12)  # scrollbar width is 12
                ui.Spacer(height=5)

            self._window_frame = ui.ScrollingFrame(**self._properties_frame_kwargs)
            with self._window_frame:
                with ui.VStack(height=0, name="main_v_stack", spacing=6):
                    if self._scheme != "":
                        widgets_to_build = []
                        unwanted_widgets = []
                        scheme_delegates_layout = self._scheme_delegates_layout.get(self._scheme)
                        scheme_delegates = self._scheme_delegates.setdefault(self._scheme, {})
                        scheme_delegates_filtered = []
                        if scheme_delegates_layout:
                            for delegate_name in scheme_delegates_layout:
                                delegate = scheme_delegates.get(delegate_name)
                                if delegate:
                                    scheme_delegates_filtered.append(delegate)
                        else:
                            scheme_delegates_filtered = scheme_delegates.values()

                        for delegate in scheme_delegates_filtered:
                            widgets_to_build.extend(delegate.get_widgets(self._payload))
                            unwanted_widgets.extend(delegate.get_unwanted_widgets(self._payload))

                        # ordered top stack + reverse ordered bottom stack
                        all_registered_widgets = {
                            **self._widgets_top.setdefault(self._scheme, {}),
                            **dict(reversed(list(self._widgets_bottom.setdefault(self._scheme, {}).items()))),
                        }

                        # keep order
                        widget_name_already_built = set()
                        built_widgets = set()
                        for widget_name in widgets_to_build:
                            # skip dup
                            if widget_name in widget_name_already_built:
                                continue
                            widget = all_registered_widgets.get(widget_name)
                            if widget and widget.on_new_payload(self._payload):
                                widget.build(self._filter)
                                built_widgets.add(widget)
                            widget_name_already_built.add(widget_name)

                        # Build the rest of the widgets that are not unwanted
                        unwanted_widgets_set = set(unwanted_widgets)
                        all_widgets = all_registered_widgets.keys()
                        for widget_name in all_widgets:
                            if widget_name not in widget_name_already_built and widget_name not in unwanted_widgets_set:
                                widget = all_registered_widgets.get(widget_name)
                                if widget and widget.on_new_payload(self._payload):
                                    widget.build(self._filter)
                                    built_widgets.add(widget)

                        # Reset those widgets that are built before but no longer needed
                        for widget in self._built_widgets:
                            if widget not in built_widgets:
                                widget.reset()
                        self._built_widgets = built_widgets

        self.restore_scroll_pos()

    def _visibility_changed_fn(self, visible):
        if not visible:
            # When the property window is no longer visible, reset all the built widget so they don't take CPU time in background
            for widget in self._built_widgets:
                widget.reset()

            self._built_widgets.clear()

            # schedule a rebuild of window frame. _rebuild_window won't be actually called until the window is visible again.
            self._window.frame.rebuild()

        if self._visibility_changed_listener:
            self._visibility_changed_listener(visible)

    def set_visibility_changed_listener(self, listener: callable):
        """Adds callback function for when window visibility is changed.

        Args:
            listener (callable): visibility changed callback.
        """
        self._visibility_changed_listener = listener

    def register_widget(self, scheme: str, name: str, property_widget: PropertyWidget, top_stack: bool = True):
        """
        Registers a PropertyWidget to PropertyWindow.

        Args:
            scheme (str): Scheme of the PropertyWidget will work with.
            name (str): A unique name to identify the PropertyWidget under. Widget with existing name will be overridden.
            property_widget (property_widget.PropertyWidget): A PropertyWidget instance to be added.
            top_stack (bool): Widgets are managed in double stack:
                              True to register the widget to "Top" stack which layouts widgets from top to bottom.
                              False to register the widget to "Button" stack which layouts widgets from bottom to top and always below the "Top" stack.
        """
        if top_stack:
            self._widgets_top.setdefault(scheme, {})[name] = property_widget
            self._widgets_bottom.setdefault(scheme, {}).pop(name, None)
        else:
            self._widgets_bottom.setdefault(scheme, {})[name] = property_widget
            self._widgets_top.setdefault(scheme, {}).pop(name, None)
        if scheme == self._scheme:
            self._window.frame.rebuild()

    def unregister_widget(self, scheme: str, name: str, top_stack: bool = True):
        """
        Unregister a PropertyWidget from PropertyWindow.

        Args:
            scheme (str): Scheme of the PropertyWidget to be removed from.
            name (str): The name to find the PropertyWidget and remove.
            top_stack (bool): see @register_widget
        """
        if top_stack:
            widget = self._widgets_top.setdefault(scheme, {}).pop(name, None)
        else:
            widget = self._widgets_bottom.setdefault(scheme, {}).pop(name, None)
        if widget:
            widget.clean()
        if scheme == self._scheme:
            self._window.frame.rebuild()

    def register_scheme_delegate(self, scheme: str, name: str, delegate: PropertySchemeDelegate):
        """
        Register a PropertySchemeDelegate for a given scheme. A PropertySchemeDelegate tests the payload and determines
        what widgets to be drawn in what order. A scheme can have multiple PropertySchemeDelegate and their result will
        be merged to display all relevant widgets.

        PropertySchemeDelegate does not hide widgets that are not returned from its get_widgets function. If you want to
        hide certain widget, return them in PropertySchemeDelegate.get_unwanted_widgets. See PropertySchemeDelegate's
        documentation for details.

        Args:
            scheme (str): Scheme of the PropertySchemeDelegate to be added to.
            name (str): A unique name to identify the PropertySchemeDelegate under. Delegate with existing name will be
                        overridden.
            delegate (PropertySchemeDelegate): A PropertySchemeDelegate instance to be added.
        """
        self._scheme_delegates.setdefault(scheme, {})[name] = delegate
        if scheme == self._scheme:
            self._window.frame.rebuild()

    def unregister_scheme_delegate(self, scheme: str, name: str):
        """
        Unregister a PropertySchemeDelegate from PropertyWindow by name.

        Args:
            scheme (str): Scheme of the PropertySchemeDelegate to be removed from.
            name (str): The name to find the PropertySchemeDelegate and remove.
        """
        self._scheme_delegates.setdefault(scheme, {}).pop(name, None)
        if scheme == self._scheme:
            self._window.frame.rebuild()

    def set_scheme_delegate_layout(self, scheme: str, layout: List[str]):
        """
        Register a list of PropertySchemeDelegate's names to finalize the order and visibility of all registered
        PropertySchemeDelegate. Useful if you need a fixed layout of Property Widgets for your Kit experience.

        Remark:
            If you're a Property Widget writer, DO NOT call this function. It should only be called by Kit Experience
            to tune the final look and layout of the Property Window.

        Args:
            scheme (str): Scheme of the PropertySchemeDelegate order to be added to.
            layout (List(str)): a list of PropertySchemeDelegate's name, in the order of being processed when building
                UI. Scheme delegate not in this will be skipped.
        """
        self._scheme_delegates_layout[scheme] = layout
        if scheme == self._scheme:
            self._window.frame.rebuild()

    def reset_scheme_delegate_layout(self, scheme: str):
        """
        Reset the order so PropertySchemeDelegate will be processed in the order of registration when building UI.

        Args:
            scheme (str): Scheme of the PropertySchemeDelegate order to be removed from.
        """
        self._scheme_delegates_layout.pop(scheme)
        if scheme == self._scheme:
            self._window.frame.rebuild()

    def notify(self, scheme: str, payload: Any):
        """
        Notify Property Window of a scheme and/or payload change.
        This is the function to trigger refresh of PropertyWindow.

        Args:
            scheme (str): Scheme of this notification.
            payload: Payload to refresh the widgets.
        """
        if self._notification_paused:
            self._notifications_while_paused.append((scheme, copy.copy(payload)))
        else:
            if self._scheme != scheme:
                if payload:
                    self._scheme = scheme
                    self._payload = payload
                    self._window.frame.rebuild()
            elif self._payload != payload:
                self._payload = payload
                self._window.frame.rebuild()

    def get_scheme(self):
        """
        Gets the current scheme being displayed in Property Window.
        """
        return self._scheme

    def request_rebuild(self):
        """
        Requests the entire property window to be rebuilt.
        """
        if self._window:
            self._window.frame.rebuild()

    @property
    def paused(self):
        """
        Gets if property window refresh is paused.
        """
        return self._notification_paused

    @paused.setter
    def paused(self, to_pause: bool):
        """
        Sets if property window refresh is paused.
        When property window is paused, calling `notify` will not refresh Property Window content.
        When property window is resumed, the window will refresh using the queued schemes and payloads `notified` to Property Window while paused.

        Args:
            to_pause (bool): True to pause property window refresh. False to resume property window refresh.
        """
        if to_pause:
            self._notification_paused = True
        else:
            if self._notification_paused:
                self._notification_paused = False
                for notification in self._notifications_while_paused:
                    self.notify(notification[0], notification[1])
                self._notifications_while_paused.clear()

    @property
    def properties_frame(self):
        """Gets the ui.ScrollingFrame container of PropertyWidgets"""
        return self._window_frame  # misnamed for backwards compatibility

    def save_scroll_pos(self, reset=False):
        """Save scroll position to previous position. Used when trying to keep scroll position when selecting attributes of same type.

        Args:
            reset (bool): If True clear old scroll position.
        """
        if reset:
            self.__old_scroll_pos = None
            return

        # scroll position is at the bottom of the window
        if self.properties_frame and int(self.properties_frame.scroll_y_max) == int(self.properties_frame.scroll_y):
            self.__old_scroll_pos = sys.float_info.max
            return
        if self.properties_frame :
            self.__old_scroll_pos = self.properties_frame.scroll_y

    def restore_scroll_pos(self):
        """Restore scroll position from previous position. Used when trying to keep scroll position when selecting attributes of same type."""
        import omni.kit.app

        async def set_scroll(ypos):
            # wait for window to fully populate
            await omni.kit.app.get_app().next_update_async()
            await omni.kit.app.get_app().next_update_async()

            # scroll position is at the bottom of the window
            if ypos == sys.float_info.max:
                self.properties_frame.scroll_y = self.properties_frame.scroll_y_max
            else:
                self.properties_frame.scroll_y = ypos

        if self.__old_scroll_pos:
            asyncio.ensure_future(set_scroll(self.__old_scroll_pos))
