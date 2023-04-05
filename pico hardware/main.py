import machine
import sys
import json
import time
import uselect

# ---------- Config Start ----------
# servo
duty_min = 1800
duty_max = 8100
max_degrees = 180

# z axis
z_axis_speed = 35.3 # mm/s
z_axis_tolerance = 2 # ±mm

# mainloop
loop_delay = 50 # milliseconds
# ---------- Config End ----------

# used to store servo positions and other information
data = {
  "position-z": 0,
  "angle-joint1": 90,
  "angle-joint2": 90,
  "angle-grabber": 90
}

current_z_pos = 0

# pin setup
z_axis_servo = machine.PWM(machine.Pin(0, machine.Pin.OUT))
z_limit_switch = machine.Pin(4, machine.Pin.IN, machine.Pin.PULL_DOWN)
joint1_servo = machine.PWM(machine.Pin(1, machine.Pin.OUT))
joint2_servo = machine.PWM(machine.Pin(2, machine.Pin.OUT))
grabber_servo = machine.PWM(machine.Pin(3, machine.Pin.OUT))

z_axis_servo.freq(50)
joint1_servo.freq(50)
joint2_servo.freq(50)
grabber_servo.freq(50)

poller = uselect.poll()
poller.register(sys.stdin, uselect.POLLIN)

def get_pwm(angle: float):
  return int((angle * ((duty_max - duty_min) / max_degrees)) + duty_min)

# mainloop
while True:

  events = poller.poll(loop_delay)

  # check if serial data is available
  if (sys.stdin, uselect.POLLIN) in events:   

    # try loading response into json format
    try:
      serial = json.loads(sys.stdin.readline().replace("\n", ""))

      if "data" in serial.keys():
        data.update(serial["data"])

      if ("return" in serial.keys()) and (serial["return"] == "board"):
        #TODO: return board positions
        pass

      response = '{"response": "ok"}\n'

    except Exception as e:
      # used a weird format because of the brackets in the string
      response = '{"response": "' + str(e) + '"}\n'


    # send response
    sys.stdout.write(response)

  # set servo positions
  joint1_servo.duty_u16(get_pwm(data["angle-joint1"]))
  joint2_servo.duty_u16(get_pwm(data["angle-joint2"]))
  grabber_servo.duty_u16(get_pwm(data["angle-joint3"]))

  # if current position is less than target position, go up
  if current_z_pos < (data["position-z"] - z_axis_tolerance) and (data["position-z"] != 0):
    z_axis_servo.duty_u16(get_pwm(83)) # go up

    current_z_pos += z_axis_speed * (loop_delay / 1000)

  # if limit switch is triggered set current position to 0 and stop
  elif z_limit_switch.value() == 0:
    z_axis_servo.duty_u16(0)
    current_z_pos = 0

  # go down until target position is reached or limit switch is triggered. If target position is set to 0 go down regardless to home.
  elif (current_z_pos > (data["position-z"] + z_axis_tolerance)) or (data["position-z"] == 0):
    z_axis_servo.duty_u16(get_pwm(97)) # go down

    current_z_pos -= z_axis_speed * (loop_delay / 1000)

  # target position is met, so stop moving
  else:
    z_axis_servo.duty_u16(0) # stop




