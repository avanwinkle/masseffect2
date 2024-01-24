"""Custom mode code for Global."""

from math import ceil
from mpf.modes.bonus.code.bonus import Bonus as BonusBase

class Bonus(BonusBase):

    __slots__ = []

    def mode_start(self, **kwargs):
        if self.machine.modes["global"].active:
            self.log.debug("Bonus mode starting, waiting for global")
            self.add_mode_event_handler("slide_queue_clear", self._on_proceed, **kwargs)
        else:
            self._on_proceed(**kwargs)

    def _on_proceed(self, **kwargs):
        self.log.debug("Bonus mode proceeding")
        self.machine.events.post("bonus_queue_clear")
        super().mode_start(**kwargs)

        # Set a multiplier for the reputation at 25% each
        reputation_total = self.player.reputation + self.player.paragon + self.player.renegade
        self.player.bonus_multiplier = 1.0 + (0.25 * reputation_total)
        self.add_mode_event_handler("bonus_multiplier", self._on_multiplier)

    def _on_multiplier(self, **kwargs):
        multiplier = kwargs['multiplier']
        base_multiplier = int(multiplier)
        if base_multiplier == multiplier:
            m_string = f"{base_multiplier}X"
        else:
            fraction_multiplier = multiplier - base_multiplier
            # Avoid floating-point nonsense
            if fraction_multiplier < 0.4:
                m_string = f"{base_multiplier}.25X"
            elif fraction_multiplier < 0.7:
                m_string = f"{base_multiplier}.5X"
            else:
                m_string = f"{base_multiplier}.75X"
        self.machine.events.post("show_bonus_multiplier_slide", multiplier=m_string)

    def _total_bonus(self):
        # Make sure the total bonus is nice and rounded up
        self.bonus_score = ceil(self.bonus_score / 100) * 100
        super()._total_bonus()
