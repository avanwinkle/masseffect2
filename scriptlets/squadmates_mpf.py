import logging
from .squadmate_status import SquadmateStatus
from mpf.core.custom_code import CustomCode

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

SOUND_NAME_FORMATS = {
  "destroy_core":    "squadmate_{squadmate}_destroy_core",
  "killed":          "squadmate_{squadmate}_killed",
  "killed_callback": "squadmate_{squadmate}_killed_callback_{callback_mate}",
  "skillshot":       "squadmate_{squadmate}_nice_shot",
}
COMPLETED_EVENT_NAME = {
  "killed":          "squadmate_killed_complete"
}

class MPFSquadmateHandlers(CustomCode):
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
    self._current_recruit = None
    self._just_resumed = False

    # Create a listener for a recruitmission to start
    self.machine.events.add_handler("missionselect_recruitmission_selected", self._on_missionselect)
    # Create a listener for a recruitmission to be resumed
    self.machine.events.add_handler("resume_mission", self._on_missionselect)
    # Create a listener for the field mode to start
    self.machine.events.add_handler("mode_field_started", self._enable_shothandlers)
    # Create a listener for a ball to start
    self.machine.events.add_handler("mode_base_started", self._initialize_icons)
    # Create a listener for playing a squadmate sound
    self.machine.events.add_handler("play_squadmate_sound", self._handle_squadmate_sound)

  def _enable_shothandlers(self, **kwargs):
    self.machine.events.remove_handler(self._enable_shothandlers)
    self.machine.events.add_handler("mode_field_stopped", self._disable_shothandlers)
    for mate in SquadmateStatus.all_mates():
      if self.machine.game.player["status_{}".format(mate)] < 4:
        self.machine.events.add_handler("recruit_{}_shot_hit".format(mate), self._on_hit, squadmate=mate)
    self.log.debug("Created a bunch of shothandlers! {}".format(self))

  def _disable_shothandlers(self, **kwargs):
    self.machine.events.remove_handler(self._on_hit)
    self.machine.events.remove_handler(self._disable_shothandlers)
    self.machine.events.add_handler("mode_field_started", self._enable_shothandlers)

  def _initialize_icons(self, **kwargs):
    for mate in SquadmateStatus.all_mates():
      status = self.machine.game.player["status_{}".format(mate)]
      event = None
      if status == 3 or status == 4 or status == -1:
        self.machine.events.post("set_recruiticon", squadmate=mate, status=status)

  def _handle_squadmate_sound(self, **kwargs):
    squadmate = kwargs.pop("squadmate", "random")
    if squadmate == "random":
      squadmate = SquadmateStatus.random_mate(self.machine.game.player, exclude=kwargs.get("exclude"))
    self.machine.log.info("Got a squadmate ({}) for playing sound '{}'".format(squadmate, kwargs['sound']))
    sound_name = SOUND_NAME_FORMATS[kwargs["sound"]].format(squadmate=squadmate, **kwargs)
    action = kwargs.get("action", "play")
    track = kwargs.get("track", "voice")
    # If a mode is supplied, append it to the sound name
    if kwargs.get("mode") == "infiltration":
      sound_name = "{}_{}".format(sound_name, kwargs["mode"])

    settings = {
      sound_name: {
        "action": action,
        "track": track,
      }
    }
    self.machine.log.info("SquadmateSounds made an asset to play: '{}' Args={}".format(sound_name, settings))
    # We can pass in playback event handlers too
    for config_name in ["events_when_played", "events_when_stopped"]:
      if kwargs.get(config_name):
        settings[sound_name][config_name] = kwargs.get(config_name)
    # Dunno what these do but the sound player expects them
    context = "squadmate_sounds"
    calling_context = None

    self.machine.events.post("sounds_play", settings=settings, context=context, calling_context=calling_context, priority=2)
    # If a callback mate is specified, play that too
    # EXCEPT for there's no Shepard callback for Miranda's death
    if action == "play" and kwargs.get("callback_mate") and (kwargs.get("callback_mate") == "shepard") != (kwargs.get("squadmate") == "miranda"):
      cb_sound_name = SOUND_NAME_FORMATS["{}_callback".format(kwargs.get("sound"))].format(**kwargs)
      cb_settings = {
        cb_sound_name: {
          "action": action,
          "track": track,
          "events_when_played": [COMPLETED_EVENT_NAME],
        }
      }
      self.machine.log.info("SquadmateSounds made a callback to play: '{}' Args={}".format(cb_sound_name, cb_settings))
      self.machine.events.post("sounds_play", settings=cb_settings, context=context, calling_context=calling_context, priority=1)
    elif COMPLETED_EVENT_NAME.get(kwargs["sound"]):
      self.machine.events.post(COMPLETED_EVENT_NAME[kwargs["sound"]])

  def _on_hit(self, **kwargs):
    player = self.machine.game.player
    self.log.debug("Received recruit HIT event with kwargs: {}".format(kwargs))
    mate = kwargs["squadmate"]
    future_mate_status = player["status_{}".format(mate)] + 1

    if 0 < future_mate_status <= 3:
      self.machine.events.post("recruit_advance", squadmate=mate, status=future_mate_status)
      self.machine.events.post("queue_slide", slide="recruit_advance_slide_{}".format(future_mate_status),
                                              squadmate=mate, status=future_mate_status,
                                              portrait="squadmate_{}_advance".format(mate))

      if future_mate_status == 3:
        self.machine.events.post("recruit_lit", squadmate=mate)
        self.machine.events.post("set_recruiticon", squadmate=mate, status=future_mate_status)
        # If there were no mates lit before, bonus the xp
        xp = self.machine.get_machine_var("unlock_xp") * (
          1 + (0 if SquadmateStatus.recruitable_mates(player) else self.machine.get_machine_var("bonus_xp")))
        player["xp"] += int(xp)
        player["available_missions"] += 1

      player["status_{}".format(mate)] = future_mate_status
      player["recruits_color"] = COLORS[mate]
      self.machine.events.post("flash_all_shields")

  def _on_missionselect(self, **kwargs):
    mate = kwargs["squadmate"]
    self._current_mate = mate
    self.machine.events.post("start_mode_recruit{}".format(mate))

    self.machine.events.add_handler("recruit_{}_complete".format(mate), self._on_complete, squadmate=mate)
    self.machine.events.add_handler("mode_recruit{}_stopped".format(mate), self._on_stop, squadmate=mate)

    # If we selected the mission via resume, note it
    if mate == self.machine.game.player["resume_mission"]:
      self._just_resumed = True
    # Clear the resume mission
    self.machine.game.player["resume_mission"] = " "

  def _on_stop(self, **kwargs):
    self.log.info("on_stop called for recruit mission, kwargs are {}".format(kwargs))
    self.machine.events.remove_handler(self._on_stop)
    self.machine.events.remove_handler(self._on_complete)

    # If we drained on legion but completed the recruitment, that's fine
    if kwargs.get("squadmate") == "legion" and self.machine.game.player["status_legion"] == 4:
      pass
    # If we stopped without an explicit success
    elif not kwargs.get("success"):
      # If we failed or timed out, post an event (no resuming because we didn't drain)
      if self.machine.modes["global"].active and not self.machine.modes["global"].stopping:
        self.machine.events.post("recruit_failure_{}".format(kwargs.get("squadmate")))
      # If we drained, store this mission so we can resume if it fails
      elif not self._just_resumed:
        self.machine.game.player["resume_mission"] = kwargs.get("squadmate")

    self._just_resumed = False

  def _on_complete(self, **kwargs):
    self.log.debug("Received COMPLETE event with kwargs: {}".format(kwargs))
    mate = kwargs["squadmate"]
    player = self.machine.game.player

    self.machine.game.player["xp"] += self.machine.get_machine_var("mission_xp") * (
      1 + (self.machine.get_machine_var("bonus_xp") if kwargs.get("under_par") else 0))

    self.machine.events.post("levelup", mission_name="{} Recruited".format(mate),
                                        portrait="squadmate_{}_complete".format(mate))
    self.machine.events.post("recruit_success", squadmate=mate, status=4)
    self.machine.events.post("set_recruiticon_complete", squadmate=mate)
    self.machine.events.post("recruit_success_{}".format(mate))
    player["status_{}".format(mate)] = 4
    self._on_stop(success=True, **kwargs)

    # See if we had previously failed the Suicide Mission, and if so, do we now
    # have enough tech/biotic squadmates to try again?
    achs = self.machine.game.player.achievements
    if (achs["normandyattack"] == "completed" and achs["suicidemission"] == "disabled"):
      self.log.debug("Recruitmend successful, should we re-enable the suicide mission? {} techs, {} biotics".format(
        len(SquadmateStatus.available_techs(player)), len(SquadmateStatus.available_biotics(player))))
      if len(SquadmateStatus.available_techs(player)) > 1 and len(SquadmateStatus.available_biotics(player)) > 1:
        achs["suicidemission"].enable()

