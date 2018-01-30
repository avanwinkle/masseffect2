import copy
from mpf.modes.carousel.code.carousel import Carousel

DEBUG_COLLECTORSHIP = False
DEBUG_SUICIDEMISSION = False
SQUADMATES = ["garrus", "grunt", "jack", "kasumi", "legion", "mordin", "samara", "tali", "thane", "zaeed"]

class MissionSelect(Carousel):

  """ Mode which allows the player to select a mission."""

  def mode_init(self):
    super().mode_init()
    self.debug_log("MissionSelect is ready to go!!!")
    self.debug_log(" - items:", self._items)
    self._all_items = copy.deepcopy(self._items)

  def mode_start(self, **kwargs):

    self._items = self._build_items_list()

    self.debug_log("Final list of missionselect options: {}".format(self._items.__str__()))
    super().mode_start(**kwargs)

  def _build_items_list(self):
    player = self.machine.game.player
    self.debug_log("MissionSelect player: {}".format(player.vars.__str__()))

    # Collector ship only
    if player.achievements['collectorship'] == "enabled":
      return ['collectorship']

    # If not collector ship, passing is always an option
    items = ['pass']
    if player.achievements['suicidemission'] == "enabled" or DEBUG_SUICIDEMISSION:
      items.append('suicide')
    # For debugging, allow the collector ship to be available but not required
    if DEBUG_COLLECTORSHIP and player.achievements['collectorship'] != "complete":
      items.append('collectorship')

    for mate in SQUADMATES:
      status = getattr(player, "status_{}".format(mate), -1)
      # self.machine.debug_log("   - Found missionselect status: {}".format(status))
      if (status == 1):
        items.append(mate)
    return items

  def _get_available_items(self):
    return self._items

  def _select_item(self, **kwargs):
    super()._select_item()
    selection = self._get_highlighted_item()
    if selection in SQUADMATES:
      self.machine.events.post("{}_recruitmission_selected".format(self.name), squadmate=selection)
