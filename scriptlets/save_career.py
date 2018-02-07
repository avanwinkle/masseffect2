import json, copy
import logging
from datetime import datetime
from mpf.core.scriptlet import Scriptlet

PLAYER_VARS = ("assigments_completed", "available_missions", "career_name", "level", "recruits_lit_count", "squadmates_count")

class SaveCareer(Scriptlet):

  def on_load(self):
    self.log = logging.getLogger("SaveCareer")
    self._current_career_name = None
    self._achievement_handlers = {}
    self.machine.events.add_handler("load_career", self._load_career)
    self.machine.events.add_handler("set_career", self._set_career)
    self.machine.events.add_handler("ball_will_end", self._save_career)

  def _set_career(self, **kwargs):
    self._current_career_name = kwargs.get("career_name", None)
    if self.machine.game and self.machine.game.player:
      self.machine.game.player["career_name"] = self._current_career_name

    self.log.info("Set career to '{}', Args={}".format(self._current_career_name, kwargs))

  def _save_career(self, **kwargs):
    self.log.info("Saving career for player: {}".format(self.machine.game.player.vars))
    newcareer = {"last_played": datetime.now().timestamp()}

    if self._current_career_name:
      careerdata = copy.copy(self.machine.game.player.vars)
      for key, value in careerdata.items():
        if key in PLAYER_VARS or key == "achievements" or key.startswith("status_"):
          newcareer[key] = value
    else:
      # For casual play, all we save is the timestamp
      newcareer = { "career_name": ""}

    self.log.debug("Saving career for '{}': {}".format(self._current_career_name, newcareer))
    json.dump(newcareer, open(self._get_filename(), mode="w"))

  def _load_career(self, **kwargs):
    if self._current_career_name:
      careerdata = json.load(open(self._get_filename()))
      player = self.machine.game.player
      self._achievement_handlers = {}

      self.log.info("Loading career with careerdata {}".format(careerdata))
      self.log.info("Player is {}".format(player))
      player["career_name"] = self._current_career_name
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
      self.log.info("Created achievement hansders: {}".format(self._achievement_handlers))
    # Allow the queue to continue
    self.machine.events.post("career_loaded", career_name=self._current_career_name)

  def _force_achievement(self, **kwargs):
    self.machine.log.info("Forcing acchievement state with kwargs {}".format(kwargs))
    player_achievements = self.machine.game.player.achievements
    player_achievements[kwargs["achievement"]] = kwargs["state"]

    self.machine.events.remove_handler_by_key(self._achievement_handlers[kwargs["achievement"]])
    del self._achievement_handlers[kwargs["achievement"]]

    self.log.info("Player achievements are now: {}".format(player_achievements))
    self.log.info("Save handlers are now: {}".format(self._achievement_handlers))

  def _get_filename(self):
    return "{}/{}.json".format(self.machine.machine_path + "/savegames",
                               self._current_career_name or "_default")
