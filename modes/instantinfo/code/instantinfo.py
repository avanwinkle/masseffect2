"""Instant Info: Script to manage player state and show slides accordingly."""

from custom_code.squadmate_status import SquadmateStatus
from mpf.modes.carousel.code.carousel import Carousel

class InstantInfo(Carousel):
    """Carousel mode with custom code to control items list."""

    def mode_start(self, **kwargs):
        """Start mode: build the list of items in the carousel."""
        # No info during normandy attack
        if self.machine.modes['normandyattack'].active:
            return
        self._all_items = self._build_items_list()
        self.add_mode_event_handler("flipper_cancel", self._on_flipper_cancel)
        self.add_mode_event_handler("both_flippers_one", self._on_flipper_release)
        super().mode_start(**kwargs)

    def _build_items_list(self):
        player = self.machine.game.player
        achievements = self.machine.device_manager.collections["achievements"]
        items = []
        # If the player is not in field mode, only show the current mode's info
        current_mode = self._find_current_mode()

        if not current_mode:
            for mate in SquadmateStatus.recruitable_mates(player):
                items.append("recruit{}".format(mate))
        elif current_mode.startswith("recruit"):
            items.append(current_mode)

        # MULTIBALL
        if not current_mode or current_mode in ["overlord", "arrival"]:
            items.append("overlord" if achievements["arrival"].state == "disabled" else "arrival")

        # SUICIDE PROGRESS
        if not current_mode or current_mode == "collectorship_base":
            if achievements["collectorship"].state == "disabled":
                items.append("collectorship_disabled")
            else:
                items.append("collectorship_ambush")
                items.append("collectorship_husks")
                items.append("collectorship_praetorian")

        if not current_mode or current_mode == "derelictreaper":
            if achievements["derelictreaper"].state == "disabled":
                items.append("derelictreaper_disabled")
            else:
                items.append("derelictreaper_enabled")

        for achievement in ["normandyattack", "suicidemission"]:
            if not current_mode and achievements[achievement].state == "enabled":
                items.append(achievement)

        if not current_mode:
            shadowbroker_state = player["state_machine_shadowbroker"]
            # Special case: if chase hasn't started but it's lit
            if shadowbroker_state == "start" and player["counter_sbdrops_counter"] == 3:
                items.append("shadowbroker_chase_ready")
            else:
                items.append("shadowbroker_{}".format(shadowbroker_state))
        elif current_mode.startswith("shadowbroker_"):
            items.append(current_mode)

        items.append("powers_{}".format("none" if player["power"] == " " else player["power"]))

        # If there is a current mode, it goes first and player goes second.
        if current_mode:
            items.append("player")
        # Otherwise, player goes first
        else:
            items.insert(0, "player")

        # self.machine.log.info("InstantInfo in mode {} created {} items for player {}".format(
        #     current_mode, items, player))
        return items

    def _find_current_mode(self):
        # Most likely: field
        if self.machine.modes['field'].active:
            return

        # Next most likely: a recruit mission
        for mate in SquadmateStatus.recruitable_mates(self.machine.game.player):
            if self.machine.modes["recruit{}".format(mate)].active:
                return "recruit{}".format(mate)
        # Then a list
        for mode in ["overlord", "arrival", "n7_assignments",
                     "shadowbroker_chase", "shadowbroker_vasir", "shadowbroker_hagalaz", "shadowbroker_boss",
                     "collectorship_base", "derelictreaper", "normandyattack", "suicide_base"]:
            if self.machine.modes[mode].active:
                return mode

    def _on_flipper_cancel(self, **kwargs):
        del kwargs
        self.machine.events.post("cancel_stats")
        # Create a delay to enable the stats. Mode delays are
        # automatically cancelled when the mode ends.
        if self.machine.settings.enable_stats_for_nerds:
            self.delay.reset(name="instantinfo_stats", ms=5000, callback=self._show_stats)

    def _on_flipper_release(self, **kwargs):
        del kwargs
        self.delay.remove("cancel_stats")

    def _show_stats(self, **kwargs):
        del kwargs
        self.machine.events.post("request_stats", update_interval=5)
