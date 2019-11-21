import logging
from mpf.core.mode import Mode

SHOTS = ["left_orbit", "kickback", "left_ramp", "right_ramp", "right_orbit"]


class FwRulesBase:
  def __init__(self, shots, log):
    self._shots = shots
    self._log = log
    self._name = None

  def start(self):
    self._log("Starting {}".format(self.__class__))
    # Enable all shots at the initial state
    for shot in self._shots:
      shot.restart()


class Rosalie(FwRulesBase):
  def on_hit(self, shotname):
    # Advance all shots
    for shot in self._shots:
      shot.advance()


class VolcanoStation(FwRulesBase):
  def on_hit(self, shotname):
    # Advance all enabled shots, and disable the hit one
    for shot in self._shots:
      if shot.name == shotname:
        shot.disable()
      elif shot.enabled:
        shot.advance()


class GethIncursion(FwRulesBase):
  def on_hit(self, shotname):
    # Advance only the hit shot
    for shot in self._shots:
      if shot.name == shotname:
        shot.advance()


class SurveySites(FwRulesBase):
  def on_hit(self, shotname):
    # Advance only the hit shot, reset the rest
    for shot in self._shots:
      if shot.name == shotname:
        shot.advance()
      else:
        shot.reset()


class ProtheanSite(FwRulesBase):
  def on_hit(self, shotname):
    pass


class Firewalker(Mode):
  def __init__(self, machine, config, name, path):
    super().__init__(machine, config, name, path)
    self.log = logging.getLogger("Firewalker")
    self.log.setLevel(10)

  def mode_start(self, **kwargs):
    super().mode_start(**kwargs)
    shots = []
    for shot in SHOTS:
      shotname = "firewalker_{}".format(shot)
      shots.append(self.machine.device_manager.collections["shots"][shotname])
      self.add_mode_event_handler("{}_hit".format(shotname), self._handle_hit, shot=shotname)
    self.rules = {
      "rosalie": Rosalie,
      "volcano_station": VolcanoStation,
      "geth_incursion": GethIncursion,
      "survey_sites": SurveySites,
      "prothean_site": ProtheanSite,
    }[self.machine.game.player["state_machine_firewalker"]](shots, self.log)

    self.rules.start()

  def _handle_hit(self, shotname, **kwargs):
    self.rules.on_hit(shotname)
