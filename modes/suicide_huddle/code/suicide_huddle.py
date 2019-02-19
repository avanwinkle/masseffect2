from scriptlets.squadmate_status import SquadmateStatus
from mpf.modes.carousel.code.carousel import Carousel

class SuicideHuddle(Carousel):

  """ Mode which delays gameplay between Suicide Mission rounds for the playing
      of shows, and allows the player to select a specialist when needed. """

  def mode_init(self):
    super().mode_init()
    self._mates = []
    self._specialist = "None"

  def mode_start(self, **kwargs):
    self._items = ["intro"]
    super().mode_start(**kwargs)
    self.add_mode_event_handler("slide_huddle_slide_active", self._build_specialist_list)

  def _build_specialist_list(self, **kwargs):
    player = self.machine.game.player

    # If we are suiciding, filter for the correct type of squadmate
    if player.achievements['infiltration'] != "completed":
      self._mates = SquadmateStatus.all_techs()
      self._items = SquadmateStatus.available_techs(player)
    elif player.achievements['longwalk'] != "completed":
      self._mates = SquadmateStatus.all_biotics()
      self._items = SquadmateStatus.available_biotics(player)
    else:
      raise KeyError("What specialist are we building for?", player.achievements)

    # Select the first available mate
    self._specialist = self._mates[0]
    while self._specialist not in self._items:
      self._specialist = self._mates[self._mates.index(self._specialist) + 1]

    self.machine.log.info("Huddle specialist mates are: {}".format(self._mates))
    self._render_specialists()

  def _render_specialists(self, **kwargs):
    for mate in self._mates:
      status = self.machine.game.player["status_{}".format(mate)]
      if mate == kwargs.get("squadmate", self._specialist):
        statusname = "highlighted"
        self.machine.events.post("{}_{}_highlighted".format(self.name, mate))
      # Set available specialists to be specialists
      elif status == 4:
        statusname = "default"
        self.machine.events.post("{}_{}_default".format(self.name, mate))
      # Set dead available specialists to be dead specialists
      elif status == -1:
        statusname = "dead"
        self.machine.events.post("{}_{}_dead".format(self.name, mate))
      # Can we use kwargs
      self.machine.events.post("{}_{}_state".format(self.name, mate), state=statusname)

  def _select_item(self, **kwargs):
    # Can't select before we have actual items
    if self._get_highlighted_item() == "intro":
      return
    super()._select_item()
    selection = self._get_highlighted_item()
    self.machine.game.player["specialist"] = selection
    mission = "longwalk" if self.machine.game.player.achievements["infiltration"] == "completed" else "infiltration"
    self.machine.events.post("{}_specialist_selected".format(self.name), squadmate=selection, mission=mission)

  def _update_highlighted_item(self, direction):
    h = self._get_highlighted_item()
    if h == "intro":
      return
    self.machine.events.post("{}_{}_highlighted".format(self.name, h), direction=direction)
    self._render_specialists(squadmate=h)

  def _get_available_items(self):
    return self._items
