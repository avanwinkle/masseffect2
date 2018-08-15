import logging
import random
from mpf.core.mode import Mode
from scriptlets.me_squadmates import SquadmateStatus

PATHSHOTS = ["dropbank", "left_orbit", "kickback", "left_ramp", "right_ramp", "right_orbit", "hitbank"]
SHOTS_TO_COMPLETE = 7 # This value must match the swarmpaths counter starting_count value!
RANDOMCHANCE = 0.7 # Percent chance that an available double shot will come up

class LongWalk(Mode):

  def __init__(self, machine, config, name, path):
    super().__init__(machine, config, name, path)
    self._debug_to_console = True
    self._debug_to_file = True
    self._last_shots = ["left_ramp"] # Start with left ramp so it's never the first shot

  def mode_start(self, **kwargs):
    super().mode_start(**kwargs)
    self.info_log("Longwalk mode starting, available biotics are: {}".format(
      SquadmateStatus.available_biotics(self.machine.game.player)))

    # Create event handlers for the shot counter updating. Must be the counter event to track shots hit
    self.add_mode_event_handler('logicblock_swarmpaths_hit', self._enable_shots)
    # Enable one shot to start
    self._enable_shots()

  def _enable_shots(self, **kwargs):
    biotic_count = len(SquadmateStatus.available_biotics(self.machine.game.player))
    shots_remaining = kwargs.get('count', SHOTS_TO_COMPLETE)
    shots_hit = SHOTS_TO_COMPLETE - shots_remaining
    shot1 = None

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
    if shots_hit + 1 <= biotic_count and random.random() < RANDOMCHANCE:
      # 50% chance it lights to the left, 50% to the right
      adj = random.choice([-1, 1])
      shot2 = PATHSHOTS[(PATHSHOTS.index(shot1) + adj) % len(PATHSHOTS)] # use modulo to wrap around
      self.info_log(" - Adding shot {} to initial shot {}".format(shot2, shot1))
      self._enable_shot(shot2)
      self._last_shots.append(shot2)
    else:
      self.info_log(" - No random shot this time")

  def _enable_shot(self, shotname):
    self.machine.events.post("enable_longwalk_{}".format(shotname))
