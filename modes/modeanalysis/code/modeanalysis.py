import logging
from datetime import datetime

from mpf.core.mode import Mode
from mpf.core.utility_functions import Util


class ModeAnalysis(Mode):
    """
      System mode which analysis performance of specific game modes, including
      play time and scoring.
    """

    def __init__(self, machine, config, name, path):
        super().__init__(machine, config, name, path)
        self.log = logging.getLogger("ModeAnalysis")
        self.log.setLevel(10)
        self.settings = config.get("mode_settings")

    def mode_start(self, **kwargs):
        self.handlers = {}
        self.analytics = {}
        self.trophies = {}

        trophy_levels = Util.string_to_list(
            self.settings.get("trophy_settings", {})
                .get("level_names", "gold, silver, bronze")
        )

        # Register modes for simple-setup analysis
        for mode_name in self.settings.get("analyze_modes", []):
            config = {
                "mode": mode_name,
                "player_variables": "score"
            }
            analytics = Analytics("mode_{}".format(mode_name), self.machine, config, self.log)
            self._register_tracker_handler(analytics)
        # Register arbitrary analytics
        for name, analysis_config in self.settings.get("analytics", {}).items():
            self.log.info(" - creating analysis for {}".format(name))
            analytics = Analytics(name, self.machine, analysis_config, self.log)
            self.analytics[name] = analytics
            self._register_tracker_handler(analytics)
        # Register trophies
        for name, trophy_config in self.settings.get("trophies", {}).items():
            self.log.info(" - creating trophy for {}".format(name))

            trophy = Trophy(name, self.machine, trophy_config, self.log, level_names=trophy_levels)
            self.trophies[name] = trophy
            self._register_tracker_handler(trophy)

    def _register_tracker_handler(self, tracker):
        # Consolidate start events
        for evt in Util.string_to_list(tracker.config["start_events"]):
            if not self.handlers.get(evt):
                self.handlers[evt] = []
                self.add_mode_event_handler(evt, self._start_trackers, event_name=evt)
            self.handlers[evt].append(tracker)

    def _start_trackers(self, event_name, **kwargs):
        for tracker in self.handlers[event_name]:
            tracker.start()


class ValueTrackerBase:
    """
        Base class for tracking arbitrary variable changes between two events
    """
    def __init__(self, name, machine, config, log):
        self.name = name
        self.machine = machine
        self.config = config
        self.log = log
        self._start_time = None
        self._starting_player_values = {}
        self._persists = {}

        self._reset()

        if "mode" in self.config:
            if "start_events" not in self.config:
                self.config["start_events"] = "mode_{}_will_start".format(self.config["mode"])
            if "stop_events" not in self.config:
                self.config["stop_events"] = "mode_{}_will_stop".format(self.config["mode"])

        # # Add event handlers
        # for evt in Util.string_to_list(self.config["start_events"]):
        #   self.machine.events.add_handler(evt, self.start)
        # for evt in Util.string_to_list(self.config.get("reset_events", "game_started")):
        #   self.machine.events.add_handler(evt, self._reset)

        # self.log.info("Created events for {} and {}".format(self.config["start_events"], self.config["stop_events"]))

    def start(self, **kwargs):
        if self._start_time:
            self.log.info("Tracking for {} already in progress, ignoring duplicate start event".format(self.name))
            return

        self.log.debug("Starting tracking for {}".format(self.name))
        self._start_time = datetime.now().timestamp()
        self._handlers = []

        player = self.machine.game.player

        # Track attempts for each player
        if player.number not in self._persists:
            self._persists[player.number] = {"attempts": 0, "time_played": 0, "aggregate": {}}
        self._persists[player.number]["attempts"] += 1

        # Create handlers for the stop events
        for evt in Util.string_to_list(self.config["stop_events"]):
            self._handlers.append(self.machine.events.add_handler(evt, self._stop_tracking))

    def _calculate_time(self, **kwargs):
        eval_time = datetime.now().timestamp()

        duration_secs = eval_time - self._start_time
        hours, remainder = divmod(duration_secs, 3600)
        minutes, seconds = divmod(remainder, 60)
        timestring = "{} minutes {} seconds".format(minutes, int(seconds))
        if hours > 0:
            timestring = "{} hours {}".format(hours, timestring)

        return duration_secs, timestring

    def _stop_tracking(self, **kwargs):
        self.log.info("Stopping tracking for {}".format(self.name))

        duration_secs, timestring = self._calculate_time()
        persistent_values = self._persists[self.machine.game.player.number]
        persistent_values["time_played"] += duration_secs

        analysis = {
            "duration": duration_secs,
            "timestring": timestring,
            "attempt": persistent_values["attempts"],
            "total_duration": persistent_values["time_played"],
        }
        # Call the child class' method to do something with the analysis
        self._run_analysis(analysis, **kwargs)

        # Cleanup the handlers and clear the start time
        for handler in self._handlers:
            self.machine.events.remove_handler_by_key(handler)
        self._handlers = []
        self._start_time = None

    def _run_analysis(self, analysis, **kwargs):
        raise NotImplementedError("ValueTracker types must implement their own _run_analysis method")

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


