import random
from mpf.core.mode import Mode
from mpf.core.utility_functions import Util
from scriptlets.me_squadmates import SquadmateStatus

class SuicideBase(Mode):

  def mode_start(self, **kwargs):
    super().mode_start(**kwargs)
    self.player = self.machine.game.player
    # Listen for the suicide mission to fail and reset dead squadmates
    self.add_mode_event_handler("suicidemission_failed", self._handle_failure)
    self.add_mode_event_handler("kill_squadmate", self._kill_squadmate)

  def _set_status(self, squadmate, status):
    self.player["status_{}".format(squadmate)] = status

  def _kill_squadmate(self, **kwargs):
    mate = kwargs["squadmate"]
    if mate == "specialist":
      mate = self.player["specialist"]
    elif mate == "random":
      avail_mates = SquadmateStatus.available_mates(self.player, include_specialist=False)
      # If the specialist is the only mate left, kill them even if include_specialist is false
      mate = random.choice(avail_mates) if avail_mates else self.player["specialist"]
      self.add_mode_event_handler("squadmate_killed_callback",
        self._kill_squadmate_callback,
        squadmate=mate)

    self.info_log("Found a {} mate to kill: {}".format(kwargs["squadmate"], mate))
    self._set_status(mate, -1)
    self.player["squadmates_count"] -= 1
    # It's useful to know whether the ball is ending or not
    ball_is_ending = self.machine.modes["base"].stopping or not self.machine.modes["base"].active
    self.machine.events.post("squadmate_killed", squadmate=mate, ball_is_ending=ball_is_ending)

    # Are we out of squadmates?
    if not self._squadmates_can_continue():
      self.info_log("No squadmates available to be specialists. Suicide Mission has failed.")
      # Base will already be done if the ball is ending, set the state manually
      if ball_is_ending:
        self.player.achievements["suicidemission"] = "disabled"
        self.info_log(" - achievement suicidemisson has been manually disabled")
        self._handle_failure()
      else:
        self.machine.events.post("suicidemission_failed")

    # Until we have callbacks working, trigger the relay event too
    self.machine.events.post("squadmate_killed_complete", squadmate=mate)

    # Make a sound
    self._play_sound({
      "sound": "killed",
      "squadmate": mate,
      "mode": self._get_current_mode(),
    })

  def _kill_squadmate_callback(self, **kwargs):
    self._play_sound({
      "name": "play_squadmate_sound",
      "sound": "killed_callback",
      "killed_mate": kwargs["squadmate"],
      "callback_mate": random.choice(SquadmateStatus.available_mates(self.player)),
      "events_when_played": "squadmate_killed_complete",
    })

  def _squadmates_can_continue(self):
    if self.player["squadmates_count"] == 0:
      return False
    elif self.player.achievements["infiltration"] == "started" and not SquadmateStatus.available_techs(self.player):
      return False
    elif self.player.achievements["longwalk"] == "started" and not SquadmateStatus.available_biotics(self.player):
      return False
    return True

  def _handle_failure(self, **kwargs):
    # Reset all dead squadmates to recruitable
    for mate in SquadmateStatus.dead_mates(self.player):
      # Jacob and Miranda are already recruited
      if mate in ("jacob", "miranda"):
        self._set_status(mate, 4)
        self.player["squadmates_count"] += 1
      else:
        self._set_status(mate, 0)

  def _play_sound(self, sound_event):
    self.machine.events.post("play_squadmate_sound", **sound_event)

  def _get_current_mode(self):
    for mode in ["omegarelay", "infiltration", "longwalk", "platforms", "humanreaper", "escape"]:
      if self.machine.modes["suicide_{}".format(mode)].active:
        return mode
