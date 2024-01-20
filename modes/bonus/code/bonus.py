"""Custom mode code for Global."""

from mpf.modes.bonus.code.bonus import Bonus as BonusBase
from custom_code.squadmates_mpf import SquadmateStatus

class Bonus(BonusBase):

    __slots__ = ("standups", "is_lock_slide_active")

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
