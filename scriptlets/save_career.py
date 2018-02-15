import json
import logging
from datetime import datetime
from mpf.core.scriptlet import Scriptlet

PLAYER_VARS = (
  "assigments_completed", "available_missions", "career_name", "level",
  "recruits_lit_count", "counter_sbdrops_counter", "squadmates_count")

class SaveCareer(Scriptlet):

  def on_load(self):
    self.log = logging.getLogger("SaveCareer")
    self._current_careers = {}
    self._achievement_handlers = {}
    self.machine.events.add_handler("load_career", self._load_career)
    self.machine.events.add_handler("set_career", self._set_career)
    self.machine.events.add_handler("ball_will_end", self._save_career)

  def _set_career(self, **kwargs):
    if self.machine.game and self.machine.game.player:
      career_name = kwargs.get("career_name", None)
      # Store the career for this player's number
      self._current_careers[self.machine.game.player.number] = kwargs if career_name else None
      # Attach the career name to the current player
      self.machine.game.player["career_name"] = career_name

    self.log.info("Set career to '{}', Args={}".format(self.machine.game.player.career_name, kwargs))

  def _save_career(self, **kwargs):
    player = self.machine.game.player
    if not self._current_careers.get(player.number):
      self.log.debug("Player {} is casual, not saving career".format(
        player.number))
      return
    elif self._current_careers[player.number].get("readonly"):
      self.log.debug("Career '{}' is readonly, aborting save".format(
        player.career_name))
      return

    self.log.info("Saving career for player {}: {}".format(player.number, player.vars))
    newcareer = {"last_played": datetime.now().timestamp()}

    for key, value in player.vars.items():
      if key in PLAYER_VARS or key == "achievements" or key.startswith("status_"):
        newcareer[key] = value

    self.log.debug("Saving career for '{}': {}".format(player.career_name, newcareer))
    json.dump(newcareer, open(self._get_filename(player.career_name), mode="w"))

  def _load_career(self, **kwargs):
    player = self.machine.game.player
    if self._current_careers.get(player.number):
      player.career_name = self._current_careers[player.number]["career_name"]
      with open(self._get_filename(player.career_name)) as f:
        # Is this necessary, or has the entire career already been loaded?
        careerdata = json.load(f)
        self._achievement_handlers = {}

        self.log.info("Loading career with careerdata {}".format(careerdata))
        self.log.info("Player is {}".format(player))
        for key,value in careerdata.items():
          if key in PLAYER_VARS or key.startswith("status_"):
            setattr(player, key, value) # e.g. player.available_missions = 2
          elif key == "achievements":
            for achievement, state in careerdata["achievements"].items():
              if state != "disabled":
                handler = self.machine.events.add_handler(
                            "achievement_{}_state_disabled".format(achievement),
                            self._force_achievement,
                            achievement=achievement,
                            state=state)
                self._achievement_handlers[achievement] = handler
        self.log.info("Created achievement handlers: {}".format(self._achievement_handlers))
      f.close()
    # Allow the queue to continue
    self.machine.events.post("career_loaded", career_name=player.career_name)

  def _force_achievement(self, **kwargs):
    self.machine.log.info("Forcing acchievement state with kwargs {}".format(kwargs))
    player_achievements = self.machine.game.player.achievements
    player_achievements[kwargs["achievement"]] = kwargs["state"]

    self.machine.events.remove_handler_by_key(self._achievement_handlers[kwargs["achievement"]])
    del self._achievement_handlers[kwargs["achievement"]]

    self.log.info("Player achievements are now: {}".format(player_achievements))
    self.log.info("Save handlers are now: {}".format(self._achievement_handlers))

  def _get_filename(self, career_name):
    return "{}/{}.json".format(self.machine.machine_path + "/savegames", career_name)
