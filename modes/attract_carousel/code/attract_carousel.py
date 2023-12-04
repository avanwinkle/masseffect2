"""Custom mode code for Attract carousel."""


from mpf.modes.carousel.code.carousel import Carousel


class AttractCarousel(Carousel):

    def mode_start(self, **kwargs):
        super().mode_start(**kwargs)
        if self.machine.variables.get_machine_var("free_play"):
            return
        self.add_mode_event_handler("machine_var_credit_units", self._on_credits)
        self.add_mode_event_handler("not_enough_credits", self._on_credits)

        # Check the auditor
        missing_switches = self.machine.auditor.report_missing_switches()
        if missing_switches:
            self.warning_log("Missing switches detected: %s", missing_switches)

    def _on_credits(self, **kwargs):
        del kwargs
        # Don't jump slide on game start
        if self.stopping or not self.active:
            return
        # Assume credits slide is index 1
        self._highlighted_item_index = 1
        self._update_highlighted_item(None)
