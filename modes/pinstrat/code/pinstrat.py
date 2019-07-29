try:
  from mpfpinstrat import PinStrat
except ModuleNotFoundError:
  from mpf.core.mode import Mode

  class PinStrat(Mode):

    def __init__(self, machine, config, name, path):
      super().__init__(machine, config, name, path)
      machine.log.warning("MPF-PinStrat is not installed. PinStrat will not be run.")
      machine.set_machine_var("pinstrat_enabled", 0)

    def mode_start(self, **kwargs):
      self.stop()
