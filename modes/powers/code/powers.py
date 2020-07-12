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
        self.shots = [self.machine.device_manager.collections["shots"][shot] for shot in SHOTS]
        self.shot_group = self.machine.device_manager.collections["shot_groups"]["power_shots"]
        self.shot_group.disable_rotation()
        
        self.persisted_shots = self.player["persisted_shots"]
        if not self.persisted_shots:
            self.persisted_shots = {}
            self.player["persisted_shots"] = self.persisted_shots
            self.log.debug("Set persisted shots for player {}: {}".format(self.player, self.persisted_shots))
        else:
            self.log.debug("Rectrieved persisted shots from player {}: {}".format(self.player, self.persisted_shots))
        
        self.timer = self.machine.device_manager.collections["timers"]["power_active"]
        self.log.debug("Mode started with shots: {}".format(self.shots))

        # Disable all shots before we get started
        for shot in self.shots:
            shot.disable()
            
        self.add_mode_event_handler('set_mission_shots', self._set_mission_shots)
        self.add_mode_event_handler('advance_mission_shots', self._advance_mission_shots)
        self.add_mode_event_handler('award_power', self._award_power)
        self.add_mode_event_handler('activate_power', self._activate_power)
        self.add_mode_event_handler('timer_power_active_complete', self._complete)
        
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
            self.log.debug("Found available shots for powers: {}".format(shots))
            return shots
        # If we were looking for an explicit target but it wasn't enabled, expand the search
        elif explicit_target and not include_off:
            self.log.debug("Couldn't find a lit shot for target '{}'. Expanding to all shots.".format(explicit_target))
            return self._get_power_shots(explicit_target=None, explicit_state=explicit_state)
        # If we are looking for an explicit state but it wasn't found, expand to all targets
        elif explicit_state:
            return self._get_power_shots()
        raise IndexError

    def _get_power_name(self, power):
        return self.machine.config['text_strings']['power_{}'.format(power)]

    def _set_mission_shots(self, **kwargs):
        self.log.debug("Setting initial shots from kwargs {}".format(kwargs))
        self.persisted_name = kwargs.get("persist_name")
        shots_to_set = self.persisted_shots.get(self.persisted_name)
        
        is_resume = True if shots_to_set and self.persisted_name else False

        starting_shots = kwargs.get("starting_shots")
        # We can explicitly set all shots to "hit" by setting starting shots as "none"
        # (if starting_shots is not provided, all shots will be in their initial state)
        if starting_shots == "none":
            starting_shots = []

        # Accept one profile or a list of profiles per shot
        profiles = kwargs.get("shot_profile", "lane_shot_profile")
        if not isinstance(profiles, list):
            profiles = [profiles for _ in range(0,5)]
        # If we have starting shots and no persisted shots, set both
        if starting_shots is not None and not shots_to_set:
            shots_to_set = [1 if shot in starting_shots else 0 for shot in SHOTS]
            self.log.debug("No persisted shots, setting shots {}".format(shots_to_set))
            # Set these as persisted values, maybe
            if self.persisted_name:
                self.persisted_shots[self.persisted_name] = shots_to_set
                # Set up a listener to track hit shots so we know to persist
                self.add_mode_event_handler('power_shots_lit_hit', self._update_persistence)
        
        for idx, shot in enumerate(self.shots):
            # Set the config and color, even if we're not enabling/disabling shots
            shot.config['show_tokens']['color'] = \
                NativeTypeTemplate(kwargs.get("color","FFFFFF"), self.machine)
            shot.config['profile'] = \
                self.machine.device_manager.collections["shot_profiles"][profiles[idx]]
            
            ## TODO: Provide starting_states to set explicit states for each shot.
            ##       Also, restore preserved state by .jump(shots_to_set[idx])
            if shots_to_set:
                # Our shot pointers are in the same order
                if shots_to_set[idx]:
                    shot.restart()
                else:
                    # Don't disable, the shot, set it's state to "hit" so we can rotate
                    shot.advance(force=True)
                    shot.enable()
                    
        self.machine.events.post("set_environment", env=kwargs.get("env"))
        self.machine.events.post("power_shots_started", is_resume=is_resume)

    def _update_persistence(self, **kwargs):
        # A shot was hit, update the persistence
        self.persisted_shots[self.persisted_name] = [1 if filter_enabled_and_lit_shots(shot) else 0 for shot in self.shots]
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
                shot.jump(state + shift)
            elif jump:
                self.log.debug("Jumping shot {} to {}".format(shot, jump))
                shot.jump(int(jump))
            else:
                shot.advance()

        # If we are persisting these shots, set the new name
        if self.persisted_name:
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
        self.log.debug("Rotating cloak in direction {}, kwargs {}".format(direction, kwargs))
        self.log.debug("Shot group is: {}".format(self.shot_group))
        self.shot_group.rotate(direction=direction)
        self.log.debug("Done!")

    def _activate_charge(self):
        # If there is an explicit charge target, shoot that. Or a profile state "final"
        targets = self._get_power_shots(explicit_target="charge", explicit_state="final")
        random.choice(targets).hit()
        # Charge is used up immediately
        self._complete()

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
