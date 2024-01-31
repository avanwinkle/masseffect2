"""Custom service mode for ME2 with formatted strings."""
from functools import partial
from collections import namedtuple

from typing import List
from mpf.modes.service.code.service import Service as BaseService, ServiceMenuEntry

LightChainMap = namedtuple("LightMap", ["board", "chain", "light"])

class Service(BaseService):

    """Class override for MPF Service class to modify button handlers with toggle state."""

    __slots__ = ("jam_poll",)

    def __init__(self, *args, **kwargs):
        """Initialize service mode."""
        super().__init__(*args, **kwargs)
        self.jam_poll = None

    def mode_start(self, **kwargs):
        del kwargs
        self.add_mode_event_handler("trough_jammed_active", self._check_jam)
        self.add_mode_event_handler("trough_jammed_inactive", self._check_jam)
        if self.machine.ball_devices.bd_trough.ball_count_handler.counter.is_jammed():
            self._check_jam()
        # Re-post the ball search event since we missed it
        elif self.machine.ball_devices['playfield'].ball_search.started:
            self.machine.events.post("ball_search_started")


    def _check_jam(self, **kwargs):
        del kwargs
        if self.machine.ball_devices.bd_trough.ball_count_handler.counter.is_jammed():
            if self.jam_poll:
                return
            self.machine.events.post("show_trough_jammed_active")
            self.jam_poll = self.machine.clock.schedule_interval(
                self._check_jam, 1
            )
            return
        self.machine.events.post("show_trough_jammed_inactive")
        self.jam_poll.cancel()
        self.jam_poll = None


    # Adjustments
    def _load_adjustments_menu_entries(self) -> List[ServiceMenuEntry]:
        """Return the adjustments menu items with label and callback."""
        return [
            ServiceMenuEntry("Standard\nAdjustments", partial(self._settings_menu, "standard")),
            ServiceMenuEntry("Feature\nAdjustments", partial(self._settings_menu, "feature")),
            ServiceMenuEntry("Game\nAdjustments", partial(self._settings_menu, "game")),
            ServiceMenuEntry("Coin\nAdjustments", partial(self._settings_menu, "coin")),
        ]

    def _load_diagnostic_light_menu_entries(self) -> List[ServiceMenuEntry]:
        """Return the light menu items with label and callback."""
        return [
            ServiceMenuEntry("Single Light Test", self._light_test_menu),
            ServiceMenuEntry("Light Chain Test", self._light_chain_menu)
        ]


    def _update_light_chain_slide(self, items, position, color):
        board, chain, lights = items[position]
        self.machine.events.post("service_light_test_start",
                                 board_name=board,
                                 light_name=" ",
                                 light_label=f"Chain {chain}",
                                 light_num=" ",
                                 test_color=color)

    async def _light_chain_menu(self):
        position = 0
        color_position = 0
        colors = ["white", "red", "green", "blue", "yellow"]
        items = self.machine.service.get_light_map(do_sort=self._do_sort)

        # Categorize by platform and address
        chain_lookup = {}
        for board, l in items:
            numbers = l.get_hw_numbers()
            # Just choose the first one as representative?
            number = numbers[0]
            if "-" in number:
                bits = number.split("-")  # e.g. led-7-4-r
                if len(bits) == 2:
                    # FAST lights are single addresses in blocks of 64
                    if board.startswith("FAST"):
                        addr = int(bits[0], 16)
                        chain = addr // 64
                    else:
                        chain, addr = bits
                elif len(bits) == 3:
                    chain, addr, color = bits
                elif len(bits) == 4:
                    _, chain, addr, color = bits
                else:
                    self.warning_log("What is this bits? %s", bits)
            else:
                chain = "XX"
                addr = number
            self.info_log("  - identified chain '%s' and addr '%s'", chain, addr)

            for platform in l.platforms:
                platform_name = type(platform).__name__
                if platform_name not in chain_lookup:
                    chain_lookup[platform_name] = {}
                if not chain in chain_lookup[platform_name]:
                    chain_lookup[platform_name][chain] = []
                chain_lookup[platform_name][chain].append((addr, l))
        items = []
        for platform_name, chains in chain_lookup.items():
            for chain_name, chain in chains.items():
                items.append(LightChainMap(platform_name, chain_name, chain))

        # do not crash if no lights are configured
        if not items:   # pragma: no cover
            return

        while True:
            self._update_light_chain_slide(items, position, colors[color_position])
            for addr, l in items[position].light:
                l.color(colors[color_position], key="service", priority=1000000)

            key = await self._get_key()
            for addr, l in items[position].light:
                l.remove_from_stack_by_key("service")
            if key == 'ESC':
                break
            if key == 'UP':
                position += 1
                if position >= len(items):
                    position = 0
            elif key == 'DOWN':
                position -= 1
                if position < 0:
                    position = len(items) - 1
            elif key == 'ENTER':
                # change color
                color_position += 1
                if color_position >= len(colors):
                    color_position = 0

        self.machine.events.post("service_light_test_stop")
