import logging
from mpfmc.core.scriptlet import Scriptlet
from mpf.core.utility_functions import Util

EXPIRE_SECS = 4
EXPIRE_OVERLAP_SECS = 0.5
DEFAULT_TRANS = { "type": "fade", "duration": 0.15 }

class SlideQueuePlayer(Scriptlet):
  """
  This scriptlet creates a queue player for slides, allowing a series of slide
  play calls to be stacked and played sequentially with a given timeout.
  """

  def on_load(self):
    self.log = logging.getLogger("slideQueuePlayer")
    self._queue = []
    self._play_count = 0
    self._current_timeout = None

    self.mc.events.add_handler("queue_slide", self._add_slide_to_queue)
    self.mc.events.add_handler("check_slide_queue", self._check_queue_clear)
    self.log.info("slide Queue Player Ready!")

  def _add_slide_to_queue(self, **kwargs):
    slide_name = kwargs.pop("slide")
    self._queue.append((slide_name, kwargs))

    if not self._current_timeout:
      self._advance_queue()

  def _advance_queue(self, dt=None, **kwargs):
    del kwargs
    if self._queue:
      slide_name, slide_kwargs = self._queue.pop(0)
      self.log.info("slide {} advance with kwargs {}".format(slide_name, slide_kwargs))
      expire = Util.string_to_secs(slide_kwargs.pop("expire", EXPIRE_SECS))
      timeout = expire - Util.string_to_secs(slide_kwargs.pop("expire_overlap", EXPIRE_OVERLAP_SECS))
      context = "global"
      calling_context = None
      settings = {
        slide_name: {
          "expire": expire,
          "action": "play",
          # "key": slide_kwargs.get("key"),
          "target": slide_kwargs.get("target", None),
          "priority": 1000 + self._play_count,
          # any of the below required?
          # 'priority': None,
          # 'background_color': [0.0, 0.0, 0.0, 1.0],
          # 'show': True,
          # 'force': False,
          # 'slide': None,
          'transition': {
            "type": slide_kwargs.get("transition_type", DEFAULT_TRANS["type"]),
            "duration": slide_kwargs.get("transition_duration", DEFAULT_TRANS["duration"]),
          },
          'transition_out': {
            "type": slide_kwargs.get("transition_out_type", DEFAULT_TRANS["type"]),
            "duration": slide_kwargs.get("transition_out_duration", DEFAULT_TRANS["duration"]),
          },
      }}

      portrait = slide_kwargs.pop("portrait")
      if portrait:
        portrait_name = "portrait_{}".format(portrait)
        settings["portrait_slide"] = self._generate_portrait(expire, slide_kwargs)
        slide_kwargs["portrait_name"] = portrait_name

      self.mc.slide_player.play(settings, context, calling_context, **slide_kwargs)
      self.mc.post_mc_native_event("play_queued_slide_{}".format(slide_name), **slide_kwargs)
      self._current_timeout = self.mc.clock.schedule_once(self._advance_queue, timeout)
      self._play_count += 1

    else:
      self._current_timeout = None
      self._play_count = 0
      self._check_queue_clear()

  def _generate_portrait(self, expire, slide_kwargs):
    slide_settings = {
      "expire": expire,
      "action": "play",
      "target": "lcd_right",
      "priority": 1000 + self._play_count,
      'transition': {
            "type": slide_kwargs.get("transition_type", DEFAULT_TRANS["type"]),
            "duration": slide_kwargs.get("transition_duration", DEFAULT_TRANS["duration"]),
          },
          'transition_out': {
            "type": slide_kwargs.get("transition_out_type", DEFAULT_TRANS["type"]),
            "duration": slide_kwargs.get("transition_out_duration", DEFAULT_TRANS["duration"]),
          },
    }
    return slide_settings

  def _check_queue_clear(self, **kwargs):
    if not self._current_timeout:
      self.mc.post_mc_native_event("slide_queue_clear")
