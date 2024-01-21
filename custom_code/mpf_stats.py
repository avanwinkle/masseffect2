"""MPF handlers for system stats."""

import logging
import datetime
import time
from psutil import boot_time, cpu_percent, disk_usage, virtual_memory, Process

from mpf.core.custom_code import CustomCode
from mpfmc.core.mc_custom_code import McCustomCode

def get_process_stats(process_name):
    _process = Process()
    _attrs = _process.as_dict(attrs=['cpu_percent', 'memory_info'])
    return '{} C/R/V: {} / {}/{} MB'.format(
        process_name,
        # For some reason as_dict doesn't update on intervals
        f"{_process.cpu_percent():0.1f}",
        round(_attrs['memory_info'].rss / 1048576),
        round(_attrs['memory_info'].vms / 1048576))


class MPFStats(CustomCode):

    __slots__ = ("_stats_interval",)

    def __init__(self, machine, name):
        super().__init__(machine, name)
        self._stats_interval = None

    def on_load(self):
        self.machine.events.add_handler("request_stats", self._on_request_stats)
        self.machine.events.add_handler("cancel_stats", self._clear_interval)

    def _on_request_stats(self, **kwargs):
        self._post_stats()
        self._clear_interval()

        if kwargs.get("update_interval"):
            self._stats_interval = self.machine.clock.schedule_interval(
                self._post_stats, kwargs['update_interval'])

    def _clear_interval(self, **kwargs):
        del kwargs
        if self._stats_interval:
            self.machine.clock.unschedule(self._stats_interval)

    def _post_stats(self, **kwargs):
        del kwargs
        # Generate the stats
        du = disk_usage("/")
        mem = virtual_memory()
        mb = 1024 * 1024
        gb = 1024 * 1024 * 1024
        uptime = datetime.timedelta(seconds=time.time() - boot_time())
        earnings = self.machine.modes['credits'].earnings

        stats = {
            "uptime": f"{uptime}".split(".")[0],
            "cpu_percent": f"{cpu_percent():0.1f}",
            "mpf_cpu": get_process_stats("MPF"),
            "memory": f"{mem.available / mb:0.0f}MB available ({mem.total / mb:0.0f}MB total)",
            "disk_usage": f"{du.free / gb:0.1f}GB free ({du.total / gb:0.1f}GB total)",
            "balls_played": f"{self.machine.variables.get_machine_var('balls_played_since_launch')}",
            "games_played": f"{self.machine.variables.get_machine_var('games_played_since_launch')}",
            "audit": f"{earnings['3 Total Paid Games']} / {earnings['2 Total Earnings Dollars']}",
            "mpf_handlers": len(self.machine.events.registered_handlers),
        }
        self.machine.events.post("stats_for_nerds", **stats)
        self.machine.events.post("request_mc_stats")

class MCStats(McCustomCode):

    def on_connect(self, **kwargs):
        del kwargs
        self.add_mpf_event_handler("request_mc_stats", self._post_stats)

    def _post_stats(self, **kwargs):
        del kwargs
        children = {}
        for display in self.mc.displays:
            children[display.name] = 0
            for _ in display.walk():
                children[display.name] += 1
        self.post_event_to_mpf_and_mc("mc_stats",
            mc_cpu=get_process_stats("MC"),
            slides=len(self.mc.active_slides),
            refs=len(self.mc.debug_refs),
            **children
        )
