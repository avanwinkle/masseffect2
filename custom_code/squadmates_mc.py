"""MC Handlers for Squadmate batching."""

import logging
from mpfmc.core.mc_custom_code import McCustomCode
from .squadmate_status import SquadmateStatus
from .research import RESEARCH

class MCSquadmateHandlers(McCustomCode):
    """Custom module for MC squadmate stuff, like playing sounds."""

    def on_load(self):
        """Initialize module and create event handlers."""
        self.log = logging.getLogger("SquadmatesMC")
        self.mc.events.add_handler("slide_squadicon_slide_created", self._update_sqicons)
        self.mc.events.add_handler("slide_huddle_slide_created", self._update_huddle)
        self.mc.events.add_handler("mode_suicide_base_started", self._update_sqicons, is_suicide=True)
        self.mc.events.add_handler("suicide_huddle_specialist_selected", self._update_specialist)
        self.mc.events.add_handler("slide_recruit_advance_slide_active", self._update_sqicons)
        self.mc.events.add_handler("slide_levelup_slide_active", self._update_sqicons)
        self.mc.events.add_handler("slide_store_intro_slide_active", self._update_store)
        # Track which squadmate selection changes
        self._squadmate_select_target = None

    def on_connect(self, **kwargs):
        self.add_mpf_event_handler("squadmate_select", self._select_squadmate)
        self.add_mpf_event_handler("squadmate_select_clear", self._select_squadmate_clear)
        self.add_mpf_event_handler("sqicon_update", self._update_sqicons)

    def _get_slide(self, slide_name, display):
        display = self.mc.displays[display]
        for s in display.slides:
            if s.name == slide_name:
                return s

    def _update_specialist(self, **kwargs):
        self._update_sqicons(is_suicide=True, specialist=kwargs["squadmate"])

    def _update_sqicons(self, is_suicide=False, specialist=None, **kwargs):
        player = self.mc.player
        slide = self._get_slide("squadicon_slide", "lcd_right")
        # In DMD mode (for example) there is no squadicon slide, so ignore it
        if not slide:
            return

        if slide.name == "squadicon_slide":
            # I couldn't get widget.remove() or slide.remove_widget() to work, so brute force it is
            # Hopefully this doesn't make a memory leak?
            slide.children = []
            self.log.debug("Creating new widgets, all should be removed? {}".format(slide.widgets))

            slide.add_widgets_from_library("sqicon_console")
            for mate in SquadmateStatus.all_mates():
                status = player["status_{}".format(mate)]
                style = "default"
                background = "default"
                if 0 <= status < 3:
                    style = "na"
                elif status == 3:
                    if is_suicide:
                         style = "na"
                    else:
                        background = "available"
                elif status == -1:
                    style = "dead"
                elif mate == specialist:
                    background = "specialist"
                elif mate == player["selected_mate_one"] or mate == player["selected_mate_two"]:
                    background = "selected"

                slide.add_widgets_from_library("sqicon_background_{}".format(background),
                    key="sqicon_background_{}".format(mate),
                    widget_settings={"style": "sqicon_style_mate_{}".format(mate)}
                    )
                slide.add_widgets_from_library("sqicon_mate_{}_{}".format(mate, style))


            slide.add_widgets_from_library("squadmates_grid_overlay")

        else:
            self.log.error("Current slide is NOT squadicon")

    def _update_selection_widgets(self, slide_name, widget_key, filter_fn=None, offset_last=False, **kwargs):
        parent_slide = self._get_slide(slide_name, "main")
        # Look for lcd_right as a way to determine LCD state, since we don't have access to machine vars
        is_lcd = self.mc.targets["lcd_right"].native_size[0] > 0

        if parent_slide:
            raw_widgets = [container.widget for container in parent_slide.widgets
                           if container.widget.key and container.widget.key.startswith(widget_key)]
            filtered_widgets = filter_fn(raw_widgets, self.mc.player) if filter_fn else raw_widgets
            for widget in raw_widgets:
                if widget in filtered_widgets:
                    # Position the widgets in the order they were filtered
                    widget_idx = filtered_widgets.index(widget)
                    do_offset = offset_last and (widget_idx == len(filtered_widgets) - 1)
                    if is_lcd:
                        x, y = self._calculate_widget_pos_lcd(widget_idx, slide_name, do_offset)
                    else:
                        x, y = self._calculate_widget_pos_dmd(widget_idx, slide_name, do_offset)
                    widget.x = x
                    widget.y = y
                    widget.opacity = 1
                else:
                    widget.opacity = 0

            return (parent_slide, [container.widget for container in parent_slide.widgets if container])

    def _update_huddle(self, **kwargs):
        self._update_selection_widgets("huddle_slide", "specialist_", self.filter_specialists)

    def _update_store(self, **kwargs):
        self._update_selection_widgets("store_slide", "purchase_", self.filter_store, offset_last=True)

    def _select_squadmate(self, **kwargs):
        player = self.mc.player
        # Find the current target
        available_mates = SquadmateStatus.available_mates(player)


        first_mate = player["selected_mate_one"]
        second_mate = player["selected_mate_two"]
        idx_one = available_mates.index(first_mate)
        idx_two = available_mates.index(second_mate)
        if not self._squadmate_select_target:
            # Left flipper moves the first selection, right flipper moves the second
            idx = min(idx_one, idx_two) if kwargs["switch"] == "s_flipper_left" else max(idx_one, idx_two)
            self._squadmate_select_target = "one" if idx == idx_one else "two"
        else:
            idx = idx_one if self._squadmate_select_target == "one" else idx_two
        avoid_idx = idx_one + idx_two - idx

        idx += 1
        if idx == avoid_idx:
            idx += 1
        if idx >= len(available_mates):
            idx = 0
        # In case the rollover caused collision
        if idx == avoid_idx:
            idx += 1
        player["selected_mate_{}".format(self._squadmate_select_target)] = available_mates[idx]
        # Now that the selection has been made and saved to the player, update the sqicon widgets
        self._update_sqicons()

    def _select_squadmate_clear(self, **kwargs):
        self._squadmate_select_target = None

    def create_widget(self, config):
        config["_default_settings"] = []
        widget_settings = self.mc.config_validator.validate_config(
            'widgets:{}'.format(config['type']), config,
            base_spec='widgets:common', add_missing_keys=True)
        return widget_settings

    def filter_specialists(self, widgets, player):
        # Infiltration: use techs
        if player["state_machine_suicide_progress"] == "infiltration":
            mates = SquadmateStatus.all_techs()
        elif player["state_machine_suicide_progress"] == "longwalk":
            mates = SquadmateStatus.all_biotics()
        else:
            self.log.error("NO MATES for the huddle!")
            return

        # For any unrecruited/unapplicable mates, make invisible
        widgets_to_position = []
        for widget in widgets:
            mate = widget.key.replace("specialist_", "")
            status = self.mc.player["status_{}".format(mate)]

            if mate in mates and not (0 <= status < 4):
                widgets_to_position.append(widget)
        return widgets_to_position

    def filter_store(self, widgets, player):
        current_options = player["store_options"].split("|")
        widgets_to_position = [0] * len(current_options)
        # Store the "nothing" widget so we can append it later
        nothing_widget = None
        for widget in widgets:
            option = widget.key.replace("purchase_", "")
            if option == "nothing":
                nothing_widget = widget
            elif option in current_options:
                opt = RESEARCH[option]
                # widget.text = "{} {}/6".format(opt.name, player["research_{}_level".format(option)] + 1)
                widget.text = opt.name
                # Preserve the order of the options
                widgets_to_position[current_options.index(option)] = widget
        widgets_to_position.append(nothing_widget)
        return widgets_to_position

    def _calculate_widget_pos_lcd(self, widget_idx, slide_name, do_offset=False):
        spacing = 50
        # Huddle options list from the middle-top
        if slide_name == "huddle_slide":
            x = 50
            y = 468 - (130 + widget_idx * spacing)
        # Store options list from top, start at x 20
        elif slide_name == "store_slide":
            x = 20
            y = 468 - (100 + widget_idx * spacing)
        if do_offset:
            y -= spacing / 2
        return (x, y)

    def _calculate_widget_pos_dmd(self, widget_idx, slide_name, do_offset=False):
        spacing = 8
        x = 1 if (widget_idx < 3) else 44 if (widget_idx < 6) else 86
        y = 18 - (spacing * (widget_idx % 3))
        if do_offset:
            y -= spacing / 2
        return (x, y)
