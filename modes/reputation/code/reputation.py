from mpf.core.mode import Mode
from mpf.core.assets import Asset

class Reputation(Mode):

    def mode_will_start(self, **kwargs):
        del kwargs
        self.add_mode_event_handler("reputation_build_shots_lit_complete", self._on_reputation_complete)

    def _on_reputation_complete(self, **kwargs):
        del kwargs
        self.machine.events.post("check_award_medigel")
        paragon = min(self.player["paragon"], 20)
        renegade = min(self.player["renegade"], 20)
        slide = "singleplayer_slide" if self.machine.game.num_players == 1 else "multiplayer_slide"
        self.machine.events.post("widgets_play", settings={
            'reputation_slide': {'action': 'add', 'key': None, 'slide': slide},
            'reputation_paragon': {'action': 'add', 'key': None, 'slide': slide,
                                   'widget_settings': {'start_frame': paragon}},
            'reputation_renegade': {'action': 'add', 'key': None, 'slide': slide,
                                    'widget_settings': {'start_frame': renegade}}
        }, context='reputation', calling_context='play_reputation_widget', priority=600)
        self.machine.clock.schedule_once(self._remove_reputation, 315)

    def _remove_reputation(self):
        self.machine.events.post("widgets_play", settings={
            'reputation_slide': {'action': 'remove', 'key': None},
            'reputation_paragon': {'action': 'remove', 'key': None},
            'reputation_renegade': {'action': 'remove', 'key': None}
        }, context='reputation', calling_context='remove_reputation_widget', priority=600)
