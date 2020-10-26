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
  number = 1
  title = "Rosalie Lost"
  def on_hit(self, shotname):
    # Advance all shots
    for shot in self._shots:
      shot.advance()


class SurveySites(FwRulesBase):
  number = 2
  title = "Survey Sites"
  def on_hit(self, shotname):
    # Advance all enabled shots, and disable the hit one
    for shot in self._shots:
      if shot.name == shotname:
        shot.disable()
      elif shot.enabled:
        shot.advance()


class GethIncursion(FwRulesBase):
  number = 3
  title = "Geth Incursion"
  def on_hit(self, shotname):
    # Advance only the hit shot
    for shot in self._shots:
      if shot.name == shotname:
        shot.advance()


class VolcanoStation(FwRulesBase):
  number = 4
  title = "Volcano Station"
  def on_hit(self, shotname):
    # Advance only the hit shot, reset the rest
    for shot in self._shots:
      if shot.name == shotname:
        shot.advance()
      else:
        shot.reset()


class ProtheanSite(FwRulesBase):
  number = 5
  title = "Prothean Site"
  def on_hit(self, shotname):
    pass


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

  def _handle_hit(self, **kwargs):
    self.rules.on_hit(kwargs["shotname"])
