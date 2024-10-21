import re
import carb.input
import omni.ext
import omni.usd
import omni.ui as ui
import asyncio
from omni.ui import color as cl
import ul.gemini.services.sensor_data_services as sensor_services

# from confluent_kafka import Consumer
from ul.gemini.sensor.sensor_view_ui import SensorModel, SensorDelegate
import json
import carb.events
import omni.kit.app
import threading
from omni.kit.viewport.utility import get_active_viewport_window
import omni.kit.commands
from kafka import KafkaConsumer
from omni.kit.viewport.utility import get_active_viewport
import ul.gemini.services.artifact_services as artifact_services
import random
import time
import logging
import carb.settings
import operator
from .viewport_scene import ViewportSceneInfo
from .db import ping_and_aggregate
from .utils import (
    get_kafka_topic,
    get_real_data_twin,
    create_random_equipment,
    safe_eval
)

print(f"Log file path: {carb.settings.get_settings().get('/log/file')}")
logger = logging.getLogger(__name__)


logger.info("Starting sensor extension")
extension_instance = None
partner_secure_data = artifact_services.get_partner_secure_data()
topic = get_kafka_topic(partner_secure_data)

# Flag to check if there are Kafka messages
MESSAGE_VALUE = None


def push_message_to_kafka_event():
    """
    This function listens to the Kafka topic and pushes the messages to the Kafka event.

    I already have another solution using async kafka, so we don't need to have thread for kafka.
    It is not recommended to use it, because it can make problems because of GIL

    """
    unique_group_id = f"my-group-id-{int(time.time())}"

    consumer = KafkaConsumer(
        topic,
        bootstrap_servers="52.21.129.119:9092",
        group_id=unique_group_id,
        security_protocol="SASL_PLAINTEXT",
        sasl_mechanism="PLAIN",
        sasl_plain_username="admin",
        sasl_plain_password="admin-secret",
        auto_offset_reset="latest",
        enable_auto_commit=False,
    )

    for msg in consumer:
        message_value = msg.value.decode("utf-8")
        global MESSAGE_VALUE
        MESSAGE_VALUE = message_value

        try:
            message_json = json.loads(message_value)
            #message_json = {}
            if extension_instance:
                extension_instance._kafka_messages = message_json
                extension_instance._bus.push(
                    extension_instance._KAFKA_EVENT, payload={"data": extension_instance._kafka_messages}
                )
        except json.JSONDecodeError as e:
            print(f"Failed to decode JSON message {e}")
            if extension_instance:
                extension_instance._kafka_messages = []


try:
    listener_thread = threading.Thread(target=push_message_to_kafka_event)
    listener_thread.daemon = True
    listener_thread.start()
    logger.info("CHILD THREAD STARTED")

except Exception as e:
    logger.error("Thread failure")


