import random
from mpf.core.mode import Mode
from custom_code.squadmates_mpf import SquadmateStatus

# The order of this array must be the order in which modes are completed
SUICIDE_MODES = ["omegarelay", "infiltration", "longwalk", "tubes", "final", "endrun"]


class SuicideBase(Mode):

    def mode_start(self, **kwargs):
        super().mode_start(**kwargs)
        self.player = self.machine.game.player
        self.add_mode_event_handler("mode_type_suicide_started", self._on_suicide_started)
        # Listen for the suicide mission to fail and reset dead squadmates
        self.add_mode_event_handler("suicidemission_failed", self._handle_failure)
        self.add_mode_event_handler("kill_squadmate", self._kill_squadmate)
        self.add_mode_event_handler("query_final_squadmates", self._final_squadmates)
        # Setup audit listeners here instead of the auditor, since nobody will get here
        self.add_mode_event_handler("mode_suicide_platforms_started",
                                    self._audit_final_mode, finalmode="suicide_platforms")
        self.add_mode_event_handler("mode_suicide_humanreaper_started",
                                    self._audit_final_mode, finalmode="suicide_humanreaper")

    def _on_suicide_started(self, **kwargs):
        del kwargs
        current_mode = self._get_current_mode()
        self.machine.auditor.audit_event(f"mode_suicide_{current_mode}_started")

    def _audit_final_mode(self, **kwargs):
        self.machine.auditor.audit_event(f"mode_{kwargs['finalmode']}_started")

    def _set_status(self, squadmate, status):
        self.player["status_{}".format(squadmate)] = status

    def _kill_squadmate(self, **kwargs):
        target = kwargs.get("squadmate", "random")
        if target == "specialist":
            mate = self.player["specialist"]
        elif target == "random":
            avail_mates = SquadmateStatus.available_mates(self.player, include_specialist=False)
            # If the specialist is the only mate left, kill them even if include_specialist is false
            mate = random.choice(avail_mates) if avail_mates else self.player["specialist"]

        self.info_log("Found a {} mate to kill: {}".format(target, mate))
        self._set_status(mate, -1)
        self.player["squadmates_count"] -= 1
        self.player["killed_squadmate"] = mate
        self.player["specialist"] = "none"
        # It's useful to know whether the ball is ending or not
        ball_is_ending = self.machine.modes["base"].stopping or not self.machine.modes["base"].active
        self.machine.events.post("squadmate_killed", squadmate=mate, ball_is_ending=ball_is_ending)

        # Are we out of squadmates?
        if not self._squadmates_can_continue():
            self.info_log("No squadmates available to be specialists. Suicide Mission has failed.")
            # Base will already be done if the ball is ending, set the state manually
            if ball_is_ending:
                self.player["state_machine_suicide_progress"] = "failed"
                self.info_log(" - state_machine suicidemisson manually failed, available_missions subtracted")
                self._handle_failure()
            else:
                self.machine.events.post("suicidemission_failed")

        # Until we have callbacks working, trigger the relay event too
        # self.machine.events.post("squadmate_killed_complete", squadmate=mate)

        if kwargs.get("callback_mate") == "random":
            callback_mate = random.choice(SquadmateStatus.available_mates(self.player))
        else:
            callback_mate = "shepard"
        # Make a sound
        self._play_sound({
            "sound": "killed",
            "squadmate": mate,
            "mode": self._get_current_mode(),
            "callback_mate": callback_mate,
        })

    def _final_squadmates(self, **kwargs):
        final_squadmates = SquadmateStatus.final_mates(self.player)
        self.machine.events.post("final_squadmates_count",
                                 count=len(final_squadmates),
                                 squadmates=final_squadmates)

    def _squadmates_can_continue(self):
        # Infiltration requires tech specialists
        if not self._is_mode_completed("infiltration") and not SquadmateStatus.available_techs(self.player):
            return False
        # Long Walk requires biotic specialists
        elif not self._is_mode_completed("longwalk") and not SquadmateStatus.available_biotics(self.player):
            return False
        # We only need squadmates as specialists, so if longwalk is over we can continue without any
        # -- Refactoring for state_machine, this feels redundant so I'm commenting out to see!
        # elif not self._is_mode_completed("longwalk") and self.player["squadmates_count"] == 0:
        #     return False
        return True

    def _handle_failure(self, **kwargs):
        # Reset all dead squadmates to recruitable
        for mate in SquadmateStatus.dead_mates(self.player):
            # Jacob and Miranda are already recruited
            if mate in ("jacob", "miranda"):
                self._set_status(mate, 4)
                self.player["squadmates_count"] += 1
            else:
                self._set_status(mate, 0)
        # Subtract the Suicide Mission from the available missions
        self.player["available_missions"] = self.player["available_missions"] - 1
        self.machine.auditor.audit_event("suicidemission_failed")

    def _play_sound(self, sound_event):
        self.machine.events.post("play_squadmate_sound", **sound_event)

    def _get_current_mode(self):
        for mode in SUICIDE_MODES:
            if self.machine.modes["suicide_{}".format(mode)].active:
                return mode

    def _is_mode_completed(self, mode):
        return SUICIDE_MODES.index(mode) < SUICIDE_MODES.index(self.player["state_machine_suicide_progress"])
