from mpfmc.core.scriptlet import Scriptlet

NAME_FORMATS = {
  "killed":          "squadmate_{squadmate}_killed",
  "killed_callback": "squadmate_{squadmate}_killed_callback_{callback_mate}",
  "skillshot":       "squadmate_{squadmate}_nice_shot",
}
COMPLETED_EVENT_NAME = "squadmate_killed_complete"

class SquadmateSounds(Scriptlet):

  def on_load(self):
    self.mc.events.add_handler("play_squadmate_sound", self._handle_squadmate_sound)
    self.mc.log.info("SquadmateSounds ready to go!")
    self.mc.log.info("MC: {}".format(self.mc))
    self.mc.log.info("{}".format(dir(self.mc)))
    self.mc.log.info("SOUND SYSTEM: {}".format(self.mc.sound_system))
    self.mc.log.info("{}".format(dir(self.mc.sound_system)))

  def _handle_squadmate_sound(self, **kwargs):
    sound_name = NAME_FORMATS[kwargs.get("sound")].format(**kwargs)
    action = kwargs.get("action", "play")
    track = kwargs.get("track", "voice")
    # If a mode is supplied, append it to the sound name
    if kwargs.get("mode") == "infiltration":
      sound_name = "{}_{}".format(sound_name, kwargs["mode"])

    settings = {
      sound_name: {
        "action": action,
        "track": track,
        "priority": 2,
      }
    }
    self.mc.log.info("SquadmateSounds made an asset to play: '{}' Args={}".format(sound_name, settings))
    # We can pass in playback event handlers too
    for config_name in ["events_when_played", "events_when_stopped"]:
      if kwargs.get(config_name):
        settings[sound_name][config_name] = kwargs.get(config_name)
    # Dunno what these do but the sound player expects them
    context = "squadmate_sounds"
    calling_context = None

    self.mc.sound_player.play(settings, context, calling_context)
    # If a callback mate is specified, play that too
    # EXCEPT for there's no Shepard callback for Miranda's death
    if action == "play" and kwargs.get("callback_mate") and (kwargs.get("callback_mate") == "shepard") != (kwargs.get("squadmate") == "miranda"):
      cb_sound_name = NAME_FORMATS["{}_callback".format(kwargs.get("sound"))].format(**kwargs)
      cb_settings = {
        cb_sound_name: {
          "action": action,
          "track": track,
          "events_when_played": [COMPLETED_EVENT_NAME],
          "priority": 1,
        }
      }
      self.mc.log.info("SquadmateSounds made a callback to play: '{}' Args={}".format(cb_sound_name, cb_settings))
      self.mc.sound_player.play(cb_settings, context, calling_context)
    else:
      self.mc.events.post(COMPLETED_EVENT_NAME)
