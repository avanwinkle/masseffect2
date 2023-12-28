"""Custom mode code for Global."""

from mpf.core.mode import Mode
from custom_code.squadmates_mpf import SquadmateStatus

class Global(Mode):

    __slots__ = ("standups",)

    def mode_start(self, **kwargs):
        super().mode_start(**kwargs)
        shots = self.machine.device_manager.collections["shots"]
        self.standups = (
            shots["storetarget1"],
            shots["storetarget2"],
            shots["storetarget3"],
            shots["storetarget4"],
            shots["storetarget5"]
        )
        self.add_mode_event_handler("captive_ball_hit", self._on_captive_ball)

    def _on_captive_ball(self, **kwargs):
        """On captive ball hit, spot the next standup target for shopping."""
        del kwargs
        for shot in self.standups:
            if shot.state == 0:
                shot.hit()
                break
