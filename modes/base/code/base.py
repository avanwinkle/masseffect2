"""Custom mode code for Base."""

from uuid import uuid4
from mpf.core.mode import Mode

class Base(Mode):

  def mode_start(self, **kwargs):
    del kwargs
    self.add_mode_event_handler("levelup", self._on_levelup)
    self.add_mode_event_handler("medigel_enabled_shot_lit_hit", self._check_medigel)
    self.add_mode_event_handler("mission_shot_hit", self._on_mission_hit, priority=90)
    self.add_mode_event_handler("mission_collect_score", self._on_mission_score, priority=80)

    # Assign a UUID to this user
    if self.machine.settings.enable_analytics and not self.player.uuid:
      self.player.uuid = uuid4()

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
      expire="10s" if not self.stopping else "5s"
    )

    # If the levelup is a failure, don't award player vars or upgrades
    if kwargs.get("is_failure"):
        return

    self.player["level"] += 1
    self.player["earned_level"] += 1
    # Reset the ship upgrade every levelup. Once missed, gone forever!
    self.player["available_shipupgrades"] = 0
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
    
    # Avoid a bunch of auditor handlers by posting directly
    self.machine.auditor.audit_event(f"recruits_completed_{recruits_completed}")
    # Track the total score for completing the mission
    self.player[f"final_score_recruit{kwargs['squadmate']}"] = self.player[f"total_score_recruit{kwargs['squadmate']}"]

  def _check_medigel(self, **kwargs):
    del kwargs
    # Don't use medigel during multiball
    for mb in self.machine.multiballs:
      if mb.enabled:
        return
    # The medigel shot will happen before the ball save takes effect
    # because it has highest priority on the switch event
    for bs in self.machine.ball_saves:
      if bs.enabled:
        return

    self.machine.events.post("do_medigel_save")

  def _on_mission_hit(self, **kwargs):
    del kwargs
    # For charity, include a bit of score even if the ultimate score doesn't get collected
    self._add_mission_score(self.player['mission_shot_value'] // 1000 * 100)

  def _on_mission_score(self, **kwargs):
    del kwargs
    self._add_mission_score(self.player['temp_build_value'] // 100 * 100)
    self.player['temp_build_value'] = 0

  def _add_mission_score(self, score):
    mission_name = self.player['mission_name']
    self.player.add_with_kwargs("score", score, source=mission_name)
    self.player[f"total_score_{mission_name}"] += score

    # mission_collect_score.80:
    #   score: current_player.temp_build_value // 100 * 100
    #   temp_build_value:
    #     action: set
    #     int: 0
