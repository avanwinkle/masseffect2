"""Custom mode and Shot objects for managing environment sounds."""

import logging
from mpf.core.mode import Mode

SHOTS = ["left_orbit", "left_orbit_nofull", "kickback", "left_ramp", "left_ramp_entrance",
         "right_ramp", "right_ramp_entrance", "right_orbit", "right_orbit_nofull",
         "standuptarget", "return_lane", "dropbank", "hitbank", "tenpoints"]


class Environment(Mode):

    """Mode code for creating handlers to set/unset environment shots."""

    def __init__(self, *args, **kwargs):
        """Initialize mode, create logger, set environment."""
        super().__init__(*args, **kwargs)
        self.log = logging.getLogger("Environment")
        self.log.setLevel(20)
        self.shots = []
        self._environment = None
        self._removal_handlers = None

    def mode_start(self, **kwargs):
        """Mode start: create shots and register handlers."""
        super().mode_start(**kwargs)
        self.shots = [EnvShot(self.machine, self, shot, self.log) for shot in SHOTS]
        self.shots.append(OutlaneShot(self.machine, self, "outlane", self.log))
        self._register_handlers()

    def _set_environment(self, **kwargs):
        self.log.debug("Setting environment with kwargs: %s", kwargs)
        for shot in self.shots:
            shot.reset()

        # If the environment is changing
        env = kwargs.get("env")
        if env != self._environment:
            # Stop the previous environment mode
            self._clear_environment()
            # Start a new environment mode
            if env:
                self.machine.events.post("start_mode_env_{}".format(env))
                if kwargs.get("stop_events"):
                    stop_events = kwargs.get("stop_events")
                    if isinstance(stop_events, str):
                        stop_events = stop_events.split(r", ?")
                    self._removal_handlers = [
                        self.add_mode_event_handler(event,
                                                    self._clear_environment,
                                                    priority=idx) for idx, event in enumerate(stop_events)
                    ]

            self._environment = env
            self.log.debug("Environment is now %s", self._environment)

    def _register_handlers(self):
        self.add_mode_event_handler('set_environment', self._set_environment)

    def _clear_environment(self, **kwargs):
        if self._environment:
            self.machine.events.post("stop_mode_env_{}".format(self._environment))
        if self._removal_handlers:
            self.machine.events.remove_handlers_by_keys(self._removal_handlers)
            self._removal_handlers = None
        self._environment = None
        self.log.debug("Environment cleared and removal handlers removed.")


class EnvShot():

    """Object wrapper for a shot in the current mode defined as an environment shot."""

    # Two events: a change in the enabled state and a change in the profile state
    target_statechange_events = ["player_shot_{}_enabled", "player_shot_{}"]

    def __init__(self, machine, mode, tag, log):
        """Initialize a shot object for a given environment shot."""
        self.machine = machine
        self.mode = mode
        self.name = tag
        self.log = log
        self._event_handlers = []

        try:
            self._shot = self.machine.device_manager.collections["shots"]["envshot_{}".format(self.name)]
            self._shot.disable()  # Disable by default, for safety
            # self.mode.add_mode_event_handler('s_{}{}_inactive'.format(
            #   self.name, "_exit" if self.name.endswith("_ramp") else ""), self.check_shot)
        except KeyError as e:
            self.log.error("Missing environment shot for {}".format(e))
            raise

    def reset(self):
        """Remove old handlers from this shot and find new tagged shots to add handlers for."""
        do_enable = True
        # Remove any old handlers
        for handler in self._event_handlers:
            self.machine.events.remove_handler_by_key(handler)
        self._event_handlers = []

        for target in self.get_targets():
            # Attach handlers for if this target changes state
            for evt in self.target_statechange_events:
                self._event_handlers.append(
                    self.mode.add_mode_event_handler(evt.format(target.name), self._check_shot))
            # If it's already enabled? This envshot is disabled
            if target.enabled:
                do_enable = False

        if do_enable:
            self._enable()
        else:
            self._disable()

    def _check_shot(self, **kwargs):
        del kwargs
        """Check if any shots tagged 'envshot_(name)' are enabled; disable this envshot if true, enable if false."""
        if bool(self.enabled_count):
            self._disable()
        else:
            self._enable()
        self.log.debug("Just checked %s, %s targets are enabled so this is now {}",
                       self.name, self.enabled_count, self._shot.enabled)

    def _enable(self):
        if self._shot.enabled:
            self.log.debug("Envshot %s is already enabled!", self.name)
            return
        self.log.debug("Enabling envshot %s", self.name)
        self._shot.enable()

    def _disable(self):
        if not self._shot.enabled:
            self.log.debug("Envshot %s is already disabled!", self.name)
            return
        self.log.debug("Disabling envshot %s", self.name)
        self._shot.disable()

    def get_enabled_shots(self):
        """Return a list of shots tagged with this env_shot name that are enabled and not "off" state."""
        return list(filter(lambda x: x.enabled and x.state_name != "off", self.get_targets()))

    def get_targets(self):
        """Return all shots tagged as environment shots for this EnvShot."""
        self.log.debug("Getting shots for EnvShot '%s'", self.name)
        return self.machine.device_manager.collections["shots"].items_tagged("envshot_{}".format(self.name))

    @property
    def enabled_count(self):
        """Return the number of shots tagged with this env_shot name that are currently lit."""
        return len(self.get_enabled_shots())


class OutlaneShot(EnvShot):

    """Specific EnvShot class for an outlane, with ball-save behavior."""

    target_statechange_events = ["ball_save_{}_enabled", "ball_save_{}_disabled"]

    def get_enabled_shots(self):
        """Return a list of ball_saves that are enabled."""
        return list(filter(lambda x: x.enabled, self.get_targets()))

    def get_targets(self):
        """Get outlane targets based on medigel early-saves."""
        self.log.debug("Getting ball saves for OutlaneShot '%s'", self.name)
        # Targets include any ball_save being active OR the medigel shot being active
        outlane_targets = [
            self.machine.device_manager.collections["shots"]["medigel_left_shot"],
            self.machine.device_manager.collections["shots"]["medigel_right_shot"],
        ]
        outlane_targets.extend(self.machine.device_manager.collections["ball_saves"].values())
        return outlane_targets
