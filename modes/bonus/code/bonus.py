"""Custom mode code for Global."""

from math import ceil
from mpf.modes.bonus.code.bonus import Bonus as BonusBase

class Bonus(BonusBase):

    __slots__ = []

    def mode_start(self, **kwargs):
        # Wait for the slide queue to be clear before proceeding
        self.add_mode_event_handler("slide_queue_clear", self._on_proceed, **kwargs)
        self.machine.events.post("check_slide_queue")

    def _on_proceed(self, **kwargs):
        self.machine.events.post("bonus_queue_clear")
        super().mode_start(**kwargs)

    def _total_bonus(self):
        # Make sure the total bonus is nice and rounded up
        self.bonus_score = ceil(self.bonus_score / 100) * 100
        super()._total_bonus()
