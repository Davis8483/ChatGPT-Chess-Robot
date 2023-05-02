import subprocess
import json
import time
import matrix_tools
import os
import queue


try:
    import stockfish
    import numpy
    import serial
except:
    subprocess.run(["pip", "install", "stockfish", "numpy", "pyserial"])
    import stockfish
    import numpy
    import serial

pos_z = 0
pos_x = -192.3
pos_y = -192.3
grabber_state = "closed"

# stores menu prompts to be handeled by the gui in main.py
prompt_queue = queue.Queue()
#TODO: remove this later
prompt_queue.put((("test prompt", ""), {"Ok": None}))

# returns wdl stats in the form of a bar visual
update_wdl_stats = True
def get_stats_visual(*_):
    global wdl_stats, update_wdl_stats

    bar_height = 14

    if update_wdl_stats:
        wdl_stats = sf.get_wdl_stats()

        white = '▓\n' * round(((wdl_stats[0] + (wdl_stats[1] / 2)) * bar_height) / 1000)
        black = '░\n' * round(((wdl_stats[2] + (wdl_stats[1] / 2)) * bar_height) / 1000)

        wdl_stats = f"B\n—\n{black}{white}—\nW"
        update_wdl_stats = False
    
    return wdl_stats


# returns board visuals
def get_visuals(*_):

    # load settings file
    with open('settings.json') as json_file:
        settings = json.load(json_file)

    joint1, joint2 = _get_servo_angles(pos_x, pos_y, settings["hardware"]["config"]["length-arm-1"], settings["hardware"]["config"]["length-arm-2"])
        
    board_matrix = matrix_tools.string2matrix(sf.get_board_visual(), 2)

    # draw arm 1
    a1_end_x, a1_end_y = matrix_tools.calculate_end_coordinates(5, -1, (joint1 - 180), settings["hardware"]["config"]["length-terminal-arm-1"])
    updated_matrix = matrix_tools.draw_line(board_matrix, 5, -1, a1_end_x, a1_end_y, char="▒")
    
    # draw arm 2
    a2_end_x, a2_end_y = matrix_tools.calculate_end_coordinates(a1_end_x, a1_end_y, (joint1 + joint2 - 180), settings["hardware"]["config"]["length-terminal-arm-2"])
    updated_matrix = matrix_tools.draw_line(updated_matrix, a1_end_x, a1_end_y, a2_end_x, a2_end_y, char="▓")

    return matrix_tools.matrix2string(updated_matrix)


# used outside of this file to set the position that the mainloop should try to achieve
def goto_position(x, y, z):
    global pos_y, pos_x, pos_z

    # load settings file
    with open('settings.json') as json_file:
        settings = json.load(json_file)
    
    # keep withing radial constraints
    if numpy.sqrt((x ** 2) + (y ** 2)) < (settings["hardware"]["config"]["length-arm-1"] + settings["hardware"]["config"]["length-arm-2"]):
        pos_x = x
        pos_y = y

    pos_z = z


def set_grabber(state: str):
    global grabber_state
    grabber_state = state

# inverse kinematics junk, source: https://github.com/aakieu/2-dof-planar/blob/master/python/inverse_kinematics.py
def _get_servo_angles(x, y, a1, a2):

    # equations for Inverse kinematics
    r1 = numpy.sqrt(x ** 2 + y ** 2)  # radius equation
    phi_1 = -numpy.arccos((a2 ** 2 - a1 ** 2 - r1 ** 2) /
                          (-2 * a1 * r1))  # eqauation 1
    phi_2 = numpy.arctan2(y, -x)  # equation 2
    phi_3 = -numpy.arccos((r1 ** 2 - a1 ** 2 - a2 ** 2) /
                          (-2 * a1 * a2))  # equation 3

    theta_1 = 180 - numpy.rad2deg(phi_2 - phi_1)

    theta_2 = numpy.rad2deg(phi_3) + 180

    return theta_1, theta_2

# initialize the stockfish chess engine
def stockfish_init():
    global sf
    
    # load settings file
    with open('settings.json') as json_file:
        settings = json.load(json_file)

    # initialize stockfish chess engine
    binary_found = False
    for index in settings["stockfish"]["binaries"]:
        try:
            sf = stockfish.Stockfish(path=f"{os.path.dirname(os.path.abspath(__file__))}{index}")
            binary_found = True
            break # a working stockfish binary is found so we can stop testing candidates

        except: pass

    if not binary_found:
        # binary not found, notify user and prompt them to quit
        prompt_queue.put((("[app.title]Error", "", "[app.label]Stockfish engine binary not found..."), {"Quit": quit}))

# ran as a continuous thread, controls the physical chess robot
def mainloop(serial):
    global pos_x, pos_y, settings

    # load settings file
    with open('settings.json') as json_file:
        settings = json.load(json_file)

    joint1, joint2 = _get_servo_angles(pos_x, pos_y, settings["hardware"]["config"]["length-arm-1"], settings["hardware"]["config"]["length-arm-2"])

    if grabber_state == "open":
        joint3 = settings["hardware"]["config"]["grabber-open-angle"]
    elif grabber_state == "closed":
        joint3 = settings["hardware"]["config"]["grabber-closed-angle"]

    # data to send to the chess board
    data = {"data": {
        "angle-joint1": joint1 - 90 + settings["hardware"]["offset-joint-1"],
        "angle-joint2": joint2 + settings["hardware"]["offset-joint-2"],
        "angle-joint3": joint3,
        "position-z": pos_z
        }}

    serial.write(f"{json.dumps(data)}\n".encode())

# initialize stockfish
stockfish_init()