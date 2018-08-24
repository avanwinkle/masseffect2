import logging
import json
from datetime import datetime
from mpf.core.mode import Mode

class ModeAnalysis(Mode):
  """
    System mode which analysis performance of specific game modes, including
    play time and scoring.
  """

  def __init__(self, machine, config, name, path):
    super().__init__(machine, config, name, path)
    self.log = logging.getLogger("ModeAnalysis")
    self.settings = config.get("mode_settings")
    self._mode_states = {}
    self._handlers = {}

  def mode_start(self, **kwargs):
    count = 0
    # Create listeners for each mode being analysed
    for mode_name in self.settings["analyze_modes"]:
      self._mode_states[mode_name] = {}
      self.add_mode_event_handler('mode_{}_will_start'.format(mode_name), self._mode_start_analysis, mode_name=mode_name)
      count += 1
    self.log.debug("Created listeners for {} modes".format(count))

  def _mode_start_analysis(self, **kwargs):
    self.log.debug("Analyzing mode start with kwargs {}".format(kwargs))
    mode_name = kwargs.get("mode_name")
    # Snapshot the current state
    self._mode_states[mode_name]["starting_score"] = self.machine.game.player["score"]
    self._mode_states[mode_name]["started_at"] = datetime.now().timestamp()

    # Listen for the mode to end
    self._handlers[mode_name] = self.add_mode_event_handler(
      "mode_{}_will_stop".format(mode_name),
      self._mode_stop_analysis,
      mode_name=mode_name
    )

  def _mode_stop_analysis(self, **kwargs):
    self.log.debug("Analyzing mode stop with kwargs {}".format(kwargs))
    mode_name = kwargs.get("mode_name")
    # Snapshot the new state
    self._mode_states[mode_name]["ending_score"] = self.machine.game.player["score"]
    self._mode_states[mode_name]["ended_at"] = datetime.now().timestamp()

    self._mode_states[mode_name]["score"] = self._mode_states[mode_name]["ending_score"] - self._mode_states[mode_name]["starting_score"]
    seconds = self._mode_states[mode_name]["ended_at"] - self._mode_states[mode_name]["started_at"]

    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    timestring = "{} minutes {} seconds".format(minutes, int(seconds))
    if hours > 0:
      timestring = "{} hours {}".format(hours, timestring)

    self.log.info("Mode '{}' ran for {} and earned a score of {:,}. Data={}".format(
      mode_name, timestring, self._mode_states[mode_name]["score"], json.dumps(self._mode_states[mode_name])))

    self.machine.events.remove_handler_by_key(self._handlers[mode_name])
