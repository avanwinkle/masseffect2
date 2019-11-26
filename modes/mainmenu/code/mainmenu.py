"""MainMenu for selecting profiles."""

import json
import logging
import os
from datetime import datetime
from operator import itemgetter
from mpf.modes.carousel.code.carousel import Carousel

DIFFICULTIES = { 0: "Normal", 1: "Hardcore", 2: "Insanity" }

class MainMenu(Carousel):
    """Mode which allows the player to select a profile and start/resume a game."""

    def mode_init(self):
        """Initialze and make a logger."""
        super().mode_init()
        # Set initial values
        self.mainmenu = []
        self.careers = []
        self._selected_career = None
        self._selected_difficulty = None
        self.log = logging.getLogger("MainMenu")
        self.log.setLevel(20)

    def mode_start(self, **kwargs):
        """Mode start: create event handlers."""
        if not self.machine.settings.enable_careers:
            self.log.info("Casual mode only, skipping menu")
            self.stop()
            return
        # Reset the difficulty selection
        self._selected_difficulty = -1
        # When the mode starts, create a handler to trigger the Carousel start.
        self.add_mode_event_handler("show_mainmenu", self.show_menu)
        # Watch for adding players, which we prevent during creation.
        self.add_mode_event_handler('player_add_request', self._player_add_request)
        self.add_mode_event_handler("player_added", self._player_added)

    def show_menu(self, **kwargs):
        """Load career data and display the main menu."""

        if self.machine.game and self.machine.game.num_players > 1:
            self.machine.variables.set_machine_var("players_widget_text", "Player {} of {}".format(
                                         self.machine.game.player.number, self.machine.game.num_players))

        self._load_careers()
        self._load_mainmenu()

        self.log.debug("Showing career menu for player {}".format(self.machine.game.player.number))
        self._shown_menu = self.mainmenu
        super().mode_start()
        if self._selected_career:
            if "achievements" in self._selected_career:
                starting_item = "resume_game"
            else:
                starting_item = "new_game"
        else:
            starting_item = "casual"
        self._highlighted_item_index = self.mainmenu.index(starting_item)
        self._update_highlighted_item(None)
        # We've already set the selected career, but want the event to be posted
        self._set_selected_career(self._selected_career)

    def _load_mainmenu(self):
        menu = ["casual", "create_career"]
        if len(self.careers) > (0 if not self._selected_career else 1):
            menu = ["change_career"] + menu
        if self._selected_career:
            menu = ["new_game"] + menu
            if "achievements" in self._selected_career:
                menu = ["resume_game"] + menu
        self.mainmenu = menu
        self._highlighted_item_index = 0
        self.log.debug("Created main menu with {}".format(", ".join(self.mainmenu)))

    def _load_careers(self):
        gamepath = self.machine.machine_path + "/savegames/"
        self.careers = []
        self._selected_career = None

        # On first load there is no game, but we know it'll be player one
        player_num = self.machine.game.player.number if self.machine.game else 1

        # Don't include careers chosen by previous players
        already_chosen = [self.machine.variables.get_machine_var("last_career_player_{}".format(x)) for x in range(1, player_num)]
        self.log.debug("Already chosen careers: {}".format(already_chosen))

        for path, dirs, files in os.walk(gamepath):
            self.log.debug("Searching savegame files: {}".format(files))
            for file in files:
                if file.endswith(".json"):
                    with open("{}/{}".format(path, file)) as f:
                        career = json.load(f)
                        # Rudimentary validation, at least what we need to get started
                        if career["career_name"] and career["last_played"]:
                            if career["career_name"] in already_chosen:
                                continue

                            career["_career_started"] = datetime.fromtimestamp(career.get("career_started", 0)) \
                                                                .strftime("%x")
                            career["_last_played"] = datetime.fromtimestamp(career.get("last_played", 0)) \
                                                             .strftime("%x")
                            self.careers.append(career)

                            # Set a default/initial selection if it's the most recently played for player 1
                            if career["career_name"] == self.machine.variables.get_machine_var("last_career_player_{}"
                                                                                     .format(player_num)):
                                self._selected_career = career
                    f.close()

        # Sort by the date last played (newest first)
        self.careers.sort(key=itemgetter("last_played"), reverse=True)
        self.log.debug("Created player {} career menu with [{}]; initial selection is {}".format(player_num,
                       ", ".join([c["career_name"] for c in self.careers]), self._selected_career))

    def _get_available_items(self):
        return self._shown_menu

    def _get_highlighted_item(self):
        if self._shown_menu == self.careers:
            return self._shown_menu[self._highlighted_item_index]["career_name"]
        else:
            return self._shown_menu[self._highlighted_item_index]

    def _select_item(self, force=None, **kwargs):
        selection = force or self._get_highlighted_item()
        self.log.debug("Selecting item {} for shown menu {}".format(selection, self._shown_menu))
        # If a career was selected, track it and return to main menu
        if self._shown_menu == self.careers:
            # Use the index of the selected name to get the entire career object
            self._set_selected_career(self.careers[self._highlighted_item_index])
            # Update the main menu with new options, if need be
            self._load_mainmenu()
            # Return to the main menu
            self._shown_menu = self.mainmenu
            self._update_highlighted_item(None)
            self._post_career_event("mainmenu_career_selected")
            # Don't post selection via carousel, keep the carousel open
            return
        # If the career menu was selected, change the menu items and highlight the first one
        elif selection == "change_career":
            self.machine.events.post("mainmenu_change_career_selected")

            if not self._selected_career:
                self._set_selected_career(self.careers[0])
            else:
                self._set_selected_career(self._selected_career)
            self._shown_menu = self.careers
            self._highlighted_item_index = self.careers.index(self._selected_career)
            self._update_highlighted_item(None)
            # Don't post selection via carousel, keep the carousel open
            return
        # If casual mode was chosen, clear the career
        elif selection == "casual":
            self._set_selected_career(None)
        # If resume was chosen, load the career
        elif selection == "resume_game":
            self._post_career_event("load_career")
        # If new game was chosen, need to set the started time
        elif selection == "new_game":
            # If we haven't set a difficulty yet, do so before completing
            if self._selected_difficulty == -1:
                self._selected_difficulty = 0
                self.machine.events.post("update_difficulty", detail=DIFFICULTIES[0])
                self.machine.events.post("update_difficulty_easiest")
                return
            self._post_career_event("new_career", difficulty=self._selected_difficulty)
        # If create career was chosen, switch modes
        elif selection == "create_career":
            self.machine.events.post("start_mode_createprofile")
            self.add_mode_event_handler("createprofile_complete", self._create_profile)
            # Prevent the super from calling select, which closes the carousel mode
            return
        else:
            self.log.error("Unknown selection '{}' from main menu!".format(selection))
        self.log.debug("*** Exiting menu, player is now {}".format(self.machine.game.player.vars))
        super()._select_item()

    def _update_highlighted_item(self, direction):
        # If create mode is open, don't highlight anything
        if self.machine.modes.createprofile.active:
            self.log.debug("Highlight selected but Create Profile active, so aborting")
            return
        self.log.debug("Highlight selected, look for the next event:")
        # Career menu: select the highlighted career to post the name/level and update the widget
        if self._shown_menu == self.careers:
            career = self.careers[self._highlighted_item_index]
            self._set_selected_career(career)
            self._post_career_event("highlight_career".format(self.name),
                                    difficulty_name=DIFFICULTIES[career["difficulty"]])
        else:
            self._post_career_event("{}_{}_highlighted".format(self.name, self._get_highlighted_item()),
                                    direction=direction)

    def _next_item(self, **kwargs):
        if self._done:
            return
        # Are we picking difficulty?
        if self._selected_difficulty >=0:
            if self._selected_difficulty < 2:
                self._selected_difficulty += 1
                self.machine.events.post("update_difficulty",
                                         detail=DIFFICULTIES[self._selected_difficulty])
                if self._selected_difficulty == 2:
                    self.machine.events.post("update_difficulty_hardest")
            return
        super()._next_item(**kwargs)

    def _previous_item(self, **kwargs):
        if self._done:
            return
        # Are we picking difficulty?
        if self._selected_difficulty >= 0:
            if self._selected_difficulty > 0:
                self._selected_difficulty -= 1
                self.machine.events.post("update_difficulty",
                                         detail=DIFFICULTIES[self._selected_difficulty])
                if self._selected_difficulty == 0:
                    self.machine.events.post("update_difficulty_easiest")
            return
        super()._next_item(**kwargs)

    def _set_selected_career(self, career):
        self._selected_career = career
        self.log.debug("Setting career to {}".format(self._selected_career))
        self._post_career_event("set_career")

    def _create_profile(self, **kwargs):
        if not kwargs.get('name') or not kwargs['name'].strip():
            self.log.info("Invalid profile name '{}'.".format(kwargs.get('name')))
            return

        self._set_selected_career({"career_name": kwargs['name'], "last_played": -1})
        # Jump immediately into a new game
        self._select_item("new_game")

    def _player_add_request(self, **kwargs):
        del kwargs

        # Don't add players during profile creation, to free up the start button
        if self.machine.modes.createprofile.active:
            return False

        return True

    def _player_added(self, **kwargs):
        if kwargs.get("num") > 1:
            self.machine.variables.set_machine_var("players_widget_text", "Player {} of {}".format(
                                         self.machine.game.player.number, kwargs["num"]))

    def _post_career_event(self, evt_name, **kwargs):
        career_data = self._selected_career or { "casual": True }
        self.machine.events.post(evt_name,
                                 career_name=career_data.get("career_name"),
                                 career_started=career_data.get("_career_started"),
                                 last_played=career_data.get("_last_played"),
                                 level=career_data.get("level"),
                                 casual=career_data.get("casual"),
                                 **kwargs
                                 )
