import os, json
from mpf.modes.carousel.code.carousel import Carousel

class MainMenu(Carousel):

  """ Mode which allows the player to select a profile and start/resume a game. """

  def mode_init(self):
    super().mode_init()
    self.mainmenu = []
    self.careermenu = []
    self.careers = []
    self.selected_career = None

  def mode_start(self, **kwargs):
    self._load_careers()
    self._load_mainmenu()
    self._selected_career = self.careers[0] if self.careers else None
    self._shown_menu = self.mainmenu

  def _load_mainmenu(self):
    menu = ["change_career", "casual"]
    if self._selected_career:
      menu = ["resume_game", "new_game"] + menu
    self.mainmenu = menu

  def _load_careers(self):
    gamepath = "../savegames/"
    self.careers = []

    for path, dirs, files in os.walk(gamepath):
      for file in files:
        if file.endswith(".json"):
          career = json.load(open(file))
          if career.career_name and career.level:
            self.careers.push(career)

    # Sort by update date
    self.careermenu = [career.career_name for career in sorted(careers, 
                                                              key=attrgetter('last_played'),
                                                              reverse=True)]

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
      self.machine.events.post("set_career", career_name=self._selected_career)
    # If the career menu was selected, change the menu items and highlight one
    elif selection == "change_career":
      self._shown_menu = self.careermenu
      self._highlighted_item_index = 0
      self._update_highlighted_item("forwards")
    # If casual mode was chosen, clear the career
    elif selection == "casual":
      self.machine.events.post("set_career", career_name=None)

    super()._select_item()
