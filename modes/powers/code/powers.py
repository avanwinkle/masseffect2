import logging
import random
from mpf.core.mode import Mode
from mpf.devices.shot_group import ShotGroup
from mpf.core.placeholder_manager import NativeTypeTemplate
from mpf.core.utility_functions import Util

SHOTS = ["left_orbit", "kickback", "left_ramp", "right_ramp", "right_orbit"]
TEST_POWER = None
DESCRIPTIONS = {
    "adrenaline": "Pauses all timers\nfor 15 seconds",
    "cloak": "Allows flippers to\nrotate lanes",
    "armor": "Enables a 10s\nball save",
    "drone": "Instant multiball or\nadd-a-ball",
    "singularity": "Target hits count\nas lane hits",
    "charge": "Hits a lit lane\nat random",
}
TIMES = {
    "adrenaline": 15,
    "cloak": 30,
    "armor": 10,
    "drone": 0,
    "singularity": 20,
    "charge": 0
}
POWER_WIDGET_HEIGHT = 92  # Height of the widget in pixels, to calculate cooldown mask height


def filter_enabled_shots(x):
    return x.enabled

def filter_enabled_and_lit_shots(x):
    return x.enabled and x.state_name == "lit"

def filter_enabled_and_state_shots(x, state_name):
    return x.enabled and x.state_name == state_name

