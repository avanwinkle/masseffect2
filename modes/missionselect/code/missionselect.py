import copy
from mpf.modes.carousel.code.carousel import Carousel

SQUADMATES = [
  "grunt",
  "zaeed",
  "jack",
  "legion",
  "garrus",
  "samara",
  "kasumi",
  "thane",
  "mordin",
  "tali",
]

class MissionSelect(Carousel):

  """ Mode which allows the player to select a mission."""

  def mode_init(self):
    super().mode_init()
    self.debug_log("MissionSelect is ready to go!!!")
    self.debug_log(" - items: {}".format(self._items))
    self._all_items = copy.copy(self._items)

  def mode_start(self, **kwargs):

    self._items = self._build_items_list()

    self.debug_log("Final list of missionselect options: {}".format(self._items.__str__()))
    super().mode_start(**kwargs)

  def _build_items_list(self):
    player = self.machine.game.player
    items = []

    # Collector ship only (first time)
    if player.achievements['collectorship'] == "enabled":
      return ['collectorship']
    # Derelict Reaper only (first time)
    if player.achievements['derelictreaper'] == "enabled":
      return ['derelictreaper']

    # If collectorship has been played but failed, it _can_ be replayed (pre-derelictreaper)
    if player.achievements['collectorship'] == "stopped" and player.achievements['derelictreaper'] == "disabled":
      items.append('collectorship')
    # If suicide mission is available, it goes first
    elif player.achievements['suicidemission'] == "enabled":
      items.append('suicide')

    for mate in SQUADMATES:
      status = player.vars.get("status_{}".format(mate))
      if (status == 3):
        items.append(mate)
    # Pass is last
    items.append('pass')
    return items

  def _get_available_items(self):
    return self._items

  def _select_item(self, **kwargs):
    super()._select_item()
    selection = self._get_highlighted_item()
    if selection in SQUADMATES:
      self.machine.events.post("{}_recruitmission_selected".format(self.name), squadmate=selection)
    elif selection == "pass":
      # Store the current menu options so we can bypass
      self.machine.game.player['bypass_missionselect'] = 1

  def _update_highlighted_item(self, direction):
    h = self._get_highlighted_item()
    self.machine.events.post("{}_{}_highlighted".format(self.name, h), direction=direction)
    if h in SQUADMATES:
      self.machine.events.post("{}_recruit_highlighted".format(self.name), squadmate=h)
