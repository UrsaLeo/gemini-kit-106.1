# Copyright (c) 2018-2020, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#
__all__ = ["StageWidget"]

from .context_menu import ContextMenu
from .column_menu import ColumnMenuDelegate
from .column_menu import ColumnMenuItem
from .column_menu import ColumnMenuModel
from .event import Event, EventSubscription
from .stage_column_delegate_registry import StageColumnDelegateRegistry
from .stage_delegate import StageDelegate
from .stage_icons import StageIcons
from .stage_model import StageModel
from .stage_settings import StageSettings
from .stage_style import Styles as StageStyles
from .stage_filter import StageFilterButton


from pxr import Sdf
from pxr import Tf
from pxr import Usd
from pxr import UsdGeom
from pxr import UsdSkel

from typing import Callable
from typing import List
from typing import Tuple
from typing import Optional

import asyncio
import carb.settings
import omni.kit.app
import omni.ui as ui
import omni.kit.notification_manager as nm
import omni.kit.usd.layers as layers
import weakref
from omni.kit.widget.options_button import OptionsButton
from omni.kit.widget.options_menu import OptionItem, OptionCustom, OptionSeparator, OptionLabelMenuItemDelegate

STAGE_ROOT="/World/Twins/Building" #chandika

class StageWidget:
    """
    The Stage widget that represents the stage with a tree view displaying the prim hierarchy with multiple columns.
    For each treeview item, multiple columns representing different aspects for the prim can be customized and
    displayed. It also provides context menu items associated with the stage/prims.
    """

    def __init__(
        self, stage: Usd.Stage,
        columns_accepted: List[str] = None,
        columns_enabled: List[str] = None,
        lazy_payloads: bool = False,
        **kwargs
    ):
        """
        The constructor for the Stage Widget.

        Args:
            stage (Usd.Stage): The instance of USD stage to be managed by this widget.

        Keyword Args:
            columns_accepted (List[str]): The list of columns that are supported. By default, it's all registered
                columns if this arg is not provided.
            columns_enabled (List[str]): The list of columns that are enabled when the widget is shown by default.
            lazy_payloads (bool): Whether it should load all payloads when stage items are shown or not.
                False by default.
            children_reorder_supported (bool): Whether it should enable children reorder support or not. By default,
                children reorder support is disabled, which means you cannot reorder children in the widget, and
                renaming name of prim will put the prim at the end of the children list. REMINDER: Enabling this
                option has performance penalty as it will trigger re-composition to the parent of the reordered/renamed
                prims.
            show_prim_display_name (bool): Whether it's to show displayName from prim's metadata or the name of the prim.
                By default, it's False, which means it shows name of the prim.
            auto_reload_prims (bool): Whether it will auto-reload prims if there are any new changes from disk. By
                default, it's disabled.
            show_undefined_prims (bool): Whether it's to show prims that have no def or not.
                By default, it's False.

        Other:
            All other arguments inside kwargs except the above 3 will be passed as params to the ui.Frame for the
            stage widget.
        """

        # create_stage_update_node` calls `_on_attach`, and the models will be created there.
        self._model = None
        self._tree_view = None
        self._tree_view_flat = None
        self._option_button: Optional[OptionsButton] = None

        self._delegate = kwargs.get("stage_delegate", StageDelegate())
        self._delegate.expand_fn = self.expand
        self._delegate.collapse_fn = self.collapse
        self._selection = None
        self._stage_settings = StageSettings()

        self._stage_settings.children_reorder_supported = kwargs.pop("children_reorder_supported", False)
        self._stage_settings.show_prim_displayname = kwargs.pop("show_prim_display_name", False)
        self._stage_settings.auto_reload_prims = kwargs.pop("auto_reload_prims", False)
        self._stage_settings.show_undefined_prims = kwargs.pop("show_undefined_prims", False)

        # Initialize columns
        self._columns_accepted = columns_accepted
        self._columns_enabled = columns_enabled
        self._lazy_payloads = lazy_payloads
        self._column_widths = []
        self._min_column_widths = []

        self._column_model = kwargs.get("column_menu_model", None)
        if not self._column_model:
            self._column_model = ColumnMenuModel(self._columns_enabled, self._columns_accepted)
        self._column_delegate = ColumnMenuDelegate()
        self._column_changed_sub = self._column_model.subscribe_item_changed_fn(self._on_column_changed)
        # We need it to be able to add callback to StageWidget
        self._column_changed_event = Event()

        self._column_delegate_registry = kwargs.get("column_delegate_registry", StageColumnDelegateRegistry())

        self.open_stage(stage)

        self._root_frame = ui.Frame(**kwargs)
        self.build_layout()

        # The filtering logic
        self._begin_filter_subscription = self._search.subscribe_begin_edit_fn(
            lambda _: self._set_widget_visible(self._search_label, False)
        )
        self._end_filter_subscription = self._search.subscribe_end_edit_fn(
            lambda m: self._filter_by_text(m.as_string)
            or self._set_widget_visible(self._search_label, not m.as_string)
        )

        # Update icons when they changed
        self._icons_subscription = StageIcons().subscribe_icons_changed(self.update_icons)

        self._expand_task = None

    @staticmethod
    def _get_path_converter() -> Callable:
        """
        The Path conversion function to use for prim paths.

        Returns:
            Callable: The path conversion function.
        """
        return Sdf.Path

    def _build_options_button(self):
        """
        Builds the options buttons.
        Options include:
            Auto Reload Primitives: Whether to auto reload prims.
            Reload Outdated Primitives: Reloads outdated prims when triggered.
            Reset: Resets all options to default.
            Flat List Search: Whether to turn on flat list search.
            Show Root: Whether to show root.
            Show Display Names: Whether to show display names for prims.
            Show Undefined Prims: Whether to show undefined prims.
            Enable Children Reorder: Whether to enable children re-ordering.
            Columns: Groups all registered column types, and creates a sub item for each registered column type.
        """
        def _set_auto_reload_prims(value: bool):
            self.auto_reload_prims = value

            stage_model = self.get_model()

            all_stage_items = stage_model._get_all_stage_items_from_cache()

            if not all_stage_items:
                return

            for stage_item in all_stage_items:
                stage_item.update_flags()
                stage_model._item_changed(stage_item)

            property_window = omni.kit.window.property.get_window()
            if property_window:
                property_window.request_rebuild()

        def _set_display_name(value: bool):
            self.show_prim_display_name = value

        def _show_undefined_prims(value: bool):
            self.show_undefined_prims = value

        def _children_reorder_supported(value: bool):
            self.children_reorder_supported = value

        def _build_columns_menu():
            with ui.Menu("Columns", delegate=ui.MenuDelegate()):
                # Sub-menu with list view, so it's possible to reorder it.
                with ui.Frame():
                    self._column_list = ui.TreeView(
                        self._column_model,
                        delegate=self._column_delegate,
                        root_visible=False,
                        drop_between_items=True,
                        width=150,
                        style={ "background_selected_color": 0xFF323434},
                    )
                    self._column_list.set_selection_changed_fn(self._on_column_selection_changed)

        option_items = [
            OptionItem("Auto Reload Primitives", default=self.auto_reload_prims, on_value_changed_fn=_set_auto_reload_prims),
            OptionCustom(build_fn=lambda: ui.MenuItem("Reload Outdated Primitives", delegate=OptionLabelMenuItemDelegate(), triggered_fn=self._on_reload_all_prims)),
            OptionSeparator(),
            OptionCustom(build_fn=lambda: ui.MenuItem("Reset", delegate=OptionLabelMenuItemDelegate(), triggered_fn=self._on_reset)),
            OptionSeparator(),
            OptionItem("Flat List Search", default=self._stage_settings.flat_search, on_value_changed_fn=self._on_flat_changed),
            OptionItem("Show Root", default=False, on_value_changed_fn=self._on_show_root_changed),
            OptionItem("Show Display Names", default=self.show_prim_display_name, on_value_changed_fn=_set_display_name),
            OptionItem("Show Undefined Prims", default=self.show_undefined_prims, on_value_changed_fn=_show_undefined_prims),
            OptionItem("Enable Children Reorder", default=self.children_reorder_supported, on_value_changed_fn=_children_reorder_supported),
            OptionCustom(build_fn=_build_columns_menu),
        ]
        self._option_button = OptionsButton(option_items, width=20, height=20)

    def _on_column_selection_changed(self, _):
        self._column_list.selection = []

    def build_layout(self):
        """Creates all the widgets in the widget."""
        style = StageStyles.STAGE_WIDGET
        use_default_style = (
            carb.settings.get_settings().get_as_string("/persistent/app/window/useDefaultStyle") or False
        )
        if not use_default_style:
            self._root_frame.set_style(style)

        with self._root_frame:
            with ui.VStack(style=style):
                ui.Spacer(height=4)
                with ui.ZStack(height=0):
                    with ui.HStack(spacing=4):
                        # Search filed
                        self._search = ui.StringField(name="search").model
                        # Filter button
                        self._filter_button = StageFilterButton(self)
                        # Options button
                        self._build_options_button()
                    # The label on the top of the search field
                    self._search_label = ui.Label("Search", name="search")
                ui.Spacer(height=7)
                with ui.ScrollingFrame(
                    horizontal_scrollbar_policy=ui.ScrollBarPolicy.SCROLLBAR_ALWAYS_OFF,
                    style_type_name_override="TreeView.ScrollingFrame",
                    mouse_pressed_fn=lambda x, y, b, _: self._delegate.on_mouse_pressed(
                        b, self._model and self._model.stage, None, False
                    ),
                ):
                    with ui.ZStack():
                        # Sometimes we need to switch between regular tree and flat list. To do it fast we keep
                        # both widgets.
                        self._tree_view = ui.TreeView(
                            self._model,
                            delegate=self._delegate,
                            drop_between_items=True,
                            header_visible=True,
                            root_visible=False,
                            columns_resizable=True,
                        )
                        self._tree_view_flat = ui.TreeView(
                            self._model,
                            delegate=self._delegate,
                            header_visible=True,
                            root_visible=False,
                            columns_resizable=True,
                            visible=False,
                        )

        self.set_columns_widths()

    def update_filter_menu_state(self, filter_type_list: list):
        """
        Enable filters.

        Args:
            filter_type_list (list): List of usd types to be enabled. If not all usd types are pre-defined, hide filter
            button and Reset in the options button.
        """
        unknown_types = self._filter_button.enable_filters(filter_type_list)
        if unknown_types:
            self._options_menu_reset.visible = False

    def set_selection_watch(self, selection):
        """
        Sets the selection watch of the current stage widget.

        Args:
            selection (omni.kit.widget.stage.DefaultSelectionWatch): The selection watch.
        """
        self._selection = selection
        if self._selection:
            if self._tree_view.visible:
                self._selection.set_tree_view(self._tree_view)
            if self._tree_view_flat.visible:
                self._selection.set_tree_view(self._tree_view_flat)

    def get_model(self) -> StageModel:
        """
        Gets the stage model.

        Returns:
            Optional[StageModel]: If the treeview is visible, returns the treeview stage model, otherwise returns None.
        """
        if self._tree_view.visible:
            return self._tree_view.model
        elif self._tree_view_flat.visible:
            return self._tree_view_flat.model

        return None

    def expand(self, path: Sdf.Path):
        """
        Sets the given path to be expanded.

        Args:
            path (Sdf.Path): Path to be expanded.
        """
        if isinstance(path, str):
            path = self._get_path_converter()(path)

        if self._tree_view.visible:
            widget = self._tree_view
        elif self._tree_view_flat.visible:
            widget = self._tree_view_flat
        else:
            return

        # Get the selected item and its parents. Expand all the parents of the new selection.
        full_chain = widget.model.find_full_chain(path.pathString)
        if full_chain:
            for item in full_chain:
                widget.set_expanded(item, True, False)

    def collapse(self, path: Sdf.Path):
        """
        Set the given path to be collapsed.

        Args:
            path (Sdf.Path): Path to be collapsed.
        """
        if isinstance(path, str):
            path = self._get_path_converter()(path)

        if self._tree_view.visible:
            widget = self._tree_view
        elif self._tree_view_flat.visible:
            widget = self._tree_view_flat
        else:
            return

        widget.set_expanded(widget.model.find(path), False, True)

    def destroy(self):
        """
        Called by extension before destroying this object. It doesn't happen automatically.
        Without this hot reloading doesn't work.
        """
        self._cancel_expand_task()

        self._begin_filter_subscription = None
        self._end_filter_subscription = None
        self._icons_subscription = None

        self._tree_view = None
        self._tree_view_flat = None
        self._search_label = None

        if self._model:
            self._model.destroy()
            self._model = None
        if self._delegate:
            self._delegate.destroy()
            self._delegate = None

        self._stage_subscription = None

        self._selection = None

        if self._option_button:
            self._option_button.destroy()
            self._option_button = None
        self._filter_button.destroy()
        self._filter_button = None

        self._root_frame = None

        self._column_list = None
        self._column_model.destroy()
        self._column_model = None
        self._column_delegate.destroy()
        self._column_delegate = None
        self._column_changed_sub = None

    def _clear_filter_types(self):
        self._filter_button.model.reset()

    def _on_flat_changed(self, flat: bool):
        """Toggle flat/not flat search"""
        # Disable search. It makes the layout resetting to the original state
        self._filter_by_text("")
        self._clear_filter_types()
        # Change flag and clear the model
        self._stage_settings.flat_search = flat
        self._search.set_value("")
        self._search_label.visible = True

    def _on_reset(self):
        """Toggle "Reset" menu"""
        self._model.reset()

    def _on_show_root_changed(self, show: bool):
        """Called to trigger "Show Root" menu item"""
        self._tree_view.root_visible = show

        # With new options menu, it keeps open when item clicked and treeview will not refresh unless focused
        # Here force to refresh treeview to show/hide root.
        self._tree_view.model._item_changed(None)

    @property
    def show_prim_display_name(self) -> bool:
        """
        Whether to show display names for prims.

        Returns:
            bool
        """
        return self._stage_settings.show_prim_displayname

    @show_prim_display_name.setter
    def show_prim_display_name(self, show: bool):
        """
        Sets whether to show display names for prims.

        Args:
            show (bool): Value to set.
        """
        if self._stage_settings.show_prim_displayname != show:
            self._stage_settings.show_prim_displayname = show
            self._model.show_prim_displayname = show

    @property
    def show_undefined_prims(self) -> bool:
        """
        Whether to show undefined prims.

        Returns:
            bool
        """
        return self._stage_settings.show_undefined_prims

    @show_undefined_prims.setter
    def show_undefined_prims(self, show: bool):
        """
        Sets whether to show undefined prims.

        Args:
            show (bool): Value to set.
        """
        if self._stage_settings.show_undefined_prims != show:
            self._stage_settings.show_undefined_prims = show
            self._model.show_undefined_prims = show

    @property
    def children_reorder_supported(self) -> bool:
        """
        Whether children re-ordering is supported.

        Returns:
            bool
        """
        return self._stage_settings.children_reorder_supported

    @children_reorder_supported.setter
    def children_reorder_supported(self, enabled: bool):
        """
        Sets whether children re-ordering should be supported.

        Args:
            enabled (bool): Value to set.
        """
        self._stage_settings.children_reorder_supported = enabled
        self._model.children_reorder_supported = enabled

    @property
    def auto_reload_prims(self) -> bool:
        """
        Whether prims are auto loaded.

        Returns:
            bool
        """
        return self._stage_settings.auto_reload_prims

    def _on_reload_all_prims(self):
        self._on_reload_prims(not_in_session=False)

    def _on_reload_prims(self, not_in_session=True):
        if not self._model:
            return

        stage = self._model.stage
        if not stage:
            return

        usd_context = omni.usd.get_context_from_stage(stage)
        if not usd_context:
            return

        layers_state_interface = layers.get_layers_state(usd_context)
        if not_in_session:
            # this will auto reload all layers that are not currently in a live session ( silently )
            layers_state_interface.reload_outdated_non_sublayers()
        else:
            # this will reload all layers but will confirm with user if it is in a live session
            all_outdated_layers = layers_state_interface.get_all_outdated_layer_identifiers(not_in_session)

            try:
                from omni.kit.widget.live_session_management.utils import reload_outdated_layers

                reload_outdated_layers(all_outdated_layers, usd_context)
            except ImportError:
                # If live session management is not enabled. Skipps UI prompt to reload it directly.
                layers.LayerUtils.reload_all_layers(all_outdated_layers)

    @auto_reload_prims.setter
    def auto_reload_prims(self, enabled: bool):
        """
        Sets whether prims should be autoloaded.

        Args:
            enabled (bool): Value to set.
        """
        if self._stage_settings.auto_reload_prims != enabled:
            self._stage_settings.auto_reload_prims = enabled
            if enabled:
                self._on_reload_prims()

    @staticmethod
    def _set_widget_visible(widget: ui.Widget, visible):
        """Utility for using in lambdas"""
        widget.visible = visible

    def _get_geom_primvar(self, prim, primvar_name):
        primvars_api = UsdGeom.PrimvarsAPI(prim)
        return primvars_api.GetPrimvar(primvar_name)

    def _filter_by_flattener_basemesh(self, enabled):
        self._filter_by_lambda({"_is_prim_basemesh": lambda prim: self._get_geom_primvar(prim, "materialFlattening_isBaseMesh")}, enabled)

    def _filter_by_flattener_decal(self, enabled):
        self._filter_by_lambda({"_is_prim_decal": lambda prim: self._get_geom_primvar(prim, "materialFlattening_isDecal")}, enabled)

    def _filter_by_visibility(self, enabled):
        """Filter Hidden On/Off"""

        def _is_prim_hidden(prim):
            imageable = UsdGeom.Imageable(prim)
            return imageable.ComputeVisibility() == UsdGeom.Tokens.invisible

        self._filter_by_lambda({"_is_prim_hidden": _is_prim_hidden}, enabled)

    def _filter_by_active_state(self, enabled):
        """Filter Active On/Off"""

        def _is_prim_inactive(prim):
            return not prim.IsActive()

        self._filter_by_lambda({"_is_prim_inactive": _is_prim_inactive}, enabled)

    def _filter_by_def_state(self, enabled):
        """Filter Def On/Off"""

        def _is_prim_undefined(prim):
            return not prim.IsDefined()

        self._filter_by_lambda({"_is_prim_undefined": _is_prim_undefined}, enabled)

    def _filter_by_type(self, usd_types, enabled):
        """
        Set filtering by USD type.

        Args:
            usd_types: The type or the list of types it's necessary to add or remove from filters.
            enabled: True to add to filters, False to remove them from the filter list.
        """
        if not isinstance(usd_types, list):
            usd_types = [usd_types]

        for usd_type in usd_types:
            # Create a lambda filter
            fn = lambda p, t=usd_type: p.IsA(t)
            name_to_fn_dict = {Tf.Type(usd_type).typeName: fn}
            self._filter_by_lambda(name_to_fn_dict, enabled)

    def _filter_by_api_type(self, api_types, enabled):
        """
        Set filtering by USD api type.

        Args:
            api_types: The api type or the list of types it's necessary to add or remove from filters.
            enabled: True to add to filters, False to remove them from the filter list.
        """
        if not isinstance(api_types, list):
            api_types = [api_types]

        for api_type in api_types:
            # Create a lambda filter
            fn = lambda p, t=api_type: p.HasAPI(t)
            name_to_fn_dict = {Tf.Type(api_type).typeName: fn}
            self._filter_by_lambda(name_to_fn_dict, enabled)

    def _filter_by_lambda(self, filters: dict, enabled):
        """
        Set filtering by lambda.

        Args:
            filters: The dictionary of this form: {"type_name_string", lambda prim: True}. When lambda is True,
                     the prim will be shown.
            enabled: True to add to filters, False to remove them from the filter list.
        """
        if self._tree_view.visible:
            tree_view = self._tree_view
        else:
            tree_view = self._tree_view_flat

        if enabled:
            tree_view.model.filter(add=filters)
            # Filtering mode always expanded.
            tree_view.keep_alive = True
            tree_view.keep_expanded = True
            self._delegate.set_highlighting(enable=True)

            if self._selection:
                self._selection.enable_filtering_checking(True)
        else:
            for lambda_name in filters:
                keep_filtering = tree_view.model.filter(remove=lambda_name)
            if not keep_filtering:
                # Filtering is finished. Return it back to normal.
                tree_view.keep_alive = False
                tree_view.keep_expanded = False
                self._delegate.set_highlighting(enable=False)

                if self._selection:
                    self._selection.enable_filtering_checking(False)

    def _filter_by_text(self, filter_text: str):
        """Set the search filter string to the models and widgets"""
        if self._selection:
            self._selection.set_filtering(filter_text)

        self._model.flat = self._stage_settings.flat_search
        self._model.filter_by_text(filter_text)

        # Depends on the flat mode to see which treeview to show.
        if self._model.flat:
            self._tree_view.visible = False
            self._tree_view_flat.visible = True
            tree_view = self._tree_view_flat
        else:
            self._tree_view.visible = True
            self._tree_view_flat.visible = False
            tree_view = self._tree_view

        tree_view.keep_alive = not not filter_text
        tree_view.keep_expanded = not not filter_text

        # Replace treeview in the selection model will allow to use only one selection watch for two treeviews
        if self._selection:
            self._selection.set_tree_view(tree_view)

        self._delegate.set_highlighting(text=filter_text)

    def _on_column_changed(self, column_model: ColumnMenuModel, item: ColumnMenuItem = None):
        """Called by Column Model when columns are changed or toggled"""
        all_columns = column_model.get_columns()

        column_delegate_names = [i[0] for i in all_columns if i[1]]

        # Name column should always be shown
        if "Name" not in column_delegate_names:
            column_delegate_names.insert(0, "Name")

        column_delegate_types = [
            self._column_delegate_registry.get_column_delegate(name) for name in column_delegate_names
        ]

        # Create the column delegates
        column_delegates = [delegate_type() for delegate_type in column_delegate_types if delegate_type]

        # Set the model
        self._delegate.set_column_delegates(column_delegates)
        if self._model:
            self._model.set_item_value_model_count(len(column_delegates))

        # Set the column widths
        self._column_widths = [d.initial_width for d in column_delegates]
        self._min_column_widths = [d.minimum_width for d in column_delegates]
        self.set_columns_widths()

        # Callback if someone subscribed to the StageWidget events
        self._column_changed_event(all_columns)

    def _get_stage_model(self, stage: Usd.Stage):
        return StageModel(
            stage, load_payloads=self._lazy_payloads,
            children_reorder_supported=self._stage_settings.children_reorder_supported,
            show_prim_displayname=self._stage_settings.show_prim_displayname,
            show_undefined_prims=self._stage_settings.show_undefined_prims
        )

    def set_columns_widths(self):
        """Sets the column width for treeview and flat treeview."""
        for w in [self._tree_view, self._tree_view_flat]:
            if not w:
                continue
            w.column_widths = self._column_widths
            w.min_column_widths = self._min_column_widths
            w.dirty_widgets()

    def subscribe_columns_changed(self, fn: Callable[[List[Tuple[str, bool]]], None]) -> EventSubscription:
        """
        Subscribe to columns changed event with fn.

        Args:
            fn (Callable[[List[Tuple[str, bool]]], None]): The event handler for the subscription.

        Returns:
            EventSubscription: The event subscription object.
        """
        return EventSubscription(self._column_changed_event, fn)

    def _cancel_expand_task(self):
        if self._expand_task and not self._expand_task.done():
            self._expand_task.cancel()
            self._expand_task = None

    def open_stage(self, stage: Usd.Stage):
        """
        Called when opening a new stage.

        Args:
            stage (Usd.Stage): The stage that is being opened.
        """
        if self._model:
            self._clear_filter_types()
            self._model.destroy()

        # Sometimes we need to switch between regular tree and flat list. To do it fast we keep both models.
        self._model = self._get_stage_model(stage)

        # Don't regenerate delegate as it's constructed already and treeview references to it.
        self._delegate.model = self._model

        self._on_column_changed(self._column_model)

        # Widgets are not created if `_on_attach` is called from the constructor.
        if self._tree_view:
            self._tree_view.model = self._model
            # FIXME: refresh selection subscription after changing model
            if self._tree_view.visible and self._selection:
                self._selection.set_tree_view(self._tree_view)
        if self._tree_view_flat:
            self._tree_view_flat.model = self._model
            # FIXME: refresh selection subscription after changing model
            if self._tree_view_flat.visible and self._selection:
                self._selection.set_tree_view(self._tree_view_flat)

        async def expand(tree_view, path_str: str):
            await omni.kit.app.get_app().next_update_async()

            # It's possible that weakly referenced tree view is not existed anymore.
            if not tree_view:
                return

            chain_to_world = tree_view.model.find_full_chain(path_str)
            if chain_to_world:
                for item in chain_to_world:
                    tree_view.set_expanded(item, True, False)

            self._expand_task = None

        # Expand default or the only prim or World
        if self._tree_view and stage:
            default: Usd.Prim = stage.GetDefaultPrim()
            if default:
                # We have default prim
                path_str = default.GetPath().pathString
            else:
                root: Usd.Prim = stage.GetPseudoRoot()
                children: List[Usd.Prim] = root.GetChildren()
                if children and len(children) == 1:
                    # Root has the only child
                    path_str = children[0].GetPath().pathString
                else:
                    # OK, try to open /World
                    path_str = "/World"

            self._cancel_expand_task()
            path_str=STAGE_ROOT #chandika
            self._expand_task = asyncio.ensure_future(expand(weakref.proxy(self._tree_view), path_str))

    def update_icons(self):
        """Called to update icons in the TreeView"""
        self._tree_view.dirty_widgets()
        self._tree_view_flat.dirty_widgets()

    def get_context_menu(self) -> ContextMenu:
        """
        Gets the context menu object associated with the current stage widget.

        Returns:
            ContextMenu: The ContextMenu associated with the delegate.
        """
        return self._delegate._context_menu