class Powers(Mode):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.log = logging.getLogger("Powers")
        self.log.setLevel(10)
        self.shots = []
        self.shot_group = None
        self.timer = None
        self.handlers = []
        self.power_handlers = {
            "adrenaline": self._activate_adrenaline,
            "armor": self._activate_armor,
            "cloak": self._activate_cloak,
            "charge": self._activate_charge,
            "drone": self._activate_drone,
            "singularity": self._activate_singularity,
        }
        self.persisted_name = None
        self.persisted_shots = None

    def mode_will_start(self, **kwargs):
        # These four steps are needed before the legion bailout
        self.timer = self.machine.device_manager.collections["timers"]["power_active"]
        self._base_cooldown = self.machine.variables.get("base_cooldown")

        self.add_mode_event_handler('award_power', self._award_power)
        self.add_mode_event_handler('activate_power', self._activate_power)
        self.add_mode_event_handler('timer_power_active_complete', self._complete)
        self.add_mode_event_handler('mode_intro_complete', self._mode_intro_complete)
        self.add_mode_event_handler('logicblock_powers_cooldown_updated', self._update_cooldown_progress)

        # LEGION special case: don't deal with shots
        if self.machine.modes.recruitlegion.active:
            self.shot_group = self.machine.device_manager.collections["shot_groups"]["heretic_shots"]
            self.shot_group.disable_rotation()
            self.shots = self.shot_group.config["shots"]
            for shot in self.shots:
                shot.disable()
            self.log.debug("Powers sees LEGION, aborting all shot management. {}".format(self.shots))
            return

        self.shots = [self.machine.device_manager.collections["shots"][shot] for shot in SHOTS]
        self.shot_group = self.machine.device_manager.collections["shot_groups"]["power_shots"]
        self.shot_group.disable_rotation()

        self.persisted_shots = self.machine.game.player["persisted_shots"]
        if not self.persisted_shots:
            self.persisted_shots = {}
            self.machine.game.player["persisted_shots"] = self.persisted_shots
            self.log.debug("Set persisted shots for player {}: {}".format(self.player, self.persisted_shots))
        else:
            self.log.debug("Retrieved persisted shots from player {}: {}".format(self.player, self.persisted_shots))

        self.log.debug("Mode started with shots: {}".format(self.shots))

        # Disable all shots before we get started
        for shot in self.shots:
            shot.disable()

        self.add_mode_event_handler('set_mission_shots', self._set_mission_shots)
        self.add_mode_event_handler('advance_mission_shots', self._advance_mission_shots)

    def mode_stop(self, **kwargs):
        self.log.debug("Powers mode stopping, disabling all shots")
        for shot in self.shots:
            shot.disable()

    def _mode_intro_complete(self, **kwargs):
        # On mode intro complete, if there's a power the player has then enable it immediately
        power = self.machine.game.player["power"]
        if power != " ":
            self._award_power(power=power)
        else:
            self.machine.events.post("show_cooldown")
            # Pick a random power to highlight, doesn't matter what
            self.machine.events.post("player_shot_cooldown_shot_{}".format(
                random.choice(["biotic", "combat", "tech"])
            ), value=random.randint(0,3))

    def _activate_power(self, **kwargs):
        power = self.machine.game.player["power"]
        self.log.info("Activating power {}".format(power))
        try:
            self.power_handlers[power]()
            self.machine.events.post("power_activation_success", power=power)
            if self.timer.ticks > 0:
                self.timer.start()
        except IndexError:
            self.machine.events.post("power_activation_failure", power=power)

    def _award_power(self, **kwargs):
        power = TEST_POWER or kwargs["power"]
        # variable_player can't sub values, so do it manually
        self.machine.game.player["power"] = power
        self.machine.events.post("power_awarded",
                                 power=power,
                                 power_name=self._get_power_name(power),
                                 description=DESCRIPTIONS[power])
        self.timer.ticks = TIMES[power]

    def _update_cooldown_progress(self, **kwargs):
        value = kwargs["value"]
        enabled = kwargs["enabled"]
        if not enabled:
            opacity = 1.0
            complete_height = POWER_WIDGET_HEIGHT
        elif value == 100:
            opacity = 0
            complete_height = 0
        else:
            # Opacity == complete_pct starts at 0%, so the bottom looks real bad.
            complete_pct = (1 - value / self._base_cooldown)
            # Instead, start at 50% and go up 0.5% for each 1% complete
            opacity = 0.5 + (complete_pct / 2)
            complete_height = complete_pct * POWER_WIDGET_HEIGHT
        self.machine.events.post("update_cooldown_progress",
                                 # complete_pct=complete_pct,
                                 complete_height=complete_height,
                                 opacity=opacity
                                 )

    def _complete(self, **kwargs):
        self.machine.game.player["power"] = " "
        self.shot_group.disable_rotation()
        # Clear out specific handlers we added to manage the power while it was active
        for handler in self.handlers:
            self.machine.events.remove_handler_by_key(handler)
        self.machine.events.post("power_activation_complete")

    def _get_power_shots(self, include_off=False, explicit_state=None, explicit_target=None):
        shots = []
        if include_off:
            # Include any power shots that are enabled
            filter_fn = filter_enabled_shots
        elif explicit_state and not explicit_target:
            # Include any power shots in the specified state
            filter_fn = lambda x: filter_enabled_and_state_shots(x, explicit_state)
        else:
            # Include any power shots that are enabled and "lit"
            filter_fn = filter_enabled_and_lit_shots

        # We can search for an explicit target, if desired. Otherwise, the default lane shots
        if explicit_target:
            tag = "power_target_{}".format(explicit_target)
            targets = self.machine.device_manager.collections["shots"].items_tagged(tag)
        else:
            targets = self.shots
        shots = list(filter(filter_fn, targets))

        if shots:
            self.log.debug("Found available shots for powers: %", shots)
            return shots
        # If we were looking for an explicit target but it wasn't enabled, expand the search
        if explicit_target and not include_off:
            self.log.debug("Couldn't find a lit shot for target '%'. Expanding to all shots.", explicit_target)
            return self._get_power_shots(explicit_target=None, explicit_state=explicit_state)
        # If we are looking for an explicit state but it wasn't found, expand to all targets
        if explicit_state:
            return self._get_power_shots()
        raise IndexError

    def _get_power_name(self, power):
        return self.machine.config['text_strings']['power_{}'.format(power)]

    def _set_mission_shots(self, **kwargs):
        self.log.debug("Setting initial shots from kwargs {}".format(kwargs))
        self.persisted_name = kwargs.get("persist_name")
        if self.persisted_name:
            shots_to_set = self.persisted_shots.get(self.persisted_name)
            self.log.debug("Found persisted shots: {}".format(shots_to_set))
        else:
            shots_to_set = []

        is_resume = bool(shots_to_set and self.persisted_name)

        starting_shots = kwargs.get("starting_shots")
        # We can explicitly set all shots to "hit" by setting starting shots as "none"
        # (if starting_shots is not provided, all shots will be in their initial state)
        if starting_shots == "none":
            starting_shots = [0, 0, 0, 0, 0]
        else:
            starting_shots = [int(idx) for idx in Util.string_to_list(starting_shots)]
        self.log.debug("Starting shots: %s", starting_shots)

        # Accept one profile. We can't use per-shot profiles because rotating
        # shots updates their state and does NOT move profiles from shot to shot
        profile = kwargs.get("shot_profile", "lane_shot_profile")
        # If we have no persisted shots, set them to be the starting shots
        if not shots_to_set:
            # The default profile is lit at zero and hit at 1, so the starting_shots
            # states are 0 for enabled and 1 for disabled
            shots_to_set = starting_shots
            self.log.debug("No persisted shots, setting shots %s", shots_to_set)
            # Set these as persisted values, maybe
            if self.persisted_name:
                self.persisted_shots[self.persisted_name] = shots_to_set

        if kwargs.get("is_resumable"):
            # Set up a listener to track hit shots so we know to persist
            self.add_mode_event_handler('power_shots_lit_hit', self._update_persistence)

        for idx, shot in enumerate(self.shots):
            shot.config['profile'] = \
                self.machine.device_manager.collections["shot_profiles"][profile]

            # Set the config and color, even if we're not enabling/disabling shots
            color = kwargs.get("color","FFFFFF")
            # If "inherit", use the color from the profile. Otherwise, use the specified color
            if color == "inherit":
                # Remove a previous color token, in case a different mode set one
                if shot.config['show_tokens'].get('color'):
                    shot.config['show_tokens'].pop('color')
                # shot.config['show_tokens']['color'] = shot.config['profile'].config['show_tokens'][shots_to_set[idx]]['color']
                self.log.debug("Inherit color, shot config tokens are {}".format(shot.config['show_tokens']))
            else:
                shot.config['show_tokens']['color'] = \
                    NativeTypeTemplate(kwargs.get("color","FFFFFF"), self.machine)

            if shots_to_set:
                # Our shot pointers are in the same order as shots_to_set
                try:
                    self.log.debug(" - Jumping shot idx %s to state %s", idx, shots_to_set[idx])
                    self.log.debug("    - profile is: %s", shot.config['profile'])
                    self.log.debug("    - show_tokens are: %s", shot.config['show_tokens'])
                    self.log.debug("    - state is %s, name is: %s", shot.state, shot.state_name)
                except IndexError:
                    # If we previously had a profile with more states than this one, that's okay.
                    # The jump will move us to the right place
                    self.log.debug("    - shot %s is in state %s, which profile %s doesn't have",
                                   shot.name, shot.state, shot.config['profile'].name)
                # Force jump to trigger the new show
                shot.jump(shots_to_set[idx], True, True)
                shot.enable()

        self.machine.events.post("set_environment", env=kwargs.get("env"))
        self.machine.events.post("power_shots_started", is_resume=is_resume)

    def _update_persistence(self, **kwargs):
        # A shot was hit, update the persistence
        self.persisted_shots[self.persisted_name] = [shot.state for shot in self.shots]
        self.log.debug("Updated persistence state for {}: {}".format(self.persisted_name, self.persisted_shots[self.persisted_name]))

    # Certain modes can set shot profiles with manual advance
    # Can specify one or more shots as a list, or "enabled" for all enabled shots
    def _advance_mission_shots(self, **kwargs):
        shot_names = kwargs.get("shots")
        if shot_names:
            shots = [self.shots[SHOTS.index(name)] for name in Util.string_to_event_list(shot_names)]
        else:
            state = kwargs.get("state")
            shots = list(filter(lambda x: filter_enabled_and_state_shots(x, state), self.shots))

        if not shots:
            self.log.warning("Advance mission shots found no shots by kwarg 'shots' or 'state'.")

        reset = kwargs.get("reset")
        shift = kwargs.get("shift")
        jump = kwargs.get("jump")
        for shot in shots:
            if reset:
                self.log.debug("Resetting shot {}!".format(shot))
                shot.reset()
            elif shift is not None:
                state = shot._get_state()
                self.log.debug("Shifting shot {} from {} to {}".format(shot, state, state+shift))
                shot.jump(state + shift, True)
            elif jump is not None:
                self.log.debug("Jumping shot {} to {}".format(shot, jump))
                shot.jump(int(jump), True)
            else:
                self.log.debug("Advancing shot {} (no action kwarg provided)")
                shot.advance()

        # If we are persisting these shots, set the new name
        if self.persisted_name:
            self.log.debug("Updating persistence as the result of shot advancement")
            self._update_persistence()

    # SPECIFIC POWERS
    def _activate_adrenaline(self):
        self.handlers.append(self.add_mode_event_handler(
            'timer_missiontimer_started',
            self._complete
        ))
        self.machine.events.post("missiontimer_pause_adrenaline")

    def _activate_armor(self):
        self.handlers.append(self.add_mode_event_handler(
            'ball_save_armor_disabled',
            self._complete
        ))
        self.machine.events.post("enable_armor")

    def _activate_cloak(self):
        self.log.debug("Enabling cloak shot group {}".format(self.shot_group))
        self.shot_group.enable_rotation()
        self.handlers.append(self.add_mode_event_handler(
            'flipper_cancel',
            self._rotate_cloak))
        self.handlers.append(self.add_mode_event_handler(
            'timer_power_active_complete',
            self._complete
        ))

    def _rotate_cloak(self, **kwargs):
        # TODO: Update MPF with triggering_switch kwarg to allow rotation
        direction = "right" if kwargs.get("triggering_group") == 2 else "left"
        # SAMARA special case: rotate the target shots as well, so the player
        # doesn't get stuck with no more shots to light.
        if self.machine.modes.recruitsamara.active:
            targets_group = self.machine.device_manager.collections["shot_groups"]["samara_targets"]
            targets_group.rotate(direction=direction)
        # LEGION special case: post an event so the mode can rotate the _significant_ticks
        elif self.machine.modes.recruitlegion.active:
            self.machine.events.post("powers_cloak_rotation", direction=direction)
        # ALL OTHER CASES rotate
        else:
            self.shot_group.rotate(direction=direction)
        self.log.debug("Done!")

    def _activate_charge(self):
        # If there is an explicit charge target, shoot that. Or a profile state "final"
        targets = self._get_power_shots(explicit_target="charge", explicit_state="final")
        random.choice(targets).hit()
        # Charge is used up immediately, but leave the slide up for 5 seconds
        self.machine.clock.schedule_once(self._complete, 5)

    def _activate_drone(self):
        self.handlers.append(self.add_mode_event_handler(
            'ball_drain', self._complete
        ))
        self.machine.events.post("enable_drone")

    def _activate_singularity(self):
        self.handlers.append(self.add_mode_event_handler(
            'timer_power_active_complete', self._complete
        ))
        self.machine.events.post("enable_singularity")
