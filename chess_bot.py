import subprocess
import json
import time
import matrix_tools
import os
import queue

try:
    import stockfish
    import numpy
    from safe_cast import *

except:
    subprocess.run(["pip", "install", "stockfish", "numpy", "safe-cast"])
    import stockfish
    import numpy
    from safe_cast import *

# load settings file
with open('settings.json') as json_file:
    settings = json.load(json_file)

pos_z = 0
pos_x = -settings["hardware"]["length-arm-1"]
pos_y = -settings["hardware"]["length-arm-2"]
pos_joint1 = 90
pos_joint2 = 90
grabber_state = "closed"

# stores menu prompts to be handeled by the gui in main.py
prompt_queue = queue.Queue()

# returns wdl stats in the form of a bar visual
update_wdl_stats = True
def get_stats_visual(*_):
    global wdl_stats, update_wdl_stats

    if stockfish_ready:
       
        bar_height = 14

        if update_wdl_stats:
            wdl_stats = sf.get_wdl_stats()

            white = '▓\n' * round(((wdl_stats[0] + (wdl_stats[1] / 2)) * bar_height) / 1000)
            black = '░\n' * round(((wdl_stats[2] + (wdl_stats[1] / 2)) * bar_height) / 1000)

            wdl_stats = f"B\n—\n{black}{white}—\nW"
            update_wdl_stats = False
        
        return wdl_stats

    else:
        return ""

# returns board visuals
def get_board_visual(*_):
    global settings

    # check if stockfish engine is ready
    if stockfish_ready:

        try:
            # load settings file
            with open('settings.json') as json_file:
                settings = json.load(json_file)
        except:
            pass
            
        board_matrix = matrix_tools.string2matrix(sf.get_board_visual(), 2)

        # draw arm 1
        a1_end_x, a1_end_y = matrix_tools.calculate_end_coordinates(5, -1, (pos_joint1 - 180), settings["gui"]["length-terminal-arm-1"])
        updated_matrix = matrix_tools.draw_line(board_matrix, 5, -1, a1_end_x, a1_end_y, char="▒")
        
        # draw arm 2
        a2_end_x, a2_end_y = matrix_tools.calculate_end_coordinates(a1_end_x, a1_end_y, (pos_joint1 + pos_joint2 - 180), settings["gui"]["length-terminal-arm-2"])
        updated_matrix = matrix_tools.draw_line(updated_matrix, a1_end_x, a1_end_y, a2_end_x, a2_end_y, char="▓")

        return matrix_tools.matrix2string(updated_matrix)

    else:
        return ""

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
stockfish_ready = False
def stockfish_init():
    global sf, stockfish_ready
    
    # load settings file
    with open('settings.json') as json_file:
        settings = json.load(json_file)

    # initialize stockfish chess engine
    for index in settings["stockfish"]["binaries"]:
        try:
            sf = stockfish.Stockfish(path=f"{os.path.dirname(os.path.abspath(__file__))}{index}")
            stockfish_ready = True
            break # a working stockfish binary is found so we can stop testing candidates

        except: pass

    if not stockfish_ready:
        # binary not found, notify user and prompt them to quit
        prompt_queue.put((("[app.title]Error", "", "[app.label]Stockfish engine binary not found..."), {"Quit": quit}))

# initialize stockfish
stockfish_init()

