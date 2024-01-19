"""Custom mode code for Base."""

from mpf.core.mode import Mode
from custom_code.squadmates_mpf import SquadmateStatus

class Base(Mode):

  def mode_start(self, **kwargs):
    del kwargs
    self.add_mode_event_handler("levelup", self._on_levelup)

  def _on_levelup(self, **kwargs):
    self.machine.events.post("queue_slide",
      slide="levelup_slide",
      title_text="MISSION\nCOMPLETE" if kwargs.get("is_failure") else "LEVEL UP!",
      mission_name=kwargs.get("mission_name"),
      portrait=kwargs.get("portrait"),
      clear=True,
      clear_current=True,
      priority=1999,
      # TODO: Customize expiration times based on video length
      expire="10s"
    )

    # If the levelup is a failure, don't award player vars or upgrades
    if kwargs.get("is_failure"):
        return

    self.player["level"] += 1
    self.player["earned_level"] += 1
    # Reset the ship upgrade every levelup. Once missed, gone forever!
    self.player["shipupgrade_available"] = 0
    # Block the playback of field music
    self.player["levelup_pending"] = 1

    # The below is only for squadmate recruitment-based levelups
    if not kwargs.get("squadmate"):
      return

    # The levelup event happens before the squadmate count increments
    # Starting with Miranda and Jacob means the count is one higher than
    # the actual number of recruitment missions completed
    # TODO: use earned_squadmates_count instead
    recruits_completed = self.player.squadmates_count - 1

    # For normal games, 4 recruits is collectorship
    # For expo demo mode, go to collector ship after 3 recruited
    if (recruits_completed == 4) or (
      self.machine.settings.demo_mode and recruits_completed == 3
    ):
      self.machine.events.post("enable_collectorship")
    # Otherwise, extra ball after 3 recruited!
    elif recruits_completed == 3:
      self.machine.events.post("extra_ball_lit")
      # Queue the slide immediately so it's right behing levelup
      self.machine.events.post("queue_slide",
        slide="extra_ball_lit_slide",
        portrait="extra_ball_lit",
        priority=1998,
        expire="5s"
        )
