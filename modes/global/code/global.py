"""Custom mode code for Global."""

from mpf.core.mode import Mode
from custom_code.squadmates_mpf import SquadmateStatus

class Global(Mode):

    __slots__ = ("standups", "is_lock_slide_active")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.is_lock_slide_active = None

    def mode_start(self, **kwargs):
        super().mode_start(**kwargs)
        shots = self.machine.device_manager.collections["shots"]
        self.is_lock_slide_active = False
        self.standups = (
            shots["storetarget1"],
            shots["storetarget2"],
            shots["storetarget3"],
            shots["storetarget4"],
            shots["storetarget5"]
        )
        self.add_mode_event_handler("captive_ball_hit", self._on_captive_ball)
        self.add_mode_event_handler("overlord_ball_will_lock",
                                    self._set_slide, active=True)
        self.add_mode_event_handler("arrival_ball_will_lock",
                                    self._set_slide, active=True)
        self.add_mode_event_handler("slide_fmball_ball_locked_slide_removed",
                                    self._set_slide, active=False)

    def _on_captive_ball(self, **kwargs):
        """On captive ball hit, spot the next standup target for shopping."""
        del kwargs
        for shot in self.standups:
            if shot.state == 0:
                shot.hit()
                break

    def _set_slide(self, active, **kwargs):
        del kwargs
        self.is_lock_slide_active = active
