"""MPF handlers for bulk squadmate behaviors."""

import logging
import random
from mpf.core.custom_code import CustomCode
from .squadmate_status import SquadmateStatus

LEDS = {
    "garrus": "color_shield_blue",
    "grunt": "color_shield_orange",
    "jack": "color_shield_purple",
    "kasumi": "color_shield_yellow",
    "legion": "color_shield_white",
    "mordin": "color_shield_red",
    "samara": "l_iron_throne",
    "tali": "l_right_return_lane",
    "thane": "color_shield_green",
    "zaeed": "l_hand_of_the_king",
}

COLORS = {
    "garrus": "0E1B4F",
    "grunt": "EF521F",
    "jack": "7B3FB8",
    "kasumi": "F7F315",
    "legion": "FFFFFF",
    "mordin": "BD000A",
    "samara": "0037FF",
    "tali": "D323FF",
    "thane": "00FF00",
    "zaeed": "FF0000",
}

MATE_PAIRS = (
    ("grunt", "zaeed", "lo", "left_orbit"),
    ("jack", "legion", "kb", "kickback"),
    ("garrus", "samara", "lr", "left_ramp"),
    ("kasumi", "thane", "rr", "right_ramp"),
    ("mordin", "tali", "ro", "right_orbit")
)

SOUND_NAME_FORMATS = {
    "destroy_core": "squadmate_{squadmate}_destroy_core",
    "husks": "squadmate_{squadmate}_husks",
    "killed": "squadmate_{squadmate}_killed",
    "killed_callback": "squadmate_{squadmate}_killed_callback_{callback_mate}",
    "skillshot": "squadmate_{squadmate}_nice_shot",
    "target_center": "target_center_{squadmate}_{variant}",
    "target_left": "target_left_{squadmate}_{variant}",
    "target_right": "target_right_{squadmate}_{variant}",
}
COMPLETED_EVENT_NAME = {
    "killed": "squadmate_killed_complete"
}


