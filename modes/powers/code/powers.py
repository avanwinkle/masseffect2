import logging
import random
from mpf.core.mode import Mode
from mpf.devices.shot_group import ShotGroup

SHOTS = ["left_orbit", "kickback", "left_ramp", "right_ramp", "right_orbit", "dropbank", "hitbank"]
POWER_NAMES = {
    "adrenaline": "Adrenaline Rush"
}
TEST_POWER = None

class Powers(Mode):

  def __init__(self, machine, config, name, path):
    super().__init__(machine, config, name, path)
    self.log = logging.getLogger("Powers")
    self.log.setLevel(10)
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
    self.add_mode_event_handler('mode_powers_will_stop', self._complete)

  def _activate_power(self, **kwargs):
    power = self.player["power"]
    self.log.debug("Activating power {}".format(power))
    try:
        self.power_handlers[power]()
        self.machine.events.post("power_activation_success", power=power)
    except:
        self.machine.events.post("power_activation_failure", power=power)

  def _award_power(self, **kwargs):
    power = TEST_POWER or kwargs["power"]
    # variable_player can't sub values, so do it manually
    self.player["power"] = power
    self.machine.events.post("power_awarded", power=power, power_name=self.machine.config['text_strings']['power_{}'.format(power)])

  def _complete(self, **kwargs):
    self.player["power"] = " "
    for handler in self.handlers:
        self.machine.events.remove_handler_by_key(handler)
    self.machine.events.post("power_activation_complete")

  def _get_power_shots(self, include_off=False):
    shots = []
    # Include any shots tagged with power_target_(shot) that are enabled and not "off", unless do
    if include_off:
        filter_fn = lambda x: x.enabled
    else:
        filter_fn = lambda x: x.enabled and x.state_name != "off"
    
    for shot in SHOTS:
        shots += list(filter(
            filter_fn, self.machine.device_manager.collections["shots"].items_tagged("power_target_{}".format(shot))))

    if shots:
        return shots
    raise IndexError

  # SPECIFIC POWERS
  def _activate_adrenaline(self):
    self.machine.events.post("missiontimer_add_ten")

  def _activate_armor(self):
    self.machine.events.post("enable_armor")

  def _activate_cloak(self):
    targets = self._get_power_shots()
    self.shot_group = ShotGroup(self.machine, "{}_group".format(self.name))
    self.shot_group.rotation_enabled = True
    self.shot_group.config['shots'] = targets
    self.handlers.push(self.add_mode_event_handler('cloak_rotate_left', self.shot_group.rotate_left))
    self.handlers.push(self.add_mode_event_handler('cloak_rotate_right', self.shot_group.rotate_right))

  def _activate_charge(self):
    targets = self._get_power_shots()
    self.log.debug("BIOTIC CHARGE: Hitting a random shot from {}".format(targets))
    random.choice(targets).hit()

  def _activate_drone(self):
    self.machine.events.post("enable_drone")

  def _activate_singularity(self):
    targets = self._get_power_shots()
    for target in targets:
        shot = target.tags.next(lambda x: x.startswith("power_target_")).replace("power_target_", "")
        self.machine.events.post("enable_singularity_{}".format(shot))
        self.handlers.push(self.add_mode_event_handler('singularity_{}_hit', target.hit))

  