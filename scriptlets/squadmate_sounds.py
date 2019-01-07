import logging
from mpfmc.core.scriptlet import Scriptlet
from mpf.core.rgba_color import RGBAColor

NAME_FORMATS = {
  "killed":          "squadmate_{squadmate}_killed",
  "killed_callback": "squadmate_{squadmate}_killed_callback_{callback_mate}",
  "skillshot":       "squadmate_{squadmate}_nice_shot",
}
COMPLETED_EVENT_NAME = "squadmate_killed_complete"

SQICON_STATUSES = {
  "none": RGBAColor([0,0,0]),
  "dead" : RGBAColor([0.8, 0, 0]),
  "available": RGBAColor([1.0, 1.0, 1.0]),
  "complete": RGBAColor([0.78, 0.26, 0.07]),
  "specialist": RGBAColor([0, 0.35, 0.8]),
}

class SquadmateSounds(Scriptlet):

  def on_load(self):
    self.log = logging.getLogger("SquadmatesMC")
    self.log.setLevel(10)
    self.mc.events.add_handler("play_squadmate_sound", self._handle_squadmate_sound)
    self.mc.events.add_handler("slide_squadicon_slide_created", self._update_sqicons)
    self.mc.events.add_handler("recruit_lit", self._update_sqicons)
    self.mc.events.add_handler("recruit_success", self._update_sqicons)
    self._sqicons = None

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

  def _update_sqicons(self, **kwargs):
    self.log.info("Updating sqicons")
    sqicon_slide = self.mc.slides["squadicon_slide"]
    if not self._sqicons:
      self._sqicons = {}

    self.log.info("Displays: {}".format(self.mc.displays))
    lcd_right = self.mc.displays['lcd_right']

    slide = None
    for s in lcd_right.slides:
      self.log.info(" - slide: {}".format(s))
      if s.name == "squadicon_slide":
        slide = s

    if not slide:
      self.log.error("Unable to find squadicon slide")
      return

    self.log.info("Current slide: {}".format(slide))
    # self.log.info(dir(slide))
    self.log.info("Current widgets: {}".format(slide.widgets))
    if slide.name == "squadicon_slide":
      for container in slide.widgets:
        widget = container.widget
        if widget.key and widget.key.startswith("sqicon_"):
          mate = widget.key.replace("sqicon_", "")
          status = self.mc.player["status_{}".format(mate)]

          if 0 <= status < 3:
            color = SQICON_STATUSES["none"]
          else:
            if self.mc.player["specialist"] == mate:
              color = SQICON_STATUSES["specialist"]
            elif status == -1:
              color = SQICON_STATUSES["dead"]
            elif status == 3:
              color = SQICON_STATUSES["available"]
            elif status == 4:
              color = SQICON_STATUSES["complete"]
          widget.color = color
          widget.config["color"] = color

          self.log.info("Setting sqicon {} (status {}) to opacity {} color {}".format(mate, status, widget.opacity, widget.color))
    else:
      self.log.error("Current slide is NOT squadicon")
