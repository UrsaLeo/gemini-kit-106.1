from ..scripts.datetime_window import DateTimeWindow
from omni.ui.tests.test_base import OmniUiTest
from omni.kit.environment.core import get_sunstudy_player
from pathlib import Path
import omni.usd


CURRENT_PATH = Path(__file__).parent
TEST_DATA_PATH = CURRENT_PATH.parent.parent.parent.parent.parent.joinpath("data").joinpath("tests")


class TestDatetime(OmniUiTest):
    # Before running each test
    async def setUp(self):
        await super().setUp()
        self._golden_img_dir = TEST_DATA_PATH.absolute().joinpath("golden_img").absolute()

        # Need a stage to set player time/date
        self._stage_created = False
        omni.usd.get_context().new_stage_with_callback(self._on_new_stage)

        self._player = get_sunstudy_player()

    # After running each test
    async def tearDown(self):
        await super().tearDown()

    async def test_general(self):
        """Testing general look of datetime"""
        while (not self._stage_created):
            await omni.kit.app.get_app().next_update_async()

        self._player.current_time = 8.12234
        self._player.current_date = "2021-11-24"

        w = DateTimeWindow()
        w.show()

        await self.docked_test_window(
            window=w._window, width=DateTimeWindow.WINDOW_WIDTH, height=DateTimeWindow.WINDOW_HEIGHT
        )
        await omni.kit.app.get_app().next_update_async()

        await self.finalize_test(golden_img_dir=self._golden_img_dir, golden_img_name="datetime.png")

    def _on_new_stage(self, *args):
        self._stage_created = True
