# Copyright (c) 2022, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.

from __future__ import annotations
from omni.kit.scripting import BehaviorScript
from omni.anim.people.scripts.utils import Utils
import carb
import omni.usd
import omni.anim.graph.core as ag
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
import importlib
import json
import os
from omniverse.json.parse.scripts.client.anim_people_client import OmniAnimClien



class CharacterBehavior(BehaviorScript):
    """
    Character controller class that reads commands from a command file and drives character actions.
    """


    def on_init(self):
        """
        Called when a script is attached to characters and when a stage is loaded. Uses renew_character_state() to initialize character state.
        """
        self.omni_client = OmniAnimClien(
            omni.kit.app.get_app().get_extension_manager().get_extension_path_by_module(
                "omniverse.json.parse.extension") + "/config/commands.json", self.prim_path
        )
        self.omni_client.renew_character_state()


    def on_play(self):
        """
        Called when entering runtime (when clicking play button). Uses renew_character_state() to initialize character state.
        """

        self.omni_client = OmniAnimClien(
            omni.kit.app.get_app().get_extension_manager().get_extension_path_by_module(
                    "omniverse.json.parse.extension"
                ) + "/config/commands.json", self.prim_path
            )

        self.omni_client.renew_character_state()


    def on_stop(self):
        """
        Called when exiting runtime (when clicking stop button). Uses on_destroy() to clear state.
        """
        # self.omni_client = OmniAnimClien(
        #     omni.kit.app.get_app().get_extension_manager().get_extension_path_by_module(
        #             "omniverse.json.parse.extension"
        #         ) + "/config/commands.json", self.prim_path
        #     )

        # self.omni_client.on_destroy()
        # self.character = ag.get_character(str(self.prim_path))
        # if self.character is None:
        #     return False

        # self.commands = self.get_simulation_commands()
        # self.character.set_variable("Action", "Sit")

        # self.omni_client.renew_character_state()
        avatar = ag.get_character(str('/World/Characters/avatar_1'))
        # print("ava1", avatar)
        # avatar = omni.anim.people.get_avatar(prim_path='/World/Charatters/avatar_1')
        if avatar:
            avatar.set_variable("Action", "Sit")
            self.omni_client.on_destroy()

    def on_destroy(self):
        """
        Clears character state by deleting global variable instances.
        """
        self.omni_client = OmniAnimClien(
            omni.kit.app.get_app().get_extension_manager().get_extension_path_by_module(
                    "omniverse.json.parse.extension"
                ) + "/config/commands.json", self.prim_path
            )

        self.omni_client.renew_character_state()
        # self.omni_client.on_destroy()


    def on_update(self, current_time: float, delta_time: float):
        """
        Called on every update. Initializes character at start, publishes character positions and executes character commands.
        :param float current_time: current time in seconds.
        :param float delta_time: time elapsed since last update.
        """
        if self.omni_client.character is None:
            if not self.omni_client.init_character():
                return

        self.omni_client.execute_command(self.omni_client.commands, delta_time, current_time)
