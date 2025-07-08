from enum import Enum
from typing import Optional
import machine
import json

class LedPallet:
    color1: tuple[int, int, int]  # RGB values
    color2: tuple[int, int, int]  # RGB values

    def __init__(self, from_json: 'Optional[str]' = None):
        self.color1 = (55, 0, 0)
        self.color2 = (0, 0, 0)

        if from_json:
            for key, value in json.loads(from_json).items():
                setattr(self, key, value)

class LedEffect(Enum):
    RAINBOW = "rainbow"
    BLINK = "blink"
    GLOW = "glow"
    FADE = "fade"
    CHASE = "chase"
    GRADIENT = "gradient"
    WLD_STATS = "wld-stats"

class LedData:
    effect: LedEffect
    intensity: int
    speed: int
    brightness: int
    reversed: bool
    index: float
    pallet: LedPallet

    def __init__(self, from_json: 'Optional[str]' = None):
        self.effect = LedEffect.GLOW
        self.intensity = 150
        self.speed = 100
        self.brightness = 255
        self.reversed = False
        self.index = 0.0
        self.pallet = LedPallet()

        if from_json:
            for key, value in json.loads(from_json).items():
                setattr(self, key, value)

# the data recieved from the serial port and used to control the robot. ex: setting servo angles and led effects
class ProtocalInboundData:
    positionZ: int
    angleJoint1: int
    angleJoint2: int
    angleJoint3: int

    flushMoveQueue: bool

    leds: LedData

    def __init__(self, from_json: 'Optional[str]' = None):

        if from_json:
            for key, value in json.loads(from_json).items():
                setattr(self, key, value)
        else:
            self.positionZ = 0
            self.angleJoint1 = 90
            self.angleJoint2 = 90
            self.angleJoint3 = 90

            self.flushMoveQueue = False

    def to_dict(self):
        return json.dumps(self.__dict__)

class BoardData:
    stateChanges: list[tuple[str, bool]]

    columns: dict[str, list[bool]] = {"a": [], "b": [], "c": [], "d": [], "e": [], "f": [], "g": [], "h": []}

    def __init__(self):
        self.stateChanges = []

        # initialize each column with 8 squares, all set to False (no piece on the square)
        for column in self.columns.values():
            for square in range(8):
                column.append(False)

        self.update()  # now, initialize the columns with sensor data

    def update(self) -> dict[str, list[bool]]:

        # haul effect sensor pin setup
        sensor_power_pins = [6, 7, 8, 9, 10, 11, 12, 13] # sensor rows 1 - 8 ascending
        sensor_data_pins = [16, 17, 18, 19, 20, 21, 22, 26] # sensor columns a - h ascending

        for row_index in range(8):
            power_pin = machine.Pin(sensor_power_pins[row_index], machine.Pin.OUT)
            data_pin = machine.Pin(sensor_data_pins[row_index], machine.Pin.IN, machine.Pin.PULL_UP)

            power_pin.on()  # turn on the sensor row

            for column in self.columns.keys():
                # invert the data so sensor reads true when a piece is on it
                self.columns[column][row_index] = not bool(data_pin.value())

            power_pin.off()  # we are done collecting sensor data, turn off row

        return self.columns

class ResponseType(Enum):
    SUCCESS = "ok"
    ERROR = "error"

class ProtocalOutboundData:
    response: ResponseType
    error: Exception
    boardData: BoardData
    ledEffectsList: list[LedEffect]

    def __init__(self):
        self.response = ResponseType.SUCCESS
        self.boardData = BoardData()
        self.ledEffectsList = list(LedEffect)