class Analytics(ValueTrackerBase):
    """
    Analytics class for assessing and aggregating deltas between a start and stop event
    """
    def start(self, **kwargs):
        super().start(**kwargs)
        # Set the starting-time values for the variables we're tracking
        for player_var in Util.string_to_list(self.config.get("player_variables", [])):
            self._starting_player_values[player_var] = self.machine.game.player.vars[player_var]
        self.log.info("Noted player vars at the start of tracking: {}".format(self._starting_player_values))

        # Create listeners for count events
        for key, count_config in self.config.get("counts", {}).items():
            if key in self._player_vars:
                raise AttributeError(
                    "Cannot store count named {}, a player_variable already exists with that name".format(key))
            starting_count = self.machine.placeholder_manager.build_int_template(count_config["starting_count"])
            self._counts[key] = [starting_count.evaluate({}), 0]
            self._handlers.append(self.machine.events.add_handler(count_config["count_events"], self._count, key=key))
        self.log.info("Created counts: {}".format(self._counts))

    def _run_analysis(self, analysis, **kwargs):
        persist_values = self._persists[self.machine.game.player.number]
        # "player_variables" tracks the delta in any number of player values
        for player_var, starting_value in self._starting_player_values.items():
            change = self.machine.game.player.vars[player_var] - starting_value
            if player_var not in persist_values["aggregate"]:
                persist_values["aggregate"][player_var] = 0
            persist_values["aggregate"][player_var] += change

            analysis[player_var] = {
                "starting_value": starting_value,
                "change": change,
                "aggregate": persist_values["aggregate"][player_var]
            }
        # "counts" tracks an arbitrary number of count_events against a starting count
        for count_var, starting_value in self._counts.items():
            if count_var not in persist_values["aggregate"]:
                persist_values["aggregate"][count_var] = 0
            persist_values["aggregate"][count_var] += starting_value[1]

            analysis[count_var] = {
                "starting_value": starting_value[0],
                "change": starting_value[1],
                "aggregate": persist_values["aggregate"][count_var],
            }

        self.log.info("Analysis complete: {}".format(analysis))
        return analysis


class Trophy(ValueTrackerBase):
    """
    Trophy class for awarding a trophy level according to a player's performance against a benchmark.
    """
    def __init__(self, name, machine, config, log, level_names):
        super().__init__(name, machine, config, log)
        self._level_names = level_names
        self._level_bases = Util.string_to_list(config["award_levels"])

    def start(self, **kwargs):
        # Some trophies can only be awarded on the first attempt (i.e. resuming a mission disqualifies the trophy)
        if self.config.get("aggregate_type") == "first_only" and self._persists \
                .get(self.machine.game.player.number, {}).get("attempts", 0) > 1:
            self.log.debug(" - Trophy {} won't be tracked because this is not the first attempt".format(self.name))
            return

        super().start(**kwargs)
        # Set the starting-time value for the variable we're tracking
        player_var = self.config["value"]
        if player_var != "duration":
            self._starting_player_values[player_var] = self.machine.game.player.vars[player_var]
            self.log.info("{}: value at the start of tracking: {}".format(self.name, self._starting_player_values))

        self._handlers.append(self.machine.events.add_handler(
            self.config["award_event"], self._stop_tracking, from_award_event=True))

    def _run_analysis(self, analysis, **kwargs):
        # If the analysis stopped because of a stop_event, do not evaluate for a trophy
        if not kwargs.get("from_award_event"):
            return

        player_var = self.config["value"]
        trophies = self.machine.game.player.vars.setdefault("trophies", {})

        if player_var == "duration":
            value, timestring = self._calculate_time()
            greater_wins = False
        else:
            value = self.machine.game.player.vars[player_var] - self._starting_player_values[player_var]
            greater_wins = True

        self.log.info("Evaluating trophy award {} with a value of {}".format(self.name, value))
        award = 0
        for idx, level in enumerate(self._level_bases):
            if ((value - float(level)) >= 0) == greater_wins:
                award = idx + 1
                self.log.info(" - Awarded trophy level {} because score is better than {}".format(award, level))
                break

        if not award:
            self.log.info(" - Player score does not qualify for any trophies. Sorry.")
        elif award < trophies.get(self.name, 1000):
            self.log.info(" - That's a new trophy for the player! Hurray!")
            trophies[self.name] = {"level": award, "value": value, "timestamp": datetime.now().timestamp()}
            self.machine.events.post("trophy_awarded_{}".format(self.name),
                                     value=value,                            # The player's score that won a trophy
                                     level=self._level_names[award - 1],     # The friendly name of the trophy level
                                     baseline=self._level_bases[award - 1]   # The baseline value that was beaten
                                     )
        else:
            self.log.info(" - Player already has trophy level {}, no new trophy awarded.".format(trophies[self.name]))
