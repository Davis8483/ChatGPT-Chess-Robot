import json
import threading
import time
from typing import Callable
from serial import Serial
from serial_protocal import BoardData, ProtocalInboundData, ReturnRequestType, ProtocalOutboundData

class BoardStateChange:
    def __init__(self, serial_interface: Serial):
        self.serial_interface = serial_interface
        self._callback = None
        self._thread = None
        self._stop_event = threading.Event()

    def subscribe(self, callback: Callable[[BoardData], None]):
        self._callback = callback
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._listen_for_board_data, daemon=True)
        self._thread.start()

    def unsubscribe(self):
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=2)
        self._callback = None

    def _listen_for_board_data(self):
        while not self._stop_event.is_set():
            try:
                if self.serial_interface.is_open and self.serial_interface.in_waiting > 0:
                    # Read response if available
                    line = self.serial_interface.readline().decode("utf-8")
                    if not line:
                        continue

                    host_inbound_data: ProtocalOutboundData = json.loads(line)

                    if host_inbound_data.boardData:
                        if self._callback:
                            self._callback(host_inbound_data.boardData)
            except Exception as e:
                # Optionally log error
                pass
            time.sleep(0.05)