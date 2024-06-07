
from mpf.core.platform import SwitchSettings, DriverSettings
from mpf.platforms.interfaces.driver_platform_interface import PulseSettings
from mpf.tests.MpfTestCase import MpfTestCase, MagicMock
from ME2TestCase import ME2TestCase


class TestBaseMode(ME2TestCase):


    def test_startEvents(self):
        self.mock_event("start_mode_global")
        self.start_game()

        self.assertIn(
            self.machine.modes["base"], self.machine.mode_controller.active_modes
        )
        self.assertEqual(1, self._events["start_mode_global"])

    def test_startingSquadmate(self):
        self.machine.settings.set_setting_value("free_starting_mission", 2)
        self.start_game()
        initial_states = [self.machine.game.player[f"status_{mate}"] for mate in ("grunt", "jack", "garrus", "kasumi", "mordin")]
        self.assertEqual(sorted(initial_states), [0, 0, 0, 0, 3])

    def test_noStartingSquadmate(self):
        self.machine.settings.set_setting_value("free_starting_mission", 0)
        self.start_game()
        initial_states = [self.machine.game.player[f"status_{mate}"] for mate in ("grunt", "jack", "garrus", "kasumi", "mordin")]
        self.assertEqual(sorted(initial_states), [0, 0, 0, 0, 0])

