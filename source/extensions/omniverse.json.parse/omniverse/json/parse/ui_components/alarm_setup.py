# Copyright (c) 2022, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.

from omni import ui
import carb
import __main__

class AlarmButtonWidget:

    is_alarm = False
    def __init__(self, ext_ui_instance):
        self._ext_ui_instance = ext_ui_instance
        self._alaram_switcher= None
        self._alaram_switcher = None

    def shutdown(self):
        self._alaram_switcher= None
        self._textbox_label = None

    def _build_content(self, title_stack, content_stack):
        with content_stack:
            with ui.HStack(spacing=30):
                self.alarm_message = ui.Label("not alarmed")
                #self._textbox_label = ui.Label("Alarm settings")
                self._alaram_switcher = ui.Button(text="Switch alarm")
                self._alaram_switcher.set_clicked_fn(self._on_changed)


    def _on_changed(self):
        AlarmButtonWidget.is_alarm = not AlarmButtonWidget.is_alarm
        if AlarmButtonWidget.is_alarm:
            self.alarm_message.text = "ALARM!!!"
        else:
            self.alarm_message.text = "not alarmed"