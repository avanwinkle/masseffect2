import logging
from mpf.core.custom_code import CustomCode

SQUADMATES = ("garrus", "grunt", "jack", "kasumi", "legion", "mordin", "samara", "tali", "thane", "zaeed")
BIOTICMATES = ("jack", "jacob", "miranda", "samara", "thane")
TECHMATES = ("garrus", "jacob", "kasumi", "legion", "mordin", "tali", "thane")

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

class SquadmateStatusClass():
  def __init__(self):
    self.log = logging.getLogger("SquadmateStatus")
    self.log.info("Squadmate Status ready!")

  def _mate_status_is(self, player, squadmate, status):
    return player["status_{}".format(squadmate)] == status

  def _get_available_mates(self, player, mates, include_specialist=True):
    specialist = None if include_specialist else player["specialist"]
    return [mate for mate in mates if (self._mate_status_is(player, mate, 4) and mate != specialist)]

  def all_mates(self):
    return SQUADMATES

  def all_biotics(self):
    return BIOTICMATES

  def all_techs(self):
    return TECHMATES

  def available_mates(self, player, **kwargs):
    return self._get_available_mates(player, SQUADMATES, **kwargs)

  def available_biotics(self, player):
    return self._get_available_mates(player, BIOTICMATES)

  def available_techs(self, player):
    return self._get_available_mates(player, TECHMATES)

  def dead_mates(self, player):
    return [mate for mate in SQUADMATES if (self._mate_status_is(player, mate, -1))]

SquadmateStatus = SquadmateStatusClass()

class SquadmateHandlers(CustomCode):
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
    self._current_recruit = None

    self.machine.log.info("MPF BCP: {}".format(self.machine.bcp))
    self.machine.log.info(" - BCP Transports: {}".format(self.machine.bcp.transport._transports))

    # Create a listener for a recruitmission to start
    self.machine.events.add_handler("missionselect_recruitmission_selected", self._on_missionselect)
    # Create a listener for the field mode to start
    self.machine.events.add_handler("mode_field_started", self._enable_shothandlers)

  def _enable_shothandlers(self, **kwargs):
    self.machine.events.remove_handler(self._enable_shothandlers)
    self.machine.events.add_handler("mode_field_stopped", self._disable_shothandlers)
    for mate in SQUADMATES:
      if self.machine.game.player["status_{}".format(mate)] < 4:
        self.machine.events.add_handler("recruit_{}_shot_hit".format(mate), self._on_hit, squadmate=mate)
    self.machine.log.info("Created a bunch of shothandlers! {}".format(self))

  def _disable_shothandlers(self, **kwargs):
    self.machine.events.remove_handler(self._on_hit)
    self.machine.events.remove_handler(self._disable_shothandlers)
    self.machine.events.add_handler("mode_field_started", self._enable_shothandlers)

  def _on_hit(self, **kwargs):
    self.log.debug("Received recruit HIT event with kwargs: {}".format(kwargs))
    mate = kwargs["squadmate"]
    future_mate_status = self.machine.game.player["status_{}".format(mate)] + 1

    if 0 < future_mate_status <= 3:
      self.machine.events.post("recruit_advance", squadmate=mate, status=future_mate_status)

      if future_mate_status == 3:
        self.machine.events.post("recruit_lit", squadmate=mate)


      self.machine.game.player["status_{}".format(mate)] = future_mate_status
      self.machine.game.player["recruits_color"] = COLORS[mate]
      self.machine.events.post("flash_all_shields")

  def _on_missionselect(self, **kwargs):
    mate = kwargs["squadmate"]
    self._current_mate = mate
    self.machine.events.post("start_mode_recruit{}".format(mate))

    self.machine.events.add_handler("recruit_{}_complete".format(mate), self._on_complete, squadmate=mate)
    self.machine.events.add_handler("mode_recruit{}_stopped".format(mate), self._on_stop)

  def _on_stop(self, **kwargs):
    self.machine.events.remove_handler(self._on_stop)
    self.machine.events.remove_handler(self._on_complete)

  def _on_complete(self, **kwargs):
    self.log.debug("Received COMPLETE event with kwargs: {}".format(kwargs))

    mate = kwargs["squadmate"]
    self.machine.events.post("levelup", mission_name="{} Recruited".format(mate))
    self.machine.events.post("recruit_success", squadmate=mate)
    self.machine.events.post("recruit_success_{}".format(mate))
    self.machine.game.player["status_{}".format(mate)] = 4

