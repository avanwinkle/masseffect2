"""Contains the custom High Scoresmode code."""

from random import choice
from mpf.modes.high_score.code.high_score import HighScore as HighScoreBase

DEFAULT_NAMES = ("ANDERSON", "JACOB", "BLASTO", "CONRAD", "ARIA", "ASHLEY", "KAIDEN", "SAREN", "ARCHANGEL", "RYDER", "WREX", "SOVERIGN", "BROOKS")


class HighScore(HighScoreBase):

    def mode_start(self, **kwargs):
        self.add_mode_event_handler("high_score_enter_initials", self._on_initials)
        self.add_mode_event_handler("score_award_display", self._on_award_display)

    def _on_initials(self, **kwargs):
        """Relay the event to format the GC text."""
        award_text = "GRAND\nCHAMPION" if kwargs.get("award") == "GRAND CHAMPION" else kwargs['award']
        self.machine.events.post("show_high_score_enter_initials", award_text=award_text, **kwargs)

    def _on_award_display(self, **kwargs):
        """Relay the event to find the appropriate medal."""
        award = kwargs.get("award")
        if award == "GRAND CHAMPION":
            medal = "platinum"
        else:
            award =  int(award[-1])
            if award <= 2:
                medal = "gold"
            elif award <= 4:
                medal = "silver"
            elif award <= 6:
                medal = "bronze"
            else:
                medal = "default"
        self.machine.events.post("show_score_award_display", medal=medal,
                                 portrait=f"n7_achievement_{medal}", **kwargs)

    # pylint: disable-msg=too-many-arguments
    async def _ask_player_for_initials(self, *args, **kwargs) -> str:
        """Override base class initials to provide defaults."""
        input_initials = await super()._ask_for_initials(*args, **kwargs)
        if not input_initials:
            existing_initials = self.high_scores.keys()
            input_initials = choice([n for n in DEFAULT_NAMES if n not in existing_initials])
        return input_initials
