import copy
from mpf.modes.carousel.code.carousel import Carousel

class MissionSelect(Carousel):

  """ Mode which allows the player to select a mission."""

  def mode_init(self):
    super().mode_init()
    self.log.info("MissionSelect is ready to go!!!")
    self.log.info(" - items:", self._items)
    self._all_items = copy.deepcopy(self._items)

  def mode_start(self, **kwargs):

    self._items = self._build_items_list()

    self.log.info("Final list of missionselect options: {}".format(self._items.__str__()))
    super().mode_start(**kwargs)

  def _build_items_list(self):
    player = self.machine.game.player
    self.log.info("MissionSelect player: {}".format(player.vars.__str__()))

    # Collector ship only
    if player.achievements['collectorship'] == "enabled":
      return ['collectorship']

    # If not collector ship, passing is always an option
    items = ['pass']
    if player.achievements['suicidemission'] == "enabled":
      items.append('suicide')

    for item in self._all_items:
      # self.log.info(" (missionselect) '{}'".format(item))
      if hasattr(player, "status_{}".format(item)):
        status = getattr(player, "status_{}".format(item))
        # self.machine.log.info("   - Found missionselect status: {}".format(status))
        if (status == 1):
          items.append(item)
    return items

  def _get_available_items(self):
    return self._items
