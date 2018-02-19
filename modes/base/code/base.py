from mpf.core.mode import Mode

class Base(Mode):
  def mode_start(self, **kwargs):
    super().mode_start(**kwargs)
    self.add_mode_event_handler("mode_type_wizard_stopped", self._on_wizard_stopped)
    self.add_mode_event_handler("mode_type_mission_stopped", self._on_mission_stopped)

  def _on_wizard_stopped(self, **kwargs):
    if not self.stopping:
      self.machine.events.post("start_mode_global")

  def _on_mission_stopped(self, **kwargs):
    # Base could be stopping or global could be stopp(ed/ing)
    if not self.stopping and (self.device.modes["global"].active - self.device.modes["global"].stopping < 1):
      self.machine.events.post("start_mode_field")
