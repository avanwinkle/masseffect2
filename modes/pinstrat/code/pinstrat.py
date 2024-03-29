try:
    from mpfpinstrat import PinStrat
except ImportError:  # ModuleNotFoundError is only Python 3.6+
    from mpf.core.mode import Mode

    class PinStrat(Mode):

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.warning_log("MPF-PinStrat is not installed. PinStrat will not be run.")
            self.machine.settings.set_setting_value("enable_pinstrat", 0)

        def mode_start(self, **kwargs):
            self.stop()
