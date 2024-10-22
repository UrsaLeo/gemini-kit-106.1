from __future__ import annotations
from omni.kit.scripting import BehaviorScript
from omni.anim.people.scripts.utils import Utils
import carb
import omni.usd
import omni.anim.graph.core as ag
import omni.timeline
from omni.anim.people.scripts.global_character_position_manager import GlobalCharacterPositionManager
from omni.anim.people.scripts.global_queue_manager import GlobalQueueManager
from omni.anim.people.scripts.navigation_manager import NavigationManager
from omni.anim.people.scripts.commands.idle import *
from omni.anim.people.scripts.commands.goto import *
from omni.anim.people.scripts.commands.look_around import *
from omni.anim.people.scripts.commands.queue import *
from omni.anim.people.scripts.commands.dequeue import *
from omni.anim.people.scripts.commands.sit import *
from omni.anim.people.ui_components import CommandTextWidget
from omni.anim.people import PeopleSettings
from omniverse.json.parse.scripts.managers.globalJsonManager import GlobalJsonReaderManager
import importlib
import json
from omniverse.json.parse.ui_components.alarm_setup import AlarmButtonWidget

class OmniAnimClien:

    def __init__(self, file_path, prim_path) -> None:
        self.file_path = file_path
        self.prim_path = prim_path
        self.actions_types = ["actions", "alarm_actions"]

    def on_init(self):
        """
        Called when a script is attached to characters and when a stage is loaded. Uses renew_character_state() to initialize character state.
        """
        self.renew_character_state()
        # omni.timeline.get_timeline_interface().play()
        # self.renew_character_state()


    def on_play(self):
        """
        Called when entering runtime (when clicking play button). Uses renew_character_state() to initialize character state.
        """
        self.renew_character_state()

    def on_destroy(self):
        """
        Clears character state by deleting global variable instances.
        """
        self.character_name = None
        if self.character_manager is not None:
            self.character_manager.destroy()
            self.character_manager = None

        if self.navigation_manager is not None:
            self.navigation_manager.destroy()
            self.navigation_manager = None

        if self.queue_manager is not None:
            self.queue_manager.destroy()
            self.queue_manager = None

        # self.character.set_variable("Action", "Idle")

    def renew_character_state(self):
        """
        Defines character variables and loads settings.
        """
        self.setting =  carb.settings.get_settings()
        self.command_path = self.setting.get(PeopleSettings.COMMAND_FILE_PATH)
        self.navmeshEnabled = True
        self.avoidanceOn = True
        self.character_name = self.get_character_name(str(self.prim_path))
        carb.log_info("Character name is {}".format(self.character_name))
        self.character = None
        self.current_command = None
        self.current_alarm_comand = None
        self.navigation_manager = None
        self.character_manager = None
        self.queue_manager = None
        self.command_key = None
        self.alarm_command_key = None



    def get_character_name(self, prim_path):
        """
        For this character asset find its name used in the command file.
        """
        split_path = prim_path.split("/")
        # prim_name = split_path[-1]
        prim_name = split_path[len(split_path) - 1]
        root_path = self.setting.get(PeopleSettings.CHARACTER_PRIM_PATH)
        # If a character is loaded through the spawn command, the commands for the character can be given by using the encompassing parent name.
        if prim_path.startswith(str(root_path)):
            parent_len = len(root_path.split("/"))
            parent_name = split_path[parent_len]
            return parent_name

        return prim_name

    def init_character(self):
        """f
        Initializes global variables and fetches animation graph attached to the character. Called after entering runtime as ag.get_character() can only be used in runtime.
        """
        self.navigation_manager = NavigationManager(str(self.prim_path), self.navmeshEnabled, self.avoidanceOn)
        self.character_manager = GlobalCharacterPositionManager.get_instance()
        self.queue_manager = GlobalQueueManager.get_instance()
        self.json_manager = GlobalJsonReaderManager.get_instance()
        if not self.navigation_manager or not self.character_manager or not self.queue_manager or not self.json_manager:
            return False

        self.character = ag.get_character(str(self.prim_path))
        if self.character is None:
            return False

        self.commands = self.get_simulation_commands()



        self.character.set_variable("Action", "None")
        carb.log_info("Initialize the character")
        return True


    def read_commands_from_file(self):
        """
        Reads commands from file pointed by self.command_path. Creates a Queue using queue manager if a queue is specified.
        :return: List of commands.
        :rtype: python list
        """
        data = self.json_manager.get_json(self.file_path)

        comands = {}

        for action_type in self.actions_types:
            comands[action_type] = {}
            char_name = data.get(self.character_name)
            if char_name and char_name is not None and char_name.get(action_type) is not None:

                for index, action in enumerate(data.get(self.character_name).get(action_type)):

                    if action["type"] == "GoTo":
                        comands[action_type][index] = {"command": "{} GoTo {}".format(self.character_name, action.get("finish_pos"))}
                    if action["type"] == "Idle":
                        comands[action_type][index] = {"command": "{} Idle {}".format(self.character_name, action.get("duration"))}
                    if action["type"] == "LookAround":
                        comands[action_type][index] = {"command": "{} LookAround {}".format(self.character_name, action.get("duration"))}
                    if action["type"] == "Sit":
                        comands[action_type][index] = {"command": "{} Sit {} {}".format(self.character_name, action.get("branch_path"), action.get("duration")) }

                    comands[action_type][index]["start_time"], comands[action_type][index]["finish_time"] = action["start_time"], action["finish_time"]
                    comands[action_type][index]["status"] = "added"
            else:
                print("no charname", data.get(self.character_name))

        return comands


    def get_simulation_commands(self, current_time = 0):
        cmd_lines = self.read_commands_from_file()
        commands = {}
        for action_type in self.actions_types:
            commands[action_type] = {}

            # idle_command = {
            #     "command": ["Idle"],  # Assuming "Idle" is the command for the idle state
            #     "start_time": current_time,
            #     "finish_time": current_time + 5  # You may want to set these values as needed
            # }

            for cmd_keys, cmd_line in enumerate(cmd_lines[action_type].values()):
                if not cmd_line:
                    continue
                words = cmd_line["command"].strip().split(' ')

                if words[0] == self.character_name:
                    command = []
                    for word in words[1:]:
                        command.append(word)
                    commands[action_type][cmd_keys] = cmd_line
                    commands[action_type][cmd_keys]["command"] = command
                    if commands[action_type][cmd_keys].get("start_time"):
                        commands[action_type][cmd_keys]["start_time"] = current_time + commands[action_type][cmd_keys]["start_time"]
                    if commands[action_type][cmd_keys].get("finish_time"):
                        commands[action_type][cmd_keys]["finish_time"] = current_time + commands[action_type][cmd_keys]["finish_time"]

                if words[0] == "Queue":
                    self.queue_manager.create_queue(words[1])
                if words[0] == "Queue_Spot":
                    queue = self.queue_manager.get_queue(words[1])
                    queue.create_spot(int(words[2]), carb.Float3(float(words[3]),float(words[4]),float(words[5])), Utils.convert_angle_to_quatd(float(words[6])))
                if words[0][0] == "#":
                    continue

            # commands[action_type]["idle"] = idle_command

        return commands


    def get_command(self, command):
        """
        Returns an instance of a command object based on the command.

        :param list[str] command: list of strings describing the command.
        :return: instance of a command object.
        :rtype: python object
        """
        # print(command[0])
        if command[0] == "GoTo":
            return GoTo(self.character, command, self.navigation_manager)
        elif command[0] == "Idle":
            return Idle(self.character, command, self.navigation_manager)
        elif command[0] == "Queue":
            ####
            #self.character.set_variable("Action", "None")
            return QueueCmd(self.character, command, self.navigation_manager, self.queue_manager)
        elif command[0] == "Dequeue":

            return Dequeue(self.character, command, self.navigation_manager, self.queue_manager)
        elif command[0] == "LookAround":
            return LookAround(self.character, command, self.navigation_manager)
        elif command[0] == "Sit":
            return Sit(self.character, command, self.navigation_manager)
        else:
            module_str = ".commands.{}".format(command[0].lower(), package = None)
            try:
                custom_class = getattr(importlib.import_module(module_str, package=__package__), command[0])
            except (ImportError, AttributeError) as error:
                carb.log_error("Module or Class for the command do not exist. Check the command again.")
            return custom_class(self.character, command, self.navigation_manager)


    def execute_command(self, commands, delta_time, current_time):
        """
        Executes commands in commands list in sequence. Removes a command once completed.

        :param list[list] commands: list of commands.
        :param float delta_time: time elapsed since last execution.
        """
        if AlarmButtonWidget.is_alarm:
            self.execute_alarm_comand(commands, delta_time, current_time)
            self.command_key = None
            self.current_command = None
            return
        else:
            self.alarm_command_key = None
            self.current_alarm_comand = None

        if self.character is None:
            if not self.init_character():
                return

        commands = commands["actions"]

        if self.current_command is None:
            if commands:
                if not self.command_key:
                    for key in commands:
                        if commands[key]["status"] == "added" or commands[key]["status"] == "waiting":
                            if commands[key].get("start_time") and commands[key]["start_time"] > current_time:
                                commands[key]["status"] = "waiting"
                                continue
                            self.command_key = key
                            break
                    else:
                        return
                self.current_command = self.get_command(commands[self.command_key]["command"])
            else:
                return
        if commands[self.command_key].get("finish_time") and commands[self.command_key]["finish_time"] < current_time:
            commands[self.command_key]["status"] = "finished"
            self.current_command = None
            self.command_key = None
            return

        if self.current_command.execute(delta_time):
            commands[self.command_key]["status"] = "finished"
            self.current_command = None
            self.command_key = None


    def execute_alarm_comand(self, commands, delta_time, current_time):
        """
        Executes commands in commands list in sequence. Removes a command once completed.

        :param list[list] commands: list of commands.
        :param float delta_time: time elapsed since last execution.
        """
        if self.character is None:
            if not self.init_character():
                return

        commands = commands["alarm_actions"]

        if self.current_alarm_comand is None:
            if commands:
                if not self.alarm_command_key:
                    for key in commands:
                        if commands[key]["status"] == "added" or commands[key]["status"] == "waiting":
                            if commands[key].get("start_time") and commands[key]["start_time"] > current_time:
                                commands[key]["status"] = "waiting"
                                continue
                            self.alarm_command_key = key
                            break
                    else:
                        return
                self.current_alarm_comand = self.get_command(commands[self.alarm_command_key]["command"])
            else:
                return
        if commands[self.alarm_command_key].get("finish_time") and commands[self.alarm_command_key]["finish_time"] < current_time:
            commands[self.alarm_command_key]["status"] = "finished"
            self.current_alarm_comand = None
            self.alarm_command_key = None
            return

        if self.current_alarm_comand.execute(delta_time):
            commands[self.alarm_command_key]["status"] = "finished"
            self.current_alarm_comand = None
            self.alarm_command_key = None


    def on_update(self, current_time: float, delta_time: float):
        """
        Called on every update. Initializes character at start, publishes character positions and executes character commands.
        :param float current_time: current time in seconds.
        :param float delta_time: time elapsed since last update.
        """

        if self.avoidanceOn:
            self.navigation_manager.publish_character_positions(delta_time, 0.5)

        if self.commands and not AlarmButtonWidget.is_alarm:
            self.execute_command(self.commands, delta_time, current_time)

        if self.commands and AlarmButtonWidget.is_alarm:
            self.execute_alarm_comand(self.commands, delta_time, current_time)
