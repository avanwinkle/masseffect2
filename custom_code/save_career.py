"""SaveCareer for managing saved profile and career data."""

import json
import logging
import os
import random
from datetime import datetime
from mpf.core.custom_code import CustomCode

from custom_code.squadmate_status import SquadmateStatus

PLAYER_VARS = (
    # These are the variables that are saved in a career. Everything else resets.
    "balls_played", "career_name", "career_started", "difficulty", "readonly", "level",
    "assignments_completed", "assignments_played", "recruits_lit_count", "xp",
    "avatar", "high_flow", "fwps_lo", "fwps_kb", "fwps_lr", "fwps_rr", "fwps_ro",
    "trophies", "total_ball_time", "counter_sbdrops_counter")

ACHIEVEMENT_MISSIONS = (
    # These are achievements that qualify as available_missions if enabled/stopped
    "collectorship", "derelictreaper", "suicidemission"
)


DO_SAVE_DEATHS = False  # Should dead squadmates be saved?
SAVE_SUICIDE_PROGRESS = True  # Should suicide mission progress be saved to the career?
FORCE_INITIAL = None

class SaveCareer(CustomCode):
    """A custom code module for reading and writing savegame data."""

    def on_load(self):
        """Initialize the module by setting handlers for load/save-related events."""
        self.log = logging.getLogger("SaveCareer")
        self.log.setLevel(30)  # TODO: Use LogMixin
        self._achievement_handlers = {}
        self._career_data = {}
        self._savepath = "{}/savegames".format(self.machine.machine_path)
        self.machine.events.add_handler("load_career", self._load_career)
        self.machine.events.add_handler("new_career", self._new_career)
        self.machine.events.add_handler("set_career", self._set_career)
        self.machine.events.add_handler("player_turn_will_end", self._save_career)
        self.log.debug("SaveCareer loaded")

    def _set_career(self, **kwargs):
        if self.machine.game and self.machine.game.player:
            player = self.machine.game.player

            # Set an initial state for casual and profile games
            if kwargs.get("casual"):
                player["casual"] = 1
                player["career_name"] = "Player {}".format(player.number)
                player["high_flow"] = self.machine.settings.get_setting_value("casual_flow")
            else:
                # Text input char_list prevents spaces in custom profiles, so this should be safe
                player["casual"] = 0
                player["career_name"] = kwargs.get("career_name")
                player["avatar"] = kwargs.get("avatar", 1)

            # It's okay to set initial-only status_** here, resumed games will overwrite
            # these properties in _load_career() (only status and available_missions)
            if ((self.machine.settings.free_starting_mission == 2) or (
                self.machine.settings.free_starting_mission == 1 and player["casual"]
            )) and not player["available_missions"]:
                starting_recruit = FORCE_INITIAL or SquadmateStatus.random_recruit()
                # In a multiplayer game, make sure everybody gets a different starter
                if player["number"] == 1:
                    self.chosen_random_recruits = [starting_recruit]
                elif not FORCE_INITIAL:
                    while starting_recruit in self.chosen_random_recruits:
                        starting_recruit = SquadmateStatus.random_recruit()
                    self.chosen_random_recruits.append(starting_recruit)

                self.log.debug("Found a random recruit: %s", starting_recruit)
                player["status_{}".format(starting_recruit)] = 3
                player["available_missions"] = 1

            # Store this career name for this player number
            self.machine.variables.set_machine_var(
                "last_career_player_{}".format(player.number), player["career_name"])
            self.machine.variables.set_machine_var(
                "current_career_player_{}".format(player.number), player["career_name"])

        self.log.debug("Set career to '{}', Args={}".format(player.career_name, kwargs))

    def _save_career(self, **kwargs):
        # This is asynchronous so fetch the player from the event, not necessarily the "current" player
        player = self.machine.game.player_list[kwargs.get("number") - 1]
        if player.vars.get("casual"):
            self.log.info("Player {} is casual, not saving career".format(player.number))
            return
        elif player.vars.get("readonly", 0) == 1:
            self.log.info("Career '{}' is readonly, aborting save".format(player.career_name))
            return

        self.log.info("Saving career '{}' for player {}".format(player.career_name, player.number))
        newcareer = {"last_played": datetime.now().timestamp(), "achievements": {}}

        for key, value in player.vars.items():
            # For total ball time, add the new value to the accumulated value
            if key == "total_ball_time":
                newcareer[key] = player.total_ball_time + player.ball_time
            # For achievements, prevent "started" values (in case of hard exit)
            elif key == "achievements":
                self.log.info(" - Saving career achievements, items are: {}".format(value.items()))
                for ach, (state, selected) in value.items():
                    # Don't allow suicide mission states to save selected/completed state, always revert to enabled
                    if ach in ("omegarelay", "infiltration", "longwalk", "tubes", "humanreaper", "endrun") and \
                           state not in ("enabled", "disabled") and not SAVE_SUICIDE_PROGRESS:
                        self.log.warn(" - Suicide {} in state '{}', changing to 'enabled'".format(ach, state))
                        newcareer[key][ach] = "enabled"
                    # Don't save the started-ness of the suicide mission, revert it to enabled
                    elif ach == "suicidemission" and state != "disabled" and not SAVE_SUICIDE_PROGRESS:
                        newcareer[key][ach] = "enabled"
                    # Everything else? Save the existing state
                    else:
                        newcareer[key][ach] = state
            # Save the state of squadmates, unless they're dead (except if we're saving suicide progress)
            elif key.startswith("status_"):
                # Don't save partial progress, only completed recruits are saved
                if 0 < value < 4:
                    newcareer[key] = 0
                # If we aren't saving suicide progress or aren't saving deaths, reset the status
                elif value == -1 and (not SAVE_SUICIDE_PROGRESS or not DO_SAVE_DEATHS):
                    newcareer[key] = 4
                # Never save fives
                elif value == 5:
                    newcareer[key] = 4
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
        # Write a json file with the data
        json.dump(newcareer,
                  open(self._get_filename(player.career_name), mode="w"),
                  indent=2,
                  sort_keys=True
                  )
        # Update the cached career data too
        self._career_data[player.career_name] = newcareer

    def _load_career(self, **kwargs):
        player = self.machine.game.player
        career_name = kwargs.get("career_name")
        setattr(player, "career_name", career_name)

        # This method should only be used for resuming games, and not casual
        if career_name == " ":
            self.log.warning("_load_career() called with casual career. This should not happen. %s", careerdata)
        else:
            careerdata = self._fetch_careerdata(career_name)

        self._achievement_handlers = {}
        available_missions = 0
        squadmates_count = 0

        for key, value in careerdata.items():
            if key.startswith("status_"):
                setattr(player, key, value)
                if value == 3:
                    available_missions += 1
                elif value == 4:
                    squadmates_count += 1
            elif key in PLAYER_VARS or key.startswith("state_machine"):
                setattr(player, key, value)  # e.g. player.assignments_completed = 2
            elif key == "achievements":
                for ach, state in careerdata["achievements"].items():
                    handler = None
                    # For achievements without "enable_events" set, listen for MPF to auto-enable the event
                    if ach in ("overlord", "upgrade_armor", "upgrade_cannon", "upgrade_shields"):
                        if state != "enabled":
                            handler = self.machine.events.add_handler("achievement_{}_state_enabled".format(ach),
                                                                      self._force_achievement,
                                                                      achievement=ach,
                                                                      state=state)
                    # All other achievements will default to disabled, so listen for that to be set
                    elif state != "disabled":
                        handler = self.machine.events.add_handler("achievement_{}_state_disabled".format(ach),
                                                                  self._force_achievement,
                                                                  achievement=ach,
                                                                  state=state)
                    # Add a callback to remove the handler after we've set the achievement to the correct state
                    if handler:
                        self._achievement_handlers[ach] = handler

                    # If this achievement is to be selected from the mission select, mark it as available
                    if ach in ACHIEVEMENT_MISSIONS and state in ("enabled", "stopped"):
                        available_missions += 1

        # Based on the squadmates and achievements, set the player's progress variables
        setattr(player, "available_missions", available_missions)
        setattr(player, "squadmates_count", squadmates_count)
        # Allow the queue to continue
        self.machine.events.post("career_loaded", career_name=player.career_name)

    def _new_career(self, **kwargs):
        player = self.machine.game.player
        # Set a difficulty
        player.difficulty = kwargs.get("difficulty")
        player.high_flow = kwargs.get("high_flow")
        player.career_name = kwargs.get("career_name")
        # All we have to do is set a new career_started time
        player.career_started = datetime.now().timestamp()
        # But also, transfer over the trophies if this profile existed
        try:
            careerdata = self._fetch_careerdata(player.career_name)
            player.trophies = careerdata.get("trophies")
        # If this career has never been saved, that's okay
        except(FileNotFoundError):
            pass
        self.machine.events.post("career_loaded", career_name=player.career_name)

    def _force_achievement(self, **kwargs):
        self.log.info(" - Loading achievement '{achievement}' into state '{state}'".format(**kwargs))
        achievements = self.machine.device_manager.collections["achievements"]
        achievements[kwargs["achievement"]].state = kwargs["state"]

        self.machine.events.remove_handler_by_key(self._achievement_handlers[kwargs["achievement"]])
        del self._achievement_handlers[kwargs["achievement"]]

        self.log.debug("Player achievements are now: {}".format(achievements))
        self.log.debug("Save handlers are now: {}".format(self._achievement_handlers))

    def _get_filename(self, career_name):
        return "{}/{}.json".format(self._savepath, career_name)

    def _fetch_careerdata(self, career_name):
        if not self._career_data.get(career_name):
            with open(self._get_filename(career_name)) as f:
                try:
                    career_data = json.load(f)
                    self._career_data[career_name] = career_data
                except json.decoder.JSONDecodeError:
                    self.log.error("Error decoding career file %s, will be ignored.", f)
            f.close()
        return self._career_data[career_name]
