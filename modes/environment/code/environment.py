import logging
from mpf.core.mode import Mode

SHOTS = ["left_orbit", "kickback", "left_ramp", "right_ramp", "right_orbit"]

class Environment(Mode):
  def __init__(self, machine, config, name, path):
    super().__init__(machine, config, name, path)
    self.log = logging.getLogger("Environment")
    self.log.setLevel("DEBUG")
    self._environment = None

  def mode_start(self, **kwargs):
    super().mode_start(**kwargs)
    self.shots = [EnvShot(self.machine, self, shot, self.log) for shot in SHOTS]
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
  def __init__(self, machine, mode, tag, log):
    self.machine = machine
    self.mode = mode
    self.name = tag
    self.log = log
    self._event_handlers = []

    try:
      self._shot = self.machine.device_manager.collections["shots"]["envshot_{}".format(self.name)]
      self._shot.disable() # Disable by default, for safety
      self.mode.add_mode_event_handler('s_{}{}_inactive'.format(
        self.name, "_exit" if self.name.endswith("_ramp") else ""), self.check_shot)
    except KeyError as e:
      self.log.error("Missing environment shot for {}".format(e))
      raise

  def reset(self):
    do_enable = True
    # Remove any old handlers
    for handler in self._event_handlers:
      self.machine.events.remove_handler_by_key(handler)
    self._event_handlers = []

    for shot in self.get_mode_shots():
      # Attach a handler for if this shot changes state
      self._event_handlers.append(
        self.mode.add_mode_event_handler("player_shot_{}_enabled".format(shot.name), self.check_shot))
      # If it's already enabled? This envshot is disabled
      if shot.enabled:
        do_enable = False

    if do_enable:
      self._enable()
    else:
      self._disable()

  def check_shot(self, **kwargs):
    # If any shots are enabled, disable this envshot
    if bool(self.enabled_count):
        self._disable()
    else:
      self._enable()
    self.log.debug("Just checked {}, {} shots are enabled so this is now {}".format(
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
    return list(filter(lambda x: x.enabled, self.get_mode_shots()))

  def get_mode_shots(self):
    self.machine.log.info("Getting shots for EnvShot '{}'".format(self.name))
    return self.machine.device_manager.collections["shots"].items_tagged("envshot_{}".format(self.name))

  @property
  def enabled_count(self):
    return len(self.get_enabled_shots())