class MPFSquadmateHandlers(CustomCode):

    """Scriptlet to handles the recruit_advance and recruit_lit events for squadmate progression tracking.

    It's a convenient way to automate the event postings over all squadmates without a bunch of copy+paste
    in the yaml files.

    Possible extensions of this scriptlet:
     - Incrementing the status_squadmate player variable
     - Creating, enabling, disabling recruit lane shots
     - Creating, playing, stopping recruit lit/complete shows
    """

    def __init__(self, machine, name):
        """Create custom code to manage squadmate-specific events, handlers, and shows."""
        super().__init__(machine, name)
        self._just_resumed = None
        self._current_mate = None
        self._current_recruit = None

    def on_load(self):
        """Instantiate the module by creating listeners for squadmate-related events."""
        self.log = logging.getLogger("MESquadmates")
        self._current_recruit = None
        self._just_resumed = False

        self._shows = {}

        # Create a listener for a recruitmission to start
        self.machine.events.add_handler("missionselect_recruitmission_selected", self._on_missionselect)
        # Create a listener for a recruitmission to be resumed
        self.machine.events.add_handler("resume_mission", self._on_missionselect)
        # Create a listener for the field mode to start and stop
        self.machine.events.add_handler("mode_field_started", self._handle_field_started)
        # Base mode stopped event happens before field stopped, so use field *will* stop
        self.machine.events.add_handler("mode_field_will_stop", self._handle_field_stopped)
        # Create a listener for a ball to start and end
        self.machine.events.add_handler("mode_base_started", self._initialize_icons)
        self.machine.events.add_handler("mode_base_stopped", self._handle_end)
        # Create a listener for playing a squadmate sound
        self.machine.events.add_handler("play_squadmate_sound", self._handle_squadmate_sound)
        # Update the squad icons during suicide
        self.machine.events.add_handler("mode_suicide_base_started", self._play_squadmates_show)
        self.machine.events.add_handler("squadmate_killed", self._play_squadmates_show)
        # Create a listener for the mission select blinkenlights
        self.machine.events.add_handler("update_mission_blinken", self._update_blinken)

    def _initialize_icons(self, **kwargs):
        del kwargs
        for mate in SquadmateStatus.all_mates():
            status = self.machine.game.player["status_{}".format(mate)]
            if status in (3, 4, -1):
                self.machine.events.post("set_recruiticon", squadmate=mate, status=status)

    def _handle_field_started(self, **kwargs):
        del kwargs
        self._play_squadmates_show()
        player = self.machine.game.player
        is_post_collectorship = self.machine.device_manager.collections["achievements"] \
            .collectorship.state not in ("disabled", "enabled")
        # Enable the shots we need
        for mate1, mate2, fw, shot in MATE_PAIRS:
            mate = None
            status1 = player["status_{}".format(mate1)]
            status2 = player["status_{}".format(mate2)]
            if status1 < 3:
                mate = mate1
            elif is_post_collectorship and status2 < 3 < status1:
                mate = mate2
            self.log.debug("Status of %s:%s/%s:%s (post collectorship %s): mate is %s", mate1, status1, mate2, status2, is_post_collectorship, mate)
            # If there's a squadmate to light, light them
            if mate:
                self.machine.shots["recruit_{}_shot".format(mate)].enable()
                self.machine.modes.field.add_mode_event_handler("recruit_{}_shot_hit".format(mate), self._on_hit, squadmate=mate)
                # Disable the firewalker shot (in case it was enabled before collectorship)
                self.machine.shots["fw_packet_{}".format(shot)].disable()
            # If the shot is firewalker-eligible, light it. This means the mate from it is recruited
            # (mate1 before CS and mate2 after) and this fw shot has not been completed yet.
            elif ((status1 == 4 and not is_post_collectorship) or status2 == 4) and player["fwps_{}".format(fw)] == 0:
                self.machine.shots["fw_packet_{}".format(shot)].enable()
            # Otherwise make sure the fw shot is disabled
            else:
                self.machine.shots["fw_packet_{}".format(shot)].disable()

    def _handle_field_stopped(self, **kwargs):
        del kwargs
        self._play_squadmates_show(disable_ladder=True)
        # In theory this should delete *all* the handlers for this event
        self.machine.events.remove_handler(self._on_hit)

    def _handle_end(self, **kwargs):
        del kwargs
        self._play_squadmates_show(stop_all=True)

    def _handle_squadmate_sound(self, **kwargs):
        squadmate = kwargs.pop("squadmate", "random")
        variant = random.randint(1, kwargs["variants"]) if kwargs.get("variants") else None
        if squadmate == "random":
            squadmate = SquadmateStatus.random_mate(self.machine.game.player, exclude=kwargs.get("exclude"))
        elif squadmate == "selected":
            squadmate = SquadmateStatus.random_selected(self.machine.game.player, exclude=kwargs.get("exclude"))
        sound_name = SOUND_NAME_FORMATS[kwargs["sound"]].format(squadmate=squadmate, variant=variant)
        action = kwargs.get("action", "play")
        track = kwargs.get("track", "voice")
        delay = kwargs.get("delay", 0)
        # If a mode is supplied, append it to the sound name
        if kwargs.get("mode") == "infiltration":
            sound_name = "{}_{}".format(sound_name, kwargs["mode"])

        settings = {
            sound_name: {
                "action": action,
                "delay": delay,
                "track": track,
                "block": False,
            }
        }
        # We can pass in playback event handlers too
        for config_name in ["events_when_played", "events_when_stopped"]:
            if kwargs.get(config_name):
                settings[sound_name][config_name] = kwargs.get(config_name)
        # Dunno what these do but the sound player expects them
        context = "squadmate_sounds"
        calling_context = None

        self.machine.events.post("sounds_play",
                                 settings=settings,
                                 context=context,
                                 calling_context=calling_context,
                                 priority=2)

        # There may be an event to play when this finishes. Base on the kwargs because it's not dependent on squadmate
        completed_event = COMPLETED_EVENT_NAME.get(kwargs["sound"])

        # If a callback mate is specified, play that too
        if action == "play" and kwargs.get("callback_mate"):
            # EXCEPT for there's no Shepard callback for Miranda's death...
            if kwargs.get("callback_mate") == "shepard" and squadmate == "miranda":
                # ...so post the same completed_event as if there was no callback
                self.machine.events.post(completed_event)
            else:
                cb_sound_name = SOUND_NAME_FORMATS["{}_callback".format(kwargs.get("sound"))].format(
                    squadmate=squadmate, callback_mate=kwargs.get("callback_mate"), variant=variant)
                cb_settings = {
                    cb_sound_name: {
                        "action": action,
                        "track": track,
                        "block": False,
                        "events_when_stopped": [completed_event] if completed_event else [],
                    }
                }

                self.machine.events.post("sounds_play",
                                         settings=cb_settings,
                                         context=context,
                                         calling_context=calling_context,
                                         priority=1)
        elif completed_event:
            self.machine.events.post(completed_event)

    def _on_hit(self, **kwargs):
        player = self.machine.game.player
        self.log.debug("Received recruit HIT event with kwargs: %s", kwargs)
        mate = kwargs["squadmate"]
        future_mate_status = player["status_{}".format(mate)] + 1
        do_update_shows = False

        if 0 < future_mate_status <= 3:
            self.machine.events.post("recruit_advance", squadmate=mate, status=future_mate_status)

            if future_mate_status == 3:
                slide_title = "Mission Available"
                slide_instruction = "Left Ramp to Start" if mate not in ["garrus", "samara"] else ""
            else:
                slide_title = "Recruit Your Squad"
                slide_instruction = "{} shot{} to unlock".format(
                    3 - future_mate_status, "s" if future_mate_status == 1 else "")

            # By default, all advance slides get 3s. However, if there are missions available,
            # Garrus and Samara are quicker to get to the missionselect screen sooner, and if
            # lock or store is available, Jack and Legion are quicker.
            self.log.info("EXPIRE CHECK: mate is %s, future status is %s, available missions is %s",
                          mate, future_mate_status, player["available_missions"])
            expire = "3s"
            if (
                mate in ("garrus", "samara") and (future_mate_status == 3 or player["available_missions"] > 0)
            ) or (
                mate in ("jack", "legion") and (self.machine.multiball_locks["fmball_lock"].enabled or self.machine.ball_holds["store_hold"].enabled)
            ):
                expire = "2s"

            self.machine.events.post("queue_slide",
                                     slide="recruit_advance_slide_QUEUE_A",
                                     expire=expire,
                                     squadmate=mate, status=future_mate_status,
                                     portrait="squadmate_{}_advance".format(mate),
                                     slide_title=slide_title,
                                     slide_instruction=slide_instruction)

            if future_mate_status == 3:
                self.machine.shots["recruit_{}_shot".format(mate)].disable()
                self.machine.events.post("recruit_lit", squadmate=mate)
                self.machine.events.post("set_recruiticon", squadmate=mate, status=future_mate_status)
                # If there were no mates lit before, bonus the xp
                xp = self.machine.variables.get_machine_var("unlock_xp") * (
                    1 + (0 if SquadmateStatus.recruitable_mates(player) else
                         self.machine.variables.get_machine_var("bonus_xp")))
                player["xp"] += int(xp)
                player["available_missions"] += 1
                do_update_shows = True

            player["status_{}".format(mate)] = future_mate_status
            player["recruits_color"] = COLORS[mate]
            self.machine.events.post("flash_all_shields")

            if do_update_shows:
                self._play_squadmates_show()

    def _on_missionselect(self, **kwargs):
        mate = kwargs["squadmate"]
        self._current_mate = mate
        self.machine.events.post("start_mode_recruit{}".format(mate))

        self.machine.events.replace_handler("recruit_{}_complete".format(mate), self._on_complete, squadmate=mate)
        self.machine.events.replace_handler("mode_recruit{}_stopped".format(mate), self._on_stop, squadmate=mate)

        # If we selected the mission via resume, note it
        if mate == self.machine.game.player["resume_mission"]:
            self._just_resumed = True

        # Set a listener for the mode starting so we can play the intro show if not-resume
        self.machine.events.replace_handler("mode_recruit{}_started".format(mate), self._on_mission_started)

    def _on_mission_started(self, **kwargs):
        del kwargs
        # If we aren't resuming a mission, play an intro show
        if not self._just_resumed:
            self.machine.events.post("play_mode_intro")
        else:
            # Wait for the mission shots to update the timer before skipping intro
            self.machine.events.add_handler("set_mission_shots", self._on_mission_resumed, priority=1)
        self.machine.events.remove_handler(self._on_mission_started)

    def _on_mission_resumed(self, **kwargs):
        self.machine.events.post("mode_intro_complete")
        self.machine.events.remove_handler(self._on_mission_resumed)

    def _on_stop(self, **kwargs):
        self.log.info("on_stop called for recruit mission, kwargs are %s", kwargs)
        self.machine.events.remove_handler(self._on_stop)
        self.machine.events.remove_handler(self._on_complete)

        # If we drained on legion but completed the recruitment, that's fine
        if kwargs.get("squadmate") == "legion" and self.machine.game.player["status_legion"] == 4:
            pass
        # If we stopped without an explicit success
        elif not kwargs.get("success"):
            # If we failed or timed out, post an event (no resuming because we didn't drain)
            if self.machine.modes["global"].active and not self.machine.modes["global"].stopping:
                self.machine.events.post("recruit_failure_{}".format(kwargs.get("squadmate")))
                self.machine.game.player["resume_mission"] = " "
            # If we drained, store this mission so we can resume if it fails
            elif not self._just_resumed:
                self.machine.game.player["resume_mission"] = kwargs.get("squadmate")
            else:
                # Clear the resume mission
                self.machine.game.player["resume_mission"] = " "
                self._just_resumed = False

    def _on_complete(self, **kwargs):
        self.log.debug("Received COMPLETE event with kwargs: %s", kwargs)
        mate = kwargs["squadmate"]
        player = self.machine.game.player

        self.machine.game.player["xp"] += self.machine.variables.get_machine_var("mission_xp") * (
            1 + (self.machine.variables.get_machine_var("bonus_xp") if kwargs.get("under_par") else 0))

        self.machine.events.post("levelup",
                                 mission_name="{} Recruited".format(mate.title())
                                 # Disabling portrait so global can play shows with video
                                 # portrait="squadmate_{}_complete".format(mate))
                                 )
        self.machine.events.post("recruit_success", squadmate=mate, status=4)
        self.machine.events.post("set_recruiticon_complete", squadmate=mate)
        self.machine.events.post("recruit_success_{}".format(mate))
        player["status_{}".format(mate)] = 4
        self._on_stop(success=True, **kwargs)
        self._play_squadmates_show()

        # See if we had previously failed the Suicide Mission, and if so, do we now
        # have enough tech/biotic squadmates to try again?
        achs = self.machine.device_manager.collections["achievements"]
        if (achs.normandyattack.state == "completed" and achs.suicidemission.state == "disabled"):
            self.log.debug("Recruit successful, should we re-enable the suicide mission? %s techs, %s biotics",
                           len(SquadmateStatus.available_techs(player)),
                           len(SquadmateStatus.available_biotics(player)))
            if len(SquadmateStatus.available_techs(player)) > 1 and len(SquadmateStatus.available_biotics(player)) > 1:
                achs["suicidemission"].enable()

    def _play_squadmates_show(self, stop_all=False, disable_ladder=False, **kwargs):
        """Trigger squadmate-dependent lights on the ladder and backbox.

        Creates the necessary show files for squadmates, namely lighting the backbox with the
        appropriate light colors and filling the career ladder with solids and blinkings.
        """
        del kwargs
        mate_lists = {
            "lit": [],
            "complete": [],
            "dead": [],
            "off": [],
            "specialist": []
        }
        update_sqicons = False
        for mate in SquadmateStatus.all_mates():
            status = 0 if stop_all else self.machine.game.player["status_{}".format(mate)]
            if mate == self.machine.game.player["specialist"]:
                mate_lists["specialist"].append(mate)
                update_sqicons = True
            elif status == 3 and not self.machine.modes.suicide_base.active:
                mate_lists["lit"].append(mate)
                update_sqicons = True
            elif status == 4:
                mate_lists["complete"].append(mate)
            elif status == -1:
                mate_lists["dead"].append(mate)
            else:
                mate_lists["off"].append(mate)

        lit_count = len(mate_lists["lit"])
        complete_count = len(mate_lists["complete"]) - 2  # Discount Jacob and Miranda
        self.log.debug("Generated squadmate shows: %s", mate_lists)

        for status, mates in mate_lists.items():
            showname = "recruits_{}_show".format(status)
            if mates:
                self.log.debug("Found mates for show %s: %s", showname, mates)
                config = self.machine.show_controller.create_show_config(
                    name=showname,
                    show_tokens={
                        "leds": ", ".join(["light_bbsquad_{}".format(mate) for mate in mates])
                    }
                )

                # Show ladder lights too, if we're not in suicide
                if not self.machine.modes["suicide_base"].active and not disable_ladder:
                    if status == "lit":
                        config.show_tokens["leds"] += ", " + ", ".join(["l_ladder_light_{}".format(i + complete_count)
                                                                       for i in range(lit_count)])
                    # Miranda and Jacob start complete but no ladder lights, so watch out for trailing comma!
                    elif status == "complete" and complete_count > 0:
                        config.show_tokens["leds"] += ", " + ", ".join(["l_ladder_light_{}".format(i)
                                                                       for i in range(complete_count)])

                self._shows[showname] = self.machine.show_controller.replace_or_advance_show(
                    self._shows.get(showname),  # old_instance
                    config,  # config
                    0  # start_step
                )

            # If there are no more mates, stop the show
            elif self._shows.get(showname):
                self.log.debug("No mates found for show %s, stopping existing show.", showname)
                self._shows[showname].stop()
                self._shows[showname] = None

        # Post an event to squadmates_mc to update the squad slide
        if update_sqicons:
            # Delay by 1s to allow the slide queue to appear
            self.machine.clock.schedule_once(self._sqicon_update, 1)

    def _sqicon_update(self):
        self.machine.events.post("sqicon_update")

    def _update_blinken(self, **kwargs):
        blinken = self.machine.blinkenlights["missions_available_blinken"]
        if kwargs.get("action") == "stop":
            blinken.remove_all_colors()
            return
        player = self.machine.game.player
        self.log.info("Achievements: %s", player.achievements)

        # Non-skippable wizard modes
        if player.achievements["collectorship"][0] == "enabled":
            blinken.add_color("color_collectors", key="color_collectors", priority=0)
            return
        # Skippable wizard modes
        if player.achievements["derelictreaper"][0] == "enabled":
            blinken.add_color("color_husk", key="color_husk", priority=0)
        elif player.achievements["suicidemission"][0] == "enabled":
            blinken.add_color("color_health", key="color_health", priority=0)

        # Squadmates available
        for mate in SquadmateStatus.recruitable_mates(player):
            blinken.add_color(f"color_{mate}", key=f"color_{mate}", priority=0)
