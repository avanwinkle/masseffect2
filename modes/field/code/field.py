import logging
from mpf.core.mode import Mode
from mpf.core.rgb_color import RGBColor

class Field(Mode):

    __slots__ = ("_hints", "_hint_index")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._hints = None
        self._hint_index = None

    def mode_start(self, **kwargs):
        super().mode_start(**kwargs)

        self.generate_hints()
        self.add_mode_event_handler("player_shot_fmball_lock_shot_enabled", self.generate_hints, delay_ms=1000)
        self.add_mode_event_handler("player_available_missions", self.generate_hints)
        self.add_mode_event_handler("multiplayer_game", self._update_hints)
        self.add_mode_event_handler("timer_field_hints_timer_complete", self._update_hints)

    def generate_hints(self, **kwargs):
        """Assemble a list of hints for the main slide."""
        if kwargs.get("delay_ms"):
            # Sometimes we want to delay the slide update, e.g. if an
            # overlay slide is fading in over the main slide.
            # Mode delays will automatically be removed on mode end.
            self.delay.reset(name="generate_hints",
                             ms=kwargs['delay_ms'],
                             callback=self.generate_hints)
            return

        self._hints = []
        self._hint_index = -1

        # Most important: extra ball
        if self.player.extra_balls:
            self._hints.append((
                "EXTRA BALL IS LIT",
                "Shoot the right ramp for extra ball"
            ))

        # Multiball
        if self.machine.multiball_locks["fmball_lock"].enabled:
            mball = "Overlord" if self.player.achievements["arrival"][0] == "disabled" else "Arrival"
            if self.machine.multiball_locks["fmball_lock"].locked_balls < 2:
                self._hints.append((
                    "LOCK IS LIT",
                    f"Shoot the airlock to lock for\n{mball} Multiball"
                ))
            else:
                self._hints.append((
                    mball.upper(),
                    "Shoot the airlock to start Multiball"
                ))

        # Shadowbroker
        is_sbhold = self.machine.ball_holds.sb_hold.enabled
        if self.player.state_machine_shadowbroker=="vasir":
            self._hints.append((
                "SHADOW BROKER",
                "Shoot airlock to battle Vasir." if is_sbhold else "Complete drop bank to\nlight Vasir battle."
            ))
        elif self.player.state_machine_shadowbroker=="boss":
            self._hints.append((
                "SHADOW BROKER",
                "Shoot airlock to battle\nthe Shadow Broker." if is_sbhold else "Complete drop bank to\nlight Shadow Broker."
            ))
        elif self.player.state_machine_shadowbroker=="chase":
            self._hints.append((
                "SHADOW BROKER",
                "Complete drop bank to\nstart Vasir chase."
            ))
        elif self.player.state_machine_shadowbroker=="hagalaz":
            self._hints.append((
                "SHADOW BROKER",
                "Complete drop bank to\nstart Hagalaz attack."
            ))

        if self.player.available_shipupgrades:
            self._hints.append((
                "NORMANDY UPGRADE",
                "Shoot right ramp to collect an\nupgrade for the Normandy."
            ))
        elif self.player.available_upgrades:
            self._hints.append((
                "WEAPON UPGRADE",
                "Shoot right ramp to collect\na weapon upgrade."
            ))

        if self.player.available_missions:
            self._hints.append((
                "MISSION%s AVAILABLE" % ("" if self.player.available_missions == 1 else "S"),
                "Shoot center ramp to\nstart a mission."
            ))
        else:
            self._hints.append((
                "RECRUIT YOUR SQUAD",
                "Shoot colored lanes to unlock\nrecruitment missions."
            ))

        self._update_hints()

        if len(self._hints) > 1:
            self.machine.timers["field_hints_timer"].restart()
        else:
            self.machine.timers["field_hints_timer"].stop()

    def _update_hints(self, **kwargs):
        del kwargs
        self._hint_index += 1
        if self._hint_index >= len(self._hints):
            self._hint_index = 0
        h = self._hints[self._hint_index]
        self.machine.events.post("update_field_hint_%s" % ("sp" if self.machine.game.num_players==1 else "mp"),
                                 title=h[0],
                                 description=h[1])
