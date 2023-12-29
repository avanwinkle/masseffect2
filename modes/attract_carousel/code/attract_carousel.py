"""Custom mode code for Attract carousel."""


from mpf.modes.carousel.code.carousel import Carousel


class AttractCarousel(Carousel):

    def mode_start(self, **kwargs):
        super().mode_start(**kwargs)

        # Check the auditor
        missing_switches = self.machine.auditor.report_missing_switches()
        if missing_switches:
            self.warning_log("Missing switches detected: %s", missing_switches)
            self.machine.events.post("missing_switch_warning")

        # Set listeners for credit-related events, except on free play
        if self.machine.variables.get_machine_var("free_play"):
            return
        self.add_mode_event_handler("machine_var_credit_units", self._on_credits)
        self.add_mode_event_handler("not_enough_credits", self._on_credits)

    def _on_credits(self, **kwargs):
        del kwargs
        # Don't jump slide on game start
        if self.stopping or not self.active:
            return
        # Assume credits slide is index 1
        self._highlighted_item_index = 1
        self._update_highlighted_item(None)
        # Pause the timer
        self.machine.events.post("pause_attract_rotation_credits")
