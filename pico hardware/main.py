import machine
import sys
import json
import time
import _thread
from pi_pico_neopixel.neopixel import Neopixel
import led_tools

# ---------- Config Start ----------
# servo
duty_min = 1800
duty_max = 8100
max_degrees = 180

# z axis
z_axis_speed = 35.3 # mm/s
z_axis_tolerance = 2 # ±mm

# led strips
strip_length1 = 8
strip_length2 = 8

# mainloop
loop_delay = 50 # milliseconds
# ---------- Config End ----------

# used to store servo positions and other information
data = {
  "position-z": 0,
  "angle-joint1": 90,
  "angle-joint2": 90,
  "angle-joint3": 90,

  "leds": {
    "effect": "glow",
    "intensity": 150,
    "speed": 100,
    "brightness": 255,
    "index": 0,
    "pallet": {
      "1": [55, 0, 0],
      "2": [0, 0, 0]
    }
  }
}

letter_columns = ["a", "b", "c", "d", "e", "f", "g", "h"]

current_z_pos = 0

# servo pin setup
z_axis_servo = machine.PWM(machine.Pin(0, machine.Pin.OUT))
z_limit_switch = machine.Pin(4, machine.Pin.IN, machine.Pin.PULL_DOWN)
joint1_servo = machine.PWM(machine.Pin(1, machine.Pin.OUT))
joint2_servo = machine.PWM(machine.Pin(2, machine.Pin.OUT))
grabber_servo = machine.PWM(machine.Pin(3, machine.Pin.OUT))

z_axis_servo.freq(50)
joint1_servo.freq(50)
joint2_servo.freq(50)
grabber_servo.freq(50)

# haul effect sensor pin setup
sensor_power_pins = [6, 7, 8, 9, 10, 11, 12, 13] # sensor rows 1 - 8 ascending
sensor_data_pins = [16, 17, 18, 19, 20, 21, 22, 26] # sensor columns a - h ascending

sensor = {
  "power": {},
  "data": {}
}

for index in range(8):
  pin = machine.Pin(sensor_power_pins[index], machine.Pin.OUT)
  sensor["power"][index + 1] = pin

  pin = machine.Pin(sensor_data_pins[index], machine.Pin.IN, machine.Pin.PULL_UP)
  sensor["data"][letter_columns[index]] = pin

# led strip pin setup
led_strip1 = Neopixel(strip_length1, 0, pin=14, mode="GRB")
led_strip2 = Neopixel(strip_length2, 1, pin=15, mode="GRB")

led_effects = led_tools.effects(strip_length1 + strip_length2)

# converts an angle to a pwm signal for a 9g servo
def get_pwm(angle: float):
  return int((int(angle) * ((duty_max - duty_min) / max_degrees)) + duty_min)

# merges dictionaries without overwriting sub directories
def merge_dicts(dict1: dict, dict2: dict):
  for key, value in dict2.items():
    if isinstance(value, dict) and key in dict1:
      merge_dicts(dict1[key], value)
    else:
      dict1[key] = value

  return dict1

# ran as a seperate thread, takes in serial data and updates data dictionary
def serial_communication_thread():
  while True:

    # sent back to the host device based on data recieved
    response = {"response": {}}

    # try loading serial data into json format
    try:
      serial = json.loads(sys.stdin.readline().replace("\n", ""))

      # update data dictionary to push updates to servos
      if "data" in serial.keys():
        merge_dicts(data, serial["data"])
      
      # return board sensor readings to the host
      if "return" in serial.keys():
      
        if serial["return"] == "board":
          
          # create the board directory
          response["response"]["board"] = {}

          # rows
          for row_index in range(8):
            # turn on sensor row
            sensor["power"][row_index + 1].on()

            # create a row directory
            response["response"]["board"][str(row_index + 1)] = {}

            # save sensor data
            for column_index in letter_columns:
              # invert the data so sensor reads true when a piece is on it
              response["response"]["board"][str(row_index + 1)][str(column_index)] = not bool(sensor["data"][column_index].value())

            # we are done collecting sensor data, turn off row
            sensor["power"][row_index + 1].off()

        elif serial["return"] == "fx-list":
          response["response"]["fx-list"] = list(led_effects.fx_list.keys())

      # return "ok" to host
      else:
        response["response"] = "ok"

    # return json packet error to host
    except Exception as e:
      response["response"] = str(e)


    # send response to host
    sys.stdout.write(f"{json.dumps(response)}\n")

# start the serial communication handling thread
_thread.start_new_thread(serial_communication_thread, ())

# mainloop, updates servo positions and leds
while True:
  
  # loop delay
  time.sleep(loop_delay / 1000)

  # set servo positions
  joint1_servo.duty_u16(get_pwm(data["angle-joint1"]))
  joint2_servo.duty_u16(get_pwm(data["angle-joint2"]))
  grabber_servo.duty_u16(get_pwm(data["angle-joint3"]))

  # if current position is less than target position, go up
  if current_z_pos < (float(data["position-z"]) - z_axis_tolerance) and (float(data["position-z"]) != 0):
    z_axis_servo.duty_u16(get_pwm(83)) # go up

    current_z_pos += z_axis_speed * (loop_delay / 1000)

  # if limit switch is triggered set current position to 0 and stop
  elif z_limit_switch.value() == 0:
    z_axis_servo.duty_u16(0)
    current_z_pos = 0

  # go down until target position is reached or limit switch is triggered. If target position is set to 0 go down regardless to home.
  elif (current_z_pos > (float(data["position-z"]) + z_axis_tolerance)) or (float(data["position-z"]) == 0):
    z_axis_servo.duty_u16(get_pwm(97)) # go down

    current_z_pos -= z_axis_speed * (loop_delay / 1000)

  # target position is met, so stop moving
  else:
    z_axis_servo.duty_u16(0) # stop
  
  # calculate the step size based on loop_delay and data["leds"]["speed"]
  step_size = (loop_delay / 1000) * ((int(data["leds"]["speed"]) % 256 + 1) / 255)

  # iterate the led effect index
  data["leds"]["index"] += step_size

  # update effects pallet
  for key in data["leds"]["pallet"].keys():
    if key.isdigit():
      led_effects.pallet[int(key)] = data["leds"]["pallet"][key]
  
  # set global brightness
  led_strip1.brightness(int(data["leds"]["brightness"]) % 256)
  led_strip2.brightness(int(data["leds"]["brightness"]) % 256)

  # update the led strip
  if data["leds"]["effect"] in led_effects.fx_list:
    
    strip_update = led_effects.fx_list[data["leds"]["effect"]](led_effects, (float(data["leds"]["index"]) % 1), (int(data["leds"]["intensity"]) % 256))

    for index in range(strip_length1):
      led_strip1.set_pixel(index, strip_update[index])

    for index in range(strip_length2):
      led_strip2.set_pixel(index, strip_update[strip_length1 + index])

    # push the updates
    led_strip1.show()
    led_strip2.show()
