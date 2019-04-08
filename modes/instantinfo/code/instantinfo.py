"""Instant Info: Script to manage player state and show slides accordingly."""

from scriptlets.squadmate_status import SquadmateStatus
from mpf.modes.carousel.code.carousel import Carousel


class InstantInfo(Carousel):
    """Carousel mode with custom code to control items list."""

    def mode_start(self, **kwargs):
        """Start mode: build the list of items in the carousel."""
        # No info during normandy attack
        if self.machine.modes.normandyattack.active:
            return
        self._items = self._build_items_list()
        super().mode_start(**kwargs)

    def _build_items_list(self):
        player = self.machine.game.player
        items = ["player"]

        # If the player is not in field mode, only show the current mode's info
        current_mode = self._find_current_mode()

        if not current_mode:
            for mate in SquadmateStatus.recruitable_mates(player):
                items.append("recruit{}".format(mate))
        elif current_mode.startswith("recruit"):
            items.append(current_mode)

        # MULTIBALL
        if not current_mode or current_mode in ["overlord", "arrival"]:
            items.append("overlord" if player.achievements["arrival"] == "disabled" else "arrival")

        # SUICIDE PROGRESS
        if not current_mode or current_mode == "collectorship_base":
            if player.achievements["collectorship"] == "disabled":
                items.append("collectorship_disabled")
            else:
                items.append("collectorship_ambush")
                items.append("collectorship_husks")
                items.append("collectorship_praetorian")

        if not current_mode or current_mode == "derelictreaper":
            if player.achievements["derelictreaper"] == "disabled":
                items.append("derelictreaper_disabled")
            else:
                items.append("derelictreaper_enabled")

        for achievement in ["normandyattack", "suicidemission"]:
            if not current_mode and player.achievements[achievement] == "enabled":
                items.append(achievement)

        if not current_mode:
            items.append("shadowbroker_{}".format(player["state_machine_shadowbroker"]))
        elif current_mode.startswith("shadowbroker_"):
            items.append(current_mode)

        items.append("powers_{}".format("none" if player["power"] == " " else player["power"]))

        return items

    def _find_current_mode(self):
        # Most likely: field
        if self.machine.modes.field.active:
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