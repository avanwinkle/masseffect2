import logging
from mpf.core.mode import Mode


class Airlock(Mode):

    def __init__(self, machine, config, name, path):
        super().__init__(machine, config, name, path)
        self.log = logging.getLogger("Airlock")
        self.log.setLevel(10)
        self.settings = config.get("mode_settings")

        self._bd_physical_lock = None
        self._logicallockdevice = None
        self._lockshot = None

    def mode_start(self, **kwargs):
        super().mode_start(**kwargs)
        self.log.info("Airlock Mode is starting")
        if not self._lockshot:
            self._find_devices()
        self.add_mode_event_handler("fmball_lightshot_hit", self._debug_lightshot_hit)
        self.add_mode_event_handler("s_battering_ram_active", self._debug_enter)

        # On mode start, see if the lock shot is enabled and if so, enable the lock itself
        # (copied logic from lockhandler.py)
        if self._lockshot.enabled:
            self._post_event('enable_{}'.format(self._logicallockdevice.name))

    def _find_devices(self):
        # We need a pointer to the physical ball device to count physically locked balls
        for device in self.machine.ball_devices:
            if device.name == self.settings['ball_device']:
                self._bd_physical_lock = device
                break
        if not hasattr(self, "_bd_physical_lock"):
            raise AttributeError("Airlock cannot find ball_device named {}".format(self.settings['ball_device']))
        # We need a pointer to the multiball lock device to count virtually locked balls
        for device in self.mode_devices:
            if device.name == self.settings['lock_device']:
                self._logicallockdevice = device
                break
        if not hasattr(self, "_logicallockdevice"):
            raise AttributeError("Airlock cannot find multiball_lock named {}".format(self.settings['lock_device']))
        # We need a shot that defines whether lock is lit
        try:
            self._lockshot = self.machine.shots["{}_shot".format(self._logicallockdevice.name)]
        except KeyError:
            self.log.info("Airlock has no {} lock shot, locking will be disabled")

    def _post_event(self, event, **kwargs):
        """ Helper method for posting events """
        self.machine.events.post(event, **kwargs)

    def _debug_lightshot_hit(self, **kwargs):
        self.log.info("FMBALL was hit, where we at?")
        self.log.info("Achievements are {}".format(self.player.achievements))

        self.log.info("FMBALL lock is {}".format(self._logicallockdevice))
        self.log.info(" - enabled? {}".format(self._logicallockdevice.enabled))

    def _debug_enter(self, **kwargs):
        self.log.info("Ball has entered the airlock, lock is enabled? {}".format(self._logicallockdevice.enabled))
        self.log.info(" - lock has {} balls locked".format(self._logicallockdevice.locked_balls))
