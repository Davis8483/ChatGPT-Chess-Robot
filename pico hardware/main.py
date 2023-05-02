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
  "angle-joint3": 90
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
sensor_data_pins = [16, 17, 18, 19, 20, 21, 22, 23] # sensor columns a - h ascending

sensor = {
  "power": {},
  "data": {}
}

for index in range(8):
  sensor["power"][index + 1] = machine.Pin(sensor_power_pins[index], machine.Pin.OUT)
  sensor["data"][letter_columns[index]] = machine.Pin(sensor_data_pins[index], machine.Pin.IN, machine.Pin.PULL_UP)

# converts an angle to a pwm signal for a 9g servo
def get_pwm(angle: float):
  return int((angle * ((duty_max - duty_min) / max_degrees)) + duty_min)

poller = uselect.poll()
poller.register(sys.stdin, uselect.POLLIN)

# mainloop
while True:

  # check if serial data is available
  if (sys.stdin, uselect.POLLIN) in poller.poll(loop_delay):   

    # sent back to the host device based on data recieved
    response = {"response": {}}

    # try loading serial data into json format
    try:
      serial = json.loads(sys.stdin.readline().replace("\n", ""))

      # update data dictionary to push updates to servos
      if "data" in serial.keys():
        data.update(serial["data"])
      
      # return board sensor readings to the host
      if ("return" in serial.keys()) and (serial["return"] == "board"):

        # rows
        for row_index in range(8):
          # turn on sensor row
          sensor["power"][row_index].on()
          
          # save sensor data
          for column_index in letter_columns:
            # invert the data so sensor reads true when a piece is on it
            response["response"]["board"][f"row-{row_index + 1}"][f"column-{column_index}"] = not sensor["data"][column_index].value()

          # we are done collecting sensor data, turn off row
          sensor["power"][row_index].off()
      
      # return "ok" to host
      else:
        response["response"] = "ok"

    # return json packet error to host
    except Exception as e:
      response["response"] = str(e)


    # send response to host
    sys.stdout.write(f"{json.dumps(response)}\n")

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