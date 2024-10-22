# Copyright (c) 2022, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.

from __future__ import annotations
import json
import omni.client

class GlobalJsonReaderManager:
    """Global class which facilitates all queue interactions between characters"""

    __instance: GlobalJsonReaderManager = None

    def __init__(self):
        if self.__instance is not None:
            raise RuntimeError("Only one instance of GlobalJsonReaderManager is allowed")
        self._file_pathes = {}
        GlobalJsonReaderManager.__instance = self

    def read_from_json(self, file_path):
        if not file_path in self._file_pathes:
            result, version, context = omni.client.read_file(file_path)

            if result == omni.client.Result.OK:
                self._file_pathes[file_path] = json.loads(memoryview(context).tobytes().decode("utf-8"))

        return self._file_pathes[file_path]

    def get_json(self, file_path):
        return self._file_pathes[file_path]

    def set_json(self, file_path, data):

        self._file_pathes[file_path] = data

    def save_json(self, file_path):
        omni.client.write_file(file_path, memoryview(json.dumps(self._file_pathes[file_path]).encode("utf-8")))

    def destroy(self):
        GlobalJsonReaderManager.__instance = None

    @classmethod
    def get_instance(cls) -> GlobalJsonReaderManager:
        if cls.__instance is None:
            GlobalJsonReaderManager()
        return cls.__instance
