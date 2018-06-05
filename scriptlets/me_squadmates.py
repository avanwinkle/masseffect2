import logging
from mpf.core.scriptlet import Scriptlet

SQUADMATES = ("garrus", "grunt", "jack", "kasumi", "legion", "mordin", "samara", "tali", "thane", "zaeed")

LEDS = {
  "garrus": "color_shield_blue",
  "grunt": "color_shield_orange",
  "jack": "color_shield_purple",
  "kasumi": "color_shield_yellow",
  "legion": "color_shield_white",
  "mordin": "color_shield_red",
  "samara": "l_iron_throne",
  "tali": "l_right_return_lane",
  "thane": "color_shield_green",
  "zaeed": "l_hand_of_the_king",
}

COLORS = {
  "garrus": "0E1B4F",
  "grunt": "EF521F",
  "jack": "7B3FB8",
  "kasumi": "F7F315",
  "legion": "FFFFFF",
  "mordin": "BD000A",
  "samara": "0037FF",
  "tali": "D323FF",
  "thane": "00FF00",
  "zaeed": "FF0000",
}

class MESquadmates(Scriptlet):
  """
  This scriptlet handles the recruit_advance and recruit_lit events for squadmate progression tracking. It's
  a convenient way to automate the event postings over all squadmates without a bunch of copy+paste in the yaml
  files.

  Possible extensions of this scriptlet:
   - Incrementing the status_squadmate player variable
   - Creating, enabling, disabling recruit lane shots
   - Creating, playing, stopping recruit lit/complete shows
   """
  def on_load(self):
    self.log = logging.getLogger("MESquadmates")
    self.log.setLevel('DEBUG')

    for mate in SQUADMATES:
      # TODO: Add and remove these shot handlers as field mode is enabled/disabled?
      self.machine.events.add_handler("recruit_{}_shot_hit".format(mate), self._on_hit, squadmate=mate)
      # TODO: Add and remove these shot handlers as individual recruit modes are enabled/disabled?
      self.machine.events.add_handler("recruit_{}_complete".format(mate), self._on_complete, squadmate=mate)

  def _on_hit(self, **kwargs):
    self.log.debug("Received HIT event with kwargs: {}".format(kwargs))
    mate = kwargs["squadmate"]
    future_mate_status = self.machine.game.player["status_{}".format(mate)] + 1

    if 0 < future_mate_status <= 3:
      self.machine.events.post("recruit_advance", squadmate=mate, status=future_mate_status)
      self.machine.events.post("recruit_advance_{}".format(mate))

      if future_mate_status == 3:
        self.machine.events.post("recruit_lit", squadmate=mate)

      self.machine.game.player["recruits_color"] = COLORS[mate]
      self.machine.events.post("flash_all_shields")

  def _on_complete(self, **kwargs):
    self.log.debug("Received COMPLETE event with kwargs: {}".format(kwargs))
    self.machine.events.post("levelup", mission_name="{} Recruited".format(kwargs["squadmate"]))
    self.machine.events.post("recruit_success", squadmate=kwargs["squadmate"])
    self.machine.events.post("recruit_success_{}".format(kwargs["squadmate"]))
