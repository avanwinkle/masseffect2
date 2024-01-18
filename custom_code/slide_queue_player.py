"""Slide Queue Player is a mechanism for stacking up a queue of slide/widget plays."""
from mpf.core.custom_code import CustomCode
from mpf.core.utility_functions import Util

EXPIRE_SECS = 3
EXPIRE_OVERLAP_SECS = 0.5
DEFAULT_TRANS = {"type": "fade", "duration": 0.15}


class SlideQueuePlayer(CustomCode):

    """SlideQueuePlayer: a queue player for slides.

    This scriptlet creates a queue player for slides, allowing a series of slide
    play calls to be stacked and played sequentially with a given timeout.
    """

    def __init__(self, machine, name):
        """Initialize CustomCode."""
        super().__init__(machine, name)
        self._queue = []
        self._play_count = 0
        self._current_timeout = None
        self._last_slide_name = None
        self._last_portrait_name = None

    def on_load(self):
        """Load: create a queue and create event handlers for adding slides."""
        self.machine.events.add_handler("queue_slide", self._add_slide_to_queue)
        self.machine.events.add_handler("clear_recruit_slide_queue", self._clear_queue,
                                        filter_to_clear="recruit_advance",
                                        clear_current=False)
        self.machine.events.add_handler("check_slide_queue", self._check_queue_clear)
        self.machine.events.add_handler("clear_slide_queue", self._clear_queue)
        self.info_log("Slide Queue Player Ready!")

    def _clear_queue(self, filter_to_clear=None, filter_to_keep=None, clear_current=False, **kwargs):
        del kwargs
        self.info_log("Clearing slides from queue: %s", self._queue)
        if filter_to_keep:
            self._queue[:] = [s for s in self._queue if s[0].startswith(filter_to_clear)]
        if filter_to_clear:
            self._queue[:] = [s for s in self._queue if not s[0].startswith(filter_to_clear)]
        self.info_log("All recruit slides cleared from queue? %s", self._queue)

        if clear_current:
            self._advance_queue()

    def _add_slide_to_queue(self, clear_current=False, **kwargs):
        slide_name = kwargs.pop("slide")

        # Some slides may want to accelerate themselves by removing queued recruits
        if kwargs.get("clear_recruits"):
            self._clear_queue(filter_to_clear="recruit_advance", **kwargs)
        # Or allow slides to clear anything they like
        elif kwargs.get("clear"):
            self._clear_queue(**kwargs)

        # Check to see if the last item in the queue matches this one
        # If so, select an alternate version of the slide to avoid a
        # name-conflict and remove(). Match on '_QUEUE_A'
        if "_QUEUE_" in slide_name:
            preceding_name = (
                self._queue[-1][0] if self._queue else self._last_slide_name
            )
            self.debug_log("Adding new slide %s to queue. Preceding name is %s", slide_name, preceding_name)
            if slide_name == preceding_name:
                slide_name = (
                    slide_name.replace("_QUEUE_A", "_QUEUE_B")
                    if slide_name[-1] == "A"
                    else slide_name.replace("_QUEUE_B", "_QUEUE_A")
                )
                self.debug_log(" - Updated slide name to be %s", slide_name)
            else:
                self.debug_log(
                    "Not doing funny queue stuff. Match is %s and preceding is %s",
                    "_QUEUE_" in slide_name, preceding_name)
        self._queue.append((slide_name, kwargs))

        if clear_current or not self._current_timeout:
            self._advance_queue()

    def _advance_queue(self, _dt=None, **kwargs):
        del kwargs
        slide_name = None
        context = "global"
        calling_context = "queue_slide"
        target = None
        portrait_slide_name = None
        if self._queue:
            slide_name, slide_kwargs = self._queue.pop(0)
            expire = Util.string_to_secs(slide_kwargs.pop("expire", EXPIRE_SECS))
            timeout = expire - Util.string_to_secs(
                slide_kwargs.pop("expire_overlap", EXPIRE_OVERLAP_SECS)
            )
            target = slide_kwargs.get("target", None)
            # context = "slide_queue_player_{}_{}".format(slide_name, self._play_count)
            # calling_context = "queue_slide_{}".format(self._play_count)
            settings = {
                slide_name: {
                    "action": "play",
                    "target": target,
                    "priority": 1000
                    + self._play_count
                    + slide_kwargs.get("priority", 0),
                    "tokens": slide_kwargs.get("tokens", None),
                }
            }

            portrait = slide_kwargs.pop("portrait")
            if portrait and self.machine.variables.get("is_lcd"):
                # HACK: I'm too lazy to add placeholder evaluation to the portrait name.
                # Hard-code support for multiball
                if portrait.endswith("(locked_balls)"):
                    portrait = portrait.replace(
                        "(locked_balls)",
                        "{}".format(self.machine.multiball_locks["fmball_lock"].locked_balls)
                    )
                portrait_widget_name = "portrait_{}".format(portrait)
                if self._last_portrait_name:
                    portrait_slide_name = (
                        self._last_portrait_name.replace("_QUEUE_A", "_QUEUE_B")
                        if self._last_portrait_name[-1] == "A"
                        else self._last_portrait_name.replace("_QUEUE_B", "_QUEUE_A")
                    )
                else:
                    portrait_slide_name = "portrait_slide_QUEUE_A"
                settings[portrait_slide_name] = self._generate_portrait(slide_kwargs)
                slide_kwargs["portrait_name"] = portrait_widget_name
            self.machine.log.debug(
                "Playing slide %s (count %s) with expire %s and timeout %s",
                slide_name, self._play_count, expire, timeout
            )

            self.machine.slide_player.play(
                settings=settings,
                context=context,
                calling_context=calling_context,
                **slide_kwargs
            )
            event_name = slide_name[:-8] if "_QUEUE_" in slide_name else slide_name
            self.machine.events.post(
                "play_queued_slide_{}".format(event_name), **slide_kwargs
            )
            self._current_timeout = self.machine.clock.schedule_once(
                self._advance_queue, expire
            )
            self._play_count += 1
        else:
            self._current_timeout = None
            self._play_count = 0
            self._check_queue_clear()

        # Remove an old slide if we have one
        if self._last_slide_name:
            self.debug_log("Removing expiring queued slide %s", self._last_slide_name)
            settings = {self._last_slide_name: {"action": "remove", "target": target}}
            self.machine.slide_player.play(
                settings=settings, context=context, calling_context=calling_context
            )
        if self._last_portrait_name:
            self.debug_log("Removing expiring queued portrait %s", self._last_portrait_name)
            settings = {
                self._last_portrait_name: {"action": "remove", "target": "lcd_right"}
            }
            self.machine.slide_player.play(
                settings=settings, context=context, calling_context=calling_context
            )

        self._last_slide_name = slide_name
        self._last_portrait_name = portrait_slide_name

    def _generate_portrait(self, slide_kwargs):
        slide_settings = {
            "action": "play",
            "target": "lcd_right",
            "priority": 1000 + self._play_count + slide_kwargs.get("priority", 0),
            "tokens": slide_kwargs.get("tokens", None),
            "transition": {
                "type": slide_kwargs.get("transition_type", DEFAULT_TRANS["type"]),
                "duration": slide_kwargs.get(
                    "transition_duration", DEFAULT_TRANS["duration"]
                ),
            },
        }
        if not self._queue:
            slide_settings["transition_out"] = {
                "type": slide_kwargs.get("transition_out_type", DEFAULT_TRANS["type"]),
                "duration": slide_kwargs.get(
                    "transition_out_duration", DEFAULT_TRANS["duration"]
                ),
            }
        return slide_settings

    def _check_queue_clear(self, **kwargs):
        del kwargs
        if not self._current_timeout:
            self.machine.events.post("slide_queue_clear")
