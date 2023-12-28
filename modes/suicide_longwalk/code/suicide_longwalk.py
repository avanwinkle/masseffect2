import random
from mpf.core.mode import Mode
from custom_code.squadmate_status import SquadmateStatus

PATHSHOTS = ["dropbank", "left_orbit", "kickback", "left_ramp", "right_ramp", "right_orbit", "hitbank"]


class LongWalk(Mode):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._debug_to_console = True
        self._debug_to_file = True
        self._shots_to_complete = None
        self._random_chance = None
        self._last_shots = ["left_ramp"]  # Start with left ramp so it's never the first shot

    def mode_start(self, **kwargs):
        super().mode_start(**kwargs)
        # Get the shots_to_complete dynamically, because it varies by difficulty
        self._shots_to_complete = self.machine.device_manager.collections["counters"]["swarmpaths"].value
        # Normal difficulty has a 70% chance, insanity has only 30% chance
        self._random_chance = 0.7 - (0.2 * self.machine.game.player["difficulty"])
        self.info_log("Longwalk mode starting with {} shots to complete, available biotics are: {}".format(
            self._shots_to_complete,
            SquadmateStatus.available_biotics(self.machine.game.player)))

        # Create event handlers for the shot counter updating. Must be the counter event to track shots hit
        self.add_mode_event_handler('logicblock_swarmpaths_hit', self._enable_shots)
        # Enable one shot to start
        self._enable_shots()

    def _enable_shots(self, **kwargs):
        biotic_count = len(SquadmateStatus.available_biotics(self.machine.game.player))
        # This handler is triggered by the counter hit, so it'll pass the remaining as a count
        shots_remaining = kwargs.get('count', self._shots_to_complete)
        shots_hit = self._shots_to_complete - shots_remaining
        shot1 = None

        # Last shot is always left ramp
        if shots_remaining == 1:
            shot1 = "left_ramp"
        else:
            # Pick a random shot
            while not shot1 or shot1 in self._last_shots:
                shot1 = random.choice(PATHSHOTS)

        self._enable_shot(shot1)
        self._last_shots = [shot1]

        self.info_log("Calculating random shot: {} hit, {} remaining, {} avail biotics".format(
            shots_hit, shots_remaining, biotic_count))

        # No bonus shots on the first and last
        if shots_hit == 0 or shots_remaining == 1:
            self.info_log(" - No bonus shot on first/last swarmpath")
            return

        # If the num of available biotics warrants it, XX% chance of another shot lighting
        if shots_hit + 1 <= biotic_count and random.random() < self._random_chance:
            # 50% chance it lights to the left, 50% to the right
            adj = random.choice([-1, 1])
            shot2 = PATHSHOTS[(PATHSHOTS.index(shot1) + adj) % len(PATHSHOTS)]  # use modulo to wrap around
            self.info_log(" - Adding shot {} to initial shot {}".format(shot2, shot1))
            self._enable_shot(shot2)
            self._last_shots.append(shot2)
        else:
            self.info_log(" - No random shot this time")

    def _enable_shot(self, shotname):
        self.machine.events.post("enable_longwalk_{}".format(shotname))
