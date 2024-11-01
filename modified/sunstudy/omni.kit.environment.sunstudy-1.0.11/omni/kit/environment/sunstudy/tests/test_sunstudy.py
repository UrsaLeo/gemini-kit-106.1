from ..scripts.sunstudy_window import SunstudyWindowLayer
from ..scripts.location_window import LocationWindow
from ..scripts.datetime_window import DateTimeWindow

from omni.kit.environment.core import get_sunstudy_player
from omni.ui.tests.test_base import OmniUiTest
import omni.kit.window.preferences
from pathlib import Path
import omni.kit.app
import omni.usd
import omni.ui as ui

import omni.kit.viewport.utility


CURRENT_PATH = Path(__file__).parent
TEST_DATA_PATH = CURRENT_PATH.parent.parent.parent.parent.parent.joinpath("data").joinpath("tests")


class TestSunstudy(OmniUiTest):
    # Before running each test
    async def setUp(self):
        await super().setUp()
        self._golden_img_dir = TEST_DATA_PATH.absolute().joinpath("golden_img").absolute()

        # Need a stage to set player time/date
        self._stage_created = False
        omni.usd.get_context().new_stage_with_callback(self._on_new_stage)

    # After running each test
    async def tearDown(self):
        await super().tearDown()

    async def test_general(self):
        """Testing general look of sunstudy"""
        ui.Workspace.show_window(SunstudyWindowLayer.WINDOW_NAME, True)
        ui.Workspace.show_window(LocationWindow.WINDOW_NAME, False)
        ui.Workspace.show_window(DateTimeWindow.WINDOW_NAME, False)
        ui.Workspace.show_window("Layer", False)

        while (not self._stage_created):
            await omni.kit.app.get_app().next_update_async()

        player = get_sunstudy_player()
        player.current_time = 8.12234
        player.current_date = "2021-11-24"

        window = omni.kit.viewport.utility.get_active_viewport_window()
        await self.docked_test_window(window, width=SunstudyWindowLayer.WIDTH + 10, height=100, block_devices=False)
        for _ in range(50):
            await omni.kit.app.get_app().next_update_async()

        await self.finalize_test(golden_img_dir=self._golden_img_dir, golden_img_name="sunstudy.png")

    def _on_new_stage(self, *args):
        self._stage_created = True
