from ..scripts.sunstudy import *
from ..scripts.location_window import *
from omni.ui.tests.test_base import OmniUiTest
from ..scripts.location_window import *
from pathlib import Path
import asyncio


CURRENT_PATH = Path(__file__).parent
TEST_DATA_PATH = CURRENT_PATH.parent.parent.parent.parent.parent.joinpath("data").joinpath("tests")


class TestLocation(OmniUiTest):
    # Before running each test
    async def setUp(self):
        await super().setUp()
        self._golden_img_dir = TEST_DATA_PATH.absolute().joinpath("golden_img").absolute()

    # After running each test
    async def tearDown(self):
        await super().tearDown()

    async def test_general(self):
        """Testing general look of sunstudy"""
        sunstudy_ext = get_instance()
        # await asyncio.sleep(10)
        sunstudy_ext.show_location()
        sunstudy_ext._location_window._longitude_model.set_value(-0.985)
        sunstudy_ext._location_window._latitude_model.set_value(51.426)
        await omni.kit.app.get_app().next_update_async()
        await self.docked_test_window(
            window=sunstudy_ext._location_window._window, width=sunstudy_ext._location_window._window.width, height=260
        )
        await omni.kit.app.get_app().next_update_async()
        await self.finalize_test(golden_img_dir=self._golden_img_dir, golden_img_name="location.png")
