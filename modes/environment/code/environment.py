import logging
from mpf.core.mode import Mode

SHOTS = ["left_orbit", "left_orbit_nofull", "kickback", "left_ramp", "left_ramp_entrance", "right_ramp", "right_ramp_entrance", "right_orbit", "right_orbit_nofull", "standuptarget", "return_lane", "dropbank", "hitbank"]

class Environment(Mode):
  def __init__(self, machine, config, name, path):
    super().__init__(machine, config, name, path)
    self.log = logging.getLogger("Environment")
    self.log.setLevel("DEBUG")
    self._environment = None

  def mode_start(self, **kwargs):
    super().mode_start(**kwargs)
    self.shots = [EnvShot(self.machine, self, shot, self.log) for shot in SHOTS]
    self.shots.append(OutlaneShot(self.machine, self, "outlane", self.log))
    self._register_handlers()

  def _set_environment(self, **kwargs):
    self.log.debug("Setting environment with kwargs: {}".format(kwargs))
    for shot in self.shots:
      shot.reset()

    # If the environment is changing
    env = kwargs.get("env")
    if env != self._environment:
      # Stop the previous environment mode
      if self._environment:
        self.machine.events.post("stop_mode_env_{}".format(self._environment))
      # Start a new environment mode
      if env:
        self.machine.events.post("start_mode_env_{}".format(env))
      self._environment = env

  def _register_handlers(self):
    self.add_mode_event_handler('set_environment', self._set_environment)

  def _unregister_handlers(self):
    self.machine.events.remove_handler(self._set_environment)

class EnvShot(object):

  # Two events: a change in the enabled state and a change in the profile state
  target_statechange_events = ["player_shot_{}_enabled", "player_shot_{}"]

  def __init__(self, machine, mode, tag, log):
    self.machine = machine
    self.mode = mode
    self.name = tag
    self.log = log
    self._event_handlers = []

    try:
      self._shot = self.machine.device_manager.collections["shots"]["envshot_{}".format(self.name)]
      self._shot.disable() # Disable by default, for safety
      # self.mode.add_mode_event_handler('s_{}{}_inactive'.format(
      #   self.name, "_exit" if self.name.endswith("_ramp") else ""), self.check_shot)
    except KeyError as e:
      self.log.error("Missing environment shot for {}".format(e))
      raise

  def reset(self):
    do_enable = True
    # Remove any old handlers
    for handler in self._event_handlers:
      self.machine.events.remove_handler_by_key(handler)
    self._event_handlers = []

    for target in self.get_targets():
      # Attach handlers for if this target changes state
      for evt in self.target_statechange_events:
        self._event_handlers.append(
          self.mode.add_mode_event_handler(evt.format(target.name), self.check_shot))
      # If it's already enabled? This envshot is disabled
      if target.enabled:
        do_enable = False

    if do_enable:
      self._enable()
    else:
      self._disable()

  def check_shot(self, **kwargs):
    """Check if any shots tagged 'envshot_(name)' are enabled; disable this envshot if true, enable if false"""
    if bool(self.enabled_count):
        self._disable()
    else:
      self._enable()
    self.log.debug("Just checked {}, {} targets are enabled so this is now {}".format(
      self.name, self.enabled_count, self._shot.enabled))

  def _enable(self):
    if self._shot.enabled:
      self.log.debug("Envshot {} is already enabled!".format(self.name))
      return
    self.log.debug("Enabling envshot {}".format(self.name))
    self._shot.enable()

  def _disable(self):
    if not self._shot.enabled:
      self.log.debug("Envshot {} is already disabled!".format(self.name))
      return
    self.log.debug("Disabling envshot {}".format(self.name))
    self._shot.disable()

  def get_enabled_shots(self):
    # Return a list of shots tagged with this env_shot name that are enabled and not "off" state
    return list(filter(lambda x: x.enabled and x.state_name != "off", self.get_targets()))

  def get_targets(self):
    self.machine.log.info("Getting shots for EnvShot '{}'".format(self.name))
    return self.machine.device_manager.collections["shots"].items_tagged("envshot_{}".format(self.name))

  @property
  def enabled_count(self):
    return len(self.get_enabled_shots())

class OutlaneShot(EnvShot):

  target_statechange_events = ["ball_save_{}_enabled", "ball_save_{}_disabled"]

  def get_enabled_shots(self):
    # Return a list of ball_saves that are enabled
    return list(filter(lambda x: x.enabled, self.get_targets()))

  def get_targets(self):
    """We actually get ball saves, not mode shots, but same diff"""
    self.machine.log.info("Getting ball saves for OutlaneShot '{}'".format(self.name))
    return self.machine.device_manager.collections["ball_saves"].values()
