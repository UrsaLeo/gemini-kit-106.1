import os
import asyncio
import omni.client
import carb.settings
import omni.ext
import omni.ui as ui
import omni.timeline
import omni.kit.app
import omni.usd
from pxr import Usd, UsdGeom, Gf, UsdSkel, Sdf
import omni.kit.commands
from omni.anim.people.scripts.commands.goto import *
from omni.anim.people.scripts.navigation_manager import *
from omni.anim.graph.core import ag
import random
from omni.anim.people import PeopleSettings
from omni.isaac.core.utils import prims

from omni.isaac.core.utils.nucleus import get_assets_root_path
from omni.anim.navigation.core import CreateNavMeshVolumeCommand
import json
from omniverse.json.parse.scripts.managers.globalJsonManager import GlobalJsonReaderManager
from omniverse.json.parse.scripts.json_generator.json_generator import generate_character
from omniverse.json.parse.ui_components.alarm_setup import AlarmButtonWidget

import omni.anim.people

import ul.gemini.services.artifact_services as artifact_services

partner_secure_data = artifact_services.get_partner_secure_data()


from omni.kit.app import get_app_interface
app = get_app_interface()
extensions = omni.kit.app.get_app().get_extension_manager().fetch_all_extension_packages()


class OmniverseJsonParseExtension(omni.ext.IExt):
    def on_startup(self, ext_id):
        # Apply extension only for Canon twin
        if not partner_secure_data["twinVersionId"] == "9332e77d-fb20-4221-8cf2-9a2c8ef80e22":
            return

        self.alarm_setup = AlarmButtonWidget(self)
        self.default_biped_usd = "Biped_Setup"
        self.default_biped_asset_name = "biped_demo"
        self.stage = omni.usd.get_context().get_stage()
        self.timeline = omni.timeline.get_timeline_interface()
        self.task = None




        # window_flags = ui.WINDOW_FLAGS_NO_RESIZE
        # window_flags |= ui.WINDOW_FLAGS_NO_SCROLLBAR
        # window_flags |= ui.WINDOW_FLAGS_MODAL
        # window_flags |= ui.WINDOW_FLAGS_NO_CLOSE
        # window_flags |= ui.WINDOW_FLAGS_NO_MOVE

        self._window = ui.Window("Avatar configurations", width=449, height=300,
                                #  flags=window_flags
                                 )
        self.json_path = omni.kit.app.get_app().get_extension_manager().get_extension_path_by_module(__name__) + "/config/commands.json"
        self.json_manager = None

        self.setup_window()

    def setup_window(self):
        property_window = ui.Workspace.get_window("Property")
        # navmesh_window = ui.Workspace.get_window("NavMesh")
        # print("navmesh_window", navmesh_window)
        play_stop_label = ui.SimpleStringModel("Play")

        def toggle_play_stop():
            """Assigns Stop and Play functions to one button"""

            if play_stop_label.as_string == "Play":
                omni.timeline.get_timeline_interface().play()
                play_stop_label.set_value("Stop")
            else:
                omni.timeline.get_timeline_interface().pause()
                play_stop_label.set_value("Play")




        # async def on_json():
        #     await self._spawn_characters_form_json(self.json_path)


        # async def on_button_click():
        #     try:
        #         await on_json()
        #     except Exception as e:
        #         print("exceptt", e)
        #     omni.timeline.get_timeline_interface().play()
        #     play_stop_label.set_value("Stop")

        # loop = asyncio.get_event_loop()

        with self._window.frame:
            with ui.ScrollingFrame(horizontal_scrollbar_policy=ui.ScrollBarPolicy.SCROLLBAR_ALWAYS_OFF):
                with ui.VStack():

                    def on_json():
                        self._spawn_characters_form_json(self.json_path)


                    with ui.HStack(width=449):
                        ui.Button("Load avatars from json file", clicked_fn=lambda: on_json)

                        button = ui.Button(play_stop_label.as_string, clicked_fn=toggle_play_stop)
                        play_stop_label.add_value_changed_fn(lambda model: setattr(button, "text", model.as_string))

                        ui.Button("Save configuration", clicked_fn=self.update_json_file)

                        ui.Button(
                            "Property",
                            clicked_fn=lambda: setattr(property_window, 'visible', True)
                        )
                        # ui.Button(
                        #     "NavMesh",
                        #     clicked_fn=lambda: setattr(navmesh_window, 'visible', True)
                        # )


                    with ui.HStack(width=449):
                        ui.Button("Clear scene", clicked_fn=self.delete_avatars)
                        ui.Button("Run custom command", clicked_fn=self.generate_100_av_by_click)
                        ui.Button("Configure/edit avatar", clicked_fn=self.modify_json_file_by_key)
                        ui.Button("Add a new avatar", clicked_fn=self.add_a_new_avatart)

                    with ui.HStack(width=449):
                        self.data = self.get_json_manager().read_from_json(self.json_path)
                        self.values = list(self.data.keys())
                        self.combo_box: ui.AbstractItemModel = ui.ComboBox(0, *self.values).model
                        self._combobox_sub = self.combo_box.subscribe_item_changed_fn(self.combo_changed)

                        ui.Button("Remove avatar", clicked_fn=self.delete_avatar)

                        v_stack = ui.HStack(spacing=40)
                        self.alarm_setup._build_content(None, v_stack)

        # def on_width_changed(new_width):
        #     pass
        # self._window.set_width_changed_fn(lambda new_width: on_width_changed(new_width))


    def generate_100_av_by_click(self):
        def create_avatar():
            charater = generate_character(character_int_id=len(self.data), max_time=120)
            self.data = self.data | charater
            self.set_data_json()
            print("New avatar success added: {}".format(list(charater.keys())[0]))


        for _ in range(20):
            create_avatar()

        self._spawn_characters_form_json(self.json_path)


    def update_json_file(self):
        try:
            self.get_json_manager().save_json(self.json_path)
        except Exception as e:
            print("Error saving data to JSON file:", e)


    def set_data_json(self):
        self.get_json_manager().set_json(self.json_path, self.data)

    def combo_changed(self, item_model: ui.AbstractItemModel, item: ui.AbstractItem):
        value_model = item_model.get_item_value_model(item)
        current_index = value_model.as_int
        self.option = self.values[current_index]
        print(f"Selected '{self.option}' at index {current_index}.")


    def delete_combo_changed(self, item_model: ui.AbstractItemModel, item: ui.AbstractItem):
        value_model = item_model.get_item_value_model(item)
        current_index = value_model.as_int
        self.delete_option = self.values[current_index]


    def delete_avatar(self):
        def update_json_file():
            if not self.delete_option in list(self.data.keys()):
                carb.log_error("This avatar not exist")
                return
            self.data.pop(self.delete_option)

            self.set_data_json()

        avaible_avatars = list(self.data.keys())
        with self._window.frame:
            with ui.VStack():
                combo_box: ui.AbstractItemModel = ui.ComboBox(0, *avaible_avatars).model
                self._delete_combobox_sub = combo_box.subscribe_item_changed_fn(self.delete_combo_changed)

                with ui.HStack():
                    ui.Button("Delete avatar", clicked_fn=update_json_file)
                    ui.Button("Close", clicked_fn=self.setup_window)


    def add_a_new_avatart(self):
        def update_json_file():
            if not text_model.get_value_as_string():
                carb.log_error("Text cant be blank")
                return
            if text_model.get_value_as_string() in list(self.data.keys()):
                carb.log_error("This avatar already exist")
                return
            self.data[text_model.get_value_as_string()] = {}

            self.set_data_json()

        def generate_new_charater():
            charater = generate_character(character_int_id=len(self.data), max_time=120)

            self.data = self.data | charater
            self.set_data_json()
            print("New avatar success added: {}".format(list(charater.keys())[0])) #printed
            self.option = list(charater.keys())[0]
            self.modify_json_file_by_key()

        with self._window.frame:
            with ui.VStack():
                text_model = ui.SimpleStringModel()
                text_field = ui.StringField(model=text_model)

                with ui.HStack():
                    ui.Button("Add avatar", clicked_fn=update_json_file, height=20)
                    ui.Button("Close", clicked_fn=self.setup_window, height=20)
                    ui.Button("Auto generate new avatar", clicked_fn=generate_new_charater, height=20)


    def modify_json_file_by_key(self):
        modifing_parts = self.data[self.option]
        text = json.dumps(modifing_parts, indent=4)
        # print("text_dumps", text)

        def update_json_file():
            self.data[self.option] = json.loads(text_model.get_value_as_string())
            self.set_data_json()


        with self._window.frame:
            with ui.VStack():
                text_model = ui.SimpleStringModel(text)
                text_field = ui.StringField(model=text_model, multiline=True)

                with ui.HStack():
                    #NOTE! Changed update_json_file to self.update_json_file to update json
                    ui.Button("Save changes", clicked_fn=update_json_file)
                    ui.Button("Close", clicked_fn=self.setup_window)



    def on_shutdown(self):
        print("[startupsoft.test.world] startupsoft test world shutdown")


    def delete_avatars(self):

        omni.kit.commands.execute('DeletePrims',
	        paths=['/World/Characters'],
	        destructive=False)

    def init_json_manager(self):
        if self.json_manager is not None:
            self.json_manager.destroy()
            self.json_manager = None
        self.json_manager = GlobalJsonReaderManager().get_instance()

    def get_json_manager(self):
        if not self.json_manager:
            self.init_json_manager()
        return self.json_manager

    def _conver_json_to_cmd(self, json_path):
        data = self.get_json_manager().read_from_json(json_path)

        for key in data:
            if data[key].get("spawn_position"):
                spawn_coordinates = data.get(key).get("spawn_position")
                yield f"Spawn {key} {spawn_coordinates}"
            else:
                yield f"Spawn {key}"


    def _spawn_characters_form_json(self, json_path):

        self.available_character_list = []
        self.spawned_agents_list = []
        setting_dict = carb.settings.get_settings()
        # Get root assets path from setting, if not set, get the Isaac-Sim asset path

        #NOTE Change to local path
        # people_asset_folder = os.path.join(os.path.dirname(__file__), "Characters").replace("\\", "/")
        people_asset_folder = setting_dict.get(PeopleSettings.CHARACTER_ASSETS_PATH)

        print("PeopleSettings.CHARACTER_ASSETS_PATH", PeopleSettings.CHARACTER_ASSETS_PATH)
        print("people_asset_folder", people_asset_folder)

        character_root_prim_path = setting_dict.get(PeopleSettings.CHARACTER_PRIM_PATH)

        if not character_root_prim_path:
            character_root_prim_path = "/World/Characters"

        if people_asset_folder:
            self.assets_root_path = people_asset_folder
        else:
            root_path = get_assets_root_path()

            if root_path is None:
                carb.log_error("Could not find Isaac Sim assets folder")
                return

            self.assets_root_path  = "{}/Isaac/People/Characters".format(root_path)
            print("self.assets_root_path", self.assets_root_path)

        if not self.assets_root_path:
            carb.log_error("Could not find people assets folder")

        result, properties = omni.client.stat(self.assets_root_path)

        if result != omni.client.Result.OK:
            carb.log_error("Could not find people asset folder : " + str(self.assets_root_path))
            return

        if not Sdf.Path.IsValidPathString(character_root_prim_path):
            carb.log_error(str(character_root_prim_path) + " is not a valid character root prim's path")

        if not omni.usd.get_context().get_stage().GetPrimAtPath(character_root_prim_path):
            prims.create_prim(character_root_prim_path, "Xform")

        character_root_prim = omni.usd.get_context().get_stage().GetPrimAtPath(character_root_prim_path)
        # Delete all previously loaded agents
        for character_prim in character_root_prim.GetChildren():
            if character_prim and character_prim.IsValid() and character_prim.IsActive():
                prims.delete_prim(character_prim.GetPath())


        # Reload biped and animations
        if not omni.usd.get_context().get_stage().GetPrimAtPath("{}/{}".format(character_root_prim_path, self.default_biped_usd)):
            biped_demo_usd = "{}/{}.usd".format(self.assets_root_path, self.default_biped_usd)
            prim = prims.create_prim("{}/{}".format(character_root_prim_path,self.default_biped_usd), "Xform", usd_path=biped_demo_usd)
            # prim.GetAttribute("visibility").Set("invisible")

        # Reload character assets
        for cmd_line in self._conver_json_to_cmd(json_path):
            if not cmd_line:
                continue
            words = cmd_line.strip().split(' ')
            if words[0] != "Spawn":
                continue

            if len(words) != 6 and len(words) != 2:
                carb.log_error("Invalid 'Spawn' command issued, use command format - Spawn char_name or Spawn char_name x y z char_rotation.")
                return

            # Add Spawn defaults
            if len(words) == 2:
                words.extend([0] * 4)

            # Do not use biped demo as a character name
            if str(words[1]) == "biped_demo":
                carb.log_warn("biped_demo is a reserved name, it cannot be used as a character name.")
                continue

            # Don't allow duplicates
            if str(words[1]) in self.spawned_agents_list:
                carb.log_warn(str(words[1]) + " has already been generated")
                continue

            # Check if prim already exists
            if omni.usd.get_context().get_stage().GetPrimAtPath("{}/{}".format(character_root_prim_path,words[1])):
                carb.log_warn("Path: " + str("{}/{}".format(character_root_prim_path,words[1])) + "has been taken, please try another character name")
                continue

            char_name, char_usd_file = self.get_path_for_character_prim(words[1])
            if char_usd_file:
                prim = prims.create_prim(
                    "{}/{}".format(character_root_prim_path,words[1]), "Xform", usd_path=char_usd_file
                )

                prim.GetAttribute("xformOp:translate").Set(Gf.Vec3d(float(words[2]),float(words[3]), float(words[4])))

                prim.GetAttribute("xformOp:scale").Set((100.0, 100.0, 100.0))

                set_value = prim.GetAttribute("xformOp:scale").Get()

                if type(prim.GetAttribute("xformOp:orient").Get()) == Gf.Quatf:
                    prim.GetAttribute("xformOp:orient").Set(Gf.Quatf(Gf.Rotation(Gf.Vec3d(0,0,1), float(words[5])).GetQuat()))
                else:
                    prim.GetAttribute("xformOp:orient").Set(Gf.Rotation(Gf.Vec3d(0,0,1), float(words[5])).GetQuat())

                # Store agent names for deletion
                self.spawned_agents_list.append(words[1])
        self._setup_json_characters()

    def get_path_for_character_prim(self, agent_name):

        # Get a list of available character assets
        if not self.available_character_list:
            self.available_character_list = self.get_character_asset_list()
            if not self.available_character_list:
                return

        # Check if a folder with agent_name exists. If exists we load the character, else we load a random character
        agent_folder = "{}/{}".format(self.assets_root_path, agent_name)
        result, properties = omni.client.stat(agent_folder)
        if result == omni.client.Result.OK:
            char_name = agent_name
        else:
            # Pick a random character from available character list
            char_name = random.choice(self.available_character_list)

        # Get the usd present in the character folder
        character_folder = "{}/{}".format(self.assets_root_path, char_name)
        character_usd = self.get_usd_in_folder(character_folder)
        if not character_usd:
            return

        if len(self.available_character_list) != 0 and (char_name in self.available_character_list):
            self.available_character_list.remove(char_name)

        # Return the character name (folder name) and the usd path to the character
        return (char_name, "{}/{}".format(character_folder, character_usd))


    def get_character_asset_list(self):
        # List all files in characters directory
        result, folder_list = omni.client.list("{}/".format(self.assets_root_path))

        if result != omni.client.Result.OK:
            carb.log_error("Unable to get character assets from provided asset root path.")
            return

        # Prune items from folder list that are not directories.
        pruned_folder_list = [folder.relative_path for folder in folder_list
            if (folder.flags & omni.client.ItemFlags.CAN_HAVE_CHILDREN) and not folder.relative_path.startswith(".")]

        if self.default_biped_asset_name in pruned_folder_list:
            pruned_folder_list.remove(self.default_biped_asset_name)
        return pruned_folder_list


    def get_usd_in_folder(self, character_folder_path):
        result, folder_list = omni.client.list(character_folder_path)

        if result != omni.client.Result.OK:
            carb.log_error("Unable to read character folder path at {}".format(character_folder_path))
            return

        for item in folder_list:
            if item.relative_path.endswith(".usd"):
                return item.relative_path

        carb.log_error("Unable to file a .usd file in {} character folder".format(character_folder_path))


    def _setup_json_characters(self):
        self.stage = omni.usd.get_context().get_stage()
        anim_graph_prim = None
        for prim in self.stage.Traverse():
            if prim.GetTypeName() == "AnimationGraph":
                anim_graph_prim = prim
                break

        if anim_graph_prim is None:
            carb.log_warn("Unable to find an animation graph on stage.")
            return

        for prim in self.stage.Traverse():
            if prim.GetTypeName() == "SkelRoot" and UsdGeom.Imageable(prim).ComputeVisibility() != UsdGeom.Tokens.invisible:

                # remove animation graph attribute if it exists
                omni.kit.commands.execute(
                    "RemoveAnimationGraphAPICommand",
                    paths=[Sdf.Path(prim.GetPrimPath())]
                )

                omni.kit.commands.execute(
                    "ApplyAnimationGraphAPICommand",
                    paths=[Sdf.Path(prim.GetPrimPath())],
                    animation_graph_path=Sdf.Path(anim_graph_prim.GetPrimPath())
                )
                omni.kit.commands.execute(
                    "ApplyScriptingAPICommand",
                    paths=[Sdf.Path(prim.GetPrimPath())]
                )
                attr = prim.GetAttribute("omni:scripting:scripts")

                settings_dict = carb.settings.get_settings()

                ext_path = omni.kit.app.get_app().get_extension_manager().get_extension_path_by_module(__name__) + "/omniverse/json/parse/scripts/character_behaivor.py"
                attr.Set([r"{}".format(ext_path)])
