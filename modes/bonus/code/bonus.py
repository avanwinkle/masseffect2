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

    def _total_bonus(self):
        # Make sure the total bonus is nice and rounded up
        self.bonus_score = ceil(self.bonus_score / 100) * 100
        super()._total_bonus()