class MyExtension(omni.ext.IExt):
    def __init__(self):
        super().__init__()
        self.usd_context = omni.usd.get_context()

        self._sensor_window = None
        self._search_text = None
        self.distance = None
        self._sorted_device_kafka_messages = None
        self._sorted_reading_kafka_messages = None
        self._sorted_equipment = None
        self._flag = None
        self._filter = None

        if topic == "my_topic1":
            # For testing purposes, not affecting anything
            self._kafka_messages = [
                {
                    "device_id": "fa3c3400-1ce6-11ef-9039-4ff2c1f6b217",
                    "device_name": "humidity",
                    "name": "humidity",
                    "type": "rh",
                    "reading": random.uniform(30.0, 60.0),
                    "status": "SEVERE",
                    "readingType": "%",
                },
                {
                    "device_id": "fa3c3400-1ce6-11ef-9039-4ff2c1f6b217",
                    "device_name": "temperature",
                    "name": "temperature",
                    "type": "temp",
                    "reading": random.uniform(20.0, 30.0),
                    "status": "NORMAL",
                    "readingType": "°F",
                },
            ]

        else:
            self._kafka_messages = []
        self._KAFKA_EVENT = carb.events.type_from_string("KAFKA_EVENT")
        self._bus = omni.kit.app.get_app().get_message_bus_event_stream()
        self._sub1 = self._bus.create_subscription_to_push_by_type(self._KAFKA_EVENT, self.on_event)

        self.update_stream = omni.kit.app.get_app().get_update_event_stream()
        self.update_subscription = self.update_stream.create_subscription_to_pop(
            self.on_sensor_data_update, name="=SensorDataUpdate"
        )

        self.stage_stream = omni.usd.get_context().get_stage_event_stream()
        self._stage_subscription = self.stage_stream.create_subscription_to_pop(
            self.on_sensor_data_update, name="MyExtensionOnStageEvent1"
        )

        self._viewport = get_active_viewport_window()
        self._extension_id = None
        self.sensor_name = None
        self.random_sensor_data = True
        self._sort_ascending = True
        self._sort_column = None
        self._db_messages = None
        self._path_mapping = sensor_services.load_mapping_file()

        self._equipment_map = None
        self._filtered_messages = self._kafka_messages.copy()
        self._current_filter = None
        self.checked_devices = []

    def _process_and_sort_messages(self, message_list):
        """Returns sorted messages"""

        for message in message_list:
            self._equipment_map = create_random_equipment(message)

        kafka_with_equipment = [
            message | {"equipment": self._equipment_map.get(message["device_name"], "N/A")}
            for message in message_list if message is not None
        ]

        # We sort by equipment only in real data twins
        if get_real_data_twin(partner_secure_data["twinVersionId"]):
            self._sorted_equipment = sorted(
                kafka_with_equipment, key=lambda x: x["equipment"], reverse=not self._sort_ascending
            )

        self._sorted_device_kafka_messages = sorted(
            message_list, key=lambda x: x["device_name"], reverse=not self._sort_ascending
        )

        self._sorted_reading_kafka_messages = sorted(
            message_list, key=lambda x: x["reading"], reverse=not self._sort_ascending
        )


    def on_sensor_data_update(self, event: carb.events.IEvent):
        """
        Creating custom event so we can update manipulator every time we have a new data entry in kafka
        """

        if self._sensor_window and self._sensor_window.visible:
            if len(self._kafka_messages) > 0:
                if get_real_data_twin(partner_secure_data["twinVersionId"]):
                    value = next(
                        (
                            entry["reading"]
                            for entry in self._kafka_messages
                            if entry["device_name"] == self.sensor_name
                        ),
                        "0.00",
                    )
                else:
                    value = next(
                        (
                            entry["reading"]
                            for entry in self._kafka_messages
                            if entry["name"] == self.sensor_name
                        ),
                        "0.00",
                    )
                try:
                    self.viewport_scene.set_sensor_data(str(value))
                    self.viewport_scene.set_kafka_message(self._kafka_messages)

                    stage = self.usd_context.get_stage()

                    # Set metadata from kafka
                    selected_prim_paths = self.usd_context.get_selection().get_selected_prim_paths()

                    for prim_path in selected_prim_paths:
                        prim = stage.GetPrimAtPath(prim_path)

                        if self._kafka_messages:
                            for message in self._kafka_messages:
                                device_name = message.get("device_name")

                                new_device_name = device_name.replace('-', '_')

                                if get_real_data_twin(partner_secure_data["twinVersionId"]):
                                    if new_device_name == prim_path.split("/")[-1]:
                                        prim.SetCustomData(
                                            {
                                                "device_name": new_device_name,
                                                "reading": message["reading"],
                                                "readingType": message["readingType"],
                                            }
                                        )

                                else:
                                    json_object = sensor_services.get_json_object(
                                        partner_secure_data["twinVersionId"],
                                        prim_path.split("/")[-1],
                                        self._path_mapping
                                        )

                                    if json_object:
                                        if json_object["sensorName"] == message["device_name"]:
                                            prim.SetCustomData(
                                                {
                                                    "device_name": new_device_name,
                                                    "reading": message["reading"],
                                                    "readingType": message["readingType"],
                                                }
                                            )

                except Exception as e:
                    print(f"Ext error: {e}")
                    logger.error(e)

        if event.type == int(omni.usd.StageEventType.ASSETS_LOADED):
            stage = self.usd_context.get_stage()

            # Set metadata from db on startup
            folder = stage.GetPrimAtPath("/World/Twins/Building/Sensors")
            children = folder.GetAllChildren()

            if get_real_data_twin(partner_secure_data["twinVersionId"]):
                for child in children:
                    child_path = child.GetPath().pathString

                    if self._db_messages:
                        for message in self._db_messages:
                            device_name = message.get("device_name")

                            new_device_name = device_name.replace('-', '_')

                            if new_device_name in child_path:
                                child.SetCustomData(
                                    {
                                        "device_name": new_device_name,
                                        "reading": message["reading"],
                                        "readingType": message["readingType"],
                                    }
                                )

            else:
                if self._kafka_messages:
                    for child in children:
                        child_path = child.GetPath().pathString
                        for message in self._kafka_messages:
                            device_name = message.get("device_name")

                            new_device_name = device_name.replace('-', '_')
                            json_object = sensor_services.get_json_object(
                                partner_secure_data["twinVersionId"],
                                child_path.split("/")[-1],
                                self._path_mapping
                                )

                            if json_object:
                                if json_object["sensorName"] == message["device_name"]:
                                    child.SetCustomData(
                                        {
                                            "device_name": new_device_name,
                                            "reading": message["reading"],
                                            "readingType": message["readingType"],
                                        }
                                    )

    def on_event(self, event):
        """
        This function listens to the Kafka event and updates the sensor window with the new data.
        """

        self._kafka_messages = event.payload["data"]

        # If something is typed in search field, filter by reading is applied
        if self._current_filter and not self._filter:
            self._search_by_reading()

        # If any checkboxes are clicked in filter by device menu, filter_by device is applied
        if self._filter:
            self._filtered_messages = [
            msg for msg in self._kafka_messages
            if msg["device_name"] in self.checked_devices
            ]
            if self._current_filter:
                self._search_by_reading()

        if not self._current_filter and not self._filter:
            self._filtered_messages = self._kafka_messages.copy()

        self._process_and_sort_messages(self._filtered_messages)

        if self._sensor_window and self._sensor_window.visible:
            try:
                self._open_sensor_window()
            except Exception as e:
                logger.error(e)
                logger.error("Too many renders of the window.")

    def _window_header(self):
        """
        Header for sensor window, later i will implement search functionality here(some day :D)
        """

        ui.Label("Sensors", style={"font_size": 20, "margin": 2.0}, alignment=ui.Alignment.CENTER)
        with ui.HStack(height=20):
            self._search_text = ui.StringField(
                style={"margin": 2, "border_radius": 4}
            )
            model = self._search_text.model
            model.set_value("Search by reading, use >, <")

            model.add_value_changed_fn(self._search_by_reading)

        ui.Line(style={"color": cl.grey, "border_width": 2}, alignment=ui.Alignment.BOTTOM)
        ui.Spacer(height=4)

    def _search_by_reading(self, *args):
        allowed_operators = {
            ">": operator.gt,
            "<": operator.lt,
        }

        filter_text = self._search_text.model.get_value_as_string()
        pattern = r"[\s]*[<>][\s]*\d+"

        if filter_text and any(
                op in filter_text for op in allowed_operators
            ) and re.search(pattern, filter_text):

            try:
                filter_text = filter_text.replace(">", " reading > ")
                filter_text = filter_text.replace("<", " reading < ")

                if MESSAGE_VALUE:
                    if self._filter:
                        self._filtered_messages = [
                        msg for msg in self._filter
                        if safe_eval(filter_text, msg["reading"])
                        ]
                        self._current_filter = filter_text
                    else:
                        self._filtered_messages = [
                            msg for msg in self._kafka_messages
                            if safe_eval(filter_text, msg["reading"])
                        ]
                        self._current_filter = filter_text

                    self._process_and_sort_messages(self._filtered_messages)

                if not MESSAGE_VALUE:
                    if self._filter:
                        self._filtered_messages = [
                        msg for msg in self._filter
                        if safe_eval(filter_text, msg["reading"])
                    ]
                    else:
                        self._filtered_messages = [
                        msg for msg in self._db_messages
                        if safe_eval(filter_text, msg["reading"])
                    ]

                    self._current_filter = filter_text
                    self._process_and_sort_messages(self._filtered_messages)


            except ValueError:
                print("Invalid filter expression")

        else:
            self._filtered_messages = self._filter if self._filter else self._kafka_messages.copy()
            self._sorted_reading_kafka_messages = self._filtered_messages
            self._sorted_device_kafka_messages = self._filtered_messages
            if get_real_data_twin(partner_secure_data["twinVersionId"]):
                self._sorted_equipment = self._filtered_messages
            self._current_filter = ""

        self._open_sensor_window()

    def _filter_by_device_callback(self, model, dev, checked_devices):
        """Called whenever the checkbox value changes"""

        is_checked = model.get_value_as_bool()

        if is_checked:
            if dev not in checked_devices:
                checked_devices.append(dev)

        else:
            if dev in checked_devices:
                checked_devices.remove(dev)

        self.checked_devices = checked_devices

        if len(self.checked_devices):
            self._filtered_messages = [
                msg for msg in self._kafka_messages
                if msg["device_name"] in self.checked_devices
            ]

            self._filter = self._filtered_messages.copy()
            self._process_and_sort_messages(self._filtered_messages)

        else:
            self._filtered_messages = self._kafka_messages.copy()
            self._sorted_reading_kafka_messages = self._filtered_messages
            self._sorted_device_kafka_messages = self._filtered_messages
            if get_real_data_twin(partner_secure_data["twinVersionId"]):
                self._sorted_equipment = self._filtered_messages
            self._filter = None

        self._open_sensor_window()

    def _sensor_selection_callback(self, name, value):
        """
        This function is called when a sensor is selected from the sensor window
        We have a lot of "if" statements here, because we have two different types of twins
        First solution has real data from kharon/iot devices, and the second one has some random data

        First solution has a logic for finding the path of the sensor,
        while the second one collecting path for each sensor from json inside of services
        """

        logger.info("Calling sensor selection callback!!")
        global partner_secure_data
        self.sensor_name = name

        logger.info(f"Selection of sensor name = {name}, value={value}")
        if self._extension_id is not None and self._viewport is not None:
            self.viewport_scene.set_sensor_name(name)

            sensor_camera = sensor_services.get_sensor_camera_path(
                partner_secure_data["twinVersionId"], name
            )

            if get_real_data_twin(partner_secure_data["twinVersionId"]):
                path = f"/World/Twins/Building/Sensors/{self.sensor_name.replace('-', '_')}"

            else:
                path = sensor_services.get_path_for_sensor(partner_secure_data["twinVersionId"], name)

            if path:
                if sensor_camera:
                    logger.info(f"PATH PLEASE ZOOM IN = {path}")
                    active_viewport = get_active_viewport()
                    camera_path = active_viewport.camera_path
                    logger.info(f"Camera path: {camera_path}")
                    time = active_viewport.time
                    resolution = (1, 1)
                    resolution = active_viewport.resolution
                    zoom = 10
                    prim_to_move = sensor_camera
                    active_viewport.camera_path = prim_to_move
                else:
                    logger.info(f"PATH PLEASE ZOOM IN = {path}")
                    active_viewport = get_active_viewport()
                    camera_path = active_viewport.camera_path
                    logger.info(f"Camera path: {camera_path}")
                    time = active_viewport.time
                    resolution = (1, 1)
                    resolution = active_viewport.resolution
                    zoom = 15
                    prim_to_move = "/OmniverseKit_Persp"
                    active_viewport.camera_path = prim_to_move

                logger.info("CURRENT SELECTED PATHS")
                prim_path = omni.usd.get_context().get_selection().get_selected_prim_paths()
                logger.info(f"SELECTED CURRENT PATH {prim_path}")

                omni.kit.commands.execute(
                    "FramePrimsCommand",
                    prim_to_move=prim_to_move,
                    prims_to_frame=[path],
                    time_code=time,
                    aspect_ratio=resolution[0] / resolution[1],
                    zoom=zoom,
                )
                logger.info(f"PATH PLEASE ZOOM IN BEFORE = {path}")
                omni.usd.get_context().get_selection().set_selected_prim_paths([path], True)
                logger.info(f"PATH PLEASE ZOOM IN AFTER = {path}")
            else:
                logger.info("NO PATH MAPPING HENCE NOT ZOOMING")

    def _equipment_sensor_selection_callback(self, name, value):
        """This function is called, when we click Zoom to Equipment menu item"""

        for message in self._kafka_messages:
            utils_equipment_map = create_random_equipment(message)

        sensor_camera = sensor_services.get_sensor_camera_path(
            partner_secure_data["twinVersionId"], name
        )

        if get_real_data_twin(partner_secure_data["twinVersionId"]):
            clicked_equipment = [
                f"/World/Twins/Building/Sensors/{dev.replace('-', '_')}"
                for dev, equipment in utils_equipment_map.items()
                if equipment == utils_equipment_map[name]
            ]

            zoom_value = 0.3

        else:
            zoom_value = 0.5

            json_object_paths = sensor_services.get_all_json_objects_paths(
                partner_secure_data["twinVersionId"], self._path_mapping
            )

            clicked_equipment = json_object_paths

        if clicked_equipment:
            if sensor_camera:
                active_viewport = get_active_viewport()
                camera_path = active_viewport.camera_path
                logger.info(f"Camera path: {camera_path}")
                time = active_viewport.time
                resolution = (1, 1)
                resolution = active_viewport.resolution
                zoom = zoom_value
                prim_to_move = sensor_camera
                active_viewport.camera_path = prim_to_move

            else:
                active_viewport = get_active_viewport()
                camera_path = active_viewport.camera_path
                logger.info(f"Camera path: {camera_path}")
                time = active_viewport.time
                resolution = (1, 1)
                resolution = active_viewport.resolution
                zoom = zoom_value
                prim_to_move = "/OmniverseKit_Persp"
                active_viewport.camera_path = prim_to_move

            logger.info("CURRENT SELECTED PATHS")
            prim_path = omni.usd.get_context().get_selection().get_selected_prim_paths()
            logger.info(f"SELECTED CURRENT PATH {prim_path}")

            omni.kit.commands.execute(
                "FramePrimsCommand",
                prim_to_move=prim_to_move,
                prims_to_frame=clicked_equipment,
                time_code=time,
                aspect_ratio=resolution[0] / resolution[1],
                zoom=zoom,
            )
            omni.usd.get_context().get_selection().set_selected_prim_paths(clicked_equipment, True)
        else:
            logger.info("NO PATH MAPPING HENCE NOT ZOOMING")

    def _sort_and_reload_table(self, column_id, apply_sorting_only=False):
        """
        This function sorts the table based on the column_id.
        Args:
            column_id:
            apply_sorting_only:

        Returns:
            sorted kafka messages

        """

        self._sort_ascending = not self._sort_ascending

        if column_id == 1:
            for message in self._filtered_messages:
                self._equipment_map = create_random_equipment(message)

            kafka_with_equipment = [
                message | {"equipment": self._equipment_map.get(message["device_name"], "N/A")}
                for message in self._filtered_messages if message is not None
            ]

            if get_real_data_twin(partner_secure_data["twinVersionId"]):
                self._sorted_equipment = sorted(
                    kafka_with_equipment, key=lambda x: x["equipment"], reverse=not self._sort_ascending
                )
                self._flag = 1

        if column_id == 2:
            self._sorted_device_kafka_messages = sorted(
                self._filtered_messages, key=lambda x: x["device_name"], reverse=not self._sort_ascending
            )
            self._flag = 2


        elif column_id == 3:
            self._sorted_reading_kafka_messages = sorted(
                self._filtered_messages, key=lambda x: x["reading"], reverse=not self._sort_ascending
            )
            self._flag = 3

        self._sort_column = column_id


        if not apply_sorting_only:
            self._open_sensor_window()

    def _create_table_view(self):
        """
        This function creates the table view for the sensor window.
        We are using Treeview for creating table here
        """

        if self._sort_column:
            if self._sort_column == 1:
                if get_real_data_twin(partner_secure_data["twinVersionId"]):
                    self._sorted_equipment
            elif self._sort_column == 2:
                self._sorted_device_kafka_messages
            elif self._sort_column == 3:
                self._sorted_reading_kafka_messages
        else:
            self._filtered_messages

        with ui.ScrollingFrame(
            height=880.0,
            horizontal_scrollbar_policy=ui.ScrollBarPolicy.SCROLLBAR_ALWAYS_OFF,
            vertical_scrollbar_policy=ui.ScrollBarPolicy.SCROLLBAR_ALWAYS_ON,
            style_type_name_override="TreeView",
        ):

            self._sensor_model = SensorModel(self._filtered_messages)

            self._delegate = SensorDelegate(
                self._sensor_selection_callback,
                self._sort_and_reload_table,
                self._equipment_sensor_selection_callback,
                self._filter_by_device_callback,
                self.checked_devices
            )

            self._tree_view = ui.TreeView(
                self._sensor_model,
                delegate=self._delegate,
                root_visible=False,
                header_visible=True,
            )

    def _update_table_view_content(self):
        """
        This function updates the table view content with the new data.
        Previously we were creating new sensor window every time we have new data

        I fixed this issue by updating the model of the tree view, so we can just update the content of the table
        """

        if self._flag == 1:
            if get_real_data_twin(partner_secure_data["twinVersionId"]):
                self._sensor_model = SensorModel(self._sorted_equipment)

        elif self._flag == 2:
            self._sensor_model = SensorModel(self._sorted_device_kafka_messages)

        elif self._flag == 3:
            self._sensor_model = SensorModel(self._sorted_reading_kafka_messages)

        else:
            self._sensor_model = SensorModel(self._filtered_messages)

        self._tree_view.model = self._sensor_model

    def _open_sensor_window(self):
        """
        This function opens the sensor window and creates the window model.
        """

        def create_window_model(self):
            with self._sensor_window.frame:
                with ui.VStack():
                    with ui.ScrollingFrame(horizontal_scrollbar_policy=ui.ScrollBarPolicy.SCROLLBAR_ALWAYS_OFF):
                        if len(self._kafka_messages) == 0:
                            ui.Label(
                                "Connecting to sensor data",
                                style={
                                    "font_size": 24,
                                    "color": cl.white,
                                },
                                alignment=ui.Alignment.CENTER,
                            )
                        else:
                            with ui.VStack(
                                height=0,
                            ):
                                self._window_header()
                                self._create_table_view()

        if self._sensor_window is None:
            def adjust_column_widths(new_width):
                """Proportionally resizes Sensor table"""

                total_width = new_width
                first_column_width = ui.Length(total_width * 0.15)
                other_column_width = ui.Length((total_width - first_column_width) / 3 - 10)
                self._tree_view.column_widths = [first_column_width] + [other_column_width] * 3

            self._sensor_window = ui.Window(
                title="Sensors",
                resizable=True
                )

            self._sensor_window.set_width_changed_fn(lambda new_width: adjust_column_widths(new_width))
            create_window_model(self)

        else:
            self._update_table_view_content()

    async def fetch_kafka_messages(self):
        """
        This function fetches the latest Kafka messages from DB and opens the sensor window.

        """
        kafka_messages = await ping_and_aggregate()

        if kafka_messages is not None:
            self._db_messages = kafka_messages
            self._filtered_messages = kafka_messages
            self._kafka_messages = kafka_messages

            self._open_sensor_window()
        else:
            self._kafka_messages = []

        self.viewport_scene = ViewportSceneInfo(get_active_viewport_window(), self._extension_id)

    def on_startup(self, ext_id):
        logger.info("[ul.gemini.sensor] MyExtension startup")

        global extension_instance
        self._extension_id = ext_id
        extension_instance = self
        if get_real_data_twin(
            partner_secure_data["twinVersionId"]
        ):  # if we have real data twin - collect data from DB first
            asyncio.run(self.fetch_kafka_messages())
        else:
            self._open_sensor_window()
            logger.info("Done sensor extension startup")
            self.viewport_scene = ViewportSceneInfo(get_active_viewport_window(), self._extension_id)
        logger.info("Done sensor extension startup")

    def on_shutdown(self):
        logger.info("[ul.gemini.sensor] MyExtension shutdown")

    def select_all_children(self, prims):
        """Selects all prims given a list of prim objects."""

        prim_paths = [prim.GetPath().pathString for prim in prims]
        selection = self.usd_context.get_selection()
        selection.set_selected_prim_paths(prim_paths, False)
