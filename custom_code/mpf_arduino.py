import asyncio
import websockets
import logging

from mpf.core.scriptlet import Scriptlet
from mpf.core.utility_functions import Util

TFT_NUMS = {
  "dropbank": 0,
  "left_orbit": 0,
  "kickback": 0,
  "left_ramp": 0,
  "right_ramp": 0,
  "right_orbit": 0,
  "hitbank": 0
}

SQUADMATE_TFTS = {
  "garrus": "left_ramp",
  "grunt": "left_orbit",
  "jack": "kickback",
  "kasumi": "right_ramp",
  "legion": "kickback",
  "mordin": "right_orbit",
  "tali": "right_orbit",
  "thane": "right_ramp",
  "samara": "left_ramp",
  "zaeed": "left_orbit",
}

class MPFArduino(Scriptlet):

  def on_load(self):
    self.log = logging.getLogger("MPFArduino")
    self.log.setLevel("INFO")

    # Bind event handlers to send commands to Arduino
    # TODO: Get this into a config file
    if hasattr(self, "machine"):
      self.machine.events.add_handler('recruit_advance', self._set_squadmate)
      self.machine.events.add_handler('timer_recruittimer_tick', self._set_timer)
      self.machine.events.add_handler('timer_recruittimer_stopped', self._clear_timer)

    self.log.info("Arduino Client Initialized!")

  async def send_to_socket(self, data):
    """Open a client connection to the socket server and send a single command."""
    async with websockets.connect('ws://localhost:5052') as websocket:
      await websocket.send(data)
      # response = await websocket.recv()
      # self.log.info("{} > {}".format(data, response))


  def _set_squadmate(self, **kwargs):
    self.machine.log.info("Arduino trying to set squadmate from {}".format(kwargs))
    if "squadmate" in kwargs:
      squadmate = kwargs.get("squadmate")
      tft_num = TFT_NUMS[SQUADMATE_TFTS[kwargs["squadmate"]]]
      self.machine.clock.loop.create_task(
        self.send_to_socket("set_squadmate:{}:{}".format(squadmate, tft_num))
      )

  def _set_timer(self, **kwargs):
    self.machine.log.info("Arduino trying to set timer from {}".format(kwargs))
    self.machine.clock.loop.create_task(
      self.send_to_socket("show_ledsegment_number:{ticks}".format(**kwargs))
    )

  def _clear_timer(self, **kwargs):
    del kwargs
    self.machine.clock.loop.create_task(
      self.send_to_socket("clear_ledsegment")
    )
