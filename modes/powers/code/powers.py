import logging
import random
from mpf.core.mode import Mode
from mpf.devices.shot_group import ShotGroup

SHOTS = ["left_orbit", "kickback", "left_ramp", "right_ramp", "right_orbit", "dropbank", "hitbank"]
TEST_POWER = None
DESCRIPTIONS = {
    "adrenaline": "Pauses all timers\nfor 20 seconds",
    "cloak": "Allows flippers to\nrotate lanes",
    "armor": "Enables a 20s\nball save",
    "drone": "Instant multiball or\nadd-a-ball",
    "singularity": "Target hits count\nas lane hits",
    "charge": "Hits a lit lane\nat random",
}


def filter_enabled_shots(x):
    return x.enabled


def filter_enabled_and_lit_shots(x):
    return x.enabled and x.state_name == "lit"


class Powers(Mode):
    def __init__(self, machine, config, name, path):
        super().__init__(machine, config, name, path)
        self.log = logging.getLogger("Powers")
        self.log.setLevel(1)
        self.shot_group = None
        self.handlers = []
        self.power_handlers = {
            "adrenaline": self._activate_adrenaline,
            "armor": self._activate_armor,
            "cloak": self._activate_cloak,
            "charge": self._activate_charge,
            "drone": self._activate_drone,
            "singularity": self._activate_singularity,
        }

    def mode_start(self, **kwargs):
        super().mode_start(**kwargs)
        self.add_mode_event_handler('award_power', self._award_power)
        self.add_mode_event_handler('activate_power', self._activate_power)
        self.add_mode_event_handler('timer_power_active_complete', self._complete)

    def _activate_power(self, **kwargs):
        power = self.machine.game.player["power"]
        self.log.debug("Activating power {}".format(power))
        try:
            self.power_handlers[power]()
            self.machine.events.post("power_activation_success", power=power)
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

    def _complete(self, **kwargs):
        self.machine.game.player["power"] = " "
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

        # We can search for an explicit target, if desired. Otherwise, any power_target tag
        tag = "power_target_{}".format(explicit_target) if explicit_target else "power_target"
        shots = list(filter(filter_fn, self.machine.device_manager.collections["shots"].items_tagged(tag)))

        if shots:
            return shots
        raise IndexError

    def _get_power_name(self, power):
        return self.machine.config['text_strings']['power_{}'.format(power)]

    # SPECIFIC POWERS
    def _activate_adrenaline(self):
        self.machine.events.post("missiontimer_pause_ten")

    def _activate_armor(self):
        self.machine.events.post("enable_armor")

    def _activate_cloak(self):
        # Get all enabled targets, even those that are not lit, so we can rotate to them
        targets = self._get_power_shots(include_off=True)
        self.shot_group = ShotGroup(self.machine, "{}_group".format(self.name))
        self.shot_group.config['shots'] = targets
        self.shot_group.rotation_enabled = True
        self.handlers.append(self.add_mode_event_handler('cloak_rotate_left', self.shot_group.event_rotate_left))
        self.handlers.append(self.add_mode_event_handler('cloak_rotate_right', self.shot_group.event_rotate_right))

    def _activate_charge(self):
        # If there is an explicit charge target, shoot that
        try:
            targets = self._get_power_shots(explicit_target="charge")
        # If not, go for any shot
        except IndexError:
            targets = self._get_power_shots()
        random.choice(targets).hit()
        # Charge is used up immediately
        self._complete()

    def _activate_drone(self):
        self.machine.events.post("enable_drone")

    def _activate_singularity(self):
        targets = self._get_power_shots()
        for target in targets:
            # Find the shot that corresponds to this target so we can light the appropriate standup
            shot = next(iter(target.tags), lambda x: x.startswith("power_target_")).replace("power_target_", "")
            self.machine.events.post("enable_singularity_{}".format(shot))
            self.handlers.append(self.add_mode_event_handler('singularity_{}_hit', target.event_hit))
