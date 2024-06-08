# Copyright 2024 Paradigm Tilt
"""Debugging utils for performance and stability."""

import datetime
import time
import psutil
from mpf.core.custom_code import CustomCode
from mpfmc.core.mc_custom_code import McCustomCode


class DebuggerModule(CustomCode):

    """Instantiate some custom debugging behaviors."""

    def on_load(self):
        """Load the module to initialize the custom code."""
        self.machine.clock.schedule_interval(self.log_debug_stats, 60)

    def log_debug_stats(self):
        """Write a tab-delimited set of stat data to the log."""
        du = psutil.disk_usage("/")
        mem = psutil.virtual_memory()
        process = psutil.Process()
        proc_mem = process.memory_info()
        mb = 1024 * 1024
        gb = 1024 * 1024 * 1024
        uptime = datetime.timedelta(seconds=time.time() - psutil.boot_time())
        stats = {
            "uptime": f"{uptime}".split(".")[0],
            "cpu_percent": f"{psutil.cpu_percent():0.1f}",
            "memory_available_mb": f"{mem.available / mb:0.0f}",
            "mpf_memory_rss_mb": f"{proc_mem.rss / mb:0.0f}",
            "disk_usage_gb": f"{du.free / gb:0.1f}",
            "balls_played": f"{self.machine.variables.get_machine_var('balls_played_since_launch')}",
            "games_played": f"{self.machine.variables.get_machine_var('games_played_since_launch')}",
            "current_players": str(0 if not self.machine.game else self.machine.game.num_players),
            "mpf_handlers": str(len(self.machine.events.registered_handlers)),
        }
        self.machine.log.info("DEBUG TRACK: \t%s", "\t".join(stats.keys()))
        self.machine.log.info("DEBUG STATS: \t%s", "\t".join(stats.values()))


class DebuggerModuleMc(McCustomCode):

    """Instantiate some custom debugging behaviors."""

    def on_load(self):
        """Load the module to initialize the custom code."""
        self.mc.clock.schedule_interval(self.log_debug_stats, 60)

    def log_debug_stats(self, *args, **kwargs):
        """Write a tab-delimited set of stat data to the log."""
        du = psutil.disk_usage("/")
        mem = psutil.virtual_memory()
        process = psutil.Process()
        proc_mem = process.memory_info()
        mb = 1024 * 1024
        gb = 1024 * 1024 * 1024
        uptime = datetime.timedelta(seconds=time.time() - psutil.boot_time())
        stats = {
            "uptime": f"{uptime}".split(".")[0],
            "cpu_percent": f"{psutil.cpu_percent():0.1f}",
            "memory_available_mb": f"{mem.available / mb:0.0f}",
            "mpf_memory_rss_mb": f"{proc_mem.rss / mb:0.0f}",
            "disk_usage_gb": f"{du.free / gb:0.1f}",
            "balls_played": f"{self.mc.machine_vars.get('balls_played_since_launch', 0)}",
            "games_played": f"{self.mc.machine_vars.get('games_played_since_launch',0)}",
            "current_players": str(len(self.mc.player_list))
        }
        self.mc.log.info("DEBUG TRACK: \t%s", "\t".join(stats.keys()))
        self.mc.log.info("DEBUG STATS: \t%s", "\t".join(stats.values()))
