"""Custom mode code for Attract carousel."""

import datetime
import psutil
import time
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
        # Stats for nerds
        self.add_mode_event_handler("flipper_cradle", self._on_flipper_cradle)

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

    def _on_flipper_cradle(self, **kwargs):
        # TBD: is there a kwarg?
        del kwargs
        # Left flipper - nothing yet
        if self.machine.switches.s_flipper_left.state:
            return
        # Right flipper: stats
        self._post_stats()

    def _post_stats(self, **kwargs):
        del kwargs
        # Generate the stats
        du = psutil.disk_usage("/")
        mem = psutil.virtual_memory()
        mb = 1024 * 1024
        gb = 1024 * 1024 * 1024
        uptime = datetime.timedelta(seconds=time.time() - psutil.boot_time())
        earnings = self.machine.modes['credits'].earnings
        self.machine.log.info("EARNINGS: %s", earnings)

        stats = {
            "uptime": f"{uptime}".split(".")[0],
            "cpu_percent": f"{psutil.cpu_percent():0.1f}%%",
            "memory": f"{mem.available / mb:0.0f}MB available ({mem.total / mb:0.0f}MB total)",
            "disk_usage": f"{du.free / gb:0.1f}GB free ({du.total / gb:0.1f}GB total)",
            "balls_played": f"{self.machine.variables.get_machine_var('balls_played_since_launch')}",
            "games_played": f"{self.machine.variables.get_machine_var('games_played_since_launch')}",
            "audit": f"{earnings['3 Total Paid Games']} / {earnings['2 Total Earnings Dollars']}",
            "mpf_handlers": len(self.machine.events.registered_handlers),
        }
        self.machine.events.post("stats_for_nerds", **stats)
        self.machine.events.post("request_mc_stats")
