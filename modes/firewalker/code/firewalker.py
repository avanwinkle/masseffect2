import logging
from mpf.core.mode import Mode

SHOTS = ["left_orbit", "kickback", "left_ramp", "right_ramp", "right_orbit"]


class FwRulesBase:
  def __init__(self, shots, log):
    self._shots = shots
    self._log = log
    self._name = None

  def start(self):
    self._log.info("Starting {}".format(self.__class__))
    # Enable all shots at the initial state
    for shot in self._shots:
      shot.restart()

  @property
  def description(self):
    return self.__class__.description

  @property
  def number(self):
    return self.__class__.number


class Rosalie(FwRulesBase):
  """Intro mission, get the Hammerhead and climb the volcano spire."""
  number = 1
  title = "Rosalie Lost"
  intro_sound = "hmd_intro_location_unstable"
  failure_sound = "hmd_intro_find_safer_ground"

  def on_hit(self, shotname):
    # Each shot advances, so remaining is the number of states left
    # Take this number before advancing because the final shot doesn't advance
    shots_remaining = 3 - (self._shots[0].state + 1)
    # Advance all shots
    for shot in self._shots:
      shot.advance()
    return shots_remaining

class SurveySites(FwRulesBase):
  """Battle the Geth through the garbage site."""
  number = 2
  title = "Survey Sites"
  intro_sound = "hmd_proximity_alert_hostiles_detected"
  failure_sound = "hmd_warning_hull_damage"

  def on_hit(self, shotname):
    shots_remaining = 0
    # Advance all enabled shots, and disable the hit one
    for shot in self._shots:
      if shot.name == shotname:
        shot.disable()
        # This shot doesn't advance, so increment the state by one
        shots_remaining = 3 - (shot.state + 1)
      elif shot.enabled:
        shot.advance()
    return shots_remaining

class GethIncursion(FwRulesBase):
  """Race through the snow and collect packets before you freeze."""
  number = 3
  title = "Geth Incursion"
  intro_sound = "hmd_intro_temperatures_not_recommended"
  failure_sound = "hmd_warning_hull_temperature"

  def on_hit(self, shotname):
    shots_remaining = 0
    # Advance only the hit shot
    for shot in self._shots:
      if shot.name == shotname:
        # Return the shots remaining on *this* shot
        shots_remaining = 3 - (shot.state + 1)
        shot.advance()
    return shots_remaining

class VolcanoStation(FwRulesBase):
  """Leap the magma rivers."""
  number = 4
  title = "Volcano Station"
  intro_sound = "hmd_warning_lava"
  failure_sound = "hmd_warning_conditions_deteriorating"

  def on_hit(self, shotname):
    shots_remaining = 0
    # Advance only the hit shot, reset the rest
    for shot in self._shots:
      if shot.name == shotname:
        shots_remaining = 3 - (shot.state + 1)
        shot.advance()
      else:
        shot.reset()
    return shots_remaining


class ProtheanSite(FwRulesBase):
  """Rockets go boom!"""
  number = 5
  title = "Prothean Site"
  intro_sound = "hmd_hostile_activity_detected"
  failure_sound = "hmd_intro_initiating_emergency_reset"
  def on_hit(self, shotname):
    return 0


class Firewalker(Mode):
  def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)
    self.log = logging.getLogger("Firewalker")
    self.log.setLevel(10)

  def mode_start(self, **kwargs):
    super().mode_start(**kwargs)
    mission = self.machine.game.player["state_machine_firewalker"]
    shots = []
    for shot in SHOTS:
      shotname = "firewalker_{}".format(shot)
      shots.append(self.machine.device_manager.collections["shots"][shotname])
      self.add_mode_event_handler("{}_hit".format(shotname), self._handle_hit, shotname=shotname)
    self.rules = {
      "rosalie": Rosalie,
      "volcano_station": VolcanoStation,
      "geth_incursion": GethIncursion,
      "survey_sites": SurveySites,
      "prothean_site": ProtheanSite,
    }[mission](shots, self.log)

    self.rules.start()
    self.machine.events.post("firewalker_mission_started",
      title=self.rules.title,
      mission=mission,
      )
    self.machine.game.player["fw_number"] = self.rules.number
    self._play_sound(self.rules.intro_sound)
    self.add_mode_event_handler("firewalker_mission_failed",
                                self._on_failure, priority=1000)

    self.add_mode_event_handler("firewalker_mission_complete",
                                self._on_success, priority=1000)

  def _on_failure(self, **kwargs):
    del kwargs
    # Pass a different context so the end of the mode doesn't kill the sound
    self._play_sound(self.rules.failure_sound, context="firewalker_ended")

  def _on_success(self, **kwargs):
    del kwargs
    self._play_sound("hmd_all_data_packets_recovered", context="firewalker_ended")

  def _handle_hit(self, **kwargs):
    shots_remaining = self.rules.on_hit(kwargs["shotname"])

    if shots_remaining > 0:
      self._play_sound(f"hmd_{shots_remaining}_remains")

  def _play_sound(self, sound_name, context="firewalker"):
      settings = {
        sound_name: {
          "action": "play",
          "delay": 0,
          "track": "voice",
          "block": False,
          "volume": 0.7,
          "ducking": {
            "target": "music",
            "attenuation": 0.8,
            "attack": "50ms",
            "release": "50ms",
            "release_point": 0
          }
        }
      }
      self.machine.events.post("sounds_play",
        settings=settings,
        context=context,
        calling_context=None,
        priority=2
      )
