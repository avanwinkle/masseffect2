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
      * If the final multiball ball is about to be locked, multiball mode starts
      * Else if mission select is enabled, the device holds the ball until mission select ends
      * Else no lock/hold happens and a ball is returned immediately to play

    And finally, play will resume
      * If multiball mode, the device and trough will fill up the multiball ball count
      * Else if the ball was locked, a new ball is added to the playfield from the trough
      * Else if the device has physically locked balls, one is ejected (and replaced by the incoming)
      * Else the device post is held open and the incoming ball flies right through without stopping

    TODO: All of this logic is still being prototyped and debugged, so many of the values are
          hard-coded to correspond to the Overlord/Arrival locks. When it's stable, these params
          should be abstracted and/or use events to set the desired mode behavior.
  """

  def __init__(self, machine, config, name, path):
    super().__init__(machine, config, name, path)
    self.log = logging.getLogger("LockHandler")
    self.log.setLevel("DEBUG")
    self.settings = config.get("mode_settings")

    # We want to track whether to lock this ball, so when handling external events we can act accordingly
    self._will_lock_ball = False

  def mode_start(self, **kwargs):
    super().mode_start(**kwargs)
    self.log.info("LockHandler Mode is starting")

    # We need a pointer to the physical ball device to count physically locked balls
    for device in self.machine.ball_devices:
      if device.name == self.settings['ball_device']:
        self._bd_physical_lock = device
    if not hasattr(self, "_bd_physical_lock"):
      raise AttributeError("LockHandler cannot find ball_device named {}".format(self.settings['ball_device']))
    # We need a pointer to the multiball lock device to count virtually locked balls
    for device in self.mode_devices:
      if device.name == self.settings['lock_device']:
        self._logicallockdevice = device
    if not hasattr(self, "_logicallockdevice"):
      raise AttributeError("LockHandler cannot find multiball_lock named {}".format(self.settings['lock_device']))
    # We need a shot that defines whether lock is lit
    try:
      lockshot = self.machine.shots["{}_shot".format(self._logicallockdevice.name)]
      self.log.info("LockHandler is looking for multiball lock shot. " +
        "state: {}, state_name: {}, enabled: {}".format(lockshot.state, lockshot.state_name, lockshot.enabled)
        )
      # If that shot is enabled when this mode starts, make an event to enable the lock
      # AVW: Is this still necessary? Doesn't feel like it would do anything
      if lockshot.enabled:
        self._post_event('enable_{}'.format(self._logicallockdevice.name))
    except KeyError:
      self.log.info("LockHandler has no {} lock shot, locking will be disabled")

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
    virtual_balls_locked = self._logicallockdevice.locked_balls
    self._will_lock_ball = self._logicallockdevice.enabled

    self._post_event('lockhandler_ball_entered',
                      will_lock_ball=self._will_lock_ball,
                      missions_available=missions_available,
                      physical_balls_locked=physical_balls_locked,
                      virtual_balls_locked=virtual_balls_locked
                      )

    if self._logicallockdevice.is_virtually_full:
      self.log.info(" - Lock is going to fill the multiball, skip lock handling")
    elif self.player.bypass_missionselect:
      self.log.info(" - Player has passed on mission selection, skipping mode start")
    elif missions_available:
      self.log.info(" - Lock is not enabled but missions are available")

  def _handle_bypasscheck(self, **kwargs):
    """ Logic for assessing whether to hold/lock the ball or bypass the lock """
    do_bypass = True
    mission_delay = -1

    # SUICIDE:
    if self.machine.modes.suicide_base.active:
      # If the suicide mission wants to hold the ball for picking a specialist, allow it to handle
      if self.machine.modes.suicide_infiltration.active:
        if self.machine.game.player["valves_state"].value <= 1:
          self.log.info(" - Suicide wants a specialist, lockhandler is taking no action")
          # We don't need to start missionselect here, suicide_base will take care of it:
          # infiltration: valves > specialist_through > infiltration_complete
          # suicide_base: infiltration_complete > start_mode_missionselect
        else:
          self._bypass_lock()
        return
      # If a specialist has died and we need to select another, queue up mission select
      #elif self.machine.game.player["status_{}".format(self.machine.game.player["specialist"])] == -1:
      elif (self.player.achievements["infiltration"] == "started" and not self.machine.modes.suicide_infiltration.active) or (self.player.achievements["longwalk"] == "started" and not self.machine.modes.suicide_longwalk.active):
        self.log.info(" - Suicide needs a specialist because infiltration/longwalk failed".format(self.machine.game.player["specialist"]))
        do_bypass = False
        mission_delay = 500

    # WIZARD:
    # If a wizard mode is enabled, NEVER attempt to lock a ball (even for multiball)
    elif not self.machine.modes.get("global").active: # global is a reserved word
      self.log.info(" - A wizard mode is active, bypassing lock post")
      self._bypass_lock()
      return

    # MULTIBALL AND MISSION
    # If a mission mode is active, bypass the lock if we have 2 balls locked already
    # (i.e. do not allow a ball to lock for a multiball to start)
    elif not self.machine.modes.field.active and self._logicallockdevice.locked_balls == 2:
      self.log.info(" - Two balls are locked and field mode isn't active, bypassing lock post")
      self._bypass_lock()
      # Temporarily disable the lock, just in case the bypass post doesn't let a ball out
      if self._logicallockdevice.enabled:
        self._logicallockdevice.disable()
        self.delay.add(callback=self._logicallockdevice.enable, ms=1000,
                     event='start_mode_missionselect')
      return

    # LOCK:
    # If the lock shot is enabled, hold onto the ball
    if self._logicallockdevice.enabled:
      self.log.info(" - Lock is lit, not going to bypass lock post")
      do_bypass = False

      # **Warning** This is a hard-coded conditional, which shouldn't be in a python file
      self.log.debug("{}".format(self.player.achievements))
      fmball = "overlord" if self.player.achievements["arrival"] == "disabled" else "arrival"
      # Show the slide for the upcoming ball while we wait for it to settle into the device
      self.machine.events.post("lockhandler_{}_ball_will_lock".format(fmball),
                               total_balls_locked=self._logicallockdevice.locked_balls+1,
                               fmball=fmball)

      # If we're about to start a multiball, don't offer missionselect
      if self._logicallockdevice.locked_balls == 2:
        return

    # HOLD:
    # If no mission currently running (i.e. field mode is active) and a mission is available
    # unless the player has opted to bypass the missions (valid until a new mission is available),
    # or if Garrus/Samara is about to be (since the ball lock shot is also their mission light shot)
    if self.machine.modes.field.active and ((self.player.status_garrus == 2 or self.player.status_samara == 2) or
                                              (self.player.available_missions > 0 and self.player.bypass_missionselect == 0)):
      self.log.info(" - Field mode is active and missions are available, not going to bypass lock post")
      do_bypass = False

      # If we are locking a ball, wait 2.5s for the slide/dialog
      if self._logicallockdevice.enabled:
        mission_delay = 2500
      # If we aren't locking the ball, start missionselect in a second
      else:
        mission_delay = 1000

    # MISSION SELECT:
    # If the above handler wants to start mission select, do so after the requested delay
    if mission_delay > -1:
      self.delay.add(callback=self._post_event, ms=mission_delay,
                     event='start_mode_missionselect')

    # BYPASS:
    # If neither of the above locking conditions, bypass the lock/hold
    elif do_bypass:
      self.log.info(" - Lock not enabled and no missions available, bypassing lock post")
      self._bypass_lock()

  def _handle_missionselect_stop(self, **kwargs):
    """ Handler for when mode_missionselect_stop is called. Namely, get a ball active! """
    del kwargs

  def _handle_multiball_start(self, **kwargs):
    """ Handler for when logic determines a multiball mode should begin """
    self._post_event('start_field_multiball')

  def _register_handlers(self):
    self.add_mode_event_handler('balldevice_{}_ball_entered'.format(self._bd_physical_lock.name),
                                self._handle_ball_enter)
    self.add_mode_event_handler('multiball_lock_{}_full'.format(self._logicallockdevice.name),
                                self._handle_multiball_start)
    self.add_mode_event_handler('lockhandler_check_bypass',
                                self._handle_bypasscheck)
    self.add_mode_event_handler('mode_missionselect_will_stop',
                                self._handle_missionselect_stop)

  def _unregister_handlers(self):
    self.machine.events.remove_handler(self._handle_ball_enter)
    self.machine.events.remove_handler(self._handle_bypasscheck)
    self.machine.events.remove_handler(self._handle_multiball_start)
    self.machine.events.remove_handler(self._handle_missionselect_stop)
