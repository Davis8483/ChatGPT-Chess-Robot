import machine
import json
import time
import gc
import select
import sys
import _thread
from pi_pico_neopixel.neopixel import Neopixel
import led_tools
from serial_protocal import BoardData, ProtocalInboundData, LedData, ProtocalOutboundData, ReturnRequestType

# ---------- Config Start ----------
# servo
duty_min = 1800
duty_max = 8100
max_degrees = 180

# z axis
z_axis_speed = 58.2 # mm/s
z_axis_tolerance = 2 # ±mm
z_axis_zero_position = 90

# led strips
strip_length1 = 8
strip_length2 = 8

# mainloop
loop_delay = 50 # milliseconds
# ---------- Config End ----------

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

target_z_pos = 0
led_state_data = LedData()

# ran as a seperate thread, recieves serial data and sends move queue updates to the host
def serial_communication_thread():
  global led_state_data
  global target_z_pos

  def data_recieved(data: str):
    global target_z_pos, led_state_data
    
    serialData = ProtocalInboundData(from_json=data) # load into object

    # save the target z position
    if serialData.positionZ:
      target_z_pos = serialData.positionZ

    # update the servo positions based on the angles recieved
    if serialData.angleJoint1:
      joint1_servo.duty_u16(get_pwm(serialData.angleJoint1))

    if serialData.angleJoint2:
      joint2_servo.duty_u16(get_pwm(serialData.angleJoint2))

    if serialData.angleJoint3:
      grabber_servo.duty_u16(get_pwm(serialData.angleJoint3))

    # update the led state data
    if serialData.leds:
      led_state_data = LedData(from_json=json.dumps(serialData.leds))

    if serialData.flushStateChanges:
      # if flushStateChanges is set to true, clear the state changes
      board_data.stateChanges.clear()

    if serialData.returnData:

      if serialData.returnData == ReturnRequestType.BOARD_DATA:
        outbound_data = ProtocalOutboundData(board_data=board_data)

      elif serialData.returnData == ReturnRequestType.LED_EFFECTS_LIST:
        outbound_data = ProtocalOutboundData(include_led_effects=True)

      if serialData.returnData != ReturnRequestType.NONE:
        sys.stdout.write(json.dumps(outbound_data.to_dict()) + "\n")

  buffer = ""
  board_data = BoardData() # the current board state
  prev_snapshot = board_data.update() # previous board snapshot to compare against

  while True:
    outbound_data = ProtocalOutboundData()

    try:

      test_poll = select.poll()
      test_poll.register(sys.stdin, select.POLLIN)

      # read serial data until a newline is received
      if test_poll.poll(10):
        while True:
          char = sys.stdin.read(1)
          if not char:
            break  # No more data available
          # print(f"Read char: {char}")  # Optional: Debugging
          if char == "\n":
            data_recieved(buffer.strip())
            buffer = ""
          else:
            buffer += char

      # get board snapshot
      board_snapshot = board_data.update() # get the current board state

      # store changes compared to previous snapshot
      for column in board_snapshot.keys():
        for square in range(8):

          # if the snapshot squares are not the same save the changes
          if bool(board_snapshot[column][square]) != bool(prev_snapshot[column][square]):
            board_data.stateChanges.append((f"{square + 1}{column}", board_snapshot[column][square])) # either True or False

            # if there are changes, push data to host
            outbound_data.boardData = board_data

            sys.stdout.write(json.dumps(outbound_data.to_dict()) + "\n") # send the data to the host

      # update previous board snapshot
      prev_snapshot = {}
      for column in board_snapshot:
        prev_snapshot[column] = list(board_snapshot[column])  # copy the list

    # return json packet error to host
    except Exception as e:
      outbound_data.error = e

      buffer = "" # clear the buffer to prevent processing old data

      sys.stdout.write(json.dumps(outbound_data.to_dict()) + "\n") # send the data to the host

    del outbound_data

# start the serial communication handling thread
_thread.start_new_thread(serial_communication_thread, ())

# mainloop, updates servo positions and leds
while True:
  
  # loop delay
  time.sleep(loop_delay / 1000)

  # MARK: z axis control
  # if current position is less than target position, go up
  if current_z_pos < (target_z_pos - z_axis_tolerance) and (target_z_pos != 0):
    z_axis_servo.duty_u16(get_pwm(83)) # go up

    current_z_pos += z_axis_speed * (loop_delay / 1000)

  # if limit switch is triggered set current position to 0 and stop
  elif z_limit_switch.value() == 0:
    z_axis_servo.duty_u16(get_pwm(z_axis_zero_position))
    current_z_pos = 0

  # go down until target position is reached or limit switch is triggered. If target position is set to 0 go down regardless to home.
  elif (current_z_pos > (target_z_pos + z_axis_tolerance)) or (target_z_pos == 0):
    z_axis_servo.duty_u16(get_pwm(97)) # go down

    current_z_pos -= z_axis_speed * (loop_delay / 1000)

  # target position is met, so stop moving
  else:
    z_axis_servo.duty_u16(get_pwm(z_axis_zero_position)) # stop

  # calculate the step size based on loop_delay and led_state_data.speed
  step_size = (loop_delay / 1000) * ((int(led_state_data.speed) % 256 + 1) / 255)

  # iterate the led effect index
  led_state_data.index += step_size
  
  # set global brightness
  led_strip1.brightness(int(led_state_data.brightness) % 256)
  led_strip2.brightness(int(led_state_data.brightness) % 256)

  # update the led strip based on the current index
  strip_update = led_effects.get_effect(led_state_data.effect)((float(led_state_data.index) % 1), (int(led_state_data.intensity) % 256))

  if led_state_data.reversed:
    strip_update.reverse()

  for index in range(strip_length1):
    led_strip1.set_pixel(index, strip_update[index])

  for index in range(strip_length2):
    led_strip2.set_pixel(index, strip_update[strip_length1 + index])

  # push the updates
  led_strip1.show()
  led_strip2.show()
