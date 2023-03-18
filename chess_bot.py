import subprocess
import json
import time
import numpy
import matrix_tools
import os

try:
  import stockfish
except:
  subprocess.run(["pip", "install", "stockfish"])
  import stockfish

# initialize stockfish chess engine
sf = stockfish.Stockfish(path=fr"{os.path.dirname(os.path.abspath(__file__))}\stockfish\stockfish-windows-2022-x86-64-avx2.exe")

_loop = False
target_x = 192.3
target_y = 192.3
target_z = 0
pos_x = 192.3
pos_y = 192.3
grabber_state = "closed"

# stops the mainloop
def stop():
  global _loop
  _loop = False

# returns if the loop controlling the machine is running
def get_status(*_):
  if _loop:
    return " 🟢 Connected"
  else:
    return " 🔴 Disconnected"

# returns board visuals
def get_visuals(*_):

  #TODO: finnish and make sure any angles are correct

  output = ''

  # load settings file
  with open('settings.json') as json_file:
    settings = json.load(json_file)

  joint1, joint2 = _get_servo_angles(pos_x, pos_y, settings["hardware"]["config"]["length-arm-1"], settings["hardware"]["config"]["length-arm-2"])

  # if connected to the chess board display board with arm overlay 
  if _loop:
    end_x, end_y = matrix_tools.calculate_end_coordinates(0, 0, joint1, settings["hardware"]["config"]["length-arm-1"])

    updated_matrix = matrix_tools.draw_line(matrix_tools.string2matrix(sf.get_board_visual(), 2), 0, 0, end_x, end_y)

    # compile list matrix into a singular string
    for row in updated_matrix:
      for item in row:
        output += item
      output += '\n'

  else:
    output = sf.get_board_visual()

  return output

# used outside of this file to set the position that the mainloop should try to achieve
def goto_position(x, y, z):
  global target_x, target_y, target_z, pos_y, pos_x
  target_x = x
  target_y = y
  target_z = z
  pos_x = x
  pos_y = y

def set_grabber(state):
  global grabber_state
  grabber_state = state

# inverse kinematics junk, source: https://github.com/aakieu/2-dof-planar/blob/master/python/inverse_kinematics.py
def _get_servo_angles(x, y, a1, a2):
  
  # equations for Inverse kinematics
  r1 = numpy.sqrt(x ** 2 + y ** 2)  # radius equation
  phi_1 = -numpy.arccos((a2 ** 2 - a1 ** 2 - r1 ** 2)/(-2 * a1 * r1))  # eqauation 1
  phi_2 = numpy.arctan2(y, -x)  # equation 2
  phi_3 = -numpy.arccos((r1 ** 2 - a1 ** 2 - a2 ** 2)/(-2 * a1 * a2)) # equation 3

  theta_1 = 180 - numpy.rad2deg(phi_2 - phi_1)

  theta_2 = numpy.rad2deg(phi_3) + 180

  return theta_1, theta_2

current_speed = 0
def _get_position(current_x, current_y, target_x, target_y, max_speed, acceleration, loop_speed):
  global current_speed

  dx = target_x - current_x
  dy = target_y - current_y
  distance = numpy.sqrt(dx**2 + dy**2)

  if distance <= acceleration:
    # We're close enough to the target, just move directly to it
    current_speed = 0
    return target_x, target_y

  # Calculate the unit vector towards the target
  ux = dx / distance
  uy = dy / distance

  # Calculate distance to accelerate/de-accelerate
  acceleration_distance = (current_speed ** 2 / (2 * acceleration)) / loop_speed
  
  # We're not at the maximum speed yet, accelerate
  if (distance > acceleration_distance) and (current_speed < max_speed):
    # We're far from the target, accelerate
    current_speed += acceleration * loop_speed
  elif distance < acceleration_distance:
    # We're close to the target, decelerate
    current_speed -= acceleration * loop_speed

  # Calculate the new position towards the target
  delta_x = ux * current_speed
  delta_y = uy * current_speed
  new_x = current_x + delta_x
  new_y = current_y + delta_y

  return new_x, new_y

# mainloop
def main(serial):
  global _loop, pos_x, pos_y, settings
  _loop = True
  while _loop:
    # load settings file
    with open('settings.json') as json_file:
      settings = json.load(json_file)

    # pos_x, pos_y = _get_position(pos_x, pos_y, target_x, target_y, settings["hardware"]["max-speed"], settings["hardware"]["acceleration"], 0.1)

    joint1, joint2 = _get_servo_angles(pos_x, pos_y, settings["hardware"]["config"]["length-arm-1"], settings["hardware"]["config"]["length-arm-2"])

    serial.write(f'{{"data": {{"angle-joint1": {joint1}, "angle-joint2": {joint2}, "position-z": {target_z}}}}}\n'.encode())
    time.sleep(0.1)

    