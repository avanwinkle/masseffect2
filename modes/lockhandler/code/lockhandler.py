from mpf.core.mode import Mode

class LockHandler(Mode):

  """Mode which handles ball entry for missionselect and multiball lock """

  def __init__(self, machine, config, name, path):
    super().__init__(machine, config, name, path)
    self.debug_log = self.machine.log.info

    self._will_lock_ball = False

  def mode_start(self, **kwargs):
    super().mode_start(**kwargs)
    self.debug_log("LockHandler Mode is starting")
    for device in self.machine.ball_devices:
      if device.name == 'bd_lock':
        self._bd_physical_lock = device

    for device in self.mode_devices:
      if device.name == 'physicallock':
        self._physicallock = device
      elif device.name == 'overlordlock':
        self._overlordlock = device

    try:
      lockshot = self.machine.shots.overlord_lock_ball_shot
      self.debug_log("LockHandler is looking for overlord lock shot. " +
        "state: {}, state_name: {}, enabled: {}".format(lockshot.state, lockshot.state_name,lockshot.enabled)
        )
      if self.machine.shots.overlord_lock_ball_shot.enabled:
        self._post_event('enable_overlord_lock')
    except KeyError:
      self.debug_log("LockHandler has no overlord lock shot, locking will be disabled")

    self._register_handlers()

  def mode_stop(self, **kwargs):
    self._unregister_handlers()
    super().mode_stop(**kwargs)

  def _bypass_lock(self):
    # If a ball is in the lock, fire it quickly to trick the ball lock
    if self._bd_physical_lock.balls > 0:
      self._post_event('bypass_lock_release_pulse_short')
    # If the lock is empty, call the bypass
    else:
      self._post_event('bypass_lock_release_pulse_long')

  def _eject_one_ball(self):
    self._post_event('lock_eject_one_ball')

  def _post_event(self, event, **kwargs):
    self.machine.events.post(event, **kwargs)

  def _handle_ball_enter(self, **kwargs):
    missions_available = self.machine.modes.recruitfield.active and self.player.available_missions > 0
    physical_balls_locked = self._bd_physical_lock.balls
    virtual_balls_locked = self._overlordlock.locked_balls
    self._will_lock_ball = self._overlordlock.enabled

    self._post_event('lockhandler_ball_entered',
                      will_lock_ball=self._will_lock_ball,
                      missions_available=missions_available,
                      physical_balls_locked=physical_balls_locked,
                      virtual_balls_locked=virtual_balls_locked
                      )

    if self._overlordlock.is_virtually_full:
      self.debug_log(" - Lock is going to fill the multiball, skip lock handling")
    elif missions_available:
      self.debug_log(" - Lock is not enabled but missions are available")
      self._post_event('start_mode_missionselect')
    else:
      self._return_ball_to_playfield()

  def _handle_bypasscheck(self, **kwargs):
    # Always allow a lock if enabled but not enough to start multiball
    if self._overlordlock.enabled and self._overlordlock.locked_balls < 2:
      self.debug_log(" - Lock is lit, not going to bypass lock post")
      return
    # Except for the above locking condition, bypass when on a mission
    # Allow mission select if they are available (or Garrus is about to be)
    elif self.machine.modes.recruitfield.active and self.player.available_missions > 0 or self.player.status_garrus == 2:
      self.debug_log(" - Recruitfield is active and missions are available, not going to bypass lock post")
      return

    self.debug_log(" - Lock not enabled and no missions available, bypassing lock post")
    self._bypass_lock()

  def _handle_missionselect_stop(self, **kwargs):
    del kwargs
    self._return_ball_to_playfield()

  def _handle_multiball_start(self, **kwargs):
    self._post_event('start_mode_overlordmultiball')

  def _return_ball_to_playfield(self):
     # If there are more physical than virtual, eject
    if self._will_lock_ball:
      self.debug_log('LockHandler is keeping a physical ball locked, adding one via playfield')
      self._overlordlock.source_playfield.add_ball(balls=1)
      self._will_lock_ball = False
    else:
      self.debug_log('LockHandler does not want to hold this ball, ejecting it')
      self._eject_one_ball()

  def _register_handlers(self):
    self.machine.events.add_handler('balldevice_bd_lock_ball_entered',
                                    self._handle_ball_enter)
    self.machine.events.add_handler('multiball_lock_overlordlock_full',
                                    self._handle_multiball_start)
    self.machine.events.add_handler('lockhandler_check_bypass',
                                    self._handle_bypasscheck)
    self.machine.events.add_handler('mode_missionselect_will_stop',
                                    self._handle_missionselect_stop)

  def _unregister_handlers(self):
    self.machine.events.remove_handler(self._handle_ball_enter)
    self.machine.events.remove_handler(self._handle_bypasscheck)
    self.machine.events.remove_handler(self._handle_multiball_start)
    self.machine.events.remove_handler(self._handle_missionselect_stop)
