import serial
import PyCmdMessenger
from mpf.core.scriptlet import Scriptlet

class MPFArduino(Scriptlet):

  def on_load(self):
    # TODO: Get this into a config file
    PORTS = ["/dev/cu.usbmodem1421", "/dev/cu.usbmodem1411"]
    ser = None
    # Look for a device on the given port, if not found then abort this Scriptlet
    for port in PORTS:
      try:
        ser = serial.Serial(port)
        break
      except serial.serialutil.SerialException:
        continue
    # If no port found, abandon
    if not ser:
      return

    arduino = PyCmdMessenger.ArduinoBoard(port, baud_rate=115200)

    # The order of commands must exactly match the Arduino sketch file mpf_arduino.ino
    commands = [
      # ["clear_display", ""],
      # ["show_number", "i"],
      ["draw_bmp", "s"],
    ]

    # Open a serial connection via PyCmdMessenger
    self._c = PyCmdMessenger.CmdMessenger(arduino, commands)

    # Bind event handlers to send commands to Arduino
    # TODO: Get this into a config file
    # self.machine.events.add_handler('player_last_recruit', self._set_squadmate)
    if getattr(self, "machine", None):
      self.machine.events.add_handler('timer_recruittimer_tick', self._set_timer)
      self.machine.events.add_handler('timer_recruittimer_stopped', self._clear_timer)

  def _set_squadmate(self, squadmate, **kwargs):
    self._c.send("draw_bmp", "r{}.bmp".format(squadmate))

  def _set_timer(self, **kwargs):
    self._c.send("show_number", kwargs['ticks'])

  def _clear_timer(self, **kwargs):
    self._c.send("clear_display")
