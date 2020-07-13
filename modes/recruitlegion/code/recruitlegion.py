"""Custom logic for handling Legion's advancing shots."""
import time
import logging
from mpf.core.mode import Mode

SHOTS = ["left_orbit", "kickback", "left_ramp", "right_ramp", "right_orbit"]
BANKS = ["dropbank", "hitbank"]
TICK_WINDOW = [8, 10, 18, 20]
TOTAL_PROGRESS = 300


class RecruitLegion(Mode):
    """Mode code for managing Legion shot progressions, timeouts, and resets."""

    def __init__(self, *args, **kwargs):
        """Initialize logger and local vars."""
        super().__init__(*args, **kwargs)
        self.log = logging.getLogger("RecruitLegion Heretics")
        self.log.setLevel(10)
        self._timer = None
        # Track an array of ticks that _might_ need handling, to avoid over-processing
        self._significant_ticks = []
        self._shot_times = {}
        self._shot_group = None
        # Track whether precomplete is achieved, to award levelup if complete fails
        self._is_precomplete = None
        # Track whether we are processing a tick, to avoid collissions
        self._block_on_tick = False
        self._block_on_rotate = False

    def mode_will_start(self, **kwargs):
        """Watch the timer and bind shot events."""
        self._timer = self.machine.device_manager.collections["timers"]["missiontimer"]
        self._shot_group = self.machine.device_manager.collections["shot_groups"]["heretic_shots"]
        self._significant_ticks = []
        self._shot_times = {}
        self._is_precomplete = False
        self.add_mode_event_handler("timer_missiontimer_tick", self._on_tick)
        self.add_mode_event_handler("legion_precomplete", self._on_precomplete)
        self.add_mode_event_handler("recruit_legion_complete", self._on_complete, priority=1000)
        self.add_mode_event_handler("powers_cloak_rotation", self._on_cloak_rotate)
        for shot_name in SHOTS:
            self.add_mode_event_handler("enable_heretic_shot_{}".format(shot_name),
                                        self._start_shot_tracking,
                                        shot_name=shot_name)
            self.add_mode_event_handler("heretic_shot_{}_hit".format(shot_name),
                                        self._on_hit,
                                        shot_name=shot_name)
        for shot_name in BANKS:
            self.add_mode_event_handler("heretic_shot_{}_hit".format(shot_name),
                                        self._on_bank,
                                        shot_name=shot_name)
        self.log.debug("Added mode event handlers for shots: {}".format(SHOTS))

    def mode_will_stop(self, **kwargs):
        # If the mode stops during precomplete, sneak in a levelup
        if self._is_precomplete:
            self.machine.game.player["level"] += 1

    def _start_shot_tracking(self, **kwargs):
        shot_name = kwargs["shot_name"]
        # If the mode hasn't started yet, don't count a lagging hit event
        if not self.active:
            self._clear_shot(shot_name)
            return

        timestamp = self._timer.ticks_remaining
        ticks = [timestamp - interval for interval in TICK_WINDOW]
        self.log.debug("Setting up shot times for shot {} with ticks: {}".format(shot_name, ticks))
        self._shot_times[shot_name] = ticks
        # Calculate some significant ticks
        self._significant_ticks += ticks
        self.log.debug("Added significant ticks for {} based at {}: {}".format(shot_name, timestamp, ticks))

    def _on_tick(self, **kwargs):
        tick = kwargs["ticks_remaining"]
        # If there's no possible action on this tick, don't even look for one
        if not tick in self._significant_ticks:
            return

        while self._block_on_rotate is True:
            time.sleep(0.02)  # 2ms wait
        self._block_on_tick = True
        for shot_name, times in self._shot_times.items():
            # The rotation creates a None value for 'times', so check its truthiness first
            if times and tick in times:
                shot = self._get_shot(shot_name)
                self.log.debug("Found a significant event at tick {} for shot {}".format(tick, shot_name))
                shot.advance()
                # If that's the last tick? Restart to set to the "off" state
                if tick == times[3]:
                    shot.restart()
                    self._clear_shot(shot_name)
                    self.machine.events.post("heretic_shot_{}_timeout".format(shot_name))
        self._block_on_tick = False
        
    def _on_bank(self, **kwargs):
        hit_shot_name = kwargs.get("shot_name")
        # Check if both banks are off. If so, restart the timer/scoring
        banks_disabled = True
        for shot_name in BANKS:
            bankshot = self._get_shot(shot_name)
            # If that's the one that was hit? disable it
            if shot_name == hit_shot_name:
                bankshot.disable()
            # If it's not the one that was hit, is the other enabled?
            elif bankshot.enabled:
                self.log.debug("Bank {} hit but {} is still enabled, skipping".format(hit_shot_name, shot_name))
                banks_disabled = False

        # Both banks are disabled? Allow shots again
        if banks_disabled:
            self.machine.events.post("heretic_banks_cleared")

            # If there are no shots, enable one
            if not self._shot_times:
                self.machine.events.post("enable_random_heretic")

    def _on_hit(self, **kwargs):
        shot_name = kwargs["shot_name"]
        shot = self._get_shot(shot_name)
        player = self.machine.game.player

        if player["temp_multiplier"] == 0:
            self.log.debug("Shot {} was hit but banks are enabled. No progress awarded.".format(shot_name))
        elif not self._shot_times[shot_name]:
            self.log.debug("Shot {} was hit but it's been rotated away. No action.".format(shot_name))
        else:
            self.log.debug("Shot {} was hit, shot times are {}".format(shot_name, self._shot_times))
            # Award a point of progress for every second left on the shot
            progress_points = self._timer.ticks_remaining - self._shot_times[shot_name][3]
            self.log.info("Shot {} was hit at {} and timeout was {}, awarding {} points!".format(
                          shot_name, self._timer.ticks_remaining, self._shot_times[shot_name][3], progress_points))
            if progress_points < 0:
                self.log.warn("PROGRESS POINTS LESS THAN ZERO?!")
                progress_points = 0
            player["heretic_progress"] = min(
                player["heretic_progress"] + (progress_points * int(TOTAL_PROGRESS/60)), TOTAL_PROGRESS)
        self.log.debug("Shot {} was hit, clearing it.".format(shot_name))
        self._clear_shot(shot_name)
        shot.restart()
        
        # If we are done?
        if player["heretic_progress"] == TOTAL_PROGRESS:
            self.machine.events.post("recruit_legion_precomplete")
        # If there are no shots, enable one
        elif not self._shot_times:
            self.log.info("All heretic shots have been hit, forcing one to enable.")
            self.machine.events.post("enable_random_heretic")

    def _on_precomplete(self, **kwargs):
        # Clear out significant ticks to avoid any advancement processing
        self._significant_ticks = []
        self._is_precomplete = True

    def _on_complete(self, **kwargs):
        # This event is high enough priority to remove the precomplete before the mode ends
        self._is_precomplete = False

    def _get_shot(self, shot_name):
        return self.machine.device_manager.collections["shots"]["heretic_shot_{}".format(shot_name)]

    def _clear_shot(self, shot_name):
        self._shot_times.pop(shot_name, None)

    def _on_cloak_rotate(self, **kwargs):
        direction = kwargs["direction"]
        while self._block_on_tick is True:
            time.sleep(0.02)  # 2ms wait
        self._block_on_rotate = True
        if direction == "left":
            new_shot_times = {
                "left_orbit": self._shot_times.get("kickback"),
                "kickback": self._shot_times.get("left_ramp"),
                "left_ramp": self._shot_times.get("right_ramp"),
                "right_ramp": self._shot_times.get("right_orbit"),
                "right_orbit": self._shot_times.get("left_orbit")
            }
        else:
            new_shot_times = {
                "left_orbit": self._shot_times.get("right_orbit"),
                "kickback": self._shot_times.get("left_orbit"),
                "left_ramp": self._shot_times.get("kickback"),
                "right_ramp": self._shot_times.get("left_ramp"),
                "right_orbit": self._shot_times.get("right_ramp")
            }
        # Don't preserve None values, so we can easily identify when there are no shot times
        self._shot_times = {k: v for k, v in new_shot_times.items() if v is not None}
        # And do the rotation as well
        self._shot_group.rotate(direction=direction)
        self._block_on_rotate = False
        