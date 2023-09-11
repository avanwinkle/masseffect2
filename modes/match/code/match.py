"""Contains the match mode code."""

from mpf.modes.match.code.match import Match as MatchBase


class Match(MatchBase):

    __slots__ = ("total_ticks", )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.total_ticks = 0

    def mode_start(self, **kwargs):
        super().mode_start(**kwargs)
        player_vars = []
        for i in range(1, 5):
            score = self.machine.variables.get_machine_var(f"player{i}_score")
            if score is not None:
                player_vars.append(("%s" % score)[-2:])
        self.machine.log.info("Got player scores:")
        self.machine.log.info(player_vars)
        spacer = " " * (5 - len(player_vars))
        self.machine.events.post("show_match_slide", scores=spacer.join(player_vars))

        self.add_mode_event_handler("timer_match_timer_tick", self._on_tick)

    def _on_tick(self, **kwargs):
        if self.total_ticks == 20:
            self.machine.events.post("show_match_num", num=self.machine.variables.get_machine_var("match_number"))
            self.machine.events.post("match_complete")
            self.total_ticks = -1
            return
        elif self.total_ticks == -1:
            self.machine.events.post("match_finished")
            return

        self.machine.events.post("show_match_num", num="%d0" % kwargs.get("ticks"))
        self.total_ticks += 1
