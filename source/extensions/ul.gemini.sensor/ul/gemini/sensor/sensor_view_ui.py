import os

import omni.ui as ui
import ul.gemini.services.artifact_services as artifact_services
from omni.ui import color as cl
from .utils import get_real_data_twin, create_random_equipment, get_unique_value_keys


partner_secure_data = artifact_services.get_partner_secure_data()
eq_map = {}


if get_real_data_twin(partner_secure_data["twinVersionId"]):

    class Item(ui.AbstractItem):
        def __init__(self, data):
            super().__init__()
            self.data = data

            # Only for ed02afb1-ac52-4275-a1dd-c072487d9d16 twin
            unit_map = {
                "Blower1TotalHours": "Hrs",
                "Blower2TotalHours": "Hrs",
                "Blower3TotalHours": "Hrs",
                "Blower4TotalHours": "Hrs",
                "Blower6TotalHours": "Hrs",
                "Blower6PartialHours": "Pr/Hrs",
                "Blower3TotalHours": "Pr/Hrs",
                "PumpingConsumption": "m³",
                "SulzerFlow": "m³/h",
                "RedoxBiological1": "mV",
                "RedoxBiological2": "mV",
            }

            if data["readingType"] == "":
                self.type_model = ui.SimpleStringModel(unit_map.get(data["device_name"], "N/A"))
                self.reading_model = ui.SimpleStringModel(
                    f"{data['reading']:.2f} {unit_map.get(data['device_name'], 'N/A')}"
                )
            else:
                self.type_model = ui.SimpleStringModel(data["readingType"])
                self.reading_model = ui.SimpleStringModel(f"{data['reading']:.2f} {data['readingType']}")

            global eq_map
            self.eq_map = create_random_equipment(data)
            eq_map = self.eq_map

            self.name_model = ui.SimpleStringModel(data["device_name"])
            self.equipment_model = ui.SimpleStringModel(self.eq_map.get(data["device_name"], "N/A"))

        def get_data(self):
            return self.data

    class SensorModel(ui.AbstractItemModel):
        def __init__(self, sensor_data):
            super().__init__()
            self._children = [Item(data) for data in sensor_data]

        def get_item_children(self, item):
            if item is not None:
                return []
            return self._children

        def get_item_value_model_count(self, item):
            return 4

        def get_item_value_model(self, item, column_id):
            if column_id == 0:
                return item.name_model
            elif column_id == 1:
                return item.equipment_model
            elif column_id == 2:
                return item.name_model
            elif column_id == 3:
                return item.reading_model

        def get_reading_value_model(self, item):
            return item.reading_model

        def get_map_model(self, item):
            return item.eq_map

        def sort_data(self, column_id, ascending=True):
            if column_id == 0:
                key = lambda item: item.data["device_name"]

            elif column_id == 1:
                key = lambda item: item.equimment_model.as_string

            elif column_id == 2:
                key = lambda item: item.data["description"]

            elif column_id == 3:
                key = lambda item: item.data["reading"]

            self._children.sort(key=key, reverse=not ascending)

    class SensorDelegate(ui.AbstractItemDelegate):
        def __init__(
            self,
            sensor_callback,
            sort_and_reload_table,
            equipment_sensor_callback,
            filter_callback,
            checked_devices
        ):
            super().__init__()
            self._sensor_callback = sensor_callback
            self._equipment_sensor_callback = equipment_sensor_callback
            self._sort_and_reload_table = sort_and_reload_table
            self._filter_callback = filter_callback
            self._equipment_paths = None

            self.menu_visible = False
            self._checked_devices = checked_devices
            self.image_visible = ui.SimpleBoolModel(True)

        def get_paths(self):
            return self._equipment_paths

        def _get_column_name(self, column_id):
            if column_id == 0:
                return "Zoom"
            elif column_id == 1:
                return "Equipment"
            elif column_id == 2:
                return "Device name"
            elif column_id == 3:
                return "Current Reading"

        def build_branch(
            self, model: ui.AbstractItemModel, item: ui.AbstractItem, column_id: int, level: int, expanded: bool
        ):
            pass

        def sensor_callback(self, value_model, reading_value):
            name = value_model.as_string
            value = reading_value.as_string
            self._sensor_callback(name, value)

        def show_pushed_menu(
            self, x, y, button, modifier, widget, data, value_model, reading_value, _map
        ):
            """Displays context menu with two zoom options"""

            self.pushed_menu = ui.Menu(
                "Zoom menu",
                style={
                    "Menu": {
                        "background_color": cl.grey,
                        "color": cl.pink,
                        "background_selected_color": cl.black,
                        "border_radius": 5,
                        "border_width": 2,
                        "border_color": cl.white,
                        "padding": 15,
                    },
                    "MenuItem": {
                        "color": cl.white,
                        "background_selected_color": cl.black,
                    },
                    "Separator": {"color": cl.red},
                },
            )
            with self.pushed_menu:
                unique_map = get_unique_value_keys(_map)

                ui.MenuItem(
                    "Zoom to Sensor",
                    triggered_fn=lambda: self._sensor_callback(
                        name=value_model.as_string, value=reading_value.as_string
                    ),
                )
                ui.MenuItem(
                    "Zoom to Equipment",
                    triggered_fn=lambda: (
                        self._equipment_sensor_callback(
                            name=value_model.as_string, value=reading_value.as_string
                        )
                        if value_model.as_string.replace('_', '-') and value_model.as_string not in unique_map
                        else self._sensor_callback(
                            name=value_model.as_string, value=reading_value.as_string
                        )
                    ),
                )

            self.pushed_menu.show_at(
                (int)(widget.screen_position_x), (int)(widget.screen_position_y + widget.computed_content_height)
            )

        def build_widget(
            self, model: SensorModel, item: ui.AbstractItem, column_id: int, level: int, expanded: bool
        ):
            value_model = model.get_item_value_model(item, column_id)
            reading_value = model.get_reading_value_model(item)
            map_value = model.get_map_model(item)

            rectangle_style = {
                "border_color": cl.white,
                "background_color": cl.black,
                "border_width": 1,
                "margin": 0,
            }
            label_style = {
                "font_size": 14,
                "color": cl.white,
            }

            with ui.HStack():
                if column_id == 0:
                    with ui.VGrid(row_height=25):
                        with ui.ZStack():
                            ui.Rectangle(style=rectangle_style)
                            button = ui.Button(
                                image_url=os.path.join(os.path.dirname(__file__), "photo", "zoom-focus.png"),
                                clicked_fn=lambda: self.show_pushed_menu(
                                    0, 0, None, None, button, item.data, value_model, reading_value, map_value
                                ),
                            )
                            button.set_mouse_pressed_fn(
                                lambda x, y, b, m, widget=button: self.show_pushed_menu(
                                    x, y, b, m, widget, item.data, value_model, reading_value, map_value
                                )
                            )

                else:
                    with ui.VGrid(row_height=25):
                        with ui.ZStack():
                            ui.Rectangle(style=rectangle_style)
                            if column_id == 1:
                                ui.Label(
                                    value_model.as_string,
                                    alignment=ui.Alignment.CENTER
                                )

                            elif column_id == 2:
                                ui.Label(
                                    value_model.as_string,
                                    alignment=ui.Alignment.CENTER
                                )
                            else:
                                ui.Label(value_model.as_string, alignment=ui.Alignment.CENTER, style=label_style)

        def _create_device_filter_dropdown(self, x, y, button, modifier, widget, col):
            """Creates dropdown menu for device filtering,
            when triangle button is clicked in build_header"""

            if self.menu_visible:
                self.filter_menu.hide()
                self.menu_visible = False
                return

            self.filter_menu = ui.Menu("Filter menu", resizable=False, width=800)

            # col will be used later for implementing filter by equipment
            print("Filter column number", col)

            with self.filter_menu:
                with ui.VStack(spacing=25):
                    max_label_len = max([len(dev) for dev in eq_map])

                    for dev in eq_map:
                        checkbox_model = ui.SimpleBoolModel(dev in self._checked_devices)
                        with ui.HStack(spacing=125):
                            ui.Label(
                                dev if max_label_len < 20 else dev[:15] + "...",
                                width=150,
                                height=25,
                                style={"font_size": 14},
                                alignment=ui.Alignment.LEFT
                            )
                            ui.CheckBox(
                                model=checkbox_model,
                                style={
                                    "min_width": 30,
                                    "min_height": 30,
                                    "background_color": cl(170, 170, 170),
                                    "color": cl.black
                                },
                                alignment=ui.Alignment.RIGHT
                            )

                        checkbox_model.add_value_changed_fn(
                            lambda model=checkbox_model, dev=dev: self._filter_callback(
                                model, dev, self._checked_devices
                            )
                        )

            self.filter_menu.show_at(
                (int)(widget.screen_position_x),
                (int)(widget.screen_position_y + widget.computed_content_height)
            )
            self.menu_visible = True

        def build_header(self, column_id):
            rectangle_style = {
                "border_color": cl.white,
                "border_width": 1,
                "margin": 0,
            }
            label_style = {
                "font_size": 14,
                "color": cl.white,
            }

            with ui.VGrid(row_height=25):
                with ui.ZStack():
                    ui.Rectangle(style=rectangle_style)

                    with ui.HStack(spacing=0):
                        ui.Button(
                            self._get_column_name(column_id),
                            alignment=ui.Alignment.CENTER,
                            style=label_style,
                            spacing=0,
                            clicked_fn=lambda col=column_id: self._sort_and_reload_table(col),
                        )
                        if column_id == 2:
                            button = ui.Button(
                                image_url=os.path.join(os.path.dirname(__file__), "photo", "down-chevron.png"),
                                style={
                                    "font_size": 16,
                                    "margin": 2,
                                    "width": 0,
                                },
                                width=25,
                                spacing=0,
                                clicked_fn=lambda: self._create_device_filter_dropdown(
                                        0, 0, None, None, button, column_id
                                    ),

                            )
                            button.set_mouse_pressed_fn(
                                lambda x, y, b, m, widget=button, col=column_id: self._create_device_filter_dropdown(
                                    x, y, b, m, widget, col
                                )
                            )


