# os = __import__("os")
# MpfTestCase = __import__("mpf.tests.MpfTestCase", fromlist=["MpfTestCase"])
# inspect = __import__("inspect")
# MachineController = __import__("mpf.core.machine", fromlist=["MachineController"])

import inspect, os
from mpf.tests.MpfTestCase import MpfTestCase, MagicMock
from mpf.tests.MpfMachineTestCase import MockConfigPlayers
from mpf.core.machine import MachineController

class ME2TestCase(MockConfigPlayers):
    # Override the MPFTestCase for the machine path
    def get_absolute_machine_path(self):
        """Return absolute machine path."""
        # check if there is a decorator
        config_directory = getattr(
            getattr(self, self._testMethodName), "config_directory", None
        )
        if not config_directory:
            config_directory = self.get_machine_path()

        # creates an absolute path based on machine_path
        return os.path.abspath(os.curdir)

    @staticmethod
    def get_abs_path(path):
        """Get absolute path relative to current directory."""
        return os.path.join(os.path.abspath(os.curdir), path)

    def get_config_file(self):
        return "config.yaml"

    def get_machine_path(self):
        return ".."

    def get_platform(self):
        return 'smart_virtual'

    def get_enable_plugins(self):
        return True

    def setUp(self):
        self.machine_config_patches['mpf']['plugins'] = ['mpf.plugins.auditor.Auditor']
        super().setUp()
        # SlideQueuePlayer calls slide_player directly
        self.machine.slide_player = MockSlidePlayer()

    def start_game(self, quest=None):
        self.machine.playfield.add_ball = MagicMock()
        # self.machine.ball_controller.num_balls_known = 3
        self.hit_and_release_switch("s_start_button")
        self.advance_time_and_run()
        self.assertIsNotNone(self.machine.game)
        if quest is not None:
            self.start_quest(quest)

class MockSlidePlayer:

    def play(self, **kwargs):
        pass
