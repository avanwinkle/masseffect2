"""Custom logic for handling Legion's advancing shots."""

import logging
from mpf.core.mode import Mode

SHOTS = ["left_orbit", "kickback", "left_ramp", "right_ramp", "right_orbit"]
BANKS = ["dropbank", "hitbank"]
TICK_WINDOW = [8, 10, 18, 20]
TOTAL_PROGRESS = 300


class RecruitLegion(Mode):
    """Mode code for managing Legion shot progressions, timeouts, and resets."""

    def __init__(self, machine, config, name, path):
        """Initialize logger and local vars."""
        super().__init__(machine, config, name, path)
        self.log = logging.getLogger("RecruitLegion Heretics")
        self.log.setLevel("INFO")
        self._timer = None
        # Track an array of ticks that _might_ need handling, to avoid over-processing
        self._significant_ticks = []
        self._shot_times = {}
        # Track whether precomplete is achieved, to award levelup if complete fails
        self._is_precomplete = None

    def mode_will_start(self, **kwargs):
        """Watch the timer and bind shot events."""
        self._timer = self.machine.device_manager.collections["timers"]["missiontimer"]
        self._significant_ticks = []
        self._shot_times = {}
        self._is_precomplete = False
        self.add_mode_event_handler("timer_missiontimer_tick", self._on_tick)
        self.add_mode_event_handler("legion_precomplete", self._on_precomplete)
        self.add_mode_event_handler("recruit_legion_complete", self._on_complete, priority=1000)
        for shot_name in SHOTS:
            self.add_mode_event_handler("player_shot_heretic_shot_{}_enabled".format(shot_name),
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
        # If the shot was disabled, reset and quit (or if the mode hasn't started yet)
        if not kwargs["value"] or not self.active:
            self._clear_shot(shot_name)
            return

        timestamp = self._timer.ticks_remaining
        ticks = [timestamp - interval for interval in TICK_WINDOW]
        self._shot_times[shot_name] = ticks
        # Calculate some significant ticks
        self._significant_ticks += ticks
        self.log.debug("Added significant ticks for {} based at {}: {}".format(shot_name, timestamp, ticks))

    def _on_tick(self, **kwargs):
        tick = kwargs["ticks_remaining"]
        # If there's no possible action on this tick, don't even look for one
        if not kwargs["ticks_remaining"] in self._significant_ticks:
            return

        for shot_name, times in self._shot_times.items():
            if tick in times:
                shot = self._get_shot(shot_name)
                self.log.info("Found a significant event at tick {} for shot {}".format(tick, shot_name))
                # The shot's advance method will handle if it's disabled
                shot.advance()
                # If that's the last tick? Disable
                if tick == times[3]:
                    shot.disable()
                    self.machine.events.post("heretic_shot_{}_timeout".format(shot_name))

    def _on_bank(self, **kwargs):
        hit_shot_name = kwargs.get("shot_name")
        # Check if both banks are off. If so, restart the timer/scoring
        for shot_name in BANKS:
            shot = self._get_shot(shot_name)
            # If that's the one that was hit? disable it
            if shot_name == hit_shot_name:
                shot.disable()
            # If it's not the one that was hit, is the other enabled?
            elif shot.enabled:
                self.log.debug("Bank {} hit but {} is still enabled, skipping".format(hit_shot_name, shot_name))
                return
        # Both banks are disabled? Allow shots again
        self.machine.events.post("heretic_banks_cleared")

        # If there are no shots, enable one
        if not self._shot_times:
            self.machine.events.post("enable_random_heretic")

    def _on_hit(self, **kwargs):
        shot_name = kwargs["shot_name"]
        shot = self._get_shot(shot_name)
        player = self.machine.game.player

        if player["temp_multiplier"] == 0:
            self.log.info("Shot {} was hit but banks are enabled. No progress awarded.".format(shot_name))
        else:
            # Award a point of progress for every second left on the shot
            progress_points = self._timer.ticks_remaining - self._shot_times[shot_name][3]
            self.log.info("Shot {} was hit at {} and timeout was {}, awarding {} points!".format(
                          shot_name, self._timer.ticks_remaining, self._shot_times[shot_name][3], progress_points))
            if progress_points < 0:
                self.log.warn("PROGRESS POINTS LESS THAN ZERO?!")
                progress_points = 0
            player["heretic_progress"] = min(
                player["heretic_progress"] + (progress_points * int(TOTAL_PROGRESS/60)), TOTAL_PROGRESS)

        self._clear_shot(shot_name)
        shot.disable()

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
        self._on_precomplete = True

    def _on_complete(self, **kwargs):
        # This event is high enough priority to remove the precomplete before the mode ends
        self._on_precomplete = False

    def _get_shot(self, shot_name):
        return self.machine.device_manager.collections["shots"]["heretic_shot_{}".format(shot_name)]

    def _clear_shot(self, shot_name):
        self._shot_times.pop(shot_name, None)
