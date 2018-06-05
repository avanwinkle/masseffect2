import logging
from mpf.core.mode import Mode
from mpf.core.rgb_color import RGBColor

class ColorPicker(Mode):

  def __init__(self, machine, config, name, path):
    super().__init__(machine, config, name, path)
    self.log = logging.getLogger("ColorPicker")
    self.log.setLevel("DEBUG")
    self.color = RGBColor((255, 0, 0))
    self.white = 255

  def mode_start(self, **kwargs):
    self.debug_log("Starting ColorPicker with config: {}".format(self.config))
    # Set the white lights
    for light_name in self.config['mode_settings']['white_lights']:
      if light_name in self.machine.lights:
        self.machine.lights[light_name].tags.append("colorpicker-white-light")
      else:
        self.log.warning("Machine has no light named '{}'".format(light_name))
    for light_name in self.config['mode_settings']['rgb_lights']:
      if light_name in self.machine.lights:
        self.machine.lights[light_name].tags.append("colorpicker-rgb-light")
      else:
        self.log.warning("Machine has no light named '{}'".format(light_name))

    # Start with values
    self.set_color()
    self.set_white()

    # Create some listeners
    self.add_mode_event_handler("colorpicker", self._on_color_event)
    self.log.info(self.machine.device_manager.collections["lights"])

  def set_color(self):
    for light in self.machine.device_manager.collections["lights"].items_tagged("colorpicker-rgb-light"):
      self.log.debug("Setting color {} for light {}".format(self.color.hex, light.name))
      light.color(self.color, priority=10000, fade_ms=10)
    self.machine.events.post("colorpicker_color_updated",
      color=self.color.hex)

  def set_white(self):
    for light in self.machine.device_manager.collections["lights"].items_tagged("colorpicker-white-light"):
      light.clear_stack()
      light.on(brightness=self.white, priority=10000)
    self.machine.events.post("colorpicker_white_updated",
      brightness="{:02x}".format(self.white))


  def _on_color_event(self, **kwargs):
    amount = 1 if kwargs.get("scale") == "micro" else 17
    shift = amount * (1 if kwargs.get("direction") == "up" else -1)
    channel = kwargs.get("channel")

    if channel == "white":
      self.white = max(min(self.white + shift, 255), 0)
      self.set_white()
      return

    if channel == "red":
      self.color.red = max(min(self.color.red + shift, 255), 0)
    elif channel == "green":
      self.color.green = max(min(self.color.green + shift, 255), 0)
    elif channel == "blue":
      self.color.blue = max(min(self.color.blue + shift, 255), 0)
    elif channel == "all":
      self.color.red = max(min(self.color.red + shift, 255), 0)
      self.color.green = max(min(self.color.green + shift, 255), 0)
      self.color.blue = max(min(self.color.blue + shift, 255), 0)

    self.set_color()
