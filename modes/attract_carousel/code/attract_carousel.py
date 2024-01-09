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

        # Format strings for the high scores
        self.add_mode_event_handler("attract_carousel_high_scores_1_highlighted", self._on_high_scores, value=1)
        self.add_mode_event_handler("attract_carousel_high_scores_2_highlighted", self._on_high_scores, value=2)

        # Set listeners for credit-related events, except on free play
        if self.machine.variables.get_machine_var("free_play"):
            return
        self.add_mode_event_handler("machine_var_credit_units", self._on_credits)
        self.add_mode_event_handler("not_enough_credits", self._on_credits)

    def _on_high_scores(self, value, **kwargs):
        names = []
        scores = []
        for i in range(2,6):
            if value==2:
                i += 4
            name = self.machine.variables.get_machine_var(f'score{i}_name')
            names.append(f"{i-1}. {name}")
            score = self.machine.variables.get_machine_var(f"score{i}_value")
            scores.append(f"{score:,}")
        self.machine.events.post("show_high_scores_slide",
                                 names="\n".join(names),
                                 scores="\n".join(scores))

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
