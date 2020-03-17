import logging
import random
from mpf.core.mode import Mode
from mpf.devices.shot_group import ShotGroup
from mpf.core.utility_functions import Util
from mpf.core.rgb_color import RGBColor
from mpf.core.placeholder_manager import NativeTypeTemplate

SHOTS = ["left_orbit", "kickback", "left_ramp", "right_ramp", "right_orbit"]
TEST_POWER = "singularity"
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


class Powers(Mode):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.log = logging.getLogger("Powers")
        self.log.setLevel(1)
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
        self.persisted_shots = {}

    def mode_will_start(self, **kwargs):
        self.shots = [self.machine.device_manager.collections["shots"][shot] for shot in SHOTS]
        self.shot_group = self.machine.device_manager.collections["shot_groups"]["power_shots"]
        self.shot_group.disable_rotation()
        self.timer = self.machine.device_manager.collections["timers"]["power_active"]
        self.log.info("Mode started with shots: {}".format(self.shots))
        self.add_mode_event_handler('set_mission_shots', self._set_mission_shots)
        self.add_mode_event_handler('award_power', self._award_power)
        self.add_mode_event_handler('activate_power', self._activate_power)
        self.add_mode_event_handler('timer_power_active_complete', self._complete)
        
    def _activate_power(self, **kwargs):
        power = self.machine.game.player["power"]
        self.log.debug("Activating power {}".format(power))
        try:
            self.power_handlers[power]()
            self.machine.events.post("power_activation_success", power=power, l_power="l_power_{}".format(power))
            if self.timer.ticks > 0:
                self.timer.start()
        except IndexError:
            self.machine.events.post("power_activation_failure", power=power)

    def _award_power(self, **kwargs):
        power = TEST_POWER or kwargs["power"]
        # variable_player can't sub values, so do it manually
        self.machine.game.player["power"] = power
        self.machine.events.post("power_awarded",
                                 l_power="l_power_{}".format(power),
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

    def _get_power_shots(self, include_off=False, explicit_target=None):
        shots = []
        if include_off:
            # Include any shots tagged with power_target that are enabled
            filter_fn = filter_enabled_shots
        else:
            # Include any shots tagged with power_target that are enabled AND "lit"
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
        # If we were looking for an explicit target but it wasn't enabled, expand to all targets
        elif explicit_target and not include_off:
            self.log.debug("Couldn't find a lit shot for target '{}'. Expanding to all shots.".format(explicit_target))
            return self._get_power_shots(explicit_target=None)
        raise IndexError

    def _get_power_name(self, power):
        return self.machine.config['text_strings']['power_{}'.format(power)]

    def _set_mission_shots(self, **kwargs):
        self.log.info("Setting initial shots from kwargs {}".format(kwargs))
        name = kwargs.get("persist_name")
        name = name and name != True
        shots_to_set = self.persisted_shots.get(name)
        starting_shots = kwargs.get("starting_shots")
        
        # If we have starting shots and no persisted shots, set both
        if starting_shots and not shots_to_set:
            shots_to_set = [1 if shot in starting_shots else 0 for shot in SHOTS]
            self.log.info("No persisted shots, setting shots {}".format(shots_to_set))
            # Set these as persisted values, maybe
            if name:
                self.persisted_shots[name] = shots_to_set
        
        if shots_to_set:
            # Our shot pointers are in the same order
            for idx, shot in enumerate(self.shots):
                shot.config['show_tokens']['color'] = NativeTypeTemplate(kwargs.get("color","FFFFFF"), self.machine)
                if shots_to_set[idx]:
                    self.log.info("Shot {} has config {}".format(shot, shot.config))
                    shot.restart()
                else:
                    # Don't disable, the shot, set it's state to "hit" so we can rotate
                    shot.advance(force=True)
                    shot.enable()
        else:
            self.log.info("No shots to set!")
        self.machine.events.post("set_env", env=kwargs.get("env"))

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
        # If there is an explicit charge target, shoot that
        targets = self._get_power_shots(explicit_target="charge")
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
