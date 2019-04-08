"""MC Handlers for Squadmate batching."""

import logging
from mpfmc.core.scriptlet import Scriptlet
from mpf.core.rgba_color import RGBAColor
from .squadmate_status import SquadmateStatus

SQICON_STATUSES = {
    "none": RGBAColor([0, 0, 0]),
    "dead": RGBAColor([0.8, 0, 0]),
    "available": RGBAColor([1.0, 1.0, 1.0]),
    "complete": RGBAColor([0.78, 0.26, 0.07]),
    "specialist": RGBAColor([0, 0.35, 0.8]),
}


class MCSquadmateHandlers(Scriptlet):
    """Custom module for MC squadmate stuff, like playing sounds."""

    def on_load(self):
        """Initialize module and create event handlers."""
        self.log = logging.getLogger("SquadmatesMC")
        self.log.setLevel(10)
        self.mc.events.add_handler("slide_squadicon_slide_created", self._update_sqicons)
        self.mc.events.add_handler("slide_huddle_slide_created", self._update_huddle)
        self.mc.events.add_handler("mode_suicide_base_started", self._update_sqicons, is_suicide=True)
        self.mc.events.add_handler("suicide_huddle_specialist_selected", self._update_specialist)
        self.mc.events.add_handler("recruit_lit", self._update_sqicons)
        self.mc.events.add_handler("recruit_success", self._update_sqicons)
        self._sqicons = None

    def _get_slide(self, slide_name, display):
        display = self.mc.displays[display]
        for s in display.slides:
            self.log.info(" - slide: {}".format(s))
            if s.name == slide_name:
                return s

    def _update_specialist(self, **kwargs):
        self._update_sqicons(is_suicide=True, specialist=kwargs["squadmate"])

    def _update_sqicons(self, is_suicide=False, specialist=None, **kwargs):
        slide = self._get_slide("squadicon_slide", "lcd_right")
        # In DMD mode (for example) there is no squadicon slide, so ignore it
        if not slide:
            return

        self.log.info("Updating sqicons")
        if not self._sqicons:
            self._sqicons = {}

        self.log.info("Current slide: {}".format(slide))
        # self.log.info(dir(slide))
        self.log.info("Current widgets: {}".format(slide.widgets))
        if slide.name == "squadicon_slide":
            for container in slide.widgets:
                widget = container.widget
                if widget.key and widget.key.startswith("sqicon_"):
                    mate = widget.key.replace("sqicon_", "")
                    status = self.mc.player["status_{}".format(mate)]

                    if 0 <= status < 3 or (status == 3 and is_suicide):
                        color = SQICON_STATUSES["none"]
                    else:
                        if mate == specialist:
                            color = SQICON_STATUSES["specialist"]
                        elif status == -1:
                            color = SQICON_STATUSES["dead"]
                        elif status == 3:
                            color = SQICON_STATUSES["available"]
                        elif status == 4:
                            color = SQICON_STATUSES["complete"]
                    widget.color = color
                    widget.config["color"] = color

                    self.log.info("Setting sqicon {} (status {}) to opacity {} color {}".format(
                                  mate, status, widget.opacity, widget.color))
        else:
            self.log.error("Current slide is NOT squadicon")

    def _update_huddle(self, **kwargs):
        huddle_slide = self._get_slide("huddle_slide", "main")
        # Look for lcd_right as a way to determine LCD state, since we don't have access to machine vars
        is_lcd = self.mc.targets["lcd_right"].native_size[0] > 0

        # Using the priority to distinguish between infiltration and longwalk? Yuk
        if huddle_slide.priority % 10 == 1:
            mates = SquadmateStatus.all_techs()
        elif huddle_slide.priority % 10 == 2:
            mates = SquadmateStatus.all_biotics()
        else:
            self.log.error("NO MATES for the huddle!")
            return

        if huddle_slide:
            widget_pos = 0
            for container in huddle_slide.widgets:
                widget = container.widget
                if widget.key and widget.key.startswith("specialist_"):
                    mate = widget.key.replace("specialist_", "")
                    status = self.mc.player["status_{}".format(mate)]

                    if mate not in mates or 0 <= status < 4:
                        widget.opacity = 0
                        continue
                    else:
                        if is_lcd:
                            x, y = self._calculate_huddle_widget_pos_lcd(widget_pos)
                        else:
                            x, y = self._calculate_huddle_widget_pos_dmd(widget_pos)
                        widget.x = x
                        widget.y = y
                        widget.opacity = 1
                        widget_pos += 1

    def _calculate_huddle_widget_pos_lcd(self, widget_pos):
        x = 50
        y = 468 - (130 + widget_pos * 50)
        return (x, y)

    def _calculate_huddle_widget_pos_dmd(self, widget_pos):
        x = 1 if (widget_pos < 3) else 44 if (widget_pos < 6) else 86
        y = 18 - (8 * (widget_pos % 3))
        return (x, y)
