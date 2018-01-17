import serial
import PyCmdMessenger
from mpf.core.scriptlet import Scriptlet

class MPFArduino(Scriptlet):

  def on_load(self):
    # TODO: Get this into a config file
    PORT = "/dev/cu.usbmodem1421"

    # Look for a device on the given port, if not found then abort this Scriptlet
    try:
      ser = serial.Serial(PORT)
    except serial.serialutil.SerialException:
      return

    arduino = PyCmdMessenger.ArduinoBoard(PORT, baud_rate=115200)

    # The order of commands must exactly match the Arduino sketch file mpf_arduino.ino
    commands = [
      ["draw_text", "s"],
      ["error","s"]
    ]

    # Open a serial connection via PyCmdMessenger
    self._c = PyCmdMessenger.CmdMessenger(arduino, commands)

    # Bind event handlers to send commands to Arduino
    # TODO: Get this into a config file
    self.machine.events.add_handler('player_last_recruit', self._set_squadmate)

  def _set_squadmate(self, **kwargs):
    self._c.send("draw_text", "{}\n".format(kwargs['value']))