else:
    class Item(ui.AbstractItem):
        def __init__(self, data):
            super().__init__()
            self.data = data
            self.name_model = ui.SimpleStringModel(data["name"])
            self.type_model = ui.SimpleStringModel(data["readingType"])
            self.reading_model = ui.SimpleStringModel(f"{data['reading']:.2f} {data['readingType']}")

            self.eq_map = create_random_equipment(data)
            global eq_map
            eq_map = self.eq_map

            # It sets the same equipment to every entry, since there are only two mock entries
            self.eq_map = {key: "Equipment2" for key, _ in self.eq_map.items() if len(self.eq_map) < 3}

            self.name_model = ui.SimpleStringModel(data["device_name"])
            self.equipment_model = ui.SimpleStringModel(self.eq_map.get(data["device_name"], "N/A"))

        def get_data(self):
            return self.data


    class SensorModel(ui.AbstractItemModel):
        def __init__(self, sensor_data):
            super().__init__()
            self._children = [Item(data) for data in sensor_data]

        def get_item_children(self, item):
            if item is not None:
                return []
            return self._children

        def get_item_value_model_count(self, item):
            return 4

        def get_item_value_model(self, item, column_id):
            if column_id == 0:
                return item.name_model
            elif column_id == 1:
                return item.equipment_model
            elif column_id == 2:
                return item.name_model
            elif column_id == 3:
                return item.reading_model

        def get_reading_value_model(self, item):
            return item.reading_model

        def get_map_model(self, item):
            return item.eq_map

        def sort_data(self, column_id, ascending=True):
            if column_id == 0:
                key = lambda item: item.data["device_name"]

            elif column_id == 1:
                key = lambda item: item.equimment_model.as_string

            elif column_id == 2:
                key = lambda item: item.data["description"]

            elif column_id == 3:
                key = lambda item: item.data["reading"]

            self._children.sort(key=key, reverse=not ascending)

    class SensorDelegate(ui.AbstractItemDelegate):
        def __init__(
            self,
            sensor_callback,
            sort_and_reload_table,
            equipment_sensor_callback,
            filter_callback,
            checked_devices
        ):
            super().__init__()
            self._sensor_callback = sensor_callback
            self._equipment_sensor_callback = equipment_sensor_callback
            self._sort_and_reload_table = sort_and_reload_table
            self._equipment_paths = None

            self._filter_callback = filter_callback

            self.menu_visible = False
            self._checked_devices = checked_devices

        def get_paths(self):
            return self._equipment_paths

        def _get_column_name(self, column_id):
            if column_id == 0:
                return "Zoom"
            elif column_id == 1:
                return "Equipment"
            elif column_id == 2:
                return "Device name"
            elif column_id == 3:
                return "Current Reading"

        def build_branch(
            self, model: ui.AbstractItemModel, item: ui.AbstractItem, column_id: int, level: int, expanded: bool
        ):
            pass

        def sensor_callback(self, value_model, reading_value):
            name = value_model.as_string
            value = reading_value.as_string
            self._sensor_callback(name, value)

        def show_pushed_menu(
            self, x, y, button, modifier, widget, data, value_model, reading_value, _map
        ):
            """Displays context menu with two zoom options"""

            self.pushed_menu = ui.Menu(
                "Zoom menu",
                style={
                    "Menu": {
                        "background_color": cl.grey,
                        "color": cl.pink,
                        "background_selected_color": cl.black,
                        "border_radius": 5,
                        "border_width": 2,
                        "border_color": cl.white,
                        "padding": 15,
                    },
                    "MenuItem": {
                        "color": cl.white,
                        "background_selected_color": cl.black,
                    },
                    "Separator": {"color": cl.red},
                },
            )

            with self.pushed_menu:
                unique_map = get_unique_value_keys(_map)

                ui.MenuItem(
                    "Zoom to Sensor",
                    triggered_fn=lambda: self._sensor_callback(
                        name=value_model.as_string, value=reading_value.as_string
                    ),
                )
                ui.MenuItem(
                    "Zoom to Equipment",
                    triggered_fn=lambda: (
                        self._equipment_sensor_callback(
                            name=value_model.as_string, value=reading_value.as_string
                        )
                        if value_model.as_string.replace('_', '-') and value_model.as_string not in unique_map
                        else self._sensor_callback(
                            name=value_model.as_string, value=reading_value.as_string
                        )
                    ),
                )

            self.pushed_menu.show_at(
                (int)(widget.screen_position_x),
                (int)(widget.screen_position_y + widget.computed_content_height)
            )

        def build_widget(
            self, model: SensorModel, item: ui.AbstractItem, column_id: int, level: int, expanded: bool
        ):
            value_model = model.get_item_value_model(item, column_id)
            reading_value = model.get_reading_value_model(item)
            map_value = model.get_map_model(item)

            rectangle_style = {
                "border_color": cl.white,
                "background_color": cl.black,
                "border_width": 1,
                "margin": 0,
            }

            label_style = {
                "font_size": 14,
                "color": cl.white,
            }

            with ui.HStack():
                if column_id == 0:
                    with ui.VGrid(row_height=25):
                        with ui.ZStack():
                            ui.Rectangle(style=rectangle_style)
                            button = ui.Button(
                                image_url=os.path.join(os.path.dirname(__file__), "photo", "zoom-focus.png"),
                                clicked_fn=lambda: self.show_pushed_menu(
                                    0, 0, None, None, button, item.data, value_model, reading_value, map_value
                                ),
                            )
                            button.set_mouse_pressed_fn(
                                lambda x, y, b, m, widget=button: self.show_pushed_menu(
                                    x, y, b, m, widget, item.data, value_model, reading_value, map_value
                                )
                            )

                else:
                    with ui.VGrid(row_height=25):
                        with ui.ZStack():
                            ui.Rectangle(style=rectangle_style)
                            if column_id == 1:
                                ui.Label(
                                    value_model.as_string,
                                    alignment=ui.Alignment.CENTER
                                )

                            elif column_id == 2:
                                ui.Label(
                                    value_model.as_string,
                                    alignment=ui.Alignment.CENTER
                                )
                            else:
                                ui.Label(value_model.as_string, alignment=ui.Alignment.CENTER, style=label_style)

        def _create_device_filter_dropdown(self, x, y, button, modifier, widget, col):
            """Creates dropdon menu for device filtering,
            when triangle button is clicked in build_header"""

            if self.menu_visible:
                self.filter_menu.hide()
                self.menu_visible = False
                return

            self.filter_menu = ui.Menu("Filter menu", resizable=False, width=800)

            with self.filter_menu:
                with ui.VStack(spacing=25):
                    max_label_len = max([len(dev) for dev in eq_map])

                    for dev in eq_map:
                        checkbox_model = ui.SimpleBoolModel(dev in self._checked_devices)
                        with ui.HStack(spacing=125):
                            ui.Label(
                                dev if max_label_len < 20 else dev[:15] + "...",
                                width=150,
                                height=25,
                                style={"font_size": 14},
                                alignment=ui.Alignment.LEFT
                            )
                            ui.CheckBox(
                                model=checkbox_model,
                                style={
                                    "min_width": 30,
                                    "min_height": 30,
                                    "background_color": cl(170, 170, 170),
                                    "color": cl.black
                                },
                                alignment=ui.Alignment.RIGHT,

                            )

                        checkbox_model.add_value_changed_fn(
                            lambda model=checkbox_model, dev=dev: self._filter_callback(
                                model, dev, self._checked_devices
                            )
                        )

            self.filter_menu.show_at(
                (int)(widget.screen_position_x),
                (int)(widget.screen_position_y + widget.computed_content_height)
            )
            self.menu_visible = True

        def build_header(self, column_id):
            rectangle_style = {
                "border_color": cl.white,
                "border_width": 1,
                "margin": 0,
            }
            label_style = {
                "font_size": 14,
                "color": cl.white,
            }

            with ui.VGrid(row_height=25):
                with ui.ZStack():
                    ui.Rectangle(style=rectangle_style)

                    with ui.HStack(spacing=0):
                        ui.Button(
                            self._get_column_name(column_id),
                            alignment=ui.Alignment.CENTER,
                            style=label_style,
                            spacing=0,
                            clicked_fn=lambda col=column_id: self._sort_and_reload_table(col),
                        )
                        if column_id == 2:
                            button = ui.Button(
                                image_url=os.path.join(os.path.dirname(__file__), "photo", "down-chevron.png"),
                                style={
                                    "font_size": 16,
                                    "margin": 2,
                                    "width": 0,
                                },
                                width=25,
                                spacing=0,
                                clicked_fn=lambda: self._create_device_filter_dropdown(
                                        0, 0, None, None, button, column_id
                                    ),

                            )
                            button.set_mouse_pressed_fn(
                                lambda x, y, b, m, widget=button, col=column_id: self._create_device_filter_dropdown(
                                    x, y, b, m, widget, col
                                )
                            )
