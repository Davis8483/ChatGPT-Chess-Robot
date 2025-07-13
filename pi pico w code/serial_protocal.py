import machine
import json

# --- Define sensor pins globally ---
SENSOR_POWER_PINS = [6, 7, 8, 9, 10, 11, 12, 13]  # sensor rows 1 - 8 ascending
SENSOR_DATA_PINS = [16, 17, 18, 19, 20, 21, 22, 26]  # sensor columns a - h ascending

POWER_PINS = [machine.Pin(pin, machine.Pin.OUT) for pin in SENSOR_POWER_PINS]
DATA_PINS = [machine.Pin(pin, machine.Pin.IN, machine.Pin.PULL_UP) for pin in SENSOR_DATA_PINS]

class LedPallet:
    color1: tuple[int, int, int]  # RGB values
    color2: tuple[int, int, int]  # RGB values

    def __init__(self, from_json:str|None = None):
        self.color1 = (55, 0, 0)
        self.color2 = (0, 0, 0)

        if from_json:
            for key, value in json.loads(from_json).items():
                setattr(self, key, value)

    def to_dict(self):
        return {
            "color1": self.color1,
            "color2": self.color2
        }

class LedEffect:
    RAINBOW = "rainbow"
    BLINK = "blink"
    GLOW = "glow"
    FADE = "fade"
    CHASE = "chase"
    GRADIENT = "gradient"
    WLD_STATS = "wld-stats"

class LedData:
    effect: str
    intensity: int
    speed: int
    brightness: int
    reversed: bool
    index: float
    pallet: LedPallet

    def __init__(self, from_json:str|None = None):
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

    def to_dict(self):
        return {
            "effect": self.effect,
            "intensity": self.intensity,
            "speed": self.speed,
            "brightness": self.brightness,
            "reversed": self.reversed,
            "index": self.index,
            "pallet": self.pallet.to_dict()
        }

class ReturnRequestType:
    NONE = "none"
    BOARD_DATA = "board_data"
    LED_EFFECTS_LIST = "led_effects_list"

# the data recieved from the serial port and used to control the robot. ex: setting servo angles and led effects
class ProtocalInboundData:
    positionZ: int | None
    angleJoint1: int | None
    angleJoint2: int | None
    angleJoint3: int | None

    flushStateChanges: bool | None

    leds: LedData | None

    returnData: ReturnRequestType | None

    def __init__(self, from_json:str|None = None):

        if from_json:
            self.positionZ = None
            self.angleJoint1 = None
            self.angleJoint2 = None
            self.angleJoint3 = None

            self.flushStateChanges = None

            self.leds = None

            self.returnData = None

            for key, value in json.loads(from_json).items():
                setattr(self, key, value)
        else:
            self.positionZ = 0
            self.angleJoint1 = 90
            self.angleJoint2 = 90
            self.angleJoint3 = 90

            self.flushStateChanges = False

            self.leds = LedData()

    def to_dict(self):
        return {
            "positionZ": self.positionZ,
            "angleJoint1": self.angleJoint1,
            "angleJoint2": self.angleJoint2,
            "angleJoint3": self.angleJoint3,
            "flushMoveQueue": self.flushStateChanges,
            "leds": self.leds.to_dict() if self.leds else None
        }

class BoardData:
    stateChanges: list[tuple[str, bool]]

    def __init__(self):
        self.stateChanges = []
        # Each instance gets its own columns dict with 8 False values per column
        self.columns: dict[str, list[bool]] = {col: [False]*8 for col in "abcdefgh"}
        self.update()  # now, initialize the columns with sensor data

    def update(self) -> dict[str, list[bool]]:
        for row_index in range(8):
            power_pin = POWER_PINS[row_index]

            power_pin.on()  # turn on the sensor row

            columns_list = list(self.columns.keys())
            for column in columns_list:
                data_pin = DATA_PINS[columns_list.index(column)]

                # print(column, row_index, data_pin.value())  # debug print to see sensor values

                # invert the data so sensor reads true when a piece is on it
                self.columns[column][row_index] = not bool(data_pin.value())

            power_pin.off()  # we are done collecting sensor data, turn off row

        return self.columns
    
    def to_dict(self):
        return {
            "columns": self.columns,
            "stateChanges": self.stateChanges
        }

class ProtocalOutboundData:
    response: str | None
    error: Exception | None
    boardData: BoardData | None
    ledEffectsList: list | None

    def __init__(self, board_data: BoardData | None = None, include_led_effects: bool = False):
        self.boardData = board_data
        self.error = None
        self.ledEffectsList = [
            LedEffect.RAINBOW,
            LedEffect.BLINK,
            LedEffect.GLOW,
            LedEffect.FADE,
            LedEffect.CHASE,
            LedEffect.GRADIENT,
            LedEffect.WLD_STATS
        ] if include_led_effects else None

    def to_dict(self):
        return {
            "response": self.response,
            "boardData": self.boardData.to_dict() if self.boardData else None,
            "ledEffectsList": self.ledEffectsList,
            "error": str(self.error) if self.error else None
        }