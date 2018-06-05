import os, json
from datetime import datetime
from operator import itemgetter
from mpf.modes.game.code.game import Game
from mpf.modes.carousel.code.carousel import Carousel

class MainMenu(Carousel):

  """ Mode which allows the player to select a profile and start/resume a game. """

  def mode_init(self):
    super().mode_init()
    # Set initial values
    self.mainmenu = []
    self.careers = []
    self._selected_career = None

  def mode_start(self, **kwargs):
    """ When the mode starts, create a handler to trigger the Carousel start. """
    self.add_mode_event_handler("show_mainmenu", self.show_menu)

  def show_menu(self, **kwargs):
    # Load career data
    self._load_careers()
    self._load_mainmenu()
    # If no careers to choose from, skip the menu completely
    if not self.careers:
      self.info_log("No careers to show, skipping menu")
      self.stop()
      return

    self.debug_log("Showing career menu for player {}".format(self.machine.game.player.number))
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
    menu = ["casual"]
    if self.careers:
      menu = ["change_career"] + menu
    if self._selected_career:
      menu = ["new_game"] + menu
      if "achievements" in self._selected_career:
        menu = ["resume_game"] + menu
    self.mainmenu = menu
    self._highlighted_item_index = 0
    self.debug_log("Created main menu with {}".format(", ".join(self.mainmenu)))

  def _load_careers(self):
    gamepath = self.machine.machine_path + "/savegames/"
    self.careers = []
    self._selected_career = None

    # On first load there is no game, but we know it'll be player one
    player_num = self.machine.game.player.number if self.machine.game else 1

    # Don't include careers chosen by previous players
    already_chosen = [self.machine.get_machine_var("last_career_player_{}".format(x)) for x in range(1, player_num)]
    self.debug_log("Already chosen careers: {}".format(already_chosen))

    for path, dirs, files in os.walk(gamepath):
      self.debug_log("Searching savegame files: {}".format(files))
      for file in files:
        if file.endswith(".json"):
          with open("{}/{}".format(path,file)) as f:
            career = json.load(f)
            # Rudimentary validation, at least what we need to get started
            if career["career_name"] and career["last_played"]:
              if career["career_name"] in already_chosen:
                continue

              career["_strftime"] = datetime.fromtimestamp(career["last_played"]).strftime("%x")
              self.careers.append(career)

              # Set a default/initial selection if it's the most recently played for player 1
              if career["career_name"] == self.machine.get_machine_var("last_career_player_{}".format(player_num)):
                self._selected_career = career
          f.close()

    # Sort by the date last played (newest first)
    self.careers.sort(key=itemgetter("last_played"), reverse=True)
    self.debug_log("Created player {} career menu with {}; initial selection is {}".format(player_num,
                    ", ".join([c["career_name"] for c in self.careers]), self._selected_career))

  def _get_available_items(self):
    return self._shown_menu

  def _get_highlighted_item(self):
    if self._shown_menu == self.careers:
      return self._shown_menu[self._highlighted_item_index]["career_name"]
    else:
      return self._shown_menu[self._highlighted_item_index]

  def _select_item(self, **kwargs):
    selection = self._get_highlighted_item()
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
    # If new game was chosen, mock the loading events
    elif selection == "new_game":
      self._post_career_event("career_loaded")
    else:
      self.error_log("Unknown selection '{}' from main menu!".format(selection))
    self.debug_log("*** Exiting menu, player is now {}".format(self.machine.game.player.vars))
    super()._select_item()

  def _update_highlighted_item(self, direction):
    # Career menu: select the highlighted career to post the name/level and update the widget
    if self._shown_menu == self.careers:
      self._set_selected_career(self.careers[self._highlighted_item_index])
      self._post_career_event("highlight_career".format(self.name))
    else:
      self._post_career_event("{}_{}_highlighted".format(self.name, self._get_highlighted_item()),
                                 direction=direction)

  def _set_selected_career(self, career=None):
    self._selected_career = career
    career_data = self._selected_career or {}
    self.debug_log("Setting career to {}".format(career))
    self.machine.set_machine_var("last_career_player_{}".format(self.machine.game.player.number),
                                 career_data.get("career_name", " "))
    self._post_career_event("set_career")

  def _post_career_event(self, evt_name, **kwargs):
    career_data = self._selected_career or {}
    self.machine.events.post(evt_name,
                             career_name=career_data.get("career_name"),
                             last_played=career_data.get("_strftime"),
                             level=career_data.get("level"),
                             **kwargs
                             )
