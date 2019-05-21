import logging
from mpf.core.mode import Mode


class Airlock(Mode):

    def __init__(self, machine, config, name, path):
        super().__init__(machine, config, name, path)
        self.log = logging.getLogger("LockHandler")
        self.log.setLevel(10)
        self.settings = config.get("mode_settings")

    def mode_start(self, **kwargs):
        super().mode_start(**kwargs)
        self.log.info("Airlock Mode is starting")
        self.add_mode_event_handler("fmball_lightshot_hit", self._debug_lightshot_hit)
        self.add_mode_event_handler("s_battering_ram_active", self._debug_enter)
        ball_locks = self.machine.device_manager.get_monitorable_devices().get("multiball_locks")
        self.lock = ball_locks["fmball_lock"]

    def _debug_lightshot_hit(self, **kwargs):
        self.log.info("FMBALL was hit, where we at?")
        self.log.info("Achievements are {}".format(self.player.achievements))
        ball_locks = self.machine.device_manager.get_monitorable_devices().get("multiball_locks")
        self.log.info("Ball locks are {}".format(ball_locks))
        # self.log.info("Collections are {}".format(self.machine.device_manager.collections))
        # ball_lock_coll = self.machine.device_manager.collections["multiball_locks"]
        # self.log.info("ball lock collections are {}".format(ball_lock_coll))

        self.log.info("FMBALL lock is {}".format(self.lock))
        self.log.info(" - enabled? {}".format(self.lock.enabled))

    def _debug_enter(self, **kwargs):
        self.log.info("Ball has entered the airlock, lock is enabled? {}".format(self.lock.enabled))
        self.log.info(" - lock has {} balls locked".format(self.lock.locked_balls))

