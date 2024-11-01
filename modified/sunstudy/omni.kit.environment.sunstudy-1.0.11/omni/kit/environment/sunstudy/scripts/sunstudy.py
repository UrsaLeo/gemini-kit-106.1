import carb
import carb.input
import carb.settings
import omni.ext
import omni.usd
from omni.kit.environment.core import get_sunstudy_player
import omni.kit.actions.core

from .datetime_window import DateTimeWindow
from .location_window import LocationWindow
from .sunstudy_window import SunstudyWindowLayer

from omni.kit.viewport.registry import RegisterViewportLayer
import omni.kit.menu.utils
import omni.ui as ui

MENU_PATH = "Window"
_extension_instance = None

INIT_VISIBLE_SETTING_PATH = "/exts/omni.kit.environment.sunstudy/init_visible"


class SunStudyExtension(omni.ext.IExt):
    class WindowStub(ui.Window):
        def __init__(self, visible=True):
            flags = (
                ui.WINDOW_FLAGS_NO_TITLE_BAR |
                ui.WINDOW_FLAGS_NO_RESIZE |
                ui.WINDOW_FLAGS_NO_MOVE |
                ui.WINDOW_FLAGS_NO_SCROLLBAR |
                ui.WINDOW_FLAGS_NO_BACKGROUND |
                ui.WINDOW_FLAGS_NO_SCROLL_WITH_MOUSE |
                ui.WINDOW_FLAGS_NO_MOUSE_INPUTS |
                ui.WINDOW_FLAGS_NO_FOCUS_ON_APPEARING |
                ui.WINDOW_FLAGS_NO_DOCKING |
                ui.WINDOW_FLAGS_NO_CLOSE)

            super().__init__(
                SunstudyWindowLayer.WINDOW_NAME,
                position_x=-2,
                position_y=-2,
                width=1,
                height=1,
                flags=flags,
                auto_resize=False,
                visible=visible,
            )

            self.set_visibility_changed_fn(self._on_visibility_changed)

        def _on_visibility_changed(self, visible):
            main_window_layer = SunstudyWindowLayer.get_instance()
            if main_window_layer:
                main_window_layer.visible = visible
            omni.kit.menu.utils.refresh_menu_items(MENU_PATH)

        def is_visible(self):
            return self.visible

    def __init__(self):
        self._viewport_layer = None
        super().__init__()

    def on_startup(self, ext_id):
        global _extension_instance
        _extension_instance = self

        self._ext_id = ext_id

        settings = carb.settings.get_settings()
        init_visible = settings.get_as_bool(INIT_VISIBLE_SETTING_PATH)

        SunstudyWindowLayer.set_init_visible(init_visible)
        self._main_window = SunStudyExtension.WindowStub(init_visible)
        self._viewport_layer = RegisterViewportLayer(SunstudyWindowLayer, "omni.kit.environment.sunstudy.MainWindowLayer")

        self._location_window = LocationWindow(get_sunstudy_player())
        self._datetime_window = DateTimeWindow()

        self._location_window.set_ui_style("NvidiaDark")
        self._datetime_window.set_ui_style("NvidiaDark")

        for window_name in [SunstudyWindowLayer.WINDOW_NAME, LocationWindow.WINDOW_NAME, DateTimeWindow.WINDOW_NAME]:
            ui.Workspace.set_show_window_fn(
                window_name,
                lambda value: self._show_window(window_name, value),
            )

        self._register_actions()

        self._menu_entry = [
            omni.kit.menu.utils.MenuItemDescription(
                name=SunstudyWindowLayer.WINDOW_NAME,
                ticked_fn=self._main_window.is_visible,
                onclick_action=(self._ext_id, "toggle_main_window"),
                hotkey=(carb.input.KEYBOARD_MODIFIER_FLAG_CONTROL, carb.input.KeyboardInput.U),
            )]

        omni.kit.menu.utils.add_menu_items(self._menu_entry, name=MENU_PATH)

    def on_shutdown(self):
        global _extension_instance

        main_window_layer = SunstudyWindowLayer.get_instance()
        if main_window_layer:
            main_window_layer.destroy()
        self._viewport_layer = None

        omni.kit.menu.utils.remove_menu_items(self._menu_entry, MENU_PATH)

        self._datetime_window.destroy()
        self._datetime_window = None
        self._location_window.destroy()
        self._location_window = None

        _extension_instance = None

    def _register_actions(self):
        actions_tag = "Sunstudy Actions"

        omni.kit.actions.core.get_action_registry().register_action(
            self._ext_id,
            "show_window",
            lambda window_name, v=True: self._show_window(window_name, v),
            display_name="Window->Show Sunstudy",
            description="Show Sunstudy",
            tag=actions_tag,
        )

        omni.kit.actions.core.get_action_registry().register_action(
            self._ext_id,
            "hide_window",
            lambda window_name, v=False: self._show_window(window_name, v),
            display_name="Window->Hide Sunstudy Window",
            description="Hide Sunstudy",
            tag=actions_tag,
        )

        omni.kit.actions.core.get_action_registry().register_action(
            self._ext_id,
            "toggle_main_window",
            lambda window_name=SunstudyWindowLayer.WINDOW_NAME: self._toggle_window(window_name),
            display_name="Window->Toggle Sunstudy",
            description="Show Sunstudy",
            tag=actions_tag,
        )

    def _deregister_actions(extension_id):
        action_registry = omni.kit.actions.core.get_action_registry()
        action_registry.deregister_all_actions_for_extension(extension_id)

    def is_sunstudy_visible(self):
        main_window_layer = SunstudyWindowLayer.get_instance()
        if main_window_layer:
            return main_window_layer.visible

        return False

    def show_sunstudy(self):
        main_window_layer = SunstudyWindowLayer.get_instance()
        if main_window_layer:
            main_window_layer.visible = True
        return True

    def hide_sunstudy(self):
        main_window_layer = SunstudyWindowLayer.get_instance()
        if main_window_layer:
            main_window_layer.visible = False
        return False

    def is_datetime_visible(self):
        return self._datetime_window.is_visible()

    def show_datetime(self, right=0, top=0):
        self._datetime_window.show_align_to_right(right, top)
        # Return True for delay execute compatiable.
        return True

    def hide_datetime(self):
        self._datetime_window.show(False)

    def is_location_visible(self):
        return self._location_window.is_visible()

    def show_location(self, right=0, top=0):
        self._location_window.show_align_to_right(right, top)
        # Return True for delay execute compatiable.
        return True

    def hide_location(self):
        self._location_window.show(False)

    def _is_visible(self, window_name: str):
        window_instance = SunstudyWindowLayer.get_instance()
        if window_instance:
            return window_instance.visible
        else:
            return False

    def _show_window(self, window_name: str, show: bool):
        if window_name == SunstudyWindowLayer.WINDOW_NAME:
            self._main_window.visible = show
        elif window_name == LocationWindow.WINDOW_NAME:
            self._location_window.show(show)
        elif window_name == DateTimeWindow.WINDOW_NAME:
            self._datetime_window.show(show)
        else:
            carb.log_warn(f"Invalid window name to show window {window_name}")

    def _toggle_window(self, window_name: str):
        if window_name == SunstudyWindowLayer.WINDOW_NAME:
            new_visible = not self._main_window.visible
            self._main_window.visible = new_visible
        elif window_name == LocationWindow.WINDOW_NAME:
            self._location_window.show(not self._location_window.is_visible())
        elif window_name == DateTimeWindow.WINDOW_NAME:
            self._datetime_window.show(not self._datetime_window.is_visible())
        else:
            carb.log_warn(f"Invalid window name to toggle window {window_name}")


def get_instance():
    return _extension_instance
