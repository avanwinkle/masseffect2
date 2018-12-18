import logging
from mpf.core.custom_code import CustomCode

SQUADMATES = ("garrus", "grunt", "jack", "jacob", "kasumi", "legion", "miranda", "mordin", "samara", "tali", "thane", "zaeed")
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

  def _get_available_mates(self, player, mates=SQUADMATES, status=4, include_specialist=True):
    specialist = None if include_specialist else player["specialist"]
    return [mate for mate in mates if (self._mate_status_is(player, mate, status) and mate != specialist)]

  def all_mates(self):
    return SQUADMATES

  def all_biotics(self):
    return BIOTICMATES

  def all_techs(self):
    return TECHMATES

  def available_mates(self, player, **kwargs):
    return self._get_available_mates(player, **kwargs)

  def available_biotics(self, player):
    return self._get_available_mates(player, mates=BIOTICMATES)

  def available_techs(self, player):
    return self._get_available_mates(player, mates=TECHMATES)

  def recruitable_mates(self, player):
    return self._get_available_mates(player, status=3)

  def dead_mates(self, player):
    return self._get_available_mates(player, status=-1)

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
    # Create a listener for a recruitmission to be resumed
    self.machine.events.add_handler("resume_mission", self._on_missionselect)
    # Create a listener for the field mode to start
    self.machine.events.add_handler("mode_field_started", self._enable_shothandlers)
    # Create a listener for a ball to start
    self.machine.events.add_handler("mode_base_started", self._initialize_icons)

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

  def _initialize_icons(self, **kwargs):
    for mate in SQUADMATES:
      status = self.machine.game.player["status_{}".format(mate)]
      event = None
      if status == 3:
        event = "set_recruiticon_available"
      elif status == 4:
        event = "set_recruiticon_complete"
      elif status == -1:
        event = "set_recruiticon_dead"
      if event:
        self.machine.events.post(event, squadmate=mate)

  def _on_hit(self, **kwargs):
    player = self.machine.game.player
    self.log.debug("Received recruit HIT event with kwargs: {}".format(kwargs))
    mate = kwargs["squadmate"]
    future_mate_status = player["status_{}".format(mate)] + 1

    if 0 < future_mate_status <= 3:
      self.machine.events.post("recruit_advance", squadmate=mate, status=future_mate_status)
      self.machine.events.post("queue_widget", widget="recruit_advance_widget_{}".format(future_mate_status),
                                               squadmate=mate, status=future_mate_status)

      if future_mate_status == 3:
        self.machine.events.post("recruit_lit", squadmate=mate)
        self.machine.events.post("set_recruiticon_available", squadmate=mate)
        # If there were no mates lit before, bonus the xp
        xp = self.machine.get_machine_var("unlock_xp") * (
          1 + (0 if SquadmateStatus.recruitable_mates(player) else self.machine.get_machine_var("bonus_xp")))
        player["xp"] += xp

      player["status_{}".format(mate)] = future_mate_status
      player["recruits_color"] = COLORS[mate]
      self.machine.events.post("flash_all_shields")

  def _on_missionselect(self, **kwargs):
    mate = kwargs["squadmate"]
    self._current_mate = mate
    self.machine.events.post("start_mode_recruit{}".format(mate))

    self.machine.events.add_handler("recruit_{}_complete".format(mate), self._on_complete, squadmate=mate)
    self.machine.events.add_handler("mode_recruit{}_stopped".format(mate), self._on_stop, squadmate=mate)

  def _on_stop(self, **kwargs):
    self.log.info("on_stop called for recruit mission, kwargs are {}".format(kwargs))
    self.machine.events.remove_handler(self._on_stop)
    self.machine.events.remove_handler(self._on_complete)

    # If we stopped without an explicit success
    if not kwargs.get("success"):
      # If we failed or timed out, post an event
      if  self.machine.modes["global"].active and not self.machine.modes["global"].stopping:
        self.machine.events.post("recruit_failure_{}".format(kwargs.get("squadmate")))
      # If we drained, # store this mission so we can resume if it fails
      else:
        self.machine.game.player["resume_mission"] = kwargs.get("squadmate")

  def _on_complete(self, **kwargs):
    self.log.debug("Received COMPLETE event with kwargs: {}".format(kwargs))
    mate = kwargs["squadmate"]

    self.machine.game.player["xp"] += self.machine.get_machine_var("mission_xp") * (
      1 + (self.machine.get_machine_var("bonus_xp") if kwargs.get("under_par") else 0))

    self.machine.events.post("levelup", mission_name="{} Recruited".format(mate))
    self.machine.events.post("recruit_success", squadmate=mate)
    self.machine.events.post("set_recruiticon_complete", squadmate=mate)
    self.machine.events.post("recruit_success_{}".format(mate))
    self.machine.game.player["status_{}".format(mate)] = 4
    self._on_stop(success=True, **kwargs)

    # See if we had previously failed the Suicide Mission, and if so, do we now
    # have enough tech/biotic squadmates to try again?
    achs = self.machine.game.player.achievements
    if (achs["normandyattack"] == "completed" and achs["suicidemission"] == "disabled"):
      self.log.debug("Recruitmend successful, should we re-enable the suicide mission? {} techs, {} biotics".format(
        len(SquadmateStatus.available_techs), len(SquadmateStatus.available_biotics)))
      if len(SquadmateStatus.available_techs) > 1 and len(SquadmateStatus.available_biotics) > 1:
        achs["suicidemission"].enable()

