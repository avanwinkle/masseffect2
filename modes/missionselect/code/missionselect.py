"""Custom mode code for mission selection."""
import logging
import random
from custom_code.squadmate_status import SquadmateStatus
from mpf.modes.carousel.code.carousel import Carousel

ALLOW_COLLECTORSHIP_REPLAY = False
ALLOW_DERELICTREAPER_REPLAY = False
SHOW_SELECT_WHEN_FORCED_SINGLE = True


class MissionSelect(Carousel):
    """Mode which allows the player to select a mission."""

    def mode_init(self):
        """Init: create a logger."""
        super().mode_init()
        self._mates = []
        self._specialist = "jacob"

    def mode_start(self, **kwargs):
        """Mode start: build a list of available missions (based on squadmates and achievements)."""
        self._all_items = self._build_items_list()
        player = self.machine.game.player

        # For high-flow players, reduce the options to one
        if player["high_flow"]:
            self.info_log("High flow player has items: {}".format(self._all_items))
            # If no mission to resume, pick at random
            if player["high_flow_resume"] == " " or not player["high_flow_resume"] in self._all_items:
                choice = random.choice(self._all_items)
                player["high_flow_resume"] = choice
            # Reduce the items to just the single option
            self._all_items = [player["high_flow_resume"]]
            self.info_log("high flow setting choce to {}".format(self._all_items))

        # Normal flow players can't skip a single recruit but can skip other missions.
        # High flow players will *always*
        single_choice = len(self._all_items) == 1 and (self._all_items[0] in self._mates or player["high_flow"])

        # If there's only one option and it's a recruit mission, start it immediately without a slide
        if single_choice and (player["high_flow"] or not SHOW_SELECT_WHEN_FORCED_SINGLE):
            self._items = self._all_items
            self._select_item()
            # We never technically start the mode, so fake the ending of it
            self.machine.events.post("mode_missionselect_will_stop")
        else:
            super().mode_start(**kwargs)
            intro_time = 1200 if single_choice else 3000
            # Disable the intro slide after a time
            self.delay.add(callback=self._remove_intro, ms=intro_time)

        # Disable the start button adding players
        self.add_mode_event_handler('player_add_request', self._player_add_request)

    def _build_items_list(self):
        player = self.machine.game.player
        achievements = self.machine.device_manager.collections["achievements"]
        self._intro = "intro"

        # If Collector Ship is available (for the first time), it is the only option
        if player.achievements['collectorship'][0] == "enabled":
            return ['collectorship']

        items = []

        # If Suicide Mission is ready, it goes first
        if achievements["suicidemission"].state == "enabled":
            # On high flow, go to suicide mission immediately
            if player["high_flow"]:
                return ['suicide']
            items.append('suicide')
        # Or if Derelict Reaper is available and not completed, it goes first
        elif achievements["derelictreaper"].state == "enabled" or (
            ALLOW_DERELICTREAPER_REPLAY and achievements["derelictreaper"].state == "started"
        ):
            items.append('derelictreaper')
            # On casual mode or high_flow, force the player to play derelict reaper
            if player["casual"] or player["high_flow"]:
                return items

        # Then any squadmates who are of the "available" status
        self._mates = SquadmateStatus.recruitable_mates(player)
        for mate in self._mates:
            items.append(mate)
        # If the last mission was one of the available mates, make it first
        # The "last_mission" variable may be redundant against high_flow_resume, but
        # currently last_mission is *only* for recruitment missions. Will there
        # be non-recruitments that are resumed by high-flow? If no, consolidate.
        last_mission = player["last_mission"]
        if last_mission in items:
            self.info_log("MissionSelect found last_mission {} in items {}".format(last_mission, items))
            items.remove(last_mission)
            items.insert(0, last_mission)
            self.info_log("  - missionselect moved last_mission {} to the front: {}".format(last_mission, items))

        # If high-flow, nothing else
        if player["high_flow"]:
            return items

        # If allowed, the collectorship can be replayed (pre-derelictreaper)
        if ALLOW_COLLECTORSHIP_REPLAY and achievements["collectorship"].state == "started":
            items.append('collectorship')

        # "Pass" is the last item in the menu (not available in casual mode except for suicide)
        if (not player["casual"] or self.machine.settings.get_setting_value("casual_no_bypass") != 2) or (len(items) == 1 and items[0] == "suicide"):
            items.append('pass')

        # If more than one option is available, include the intro slide
        if len(items) > 1:
            items.insert(0, self._intro)
            player["force_mission"] = 0
        else:
            player["force_mission"] = 1

        return items

    def _select_item(self, **kwargs):
        del kwargs
        # If select was hit while the intro still showed, pick the next one
        if self._get_highlighted_item() == self._intro:
            self.debug_log("Intro was picked as mission, advancing to next item")
            self._highlighted_item_index += 1
        # If we are in high-flow mode, there is only one item
        elif self.machine.game.player["high_flow"]:
            self._highlighted_item_index = 0

        super()._select_item()
        selection = self._get_highlighted_item()
        if selection in self._mates:
            # Store the last selected mate so we can put it first next time
            self.machine.game.player["last_mission"] = selection
            self.machine.events.post("{}_recruitmission_selected".format(self.name), squadmate=selection)
        elif selection == "pass":
            # Store the choice to pass so we can skip missionselect until a new mission is available
            can_bypass = True
            # This is only applicable if there are still missions to unlock, otherwise we could get stuck
            if self.machine.game.player["squadmates_count"] == 12:
                can_bypass = False
            # If game settings prevent bypass, disallow it
            elif (not self.machine.game.player["casual"] or self.machine.settings.get_setting_value("casual_no_bypass")==0):
                can_bypass = False
            # If a critical non-mandatory mission is available, cannot bypass
            for m in ("derelictreaper", "suicidemission"):
                if self.player.achievements[m][0] == "enabled":
                    can_bypass = False
            if can_bypass:
                self.machine.game.player['bypass_missionselect'] = 1
        self.stop()

    def _update_highlighted_item(self, direction):
        h = self._get_highlighted_item()

        # If we moved away from the intro, remove it
        if h != self._intro and self._intro in self._items:
            self._items.remove(self._intro)
            self._highlighted_item_index -= 1

        idx = self._items.index(h) + (0 if self._items[0] == self._intro else 1)
        total = len(self._items) - (1 if self._items[0] == self._intro else 0)
        self.machine.events.post("{}_{}_highlighted".format(self.name, h),
                                 direction=direction, index=idx, items=total)
        if h in self._mates:
            self.machine.events.post("{}_recruit_highlighted".format(self.name),
                                     squadmate=h, index=idx, items=total)

        # If there is only one item, show the force countdown
        if len(self._items) == 1:
            self.machine.events.post("missionselect_force_mission")

    def _remove_intro(self):
        self.debug_log("Removing intro slide, highlighted is {} and items are: {}".format(
                       self._highlighted_item_index, self._items))
        if self._items[0] == self._intro and self._highlighted_item_index == 0:
            self._next_item()

    # Don't select or trigger selection events if there is only one item
    def _next_item(self, **kwargs):
        if len(self._items) > 1:
            super()._next_item(**kwargs)

    def _previous_item(self, **kwargs):
        if len(self._items) > 1:
            super()._previous_item(**kwargs)

    def _player_add_request(self, **kwargs):
        del kwargs
        self._select_item()
        return False
