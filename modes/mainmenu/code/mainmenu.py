import os, json
from operator import itemgetter
from mpf.modes.game.code.game import Game
from mpf.modes.carousel.code.carousel import Carousel

class MainMenu(Carousel):

  """ Mode which allows the player to select a profile and start/resume a game. """

  def mode_init(self):
    super().mode_init()
    self.mainmenu = []
    self.careermenu = []
    self.careers = []
    self._selected_career = None

  def mode_start(self, **kwargs):
    self._load_careers()
    self._selected_career = self.careers[0] if self.careers else None
    self._load_mainmenu()
    self._shown_menu = self.mainmenu
    self.add_mode_event_handler("show_mainmenu", self.show_menu)

    # Implement _some_ Carousel mode_start
    # self._register_handlers(self._next_item_events, self._next_item)
    # self._register_handlers(self._previous_item_events, self._previous_item)
    # self._register_handlers(self._select_item_events, self._select_item)

  def show_menu(self, **kwargs):
    self.machine.log.info("Showing main menu! {}".format(kwargs))
    super().mode_start()
    self._highlighted_item_index = 0
    self._update_highlighted_item(None)
    self._set_selected_career()

  def _load_mainmenu(self):
    menu = ["casual"]
    if self.careermenu:
      menu = ["change_career"] + menu
    if self._selected_career:
      menu = ["resume_game", "new_game"] + menu
    self.mainmenu = menu
    self.machine.log.info("Created main menu: {}".format(self.mainmenu))

  def _load_careers(self):
    gamepath = self.machine.machine_path + "/savegames/"
    self.careers = []

    for path, dirs, files in os.walk(gamepath):
      for file in files:
        self.machine.log.info("Files: {}".format(file))
        if file.endswith(".json"):
          career = json.load(open("{}/{}".format(path,file)))
          if career["career_name"]:
            self.careers.append(career)

    # Sort by update date
    self.careermenu = [career["career_name"] for career in sorted(self.careers,
                                                              key=itemgetter('last_played'),
                                                              reverse=True)]
    self.machine.log.info("Created career menu: {}".format(self.careermenu))

  def _get_available_items(self):
    return self._shown_menu

  def _select_item(self, **kwargs):
    selection = self._get_highlighted_item()
    # If a career was selected, track it and return to main menu
    if self._shown_menu == self.careermenu:
      self._selected_career = selection
      self._shown_menu = self.mainmenu
      self._highlighted_item_index = 0
      self._update_highlighted_item("forwards")
      self._set_selected_career()
    # If the career menu was selected, change the menu items and highlight one
    elif selection == "change_career":
      self._shown_menu = self.careermenu
      self._highlighted_item_index = 0
      self._update_highlighted_item("forwards")
    # If casual mode was chosen, clear the career
    elif selection == "casual":
      self.machine.events.post("set_career", career_name=None)
    # If resume was chosen, load the career
    elif selection == "resume_game":
      self.machine.events.post("load_career")
    # If new game was chosen, mock the loading events
    elif selection == "new_game":
      self.machine.events.post("career_loaded")
    else:
      self.machine.log.error("Unknown selection '{}' from main menu!".format(selection))

    super()._select_item()

  def _set_selected_career(self):
    career_name = self._selected_career["career_name"] if self._selected_career else None
    self.machine.events.post("set_career", career_name=career_name)

  @property
  def is_game_mode(self):
      """Return false.

      We are the game and not a mode within the game.
      """
      return False
