import omni.ui as ui
import os
import subprocess
import asyncio
from omni.kit.window.popup_dialog import MessageDialog
import ul.gemini.chatbot as chatbot
from .styles import style_system, style_system_show_window
from omni.ui import color as cl
from .styles import style_system, style_system_show_window

base_path = os.path.join(os.path.dirname(__file__), "data", "icons")


# Used to add a simple button with the given clicked_fn to the toolbar
class SimpleClickAction:
    def __init__(self, name, icon, tooltip, clicked_fn):
        self.name = name
        self.icon = icon
        self.tooltip = tooltip
        self.clicked_fn = clicked_fn

    def build(self):
        global base_path
        ui.Button(
            "",
            tooltip=self.tooltip,
            clicked_fn=self.clicked_fn,
            image_url=os.path.join(base_path, self.icon),
            width=50,
            height=50,
        )


# Used to allow switching an extension on and off.
# Can optionallly provide an init functiion that will be called the first time the functionality is used
# Whether this initialization happens on click or when tool bar is created is defined in iniit_on_click
# When switching on extension, the windows in show_windows will be made visible and the windows in
# hide_windows will be made invisible, giving fine-grained control over the behaviour of the toolbar.


class ExtensionVisibilityAction:
    initialized = False
    extension_visible = False
    _simple_tool_bar = None
    _monitor_task = None

    def __init__(self, name, icon, tooltip, init_fn, show_windows, hide_windows, init_on_click=False):
        self.name = name
        self.show_windows = show_windows
        self.hide_windows = hide_windows
        self.icon = icon
        self.tooltip = tooltip
        self.init_fn = init_fn
        if not init_on_click and init_fn:
            init_fn()
            self.initialized = True

    async def async_init(self):
        self.init_fn()

    def init_fn(self):
        asyncio.ensure_future(self.async_init())

    def build(self):
        global base_path
        self.toolbarButton=ui.Button(
            "",
            tooltip=self.tooltip,
            clicked_fn=self.clicked_fn,
            image_url=os.path.join(base_path, self.icon),
            width=50,
            height=50,
            background_color= cl("#000000")
        )

    def clicked_fn(self):

        if not self.initialized and self.init_fn:
            self.init_fn()
            self.initialized = True

        if self.extension_visible:
            self.hide_extension_windows()

        else:
            self.show_extension_windows()

    def show_extension_windows(self):
        for window in self.show_windows:
            window = ui.Workspace.get_window(window)
            if window:
                window.visible = True

        # hide other windows
        for window in self.hide_windows:
            window = ui.Workspace.get_window(window)
            if window:
                if window.visible:
                    window.visible = False
        self.extension_visible = True

    def hide_extension_windows(self):
        if not self.show_windows:
            return
        for window in self.show_windows:
            window = ui.Workspace.get_window(window)
            if window:
                window.visible = False
        self.extension_visible = False

class Toolbar:

    _simple_toolbar = None

    _actions = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, trace):
        if self._simple_toolbar:
            self._simple_toolbar.visible = not self._simple_toolbar.visible  # TBD check this logic
        else:
            self._simple_toolbar = ui.ToolBar("simple toolbar", noTabBar=True)

            with self._simple_toolbar.frame:
                with ui.HStack(spacing=15, height=28,style=style_system):
                    ui.Spacer()
                    for action in self._actions:
                        print("action:" + str(action))
                        action.build()
                    with ui.HStack(spacing=5, height=50):
                        ui.Spacer()
                        with ui.HStack(spacing=5,style=style_system):
                            self.chatbot_label = ui.Label(
                                "AI Assist: How can I help?",
                                style={
                                    "color": cl.grey,
                                    "font_size": 16,
                                    "alignment": ui.Alignment.RIGHT_BOTTOM,
                                    "margin": 5,
                                },
                                width=ui.Percent(60),
                            )
                            self.chatbot_button = ui.Button(
                                "",
                                image_url=os.path.join(base_path, "AIAssist.png"),
                                height=50,
                                witth=50,
                                clicked_fn=self.show_chatbot_window,
                                style=style_system,
                            )

        self._simple_toolbar.dock_in_window("Viewport", ui.DockPosition.BOTTOM)
        self._simple_toolbar.frame.set_style({"Window": {"background_color": cl("#000000")}})
        print(exc_value)

    def extensionVisibilityAction(self, name, icon, tooltip, init_fn, show_windows, hide_windows, init_on_click=False):
        self._actions.append(
            ExtensionVisibilityAction(name, icon, tooltip, init_fn, show_windows, hide_windows, init_on_click)
        )

    def simpleClickAction(self, name, icon, tooltip, clicked_fn):
        self._actions.append(SimpleClickAction(name, icon, tooltip, clicked_fn))

    def show_chatbot_window(self):
        windows = ui.Workspace.get_windows()
        # print(f"windows object :{windows}")
        # Check if "AI Assist" window already exists
        window_name = "Gemini AI"
        ai_assist_window = next((window for window in windows if window.title == window_name), None)

        if ai_assist_window:
            ai_assist_window.visible = True

        else:
            # If the window does not exist, create a new one
            extension_instance = chatbot.MyExtension()
            extension_instance.on_startup(extension_instance)
            ai_assist_window = ui.Workspace.get_window(window_name)
            if ai_assist_window:
                ai_assist_window.visible = True

    # A Shortcut to add the quit application action
    def quitApplicationAction(self):
        self._actions.append(SimpleClickAction("Quit", "Quit.png", "Quit Application", self._quit_application))

    def _quit_application(self):
        print(ui.Workspace.get_windows())
        omniverse_processes = ["Kit.exe", "kit.exe"]
        for process in omniverse_processes:
            subprocess.call(["taskkill", "/f", "/im", process])
