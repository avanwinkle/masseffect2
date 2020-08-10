"""Slide Queue Player is a mechanism for stacking up a queue of slide/widget plays."""
import logging
from mpf.core.custom_code import CustomCode
from mpf.core.utility_functions import Util

EXPIRE_SECS = 3
EXPIRE_OVERLAP_SECS = 0.5
DEFAULT_TRANS = {"type": "fade", "duration": 0.15}


class SlideQueuePlayer(CustomCode):
    """
    SlideQueuePlayer: a queue player for slides.

    This scriptlet creates a queue player for slides, allowing a series of slide
    play calls to be stacked and played sequentially with a given timeout.
    """

    def on_load(self):
        """Initialize: create a queue and create event handlers for adding slides."""
        self.log = logging.getLogger("slideQueuePlayer")
        self._queue = []
        self._play_count = 0
        self._current_timeout = None

        self.machine.events.add_handler("queue_slide", self._add_slide_to_queue)
        self.machine.events.add_handler("check_slide_queue", self._check_queue_clear)
        self.machine.events.add_handler("clear_slide_queue", self._clear_queue)
        self.log.info("Slide Queue Player Ready!")

    def _add_slide_to_queue(self, **kwargs):
        slide_name = kwargs.pop("slide")
        self._queue.append((slide_name, kwargs))

        if not self._current_timeout:
            self._advance_queue()

    def _advance_queue(self, dt=None, **kwargs):
        del kwargs
        if self._queue:
            slide_name, slide_kwargs = self._queue.pop(0)
            expire = Util.string_to_secs(slide_kwargs.pop("expire", EXPIRE_SECS))
            timeout = expire - Util.string_to_secs(slide_kwargs.pop("expire_overlap", EXPIRE_OVERLAP_SECS))
            context = "global"
            calling_context = "queue_slide"
            settings = {
                slide_name: {
                    "expire": expire,
                    "action": "play",
                    "target": slide_kwargs.get("target", None),
                    "priority": 1000 + self._play_count + slide_kwargs.get("priority", 0),
                    "tokens": slide_kwargs.get("tokens", None),
                    'transition': {
                        "type": slide_kwargs.get("transition_type", DEFAULT_TRANS["type"]),
                        "duration": slide_kwargs.get("transition_duration", DEFAULT_TRANS["duration"]),
                    },
                    'transition_out': {
                        "type": slide_kwargs.get("transition_out_type", DEFAULT_TRANS["type"]),
                        "duration": slide_kwargs.get("transition_out_duration", DEFAULT_TRANS["duration"]),
                    },
                }
            }

            portrait = slide_kwargs.pop("portrait")
            if portrait and self.machine.variables.get("is_lcd"):
                portrait_name = "portrait_{}".format(portrait)
                settings["portrait_slide"] = self._generate_portrait(expire, slide_kwargs)
                slide_kwargs["portrait_name"] = portrait_name

            self.machine.slide_player.play(settings=settings,
                                           context=context,
                                           calling_context=calling_context,
                                           **slide_kwargs)
            self.machine.events.post("play_queued_slide_{}".format(slide_name), **slide_kwargs)
            self._current_timeout = self.machine.clock.schedule_once(self._advance_queue, timeout)
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
            "priority": 1000 + self._play_count + slide_kwargs.get("priority", 0),
            "tokens": slide_kwargs.get("tokens", None),
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

    def _clear_queue(self, **kwargs):
        self._queue = []
        self._advance_queue()

    def _check_queue_clear(self, **kwargs):
        if not self._current_timeout:
            self.machine.events.post("slide_queue_clear")
