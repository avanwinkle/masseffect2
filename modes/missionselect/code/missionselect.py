import copy
from scriptlets.me_squadmates import SquadmateStatus
from mpf.modes.carousel.code.carousel import Carousel

ALLOW_COLLECTORSHIP_REPLAY = False

class MissionSelect(Carousel):

  """ Mode which allows the player to select a mission."""

  def mode_init(self):
    super().mode_init()
    self.debug_log("MissionSelect is ready to go!!!")
    self.debug_log(" - items: {}".format(self._items))
    self._all_items = copy.copy(self._items)
    self._mates = [];
    self._specialist = "jacob"

  def mode_start(self, **kwargs):
    self._items = self._build_items_list()
    # Disable the intro slide after a time
    self.delay.add(callback=self._remove_intro, ms=3000)

    self.debug_log("Final list of missionselect options: {}".format(self._items.__str__()))
    super().mode_start(**kwargs)

  def _build_items_list(self):
    player = self.machine.game.player
    self._intro = "intro"

    # If Collector Ship is available, it is the only option
    if player.achievements['collectorship'] == "enabled":
      return ['collectorship']

    items = [self._intro]

    # If Derelict Reaper is available and not completed, it goes first
    if player.achievements['derelictreaper'] not in ("disabled", "completed"):
      items.append('derelictreaper')
    # If Suicide Mission is ready, it goes first
    elif player.achievements['suicidemission'] == "enabled":
      items.append('suicide')

    # Then any squadmates who are of the "available" status
    self._mates = SquadmateStatus.recruitable_mates(player)
    for mate in self._mates:
      items.append(mate)

    # If collectorship has been played but the praetorian wasn't defeated, it can be replayed (pre-derelictreaper)
    if ALLOW_COLLECTORSHIP_REPLAY and player.achievements['collectorship'] == "stopped" and player.achievements['derelictreaper'] == "disabled":
      items.append('collectorship')

    # "Pass" is the last item in the menu
    items.append('pass')
    return items

  def _get_available_items(self):
    return self._items

  def _select_item(self, **kwargs):
    # If select was hit while the intro still showed, pick the next one
    if self._get_highlighted_item() == self._intro:
      self.debug_log("Intro was picked as mission, advancing to next item")
      self._highlighted_item_index += 1

    super()._select_item()
    selection = self._get_highlighted_item()
    if selection in self._mates:
        self.machine.events.post("{}_recruitmission_selected".format(self.name), squadmate=selection)
    elif selection == "pass":
      # Store the choice to pass so we can skip missionselect until a new mission is available
      self.machine.game.player['bypass_missionselect'] = 1

  def _update_highlighted_item(self, direction):
    h = self._get_highlighted_item()
    self.machine.events.post("{}_{}_highlighted".format(self.name, h), direction=direction)
    if h in self._mates:
      self.machine.events.post("{}_recruit_highlighted".format(self.name), squadmate=h)
    # If we moved away from the intro, remove it
    if h != self._intro and self._intro in self._items:
      self._items = self._items[1:]
      self._highlighted_item_index -= 1

  def _remove_intro(self):
    self.debug_log("Removing intro slide, highlighted is {} and items are: {}".format(self._highlighted_item_index, self._items))
    if self._items[0] == self._intro and self._highlighted_item_index == 0:
      self._next_item()

  # Don't select or trigger selection events if there is only one item
  def _next_item(self, **kwargs):
    if len(self._items) > 1:
      super()._next_item(**kwargs)

  def _previous_item(self, **kwargs):
    if len(self._items) > 1:
      super()._previous_item(**kwargs)