class SerialInterface():

    def __init__(self, serial_class):
        self.serial = serial_class

    def check_connection(self):
        
        connected = False
        for index in range(5):
            try:
                # push an empty packet
                self.serial.write('{}\n'.encode())

                connected = True
                break

            except:
                pass

            time.sleep(0.1)
        
        if not connected:
            self.serial.close()

    # returns board dictionary
    def get_board(self):
        
        # try 5 times
        for index in range(5):
            try:
                # request board
                self.serial.write('{"return":"board"}\n'.encode())

                line = self.serial.read(self.serial.in_waiting).decode("utf-8")

                # save board dictionary
                board = json.loads(line)["response"]["board"]

                return board

            except:
                pass

            time.sleep(0.1)

    def get_effects(self):

        if self.serial.is_open:
            # try 5 times
            for index in range(5):
                try:
                    # request board
                    self.serial.write('{"return":"fx-list"}\n'.encode())

                    line = self.serial.read(self.serial.in_waiting).decode("utf-8")

                    # save effects list
                    effects = json.loads(line)["response"]["fx-list"]

                    return effects

                except:
                    if index == 4:
                        prompt_queue.put((("[app.title]Error", "", "[app.label]Failed to fetch led effects..."), {"Ok": None}))

                time.sleep(0.1)
        else:
            prompt_queue.put((("[app.title]Not Connected", "", "[app.label]Failed to fetch led effects,", "[app.label]chess robot not connected..."), {"Ok": None}))

    # pushes a change to the chess board to preview it
    def push_data(self, data: dict):

        if self.serial.is_open:
            # try 5 times
            for index in range(5):
                try:
                    self.serial.write(f'{json.dumps(data)}\n'.encode())

                    break

                except Exception as e:
                    if index == 4:
                        prompt_queue.put((("[app.title]Error", "", "[app.label]Failed to push data,", f"[app.label]{e}"), {"Ok": None}))
                
                time.sleep(0.1)
        else:
            prompt_queue.put((("[app.title]Not Connected", "", "[app.label]Failed to push data,", "[app.label]chess robot not connected..."), {"Ok": None}))

    # moves arm, grabber, and z axis to desired position
    def goto_position(self, x: float=None, y: float=None, z: float=None, grabber: str=None, retract: bool=True):
        global pos_y, pos_x, pos_z, grabber_state, pos_joint1, pos_joint2, settings

        try:
            # load settings file
            with open('settings.json') as json_file:
                settings = json.load(json_file)
        except:
            pass
        
        data = {"data": {}}

        if z != None:
            pos_z = safe_float(z)
            data["data"]["position-z"] = pos_z

        if grabber != None:
            grabber_state = safe_str(grabber)

            if grabber_state == "open":
                joint3 = settings["hardware"]["grabber-open-angle"]
            elif grabber_state == "closed":
                joint3 = settings["hardware"]["grabber-closed-angle"]

            data["data"]["angle-joint3"] = joint3

        # push z axis and grabber states to the board
        self.push_data(data)

        xy_update = False
        
        if x == None:
            x = pos_x
        else:
            xy_update = True

        if y == None:
            y = pos_y
        else:
            xy_update = True

        # keep within radial constraints of the arm
        if numpy.sqrt((x ** 2) + (y ** 2)) < (settings["hardware"]["length-arm-1"] + settings["hardware"]["length-arm-2"]) and xy_update:

            pos_x = safe_float(x)
            pos_y = safe_float(y)
            
            # get the updated joint angles
            new_joint1, new_joint2 = _get_servo_angles(pos_x, pos_y, settings["hardware"]["length-arm-1"], settings["hardware"]["length-arm-2"])
            
            if (pos_joint2 < settings["hardware"]["retraction-angle"]) and retract:
                # move mass as close to joint 1 as possible
                self.push_data({"data": {"angle-joint2": settings["hardware"]["retraction-angle"]}})
            
                # wait for servo to finish
                time.sleep(abs(settings["hardware"]["retraction-angle"] - pos_joint2) * (1 / settings["hardware"]["servo-speed-deg/sec"]))

            # move joint 1 into position
            self.push_data({"data": {"angle-joint1": new_joint1 - 90 + settings["joint-offsets"]["1"]}})

            # wait for servo to finish
            time.sleep(abs(new_joint1 - pos_joint1) * (1 / settings["hardware"]["servo-speed-deg/sec"]))

            # move joint 2 into position
            self.push_data({"data": {"angle-joint2": new_joint2 + settings["joint-offsets"]["2"]}})

            # wait for servo to finish
            time.sleep(abs(new_joint2 - pos_joint2) * (1 / settings["hardware"]["servo-speed-deg/sec"]))

            # we are done processing moves, update joint vars to reflect changes
            pos_joint1 = new_joint1
            pos_joint2 = new_joint2
