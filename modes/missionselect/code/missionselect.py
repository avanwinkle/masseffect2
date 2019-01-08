import copy
from scriptlets.squadmate_status import SquadmateStatus
from mpf.modes.carousel.code.carousel import Carousel

ALLOW_COLLECTORSHIP_REPLAY = False
ALLOW_DERELICTREAPER_REPLAY = False

class MissionSelect(Carousel):

  """ Mode which allows the player to select a mission."""

  def mode_init(self):
    super().mode_init()
    self.debug_log("MissionSelect is ready to go!!!")
    self.debug_log(" - items: {}".format(self._items))
    self._all_items = copy.copy(self._items)
    self._mates = []
    self._specialist = "jacob"

  def mode_start(self, **kwargs):
    self._items = self._build_items_list()
    self.debug_log("List of missionselect options: {}".format(self._items.__str__()))

    # If there's only one option and it's a recruit mission, start it immediately without a slide
    if len(self._items) == 1 and self._items[0] in self._mates:
      self._select_item()
    else:
      super().mode_start(**kwargs)
      # Disable the intro slide after a time
      self.delay.add(callback=self._remove_intro, ms=3000)

  def _build_items_list(self):
    player = self.machine.game.player
    self._intro = "intro"

    # If Collector Ship is available (for the first time), it is the only option
    if player.achievements['collectorship'] == "enabled":
      return ['collectorship']

    items = []

    # If Suicide Mission is ready, it goes first
    if player.achievements['suicidemission'] == "enabled":
      items.append('suicide')
    # Or if Derelict Reaper is available and not completed, it goes first
    elif player.achievements['derelictreaper'] == "enabled" or (
      ALLOW_DERELICTREAPER_REPLAY and player.achievements['derelictreaper'] == "started"
    ):
      items.append('derelictreaper')
      # On casual mode, force the player to play derelict reaper
      if player["casual"]:
        return items

    # Then any squadmates who are of the "available" status
    self._mates = SquadmateStatus.recruitable_mates(player)
    for mate in self._mates:
      items.append(mate)

    # If allowed, the collectorship can be replayed (pre-derelictreaper)
    if ALLOW_COLLECTORSHIP_REPLAY and player.achievements['collectorship'] == "started":
      items.append('collectorship')

    # "Pass" is the last item in the menu (not available in casual mode except for suicide)
    if not player["casual"] or (len(items) == 1 and items[0] == "suicide"):
      items.append('pass')

    # If more than one option is available, include the intro slide
    if len(items) > 1:
        items.insert(0, self._intro)

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
      # This is only applicable if there are still missions to unlock, otherwise we could get stuck
      if self.machine.game.player["squadmates_count"] < 12 and not self.machine.game.player["casual"]:
        self.machine.game.player['bypass_missionselect'] = 1

  def _update_highlighted_item(self, direction):
    h = self._get_highlighted_item()
    idx = self._items.index(h) + (0 if self._items[0] == self._intro else 1)
    total = len(self._items) - (1 if self._items[0] == self._intro else 0)
    self.machine.events.post("{}_{}_highlighted".format(self.name, h), direction=direction,
                                                                       index=idx,
                                                                       items=total)
    if h in self._mates:
      self.machine.events.post("{}_recruit_highlighted".format(self.name), squadmate=h,
                                                                           index=idx,
                                                                           items=total)
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
