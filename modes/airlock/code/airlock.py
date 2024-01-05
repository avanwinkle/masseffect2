import logging
from mpf.core.mode import Mode
from mpf.core.rgb_color import RGBColor

class Airlock(Mode):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.log = logging.getLogger("Airlock")
        self.log.setLevel(10)
        self.settings = self.config.get("mode_settings")

        self._bd_physical_lock = None
        self._logicallockdevice = None
        self._lockshot = None

    def mode_start(self, **kwargs):
        super().mode_start(**kwargs)
        self.log.info("Airlock Mode is starting")
        if not self._lockshot:
            self._find_devices()
        self.add_mode_event_handler("fmball_lightshot_hit", self._debug_lightshot_hit)
        self.add_mode_event_handler("s_airlock_entrance_active", self._debug_enter)
        self.add_mode_event_handler("achievement_arrival_state_enabled", self._set_multiball_color)

        # Use a switch handler for faster & more reliable control
        self.machine.switch_controller.add_switch_handler(
               's_airlock_entrance', self._check_bypass)

        # On mode start, set the color_mball value based on which multiball is active
        self._set_multiball_color()

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

    def check_bypass(self, **kwargs):
        # These are the conditions in which we should bypass. Using this inverse
        # (double negative) so it can bail on the first *and* instead of processing
        # every *or*
        if not self.machine.multiball_locks.fmball_lock.enabled and \
            (self.machine.ball_holds.captive_hold.balls_held>=0 or not self.machine.ball_holds.captive_hold.enabled) and \
            not self.machine.ball_holds.store_hold.enabled and \
            not self.machine.ball_holds.arrival_hold.enabled and \
            not self.machine.ball_holds.sb_hold.enabled:
                self.log.debug("Bypass check failed, holding ball.")
                return
        # No balls? Longer pulse
        if self.machine.ball_devices.bd_lock.balls==0:
            self.machine.coils['c_lock_release'].timed_enable(timed_enable_ms=700)
        # Balls? Pulse with the default_timed_enable_ms
        else:
            self.machine.coils['c_lock_release'].timed_enable()


    def _set_multiball_color(self, **kwargs):
        # Re-define the named_color according to which multiball it is
        color = "color_overlord" if self.machine.device_manager.collections["achievements"].arrival.state == "disabled" else "color_arrival"
        self.machine.game.player["color_mball"] = color

    def _post_event(self, event, **kwargs):
        """ Helper method for posting events """
        self.machine.events.post(event, **kwargs)

    def _debug_lightshot_hit(self, **kwargs):
        self.log.info("FMBALL was hit, where we at?")
        self.log.info("Achievements are {}".format(self.player.achievements))

        self.log.info("FMBALL lock is {}".format(self._logicallockdevice))
        self.log.info(" - enabled? {}".format(self._logicallockdevice.enabled))
        self.log.debug("At this moment, multiball color is: {}".format(self.player["color_mball"]))

    def _debug_enter(self, **kwargs):
        self.log.info("Ball has entered the airlock, lock is enabled? {}".format(self._logicallockdevice.enabled))
        self.log.info(" - logical lock has {} balls locked, physical device has {} balls".format(
            self._logicallockdevice.locked_balls,
            self._bd_physical_lock.balls))
