import logging
from mpfmc.core.scriptlet import Scriptlet
from mpf.core.utility_functions import Util

EXPIRE_MS = 4000
EXPIRE_OVERLAP_MS = 500

class WidgetQueuePlayer(Scriptlet):
  """
  This scriptlet creates a queue player for widgets, allowing a series of widget
  play calls to be stacked and played sequentially with a given timeout.
  """

  def on_load(self):
    self.log = logging.getLogger("WidgetQueuePlayer")
    self._queue = []
    self._play_count = 0
    self._current_timeout = None

    self.mc.events.add_handler("queue_widget", self._add_widget_to_queue)
    self.mc.events.add_handler("check_widget_queue", self._check_queue_clear)
    self.log.info("Widget Queue Player Ready!")

  def _add_widget_to_queue(self, **kwargs):
    widget_name = kwargs["widget"]
    self._queue.append((widget_name, kwargs))

    if not self._current_timeout:
      self._advance_queue()

  def _advance_queue(self, dt=None, **kwargs):
    del kwargs
    if self._queue:
      widget_name, widget_kwargs = self._queue.pop(0)
      self.log.info("Widget advance with kwargs {}".format(widget_kwargs))
      expire = Util.string_to_ms(widget_kwargs.pop("expire", EXPIRE_MS))
      timeout = expire - Util.string_to_ms(widget_kwargs.pop("expire_overlap", EXPIRE_OVERLAP_MS))
      context = "global"
      calling_context = None
      settings = { widget_name: {
        "widget_settings": { "expire": "{}ms".format(expire) },
        "action": "add",
        "key": widget_kwargs.get("key"),
      }}

      for key in ["slide", "target"]:
        if widget_kwargs.get(key):
          settings[widget_name][key] = widget_kwargs.pop(key)

      self.mc.widget_player.play(settings, context, calling_context, **widget_kwargs)
      self.mc.post_mc_native_event("play_queued_widget_{}".format(widget_name), **widget_kwargs)
      self._current_timeout = self.mc.clock.schedule_once(self._advance_queue, timeout / 1000)
      self._play_count += 1

    else:
      self._current_timeout = None
      self._play_count = 0
      self._check_queue_clear()

  def _check_queue_clear(self, **kwargs):
    if not self._current_timeout:
      self.mc.post_mc_native_event("widget_queue_clear")
