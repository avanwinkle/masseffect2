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

BIOMATES = [
  "jack",
  "jacob",
  "miranda",
  "samara",
  "thane",
]

TECHMATES = [
  "garrus",
  "jacob",
  "kasumi",
  "legion",
  "mordin",
  "tali",
  "thane",
]

ALLOW_COLLECTORSHIP_REPLAY = True

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
    if self.machine.game.player.achievements['suicidemission'] == "started":
      self._items = self._build_specialist_list()
      # Wait for the mode to be ready before rendering the list of specialists
      self.add_mode_event_handler('update_specialists', self._render_specialists)
    else:
      self._items = self._build_items_list()
      # Disable the intro slide after a time
      self.delay.add(callback=self._remove_intro, ms=3000)

    self.debug_log("Final list of missionselect options: {}".format(self._items.__str__()))
    super().mode_start(**kwargs)


  def _build_items_list(self):
    player = self.machine.game.player
    # If Collector Ship is available, it is the only option
    if player.achievements['collectorship'] == "enabled":
      return ['collectorship']

    self._intro = "intro"
    self._mates = SQUADMATES
    items = [self._intro]

    # If Derelict Reaper is available and not completed, it goes first
    if player.achievements['derelictreaper'] not in ("disabled", "completed"):
      items.append('derelictreaper')
    # If Suicide Mission is ready, it goes first
    elif player.achievements['suicidemission'] == "enabled":
      items.append('suicide')

    # Then any squadmates who are of the "available" status
    for mate in self._mates:
      status = player.vars.get("status_{}".format(mate))
      if (status == 3):
        items.append(mate)

    # If collectorship has been played but the praetorian wasn't defeated, it can be replayed (pre-derelictreaper)
    if ALLOW_COLLECTORSHIP_REPLAY and player.achievements['collectorship'] == "stopped" and player.achievements['derelictreaper'] == "disabled":
      items.append('collectorship')

    # "Pass" is the last item in the menu
    items.append('pass')
    return items

  def _build_specialist_list(self):
    player = self.machine.game.player
    self._intro = "specialist"
    items = [self._intro]

    # If we are suiciding, filter for the correct type of squadmate
    if player.achievements['infiltration'] == "started":
      self._mates = TECHMATES
    elif player.achievements['longwalk'] == "started":
      self._mates = BIOMATES
    else:
      raise KeyError("What specialist are we building for?")

    for mate in self._mates:
      status = player["status_{}".format(mate)]
      if status == 4:
        items.append(mate)
    self._specialist = self._mates[0]

    return items

  def _render_specialists(self, **kwargs):
    for mate in self._mates:
      status = self.machine.game.player["status_{}".format(mate)]
      if mate == kwargs.get("squadmate"):
        self.machine.events.post("{}_specialist_{}_highlighted".format(self.name, mate))
      # Set available specialists to be specialists
      elif status == 4:
        self.machine.events.post("{}_specialist_{}_default".format(self.name, mate))
      # Set dead available specialists to be dead specialists
      elif status == -1:
        self.machine.events.post("{}_specialist_{}_dead".format(self.name, mate))

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
      if self._intro == "specialist":
        self.machine.game.player["specialist"] = selection
      else:
        self.machine.events.post("{}_recruitmission_selected".format(self.name), squadmate=selection)
    elif selection == "pass":
      # Store the choice to pass so we can skip missionselect until a new mission is available
      self.machine.game.player['bypass_missionselect'] = 1

  def _update_highlighted_item(self, direction):
    h = self._get_highlighted_item()
    self.machine.events.post("{}_{}_highlighted".format(self.name, h), direction=direction)
    if h in self._mates:
      if self._intro == "specialist":
        self._render_specialists(squadmate=h)
      else:
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
