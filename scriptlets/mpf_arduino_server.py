import asyncio
import serial
import websockets
import PyCmdMessenger

class ArduinoServer():


  def __init__(self):
    self._last_bmp = None
    self._server = websockets.serve(self._serve, 'localhost', 5052)


    self._commands = {
      "set_squadmate": self.set_squadmate,
      "clear_ledsegment": self.clear_ledsegment,
      "show_ledsegment_letters": self.show_ledsegment_letters,
      "show_ledsegment_number": self.show_ledsegment_number,
    }

    self.init_arduino()

  def run(self):
    asyncio.get_event_loop().run_until_complete(self._server)
    asyncio.get_event_loop().run_forever()

  def init_arduino(self):
    # TODO: Get this into a config file
      PORTS = ["/dev/cu.usbmodem1421", "/dev/cu.usbmodem1411", "/dev/cu.usbmodemFA131"]
      ser = None
      err = None
      # Look for a device on the given port, if not found then abort this Scriptlet
      for port in PORTS:
        try:
          ser = serial.Serial(port)
          break
        except serial.serialutil.SerialException as e:
          err = e
          continue
      # If no port found, abandon
      if not ser:
        raise err or serial.serialutil.SerialException

      arduino = PyCmdMessenger.ArduinoBoard(port, baud_rate=115200)

      # The order of commands must exactly match the Arduino sketch file mpf_arduino.ino
      commands = [
        # ["clear_display", ""],
        # ["show_number", "i"],
        ["draw_bmp", "s"],
        ["clear_ledsegment", ""],
        ["show_ledsegment_letters", "s"],
        ["show_ledsegment_number", "i"],
      ]

      # Open a serial connection via PyCmdMessenger
      self._c = PyCmdMessenger.CmdMessenger(arduino, commands)
      self._last_bmp = None


  def clear_ledsegment(self, *args):
    del args
    self._c.send("clear_ledsegment")

  def set_squadmate(self, squadmate):
    print("Setting squadmate '{}'".format(squadmate))
    if squadmate != self._last_bmp:
      self._last_bmp = squadmate
      self._c.send("draw_bmp", "r{}.bmp".format(self._last_bmp))

  def show_ledsegment_letters(self, letters):
    print("Setting segment letters to '{}'".format(letters))
    self._c.send("show_ledsegment_letters", letters)

  def show_ledsegment_number(self, number):
    print("Setting segment number to {}".format(number))
    self._c.send("show_ledsegment_number", int(number))

  async def _serve(self, websocket, path):
    request = await websocket.recv()
    print("< {}".format(request))

    if ":" in request:
      command, param = request.split(":")
    else:
      command = request
      param = None

    if command in self._commands:
      self._commands[command](param)
      await websocket.send("OKAY")
    else:
      print("ERROR: Unknown command '{}'".format(command))
      await websocket.send("ERROR")

if __name__ == "__main__":
  server = ArduinoServer()
  server.run()
