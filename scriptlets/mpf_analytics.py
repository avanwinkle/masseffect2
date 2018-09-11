import logging
import os
from datetime import datetime
from mpf.core.custom_code import CustomCode
from mpf.core.utility_functions import Util

class Analysis:
  def __init__(self, name, machine, config, log):
    self.name = name
    self.machine = machine
    self.config = config
    self.log = log
    self._start_time = None

    self._reset()
    self._attempts = {}

    # Add event handlers
    self.machine.events.add_handler(self.config["start_event"], self._start_analysis)
    self.machine.events.add_handler(self.config["stop_event"], self._stop_analysis)
    self.machine.events.add_handler(self.config.get("reset_event", "game_started"), self._reset)

    self.log.info("Created events for {} and {}".format(self.config["start_event"], self.config["stop_event"]))

  def _start_analysis(self, **kwargs):
    if self._start_time:
      self.log.info("Analysis for {} already in progress, ignoring duplicate start event".format(self.name))
      return

    self.log.debug("Starting analysis for {}".format(self.name))
    self._start_time = datetime.now().timestamp()
    self._handlers = []

    # Track attempts for each player
    if not self.machine.game.player.number in self._attempts:
      self._attempts[self.machine.game.player.number] = { self.name: 0 }
    self._attempts[self.machine.game.player.number][self.name] += 1

    # Set the initial values
    for player_var in Util.string_to_list(self.config.get("player_variables", [])):
      self._player_vars[player_var] = self.machine.game.player[player_var]

    self.log.info("Created player vars: {}".format(self._player_vars))

    # Create listeners for count events
    for key, count_config in self.config.get("counts", {}).items():
      starting_count = self.machine.placeholder_manager.build_int_template(count_config["starting_count"])
      self._counts[key] = [starting_count.evaluate({}), 0]
      self._handlers.append(self.machine.events.add_handler(count_config["count_events"], self._count, key=key))
    self.log.info("Created counts: {}".format(self._counts))

  def _stop_analysis(self, **kwargs):
    self.log.info("Stopping analysis for {}".format(self.name))
    stop_time = datetime.now().timestamp()

    for handler in self._handlers:
      self.machine.events.remove_handler(handler)
    self._handlers = []

    duration_secs = stop_time - self._start_time
    hours, remainder = divmod(duration_secs, 3600)
    minutes, seconds = divmod(remainder, 60)
    timestring = "{} minutes {} seconds".format(minutes, int(seconds))
    if hours > 0:
      timestring = "{} hours {}".format(hours, timestring)

    analysis = {
      "duration": duration_secs,
      "timestring": timestring,
      "attempt": self._attempts[self.machine.game.player.number][self.name]
    }

    for player_var, initial_value in self._player_vars.items():
      analysis[player_var] = {
        "starting_value": initial_value,
        "change": self.machine.game.player[player_var] - initial_value,
      }
    for count_var, initial_value in self._counts.items():
      analysis[count_var] = {
        "starting_value": initial_value[0],
        "change": initial_value[1],
      }

      self._start_time = None
      self.log.info("Analysis complete: {}".format(analysis))

  def _count(self, **kwargs):
    key = kwargs["key"]
    self._counts[key][1] += 1
    self.log.info("Adding a count to {}, new value is {}".format(key, self._counts[key][1]))

  def _reset(self, **kwargs):
    if self._start_time:
      self._stop_analysis()

    self._handlers = []
    self._player_vars = {}
    self._counts = {}
    self._start_time = None
    self._attempt = 0


class MpfAnalytics(CustomCode):
  def on_load(self):
    self.log = logging.getLogger("MpfAnalytics")
    self.log.setLevel("DEBUG")

    self.log.info("Loading analytics")
    self.analytics = {}

    config_file = os.path.join(self.machine.machine_path, "config", "analytics.yaml")
    self.config = self.machine.config_processor.load_config_file(config_file, "machine")
    self.log.info(" - config: {}".format(self.config))

    for name, analysis_config in self.config["analytics"].items():
      self.log.info(" - creating analytics for {}".format(name))
      self.analytics[name] = Analysis(name, self.machine, analysis_config, self.log)
