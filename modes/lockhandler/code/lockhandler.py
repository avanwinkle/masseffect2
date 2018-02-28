import logging
from mpf.core.mode import Mode

class LockHandler(Mode):

  """
    Mode which handles ball entry for missionselect hold and multiball lock.

    This is pretty good at handling the basic conditions of the lock behavior:
      * Is lock lit?
      * How many balls are physically locked in the device?
      * How many balls are virtually locked for multiball?
      * Are there missions available?

    Based on those conditions, one of the following may occur:
      * If the final multiball ball is locked, multiball mode starts
      * Else if mission select is enabled, the device holds the ball
      * Else no lock/hold happens and the/a ball is returned immediately to play

    And finally, play will resume
      * If multiball mode, the device and trough will fill up the multiball ball count
      * Else if the ball was locked, a new ball is added to the playfield from the trough
      * Else if the device has physically locked balls, one is ejected (and replaced by the incoming)
      * Else the device post is held open and the incoming ball flies right through without stopping

    TODO: All of this logic is still being prototyped and debugged, so many of the values are
          hard-coded to correspond to the Overlord multiball lock. When it's stable, these params
          should be abstracted and/or use events to set the desired mode behavior.
  """

  def __init__(self, machine, config, name, path):
    super().__init__(machine, config, name, path)
    self.log = logging.getLogger("LockHandler")
    self.log.setLevel("DEBUG")
    # We want to track whether to lock this ball, so when handling external events we can act accordingly
    self._will_lock_ball = False

  def mode_start(self, **kwargs):
    super().mode_start(**kwargs)
    self.log.debug("LockHandler Mode is starting")

    # We need a pointer to the physical ball device to count physically locked balls
    for device in self.machine.ball_devices:
      if device.name == 'bd_lock':
        self._bd_physical_lock = device
    # We need a pointer to the multiball lock device to count virtually locked balls
    for device in self.mode_devices:
      if device.name == 'overlordlock':
        self._overlordlock = device
    # We need a shot that defines whether lock is lit
    try:
      lockshot = self.machine.shots.overlord_lock_ball_shot
      self.log.debug("LockHandler is looking for overlord lock shot. " +
        "state: {}, state_name: {}, enabled: {}".format(lockshot.state, lockshot.state_name, lockshot.enabled)
        )
      if self.machine.shots.overlord_lock_ball_shot.enabled:
        self._post_event('enable_overlord_lock')
    except KeyError:
      self.log.debug("LockHandler has no overlord lock shot, locking will be disabled")

    self._register_handlers()

  def mode_stop(self, **kwargs):
    self._unregister_handlers()
    super().mode_stop(**kwargs)

  def _bypass_lock(self):
    # If a ball is in the lock, fire it quickly out of the ball device. When the incoming ball is registered,
    # the ball device will do a physical check and assess that its count has not changed. Tricky!
    if self._bd_physical_lock.balls > 0:
      # TODO: create a more precise list of pulse times depending on how many balls are locked?
      self._post_event('bypass_lock_release_pulse_short')
    # If the lock is empty, call the bypass on the ball device's eject coil, holding it open so that the
    # incoming ball will fly through. After the entrance_switch delay, the ball device will do a physical check
    # and assess that its count (zero balls) has not changed.
    else:
      self._post_event('bypass_lock_release_pulse_long')

  def _post_event(self, event, **kwargs):
    """ Helper method for posting events """
    self.machine.events.post(event, **kwargs)

  def _handle_ball_enter(self, **kwargs):
    """ Logic for assessing desired behavior when a ball enters the physical ball lock device """
    missions_available = self.machine.modes.field.active and self.player.available_missions > 0
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
      self.log.debug(" - Lock is going to fill the multiball, skip lock handling")
    elif self.player.bypass_missionselect:
      self.log.debug(" - Player has passed on mission selection, skipping mode start")
    elif missions_available:
      self.log.debug(" - Lock is not enabled but missions are available")
      self._post_event('start_mode_missionselect')

  def _handle_bypasscheck(self, **kwargs):
    """ Logic for assessing whether to hold/lock the ball or bypass the lock """

    # WIZARD:
    # If a wizard mode is enabled, NEVER attempt to lock a ball (even for multiball)
    if not self.machine.modes.get("global").active: # global is a reserved word
      self.log.debug(" - A wizard mode is active, bypassing lock post")
      pass

    # MULTIBALL AND FIELD
    # If a field mode is active, lock a ball only if it won't fill the multiball
    elif not self.machine.modes.field.active and self._overlordlock.locked_balls == 2:
      pass

    # LOCK:
    # If the lock shot is enabled, hold onto the ball
    elif self._overlordlock.enabled:
      self.log.debug(" - Lock is lit, not going to bypass lock post")
      # Show the slide already, while we wait for the balls to settle into the device
      self.machine.events.post("show_overlord_locked_slide", total_balls_locked=self._overlordlock.locked_balls)
      return

    # HOLD:
    # If no mission currently running (i.e. field mode is active) and a mission is available
    # unless the player has opted to bypass the missions (valid until a new mission is available),
    # or if Garrus/Samara is about to be (since the ball lock shot is also their mission light shot)
    elif self.machine.modes.field.active and ((self.player.status_garrus == 2 or self.player.status_samara == 2) or
                                              (self.player.available_missions > 0 and self.player.bypass_missionselect == 0)):
      self.log.debug(" - Field mode is active and missions are available, not going to bypass lock post")
      return

    # BYPASS:
    # If neither of the above locking conditions, bypass the lock/hold
    else:
      self.log.debug(" - Lock not enabled and no missions available, bypassing lock post")

    self._bypass_lock()

  def _handle_missionselect_stop(self, **kwargs):
    """ Handler for when mode_missionselect_stop is called. Namely, get a ball active! """
    del kwargs

  def _handle_multiball_start(self, **kwargs):
    """ Handler for when logic determines a multiball mode should begin """
    self._post_event('start_mode_overlordmultiball')

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
