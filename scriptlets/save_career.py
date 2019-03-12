import json
import logging
import os
from datetime import datetime
from mpf.core.custom_code import CustomCode

PLAYER_VARS = (
  # These are the variables that are saved in a career. Everything else resets.
  "balls_played", "career_name", "career_started", "difficulty", "readonly", "level",
  "assignments_completed", "recruits_lit_count", "counter_sbdrops_counter", "xp",
  "trophies" )

ACHIEVEMENT_MISSIONS = (
  # These are achievements that qualify as available_missions if enabled/stopped
  "collectorship", "derelictreaper", "suicidemission"
)

CASUAL_CAREER = { "career_name": " ", "readonly": 1, "status_mordin": 3, "counter_sbdrops_counter": 2 }

DO_SAVE_DEATHS = False  # Should dead squadmates be saved?
SAVE_SUICIDE_PROGRESS = True # Should suicide mission progress be saved to the career?

class SaveCareer(CustomCode):

  def on_load(self):
    self.log = logging.getLogger("SaveCareer")
    self.log.setLevel(10)
    self._current_careers = {}
    self._achievement_handlers = {}
    self._savepath = "{}/savegames".format(self.machine.machine_path)
    self.machine.events.add_handler("load_career", self._load_career)
    self.machine.events.add_handler("new_career", self._new_career)
    self.machine.events.add_handler("set_career", self._set_career)
    self.machine.events.add_handler("player_turn_will_end", self._save_career)
    self.log.info("SaveCarrer loaded, what about squadmates?")

  def _set_career(self, **kwargs):
    if self.machine.game and self.machine.game.player:
      player = self.machine.game.player
      career_name = kwargs.get("career_name")
      # Store this career name for this player number
      self.machine.set_machine_var("last_career_player_{}".format(player.number), career_name)
      # Store a nice name to display for the player number
      pretty_name = "Player {}".format(player.number) if career_name == " " else career_name
      self.machine.set_machine_var("current_career_player_{}".format(player.number), pretty_name)

      if career_name == " ":
        player["casual"] = 1
        player["career_name"] = "Player {}".format(player.number)
      else:
        # Store the career for this player's number
        self._current_careers[player.number] = kwargs
        # Attach the career name to the current player
        player["career_name"] = career_name
        player["casual"] = 0

    self.log.debug("Set career to '{}', Args={}".format(player.career_name, kwargs))

  def _save_career(self, **kwargs):
    # This is asynchronous so fetch the player from the event, not necessarily the "current" player
    player = self.machine.game.player_list[kwargs.get("number") - 1]
    if not self._current_careers.get(player.number):
      self.log.info("Player {} is casual, not saving career".format(
        player.number))
      return
    elif player.vars.get("readonly", 0) == 1:
      self.log.info("Career '{}' is readonly, aborting save".format(
        player.career_name))
      return

    self.log.info("Saving career '{}' for player {}".format(player.career_name, player.number))
    newcareer = {"last_played": datetime.now().timestamp(), "achievements": {}}

    for key, value in player.vars.items():
      # For achievements, prevent "started" values (in case of hard exit)
      if key == "achievements":
        for ach, state in value.items():
          # Don't allow suicide mission states to save selected/completed state, always revert to enabled
          if ach in ("omegarelay", "infiltration", "longwalk", "tubes", "humanreaper", "endrun") and state not in ("enabled", "disabled") and not SAVE_SUICIDE_PROGRESS:
            self.log.warn(" - Suicide Achievement {} in state '{}', changing to 'enabled'".format(ach, state))
            newcareer[key][ach] = "enabled"
          # Don't save the started-ness of the suicide mission, revert it to enabled
          elif ach == "suicidemission" and state != "disabled" and not SAVE_SUICIDE_PROGRESS:
            newcareer[key][ach] = "enabled"
          # Everything else? Save the existing state
          else:
            newcareer[key][ach] = state
      # Save the state of squadmates, unless they're dead (except if we're saving suicide progress, because death matters!)
      elif key.startswith("status_") and (value >= 0 or (DO_SAVE_DEATHS or SAVE_SUICIDE_PROGRESS)):
        # Try this: don't save partial progress on harder difficulties
        if 0 < value < 3 and player.vars.get("difficulty") > 0:
          newcareer[key] = 0
        else:
          newcareer[key] = value
      # Everything else we just save as-is
      elif key in PLAYER_VARS or key.startswith("state_machine"):
        newcareer[key] = value

    # Make sure the save folder is there
    try:
      os.stat(self._savepath)
    except(FileNotFoundError):
      self.log.debug("Saved career path '{}' not found, creating it.".format(self._savepath))
      os.makedirs(self._savepath, mode=0o755)

    self.log.debug("Saving career for '{}': {}".format(player.career_name, newcareer))
    json.dump(newcareer,
              open(self._get_filename(player.career_name), mode="w"),
              indent=2,
              sort_keys=True
    )

  def _load_career(self, **kwargs):
    player = self.machine.game.player
    if self._current_careers.get(player.number):
      player.career_name = self._current_careers[player.number]["career_name"]

      if player.career_name == " ":
        careerdata = CASUAL_CAREER
      else:
        careerdata = self._fetch_careerdata(player.career_name)

      self._achievement_handlers = {}
      available_missions = 0
      squadmates_count = 0

      self.log.debug("Loading career {} for Player {} ====== Args={}".format(careerdata["career_name"], player.number, careerdata))

      for key,value in careerdata.items():
        if key.startswith("status_"):
          setattr(player, key, value)
          if value == 3:
            available_missions += 1
          elif value == 4:
            squadmates_count += 1
        elif key in PLAYER_VARS or key.startswith("state_machine"):
          setattr(player, key, value) # e.g. player.assignments_completed = 2
        elif key == "achievements":
          for achievement, state in careerdata["achievements"].items():
            handler = None
            # For achievements without "enable_events" set, listen for MPF to auto-enable the event
            if achievement in ("overlord", "upgrade_armor", "upgrade_cannon", "upgrade_shields"):
              if state != "enabled":
                handler = self.machine.events.add_handler(
                          "achievement_{}_state_enabled".format(achievement),
                          self._force_achievement,
                          achievement=achievement,
                          state=state)
            # All other achievements will default to disabled, so listen for that to be set
            elif state != "disabled":
              handler = self.machine.events.add_handler(
                          "achievement_{}_state_disabled".format(achievement),
                          self._force_achievement,
                          achievement=achievement,
                          state=state)
            # Add a callback to remove the handler after we've set the achievement to the correct state
            if handler:
              self._achievement_handlers[achievement] = handler

            # If this achievement is to be selected from the mission select, mark it as available
            if achievement in ACHIEVEMENT_MISSIONS and state in ("enabled", "stopped"):
              available_missions += 1

      # Based on the squadmates and achievements, set the player's progress variables
      setattr(player, "available_missions", available_missions)
      setattr(player, "squadmates_count", squadmates_count)
      # Store the level the player loads at, to avoid super high bonuses
      setattr(player, "saved_level", careerdata.get("level", 1))
    # Allow the queue to continue
    self.machine.events.post("career_loaded", career_name=player.career_name)

  def _new_career(self, **kwargs):
    player = self.machine.game.player
    if self._current_careers.get(player.number):
      player.career_name = self._current_careers[player.number]["career_name"]
      # All we have to do is set a new career_started time
      player.career_started = datetime.now().timestamp()
      # But also, transfer over the trophies
      if player.career_name:
        careerdata = self._fetch_careerdata(player.career_name)
        player.trophies = careerdata.get("trophies")
    self.machine.events.post("career_loaded", career_name=player.career_name)

  def _force_achievement(self, **kwargs):
    self.log.info(" - Loading achievement '{achievement}' into state '{state}'".format(**kwargs))
    player_achievements = self.machine.game.player.achievements
    # TDB: This sets the value directly and doesn't post an achievement_(name)_state_(state) event. Do we need one?
    player_achievements[kwargs["achievement"]] = kwargs["state"]

    self.machine.events.remove_handler_by_key(self._achievement_handlers[kwargs["achievement"]])
    del self._achievement_handlers[kwargs["achievement"]]

    self.log.debug("Player achievements are now: {}".format(player_achievements))
    self.log.debug("Save handlers are now: {}".format(self._achievement_handlers))

  def _get_filename(self, career_name):
    return "{}/{}.json".format(self._savepath, career_name)

  def _fetch_careerdata(self, career_name):
    with open(self._get_filename(career_name)) as f:
      careerdata = json.load(f)
    f.close()
    return careerdata
