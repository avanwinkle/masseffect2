import json, copy
from datetime import datetime
from mpf.core.scriptlet import Scriptlet

SAVEPATH = "../savegames"
PLAYER_VARS = ("assigments_completed", "available_missions", "career_name", "level", "recruits_lit_count", "squadmates_count")

class SaveCareer(Scriptlet):

  def on_load(self):
    self._current_career = None
    self.machine.events.add_handler("load_career", self._load_career)
    self.machine.events.add_handler("set_career", self._set_career)
    self.machine.events.add_handler("ball_will_end", self._save_career)
    
  def self._set_career(self, **kwargs):
    self._current_career = kwargs.get("career_name", None)

  def _save_career(self, **kwargs):
    if self._current_career:
      careerdata = copy.copy(self.machine.player)
      careerdata["career_name"] = self._current_career
    else:
      # For casual play, all we save is the timestamp
      careerdata = { "career_name": ""}

    careerdata["last_played"] = datetime.now().timestamp()
    json.dump(careerdata, open("{}/{}.json".format(SAVEPATH, self._current_career), "w"))

  def _load_career(self, career_name=self._current_career)
    if career_name != self._current_career:
      self._current_career = career_name

    filename = self._current_career or "_default"
    
    if self._current_career:
      careerdata = json.load(open("{}/{}.json".format(SAVEPATH, filename)))
      player = self.machine.player
      for key,value in careerdata.items():
        if key in PLAYER_VARS:
          setattr(player, key, value) # e.g. player.available_missions = 2
        elif key.startswith("status_") and key.endswith("_state"):
          setattr(player[key], "value", value) # e.g. player.status_kasumi_state.value = 1
        elif key == "achievements":
          for achievement, state in key.items():
            setattr(player.achievements, achievement, state) # e.g. player.achievements.collectorship = "enabled"
    # Allow the queue to continue
    self.machine.events.post("career_loaded", career_name=self._career_name)
    