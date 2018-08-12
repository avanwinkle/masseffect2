from mpfmc.core.scriptlet import Scriptlet

NAME_FORMATS = {
  "killed":          "squadmate_{squadmate}_killed",
  "killed_callback": "squadmate_{killed_mate}_killed_callback_{callback_mate}"
}

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
    # If a mode is supplied, append it to the sound name
    if kwargs.get("mode"):
      sound_name = "{}_{}".format(sound_name, kwargs["mode"])

    self.mc.log.info("SquadmateSounds made an asset name to play: {}".format(sound_name))
    settings = {
      sound_name: {
        "action": kwargs.get("action", "play"),
        "track": kwargs.get("track", "voice"),
      }
    }
    # We can pass in playback event handlers too
    for config_name in ["events_when_played", "events_when_stopped"]:
      if kwargs.get(config_name):
        settings[sound_name][config_name] = kwargs.get(config_name)
    # Dunno what these do but the sound player expects them
    context = "squadmate_sounds"
    calling_context = None

    self.mc.sound_player.play(settings, context, calling_context)
