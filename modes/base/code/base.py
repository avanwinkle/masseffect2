"""Custom mode code for Base."""

from mpf.core.mode import Mode
from custom_code.squadmates_mpf import SquadmateStatus

class Base(Mode):

  def mode_start(self, **kwargs):
    del kwargs
    self.add_mode_event_handler("levelup", self._on_levelup)

  def _on_levelup(self, **kwargs):
    slide_settings = {}
    self.machine.events.post("queue_slide",
      slide="levelup_slide",
      title_text="MISSION\nCOMPLETE" if kwargs.get("is_failure") else "LEVEL UP!",
      mission_name=kwargs.get("mission_name"),
      portrait=kwargs.get("portrait"),
      priority=1999,
      expire="10s"
    )

    # If the levelup is a failure, don't award player vars
    if kwargs.get("is_failure"):
        return

    self.player["level"] += 1
    self.player["earned_level"] += 1
    # Reset the ship upgrade every levelup. Once missed, gone forever!
    self.player["shipupgrade_available"] = 0
    # Block the playback of field music
    self.player["levelup_pending"] = 1
