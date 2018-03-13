import asyncio
import websockets
import logging

from mpf.core.scriptlet import Scriptlet
from mpf.core.utility_functions import Util

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
    if kwargs.get("squadmate"):
      self.machine.clock.loop.create_task(
        self.send_to_socket("set_squadmate:{squadmate}".format(**kwargs))
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
