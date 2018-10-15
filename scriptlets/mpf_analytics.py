import logging
import os
from datetime import datetime
from mpf.core.custom_code import CustomCode
from mpf.core.utility_functions import Util

class ValueTracker:
  def __init__(self, name, machine, config, log):
    self.name = name
    self.machine = machine
    self.config = config
    self.log = log
    self._start_time = None

    self._reset()

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

    player = self.machine.game.player

    # Track attempts for each player
    if not player.number in self._persists:
      self._persists[player.number] = { "attempts": 0, "time_played": 0, "aggregate": {} }
    self._persists[player.number]["attempts"] += 1

    # Set the starting-time values for the variables we're tracking in the analysis
    for player_var in Util.string_to_list(self.config.get("player_variables", [])):
      self._player_vars[player_var] = player[player_var]

    self.log.info("Created player vars: {}".format(self._player_vars))

    # Create listeners for count events
    for key, count_config in self.config.get("counts", {}).items():
      if key in self._player_vars:
        raise AttributeError("Cannot store count named {}, a player_variable already exists with that name".format(key))
      starting_count = self.machine.placeholder_manager.build_int_template(count_config["starting_count"])
      self._counts[key] = [starting_count.evaluate({}), 0]
      self._handlers.append(self.machine.events.add_handler(count_config["count_events"], self._count, key=key))
    self.log.info("Created counts: {}".format(self._counts))

    # Create trophies and listeners
    for trophy, trophy_config in self.config.get("trophies", {}).items():
      if trophy_config["aggregate_type"] == "first_only" and self._persists[player.number]["attempts"] > 1:
        self.log.debug(" - Trophy {} won't be tracked because this is not the first attempt".format(trophy_config["name"]))
        continue
      self._handlers.append(self.machine.events.add_handler(
        trophy_config["award_event"], self._award_trophy, name=trophy, config=trophy_config))

  def _calculate_time(self, **kwargs):
    eval_time = datetime.now().timestamp()

    duration_secs = eval_time - self._start_time
    hours, remainder = divmod(duration_secs, 3600)
    minutes, seconds = divmod(remainder, 60)
    timestring = "{} minutes {} seconds".format(minutes, int(seconds))
    if hours > 0:
      timestring = "{} hours {}".format(hours, timestring)

    return duration, timestring

  def _award_trophy(self, name, config, **kwargs):
    player_var = config["value"]
    if player_var == "duration":
      value, timestring = self._calculate_time()
    else:
      value = self.machine.game.player[player_var] - self._player_vars[player_var]
    self.log.info("Awarding trophy {} with a value of {}".format(name, value))

  def _stop_analysis(self, **kwargs):
    self.log.info("Stopping analysis for {}".format(self.name))
    duration, timestring = self._calculate_time()

    persistent_values = self._persists[self.machine.game.player.number]

    analysis = {
      "duration": duration_secs,
      "timestring": timestring,
      "attempt": persist_values["attempts"],
      "total_duration": persist_values["time_played"],
    }

    for handler in self._handlers:
      self.machine.events.remove_handler_by_key(handler)
    self._handlers = []

    analysis = self._run_analysis()
    persist_values["time_played"] += analysis["duration_secs"]

    for player_var, initial_value in self._player_vars.items():
      change = self.machine.game.player[player_var] - initial_value

      if not player_var in persist_values["aggregate"]:
        persist_values["aggregate"][player_var] = 0
      persist_values["aggregate"][player_var] += change

      analysis[player_var] = {
        "starting_value": initial_value,
        "change": change,
        "aggregate": persist_values["aggregate"][player_var]
      }
    for count_var, initial_value in self._counts.items():

      if not count_var in persist_values["aggregate"]:
        persist_values["aggregate"][count_var] = 0
      persist_values["aggregate"][count_var] += initial_value[1]

      analysis[count_var] = {
        "starting_value": initial_value[0],
        "change": initial_value[1],
        "aggregate": persist_values["aggregate"][count_var],
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
    self._persists = {}

class Trophy(ValueTracker):
  def __init__(self, name, machine, config, log):
    self.name = name
    self.machine = machine
    self.config = config
    self.log = log

class MpfAnalytics(CustomCode):
  def on_load(self):
    self.log = logging.getLogger("MpfAnalytics")
    self.log.setLevel("DEBUG")

    self.log.info("Loading analytics")
    self.analytics = {}
    self.trophies = {}

    config_file = os.path.join(self.machine.machine_path, "config", "analytics.yaml")
    self.config = self.machine.config_processor.load_config_file(config_file, "machine").get("mode_settings")
    self.log.info(" - config: {}".format(self.config))

    for name, analysis_config in self.config["analytics"].items():
      self.log.info(" - creating analysis for {}".format(name))
      if "mode" in analysis_config:
        if not "start_event" in analysis_config:
          analysis_config["start_event"] = "mode_{}_will_start".format(analysis_config["mode"])
        if not "stop_event" in analysis_config:
          analysis_config["stop_event"] = "mode_{}_will_stop".format(analysis_config["mode"])

      self.analytics[name] = ValueTracker(name, self.machine, analysis_config, self.log)

    for name, trophy_config in self.config["trophies"].items():
      self.log.info(" - creating trophy for {}".format(name))

      self.trophies[name] = Trophy(name, self.machine, trophy_config, self.log)

