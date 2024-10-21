import os
from omni.ui import scene as sc
import omni.ui as ui
from omni.ui import color as cl
from omni.kit.viewport.utility import get_active_viewport
import ul.gemini.services.artifact_services as artifact_services
from .utils import get_real_data_twin, get_distance, get_changed_size

import omni.usd
from pxr import UsdGeom
import omni


partner_secure_data = artifact_services.get_partner_secure_data()


class ObjInfoManipulator(sc.Manipulator):
    """Manipulator that displays the object path and material assignment
    with a leader line to the top of the object's bounding box.
    """

    active_viewport = get_active_viewport()

    def on_build(self):
        """Called when the model is changed and rebuilds the whole manipulator"""
        if not self.model:
            return

        # If we don't have a selection then just return
        if self.model.get_item("measurement") == "":
            return

        try:
            if self.model.get_item("name").split("/")[-2] != "Sensors":
                return

        except IndexError as e:
            return

        self.model.set_manipulator(self)

        kafka_message = self.model.get_item("kafka_message")

        stage = self.model.usd_context.get_stage()

        if not stage:
            return

        all_prims = self.model.get_item("all_prims")

        for prim_path in all_prims:
            prim = stage.GetPrimAtPath(prim_path)

            # Get metadata from selected prims
            custom_data = prim.GetCustomData()
            position = self.model.get_position_for_prim(prim)

            camera = UsdGeom.Camera(stage.GetPrimAtPath(get_active_viewport().camera_path))
            camera_pos = omni.usd.get_local_transform_SRT(camera)

            with sc.Transform(transform=sc.Matrix44.get_translation_matrix(*position)):
                with sc.Transform(look_at=sc.Transform.LookAt.CAMERA):

                    new_unit = custom_data.get("readingType", "None")  # Use data from the current prim

                    if new_unit == "Degrees Celsius":
                        new_unit = "°C"

                    new_value = str(
                        round(custom_data.get("reading", 0), 2)
                    ) if "reading" in custom_data else "None"

                    sensor_name = str(self.model.get_item("sensor_name"))

                    if get_real_data_twin(partner_secure_data["twinVersionId"]):
                        unit_bubble_map = {
                            "Degrees Celsius": "temperature.png",
                            "Sm3/hour": "Air Quality Sensor Icon.png",
                            "%": "Relative Humidity Sensor Icon.png",
                            "Sm3/min": "CO2 Sensor Icon.png",
                            "mmH20": "Water Sensor Icon.png",
                        }

                        unit = self.find_unit_for_sensor(sensor_name, kafka_message)
                        bubble = unit_bubble_map.get(unit, "Relative Humidity Sensor Icon.png")

                        if unit == "Degrees Celsius":
                            unit = "°C"
                    else:
                        naming_map = {
                            "temperature": ("°F", "temperature.png"),
                            "humidity": ("%", "Relative Humidity Sensor Icon.png"),
                            "VAV1_2_25": ("%", "Relative Humidity Sensor Icon.png"),
                            "M65_F2_WEA2_T_SP_020": ("°C", "temperature.png"),
                            "M65-30-20-10-10-F72-F-020": ("°C", "temperature.png"),
                            "M65-30-20-10-10-F72-F-010": ("Sm3/hour", "Air Quality Sensor Icon.png"),
                            "M65_F2_WEA3_T_SP_020": ("Sm3/hour", "Air Quality Sensor Icon.png"),
                            "M65_F2_WEA2_T_SP_010": ("%", "Relative Humidity Sensor Icon.png"),
                        }

                        unit, bubble = naming_map.get(sensor_name, ("°C", "temperature.png"))

                    # Set different text size depending on clicked element
                    distance = get_distance(position, camera_pos)
                    changed_size = get_changed_size(distance)

                    with sc.Transform(transform=sc.Matrix44.get_translation_matrix(0, 100, 0)):
                        self.value_label = sc.Label(
                            new_value, size=changed_size, alignment=ui.Alignment.CENTER, color=cl.white
                        )

                    with sc.Transform(transform=sc.Matrix44.get_translation_matrix(0, 40, 0)):
                        self.name_label = sc.Label(
                            new_unit, size=changed_size, alignment=ui.Alignment.CENTER, color=cl.white
                        )

                with sc.Transform(look_at=sc.Transform.LookAt.CAMERA):
                    sc.Image(
                        os.path.join(os.path.dirname(__file__), "photo", "sensors", "GreenPanel.png"),
                        width=400,
                        height=400,
                    )

                    with sc.Transform(
                        transform=sc.Matrix44.get_translation_matrix(0, -215, 0),
                        look_at=sc.Transform.LookAt.CAMERA,
                    ):
                        sc.Image(
                            os.path.join(os.path.dirname(__file__), "photo", "sensors", "GreenDot.png"),
                            width=75,
                            height=75,
                        )

                        self.bubble = sc.Image(
                            os.path.join(os.path.dirname(__file__), "photo", "bubbles", bubble),
                            width=50,
                            height=50,
                        )

    def clear_manipulator(self):
        self.on_build()

    def on_model_updated(self, item):
        # Regenerate the manipulator
        self.invalidate()

    def find_unit_for_sensor(self, sensor_name, kafka_message):
        """Find the unit for a given sensor_name from the Kafka messages"""
        for message in kafka_message:
            if message.get("device_name") == sensor_name:
                unit_map = {
                    "Blower1TotalHours": "Hrs",
                    "Blower2TotalHours": "Hrs",
                    "Blower4TotalHours": "Hrs",
                    "Blower6TotalHours": "Hrs",
                    "Blower6PartialHours": "Pr/Hrs",
                    "Blower3TotalHours": "Pr/Hrs",
                    "PumpingConsumption": "m³",
                    "SulzerFlow": "m³/h",
                    "RedoxBiological1": "mV",
                    "RedoxBiological2": "mV",
                }
                # Mock data for demo, fix it later 7/26/2024
                if partner_secure_data["twinVersionId"] == "ed02afb1-ac52-4275-a1dd-c072487d9d16":
                    return unit_map.get(sensor_name)

                return message.get("readingType", "Unknown")
        return "Unknown"
