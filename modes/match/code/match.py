"""Contains the match mode code."""

from mpf.modes.match.code.match import Match as MatchBase


class Match(MatchBase):

    __slots__ = ("is_match", "match_number", "total_ticks")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.is_match = None
        self.match_number = None
        self.total_ticks = None

    def mode_start(self, **kwargs):
        super().mode_start(**kwargs)
        self.total_ticks = 0

        player_vars = []
        for i in range(1, 5):
            score = self.machine.variables.get_machine_var(f"player{i}_score")
            if score is not None:
                player_vars.append(("%s" % score)[-2:])
        spacer = " " * (5 - len(player_vars))
        self.machine.events.post("show_match_slide", scores=spacer.join(player_vars))

        self.add_mode_event_handler("match_no_match", self._set_match, is_match=False, priority=9000)
        self.add_mode_event_handler("match_has_match", self._set_match, is_match=True, priority=9000)
        self.add_mode_event_handler("timer_match_timer_tick", self._on_tick)

    def _on_tick(self, **kwargs):
        if self.total_ticks == 20:
            self.machine.events.post("show_match_%s" % ("success" if self.is_match else "failure"),
                                     num=self.match_number)
            self.machine.events.post("match_complete")
            self.total_ticks = -1
            return
        elif self.total_ticks == -1:
            self.machine.events.post("match_finished")
            return

        self.machine.events.post("show_match_num", num="%d0" % kwargs.get("ticks"))
        self.total_ticks += 1

    def _set_match(self, **kwargs):
        self.is_match = kwargs.get("is_match")
        self.match_number = kwargs.get("winner_number")