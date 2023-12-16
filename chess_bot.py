import subprocess
import json
import time
import matrix_tools
import os
import queue
import pyttsx3 # library is stored localy because of a bug with the original
import chatGPT
import play_sound
import board_visual_popout

try:
    import stockfish
    import numpy
    from safe_cast import *
    import chess
    import nltk
    import continuous_threading

except:
    subprocess.run(["pip", "install", "stockfish", "numpy", "safe-cast", "chess", "nltk", "continuous-threading"])
    import stockfish
    import numpy
    from safe_cast import *
    import chess
    import nltk
    import continuous_threading

# load settings file
with open('settings.json') as json_file:
    settings = json.load(json_file)

# load arpabet, maps words to mouth shapes
try:
    arpabet = nltk.corpus.cmudict.dict()
except:
    nltk.download("cmudict")
    arpabet = nltk.corpus.cmudict.dict()

# stores menu prompts to be handeled by the gui in main.py
prompt_queue = queue.Queue()

# initialize stockfish chess engine
stockfish_ready = False
try:
    sf = stockfish.Stockfish(path=f"{os.path.dirname(os.path.abspath(__file__))}{settings['stockfish']['path']}")

    stockfish_ready = True

except: pass

if not stockfish_ready:
    # binary not found, notify user and prompt them to quit
    prompt_queue.put((("[app.title]Error", "", "[app.label]Stockfish engine binary not found..."), {"Quit": quit}))

pos_z = 0
pos_x = -settings["hardware"]["length-arm-1"]
pos_y = -settings["hardware"]["length-arm-2"]
pos_joint1 = 90
pos_joint2 = 90
grabber_state = "closed"

if stockfish_ready:
    wdl_stats = sf.get_wdl_stats()
    board_visual = sf.get_board_visual()
else:
    wdl_stats = [0, 1000, 0]
    board_visual = ""

# initialize board svg window
board_popout_window = board_visual_popout.Visual()

# returns wdl stats in the form of a bar visuas
def get_stats_visual():
       
    bar_height = 12

    white = '▓\n' * round(((wdl_stats[0] + (wdl_stats[1] / 2)) * bar_height) / 1000)
    black = '░\n' * round(((wdl_stats[2] + (wdl_stats[1] / 2)) * bar_height) / 1000)

    wdl_stats_visual = f"B\n—\n░\n{black}{white}▓\n—\nW"
    
    return wdl_stats_visual

# returns board visuals
def get_board_visual():
    global settings, board_matrix

    try:
        # load settings file
        with open('settings.json') as json_file:
            settings = json.load(json_file)
    except:
        pass

    board_matrix = matrix_tools.string2matrix(board_visual, 2)

    # draw arm 1
    a1_end_x, a1_end_y = matrix_tools.calculate_end_coordinates(5, -1, (pos_joint1 - 180), settings["gui"]["length-terminal-arm-1"])
    updated_matrix = matrix_tools.draw_line(board_matrix, 5, -1, a1_end_x, a1_end_y, char="▒")
    
    # draw arm 2
    a2_end_x, a2_end_y = matrix_tools.calculate_end_coordinates(a1_end_x, a1_end_y, (pos_joint1 + pos_joint2 - 180), settings["gui"]["length-terminal-arm-2"])
    updated_matrix = matrix_tools.draw_line(updated_matrix, a1_end_x, a1_end_y, a2_end_x, a2_end_y, char="▓")

    return matrix_tools.matrix2string(updated_matrix)

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

# merges dictionaries without overwriting sub directories
def merge_dicts(dict1: dict, dict2: dict):
    """
    Merge two dictionaries recursively without overwriting sub-dictionaries.
    """
    for key, value in dict2.items():
        if isinstance(value, dict) and key in dict1:
            merge_dicts(dict1[key], value)
        else:
            dict1[key] = value


class SerialInterface():

    def __init__(self, serial_class):
        global pos_joint1, pos_joint2

        # initialize variables
        self.serial = serial_class
        self.board_ready = False
        self.game_state = "inactive"
        self.continue_game = False
        pos_joint1, pos_joint2 = _get_servo_angles(pos_x, pos_y, settings["hardware"]["length-arm-1"], settings["hardware"]["length-arm-2"])

    def check_connection(self):
        
        connected = False
        for index in range(10):
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
    def get_board(self, suppress_errors: bool=False):
        
        while True:
            if self.serial.is_open:
                try:
                    # request board
                    self.serial.write('{"return":"board"}\n'.encode())

                    self.serial.flush()

                    line = self.serial.read(self.serial.in_waiting).decode("utf-8").strip()

                    # save board dictionary
                    board = json.loads(line)["response"]["board"]

                    return board

                except:
                    pass
            else:
                if not suppress_errors:
                    prompt_queue.put((("[app.title]Not Connected", "", "[app.label]Failed to fetch board,", "[app.label]chess robot not connected..."), {"Ok": None}))
                break

    def get_effects(self, suppress_errors: bool=False):

        while True:
            if self.serial.is_open:
                try:
                    # request board
                    self.serial.write('{"return":"fx-list"}\n'.encode())

                    self.serial.flush()

                    line = self.serial.read(self.serial.in_waiting).decode("utf-8")

                    # save effects list
                    effects = json.loads(line)["response"]["fx-list"]

                    return effects

                except:
                    pass
            else:
                if not suppress_errors:
                    prompt_queue.put((("[app.title]Not Connected", "", "[app.label]Failed to fetch led effects,", "[app.label]chess robot not connected..."), {"Ok": None}))
                break
    
    # sets chess bots led strip
    def set_leds(self, macro: str, custom_data: dict=None, suppress_errors: bool=False):
        
        if custom_data != None:
            pass

        # load settings file
        with open('settings.json') as json_file:
            settings = json.load(json_file)
        
        if macro in settings["led-strip"]["macros"]:

            data = settings["led-strip"]["macros"][macro]

            if custom_data != None:
                merge_dicts(data, custom_data)

            self.push_data({"data": {
                                    "leds": data
                                    }})
            
        elif not suppress_errors:
            prompt_queue.put((("[app.title]Not Connected", "", "[app.label]Failed to set led effect,", "[app.label]invalid macro..."), {"Ok": None}))

    # pushes a change to the chess board to preview it
    def push_data(self, data: dict, suppress_errors: bool=False):

        while True:
            if self.serial.is_open:
                try:
                    self.serial.write(f'{json.dumps(data)}\n'.encode())

                    self.serial.flush()
                    break
                
                except:
                    pass
            elif not suppress_errors:
                prompt_queue.put((("[app.title]Not Connected", "", "[app.label]Failed to push data,", "[app.label]chess robot not connected...", "", f"[app.label]{data}"), {"Ok": None}))
                break

    # moves arm, grabber, and z axis to desired position
    def goto_position(self, x: float=None, y: float=None, z: float=None, grabber: str=None, retract: bool=True, suppress_errors: bool=False):
        global pos_y, pos_x, pos_z, grabber_state, pos_joint1, pos_joint2, settings

        if self.serial.is_open:
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
                elif grabber_state == "calibrate":
                    joint3 = 90

                data["data"]["angle-joint3"] = joint3 + settings["joint-offsets"]["3"]

            # push z axis and grabber states to the board
            self.push_data(data, suppress_errors=suppress_errors)

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
                    self.push_data({"data": {"angle-joint2": settings["hardware"]["retraction-angle"]}}, suppress_errors=suppress_errors)
                
                    # wait for servo to finish
                    time.sleep(abs(settings["hardware"]["retraction-angle"] - pos_joint2) * (1 / settings["hardware"]["servo-speed-deg/sec"]))

                # move joint 1 into position
                self.push_data({"data": {"angle-joint1": new_joint1 - 90 + settings["joint-offsets"]["1"]}}, suppress_errors=suppress_errors)

                # wait for servo to finish
                time.sleep(abs(new_joint1 - pos_joint1) * (1 / settings["hardware"]["servo-speed-deg/sec"]))

                # move joint 2 into position
                self.push_data({"data": {"angle-joint2": new_joint2 + settings["joint-offsets"]["2"]}}, suppress_errors=suppress_errors)

                # wait for servo to finish
                time.sleep(abs(new_joint2 - pos_joint2) * (1 / settings["hardware"]["servo-speed-deg/sec"]))

                # we are done processing moves, update joint vars to reflect changes
                pos_joint1 = new_joint1
                pos_joint2 = new_joint2

        elif not suppress_errors:
            prompt_queue.put((("[app.title]Not Connected", "", "[app.label]Failed to goto position,", "[app.label]chess robot not connected..."), {"Ok": None}))

    def make_move(self, move):
        # goto pick up piece
        position = settings["board-positions"][move[1]][move[0]]
        self.goto_position(x=position[0], y=position[1], suppress_errors=True)

        # plunge
        self.goto_position(z=0, grabber="open", suppress_errors=True)

        time.sleep(1.5)

        # go up
        self.goto_position(z=settings["board-positions"]["home"]["height"], grabber="closed", suppress_errors=True)

        time.sleep(2)

        # goto set down piece
        position = settings["board-positions"][move[3]][move[2]]
        self.goto_position(x=position[0], y=position[1], suppress_errors=True)

        # plunge
        self.goto_position(z=0, suppress_errors=True)

        time.sleep(1.5)

        # go up
        self.goto_position(z=settings["board-positions"]["home"]["height"], grabber="open", suppress_errors=True)

        time.sleep(2)

        # verify move was successful
        board = self.get_board()

        if board[move[1]][move[0]] or not board[move[3]][move[2]]:

            # go back to waiting position
            position = settings["board-positions"]["home"]["position"]
            self.goto_position(x=position[0], y=position[1], grabber="closed", suppress_errors=True)

            prompt_queue.put((("[app.title]Fix Board", "", "[app.label]Failed to make move,", f"[app.label]please move from {move[0]}{move[1]} to {move[2]}{move[3]}"), {"Ok": None}))

            self.speak(f"Failed to make move, please move from {move[0]}{move[1]} to {move[2]}{move[3]}")

            # wait until board is fixed
            while board[move[1]][move[0]] or not board[move[3]][move[2]] and self.continue_game:
                board = self.get_board()

    def remove_piece(self, square):
        # pick up piece
        position = settings["board-positions"][square[1]][square[0]]
        self.goto_position(x=position[0], y=position[1], suppress_errors=True)

        # plunge
        self.goto_position(z=0, grabber="open", suppress_errors=True)

        time.sleep(1.5)

        # go up
        self.goto_position(z=settings["board-positions"]["home"]["height"], grabber="closed", suppress_errors=True)

        time.sleep(2)
        
        # go back to waiting position
        position = settings["board-positions"]["home"]["position"]
        self.goto_position(x=position[0], y=position[1], grabber="closed", suppress_errors=True)

        # drop piece
        self.goto_position(grabber="open")

        time.sleep(0.5)

        # close grabber
        self.goto_position(grabber="closed")

        # verify removal was successful
        board = self.get_board()

        if board[square[1]][square[0]]:

            prompt_queue.put((("[app.title]Fix Board", "", "[app.label]Failed to remove piece,", f"[app.label]please remove {square[0]}{square[1]}"), {"Ok": None}))

            self.speak(f"Failed to remove piece, please remove {square[0]}{square[1]}")

            # wait until board is fixed
            while board[square[1]][square[0]] and self.continue_game:
                board = self.get_board()

            # countdown timer to allow player to remove hand from board
            self.set_leds("countdown", custom_data={"index": 0}, suppress_errors=True)
            time.sleep(settings["game"]["countdown-duration"])

            # switch leds back
            self.set_leds("making-move")

    def speak(self, text: str):
        global settings

        # initialize tts engine
        tts_engine = pyttsx3.Engine()

        try:
            # load settings file
            with open('settings.json') as json_file:
                settings = json.load(json_file)
        except:
            pass

        # executed every time a word is said if talking animation is enabled
        def onWord(name, location, length):

            # clear other outbound talking motions
            self.serial.reset_output_buffer()
            
            # find word using positioning info
            word = "".join(filter(str.isalpha, text[location:(location + length)])).lower()
            
            # check if word is valid
            if word in arpabet.keys():

                # select the first arpabet sequence for the word
                arpabet_letters = arpabet[word][0]

                prev_angle = 0

                # iterate through arpabet sequence
                for letter in arpabet_letters:

                    # remove numbers from the letter
                    clean_letter = "".join(filter(str.isalpha, letter))

                    # check if letter is in servo positions dictionary
                    if  clean_letter in settings["tts"]["arpabet-servo-positions"].keys():
                        
                        # send positions to servo
                        angle = settings["tts"]["arpabet-servo-positions"][clean_letter]

                        # make sure we aren't sending the exact same data
                        if angle != prev_angle:
                            self.push_data({"data": {"angle-joint3": angle + settings["joint-offsets"]["3"]}}, suppress_errors=True)

                        prev_angle = angle

                        time.sleep(settings["tts"]["arpabet-delay"])

            # close the mouth
            angle = settings["hardware"]["grabber-closed-angle"]
            self.push_data({"data": {"angle-joint3": angle + settings["joint-offsets"]["3"]}}, suppress_errors=True)

        # connect talking animation
        if settings["tts"]["talking-animation"]:
            tts_engine.connect('started-word', onWord)
            tts_engine.connect('finished-utterance', self.serial.reset_output_buffer)

        else:
            tts_engine.disconnect('started-word')
            tts_engine.disconnect('finished-utterance', self.serial.reset_output_buffer)

        # set voice
        voices = tts_engine.getProperty('voices')
        for index in voices:
            if index.name == settings["tts"]["voice"]:
                tts_engine.setProperty('voice', index.id)

        # set volume
        tts_engine.setProperty("volume", settings["tts"]["volume"])

        # set speech rate
        tts_engine.setProperty("rate", settings["tts"]["rate-wpm"])

        tts_engine.say(text)

        tts_engine.runAndWait()

    def get_voices(self):
        # initialize tts engine
        tts_engine = pyttsx3.Engine()

        voices = tts_engine.getProperty('voices')

        voice_names = []

        for index in voices:
            voice_names.append(index.name)

        return voice_names

    # make sure all pieces are in their starting position, keep prompting user until this happens
    def prepare_board(self):
        
        # update connection status
        self.check_connection()

        # check if board is connected
        if self.serial.is_open:
            board_snapshot = self.get_board()
            
            is_ready = True

            for row in board_snapshot.keys():
                for column in board_snapshot[row].keys():
                    if not board_snapshot[row][column] and (sf.get_what_is_on_square(f"{column}{row}") != None):
                        is_ready = False

            if is_ready == False:
                prompt_queue.put((("[app.title]Prepare Board", "", "[app.label]All pieces must be in their", "[app.label]starting position..."), {"Fixed": self.prepare_board, "End Game": lambda *_: self.game_end(do_exit=False)}))

            self.board_ready = is_ready

        else:
            prompt_queue.put((("[app.title]Not Connected", "", "[app.label]Board was disconnected,", "[app.label]chess game cannot be continued..."), {"End Game": lambda *_: self.game_end(do_exit=False)}))

        
    # runs the chess game
    def game_start(self):
        global settings, board_visual, wdl_stats

        # wait until other game threads are finnished
        while self.continue_game:
            time.sleep(1)

        # additional delay
        time.sleep(1)

        self.game_state = "starting"
        self.continue_game = True

        # reset ChatGPT message history
        chatGPT.reset_history()

        # reset stockfish board
        sf.set_fen_position(settings["game"]["starting-fen"])
        board_visual = sf.get_board_visual()
        board_popout_window.update(sf.get_fen_position())

        # make sure all pieces are in their starting position
        self.prepare_board()

        # wait for board preparations to finnish
        while not self.board_ready and self.continue_game:
            time.sleep(1)

        if not self.continue_game:
            self.game_end()

        # used to detect castling
        self.castling_bishop_positions = {"e1g1": "h1f1",
                                        "e1c1": "a1d1",
                                        "e8g8": "h8f8",
                                        "e8c8": "a8d8"}

        # set stockfish elo/skill level
        sf.set_elo_rating(settings["game"]["bot-elo"])

        # home z axis
        self.goto_position(z=0, suppress_errors=True)

        time.sleep(2)
        
        # raise z axis
        self.goto_position(z=settings["board-positions"]["home"]["height"], suppress_errors=True)

        time.sleep(2)

        # goto waiting position
        position = settings["board-positions"]["home"]["position"]
        self.goto_position(x=position[0], y=position[1], grabber="closed", suppress_errors=True)
        
        time.sleep(1)

        self.speak(chatGPT.get_response("The game has just started. You are waiting on your opponent to make a move."))
        
        self.game_waiting()


    def game_waiting(self):
        global board_visual, wdl_stats, best_moves

        self.game_state = "waiting"

        self.castling = (False, [""])
        self.pawn_promotion = (False, [""])
        self.capture = (False, "")

        board_changes = []

        prev_snapshot = self.get_board(suppress_errors=True)

        # update led wdl stats
        wdl_stats = sf.get_wdl_stats()
        self.set_leds("wld-stats", custom_data={"intensity": round(((wdl_stats[0] + (wdl_stats[1] / 2)) * 255) / 1000)}, suppress_errors=True)
        
        moves_shown = False

        best_moves = []

        if settings["game"]["top-move-count"] != 0:

            # save top (n) best moves to determine if an insult should be thrown later on
            for move in sf.get_top_moves(settings["game"]["top-move-count"]):
                best_moves.append(move["Move"])

        while self.continue_game:

            # get board snapshot
            board_snapshot = self.get_board(suppress_errors=True)

            # check if board is valid
            if board_snapshot != None:
                
                # store changes compared to previous snapshot
                for row in board_snapshot.keys():
                    for square in board_snapshot[row].keys():

                        # if the snapshot squares are not the same save the changes
                        if board_snapshot[row][square] != prev_snapshot[row][square]:
                            board_changes.append((f"{square}{row}", board_snapshot[row][square])) # either True or False

                # update previous board snapshot
                prev_snapshot = board_snapshot


                # move input logic ----------------------------------------

                self.capture = (False, "")

                if (len(board_changes) == 3):
                    
                    move1 = [board_changes[0][0], board_changes[2][0]] # first possibility
                    move2 = [board_changes[1][0], board_changes[2][0]] # second possibility
                
                    # test for a capture move
                    if not board_changes[0][1] and not board_changes[1][1] and board_changes[2][1] and ((move1[0] == move1[1]) or (move2[0] == move2[1])):
                        
                        valid_move = False

                        for index in [move1, move2, (move1 + ["q"]), (move2 + ["q"])]:

                            if sf.is_move_correct("".join(index)):

                                valid_move = True

                                self.capture = (True, sf.get_what_is_on_square(index[1]))

                                play_sound.play_json_sound("capture")

                                # check for pawn promotion then enable it
                                if ("PAWN" in str(sf.get_what_is_on_square(index[0]))) and (("1" in index[1]) or ("8" in index[1])):
                                    self.pawn_promotion = (True, index[0:2])

                                    # ask user what they would like to promote to
                                    prompt_queue.put((("[app.title]Pawn Promotion", "", "[app.label]Select promotion type,", "[app.label]then swap out piece."),
                                                    {"♛  Queen": lambda *_: self.pawn_promotion[1].append("q"), "♝  Bishop": lambda *_: self.pawn_promotion[1].append("b"), "♞  Knight": lambda *_: self.pawn_promotion[1].append("n"), "♜  Rook": lambda *_: self.pawn_promotion[1].append("r")}))

                                else:
                                    # make move
                                    sf.make_moves_from_current_position(["".join(index)])
                                    board_visual = sf.get_board_visual()

                                    # update board popout window
                                    board_popout_window.update(sf.get_fen_position(), lastmove="".join(index))
                                
                                    self.game_moving(lastmove="".join(index))

                                board_changes = []
                                break

                        if not valid_move:
                            self.game_invalid()

                    else:
                        self.game_invalid()

                elif (len(board_changes) == 2):

                    move1 = [board_changes[0][0], board_changes[1][0]] # first possibility
                    move2 = [board_changes[1][0], board_changes[0][0]] # second possibility
                    
                    # test if castling is enabled
                    if self.castling[0]:
                        if "".join(move1) == self.castling_bishop_positions["".join(self.castling[1])]:

                            self.castling = (False, [""])

                            self.game_moving(lastmove="".join(index))

                        else:
                            self.game_invalid()

                    # test if pawn promotion is enabled
                    elif self.pawn_promotion[0]:

                        # wait until piece modifier is added
                        if len(self.pawn_promotion[1]) == 3:

                            # make move
                            sf.make_moves_from_current_position(["".join(self.pawn_promotion[1])])

                            # make sure no other moves are being made
                            for index in board_changes:
                                if (index[0] != self.pawn_promotion[1][1]):

                                    self.game_invalid()

                            board_visual = sf.get_board_visual()

                            # update board popout window
                            board_popout_window.update(sf.get_fen_position(), lastmove="".join(self.pawn_promotion[1]))

                            self.pawn_promotion = (False, [""])

                            self.game_moving(lastmove="".join(index))

                        else:
                            self.game_invalid()

                    # test for the precursor to a capture move
                    elif not board_changes[0][1] and not board_changes[1][1]:
                        
                        valid_move = False

                        for index in [move1, move2, (move1 + ["q"]), (move2 + ["q"])]:

                            if sf.is_move_correct("".join(index)) and (str(sf.will_move_be_a_capture("".join(index))) != sf.Capture.NO_CAPTURE):
                                valid_move = True
                                break

                        if not valid_move:
                            self.game_invalid()

                    # test for a normal move
                    elif not board_changes[0][1] and board_changes[1][1]:
                        
                        valid_move = False

                        for index in [move1, (move1 + ["q"])]:
                            if sf.is_move_correct("".join(index)):

                                valid_move = True
                                
                                # check for castling then enable it
                                if ("".join(index) in self.castling_bishop_positions.keys()) and ("KING" in str(sf.get_what_is_on_square(index[0]))):
                                    self.castling = (True, index[0:2])

                                    # make move
                                    sf.make_moves_from_current_position(["".join(index)])
                                    board_visual = sf.get_board_visual()

                                    # update board popout window
                                    board_popout_window.update(sf.get_fen_position(), lastmove="".join(index))

                                # check for pawn promotion then enable it
                                elif ("PAWN" in str(sf.get_what_is_on_square(index[0]))) and (("1" in index[1]) or ("8" in index[1])):
                                    self.pawn_promotion = (True, index[0:2])

                                    # ask user what they would like to promote to
                                    prompt_queue.put((("[app.title]Pawn Promotion", "", "[app.label]Select promotion type,", "[app.label]then swap out piece."),
                                                    {"♛  Queen": lambda *_: self.pawn_promotion[1].append("q"), "♝  Bishop": lambda *_: self.pawn_promotion[1].append("b"), "♞  Knight": lambda *_: self.pawn_promotion[1].append("n"), "♜  Rook": lambda *_: self.pawn_promotion[1].append("r")}))
                                    
                                    self.speak("Select what you would like to promote to on the computer, then swap out the piece.")

                                else:
                                    play_sound.play_json_sound("move")

                                    # make move
                                    sf.make_moves_from_current_position(["".join(index)])
                                    board_visual = sf.get_board_visual()

                                    # update board popout window
                                    board_popout_window.update(sf.get_fen_position(), lastmove="".join(index))

                                    self.game_moving(lastmove="".join(index))


                            # check if piece didn't move position
                            elif index[0] == index[1]:
                                valid_move = True

                                # hide possible moves for that piece
                                board_popout_window.update(sf.get_fen_position())

                                moves_shown = False

                                board_changes = []

                        if not valid_move:
                            self.game_invalid()

                    else:
                        self.game_invalid()


                elif (len(board_changes) == 1) and not board_changes[0][1]:

                    if not moves_shown:
                        # show possible moves on popout window
                        # run it in a seperate thread
                        t = continuous_threading.Thread(board_popout_window.update, args=(sf.get_fen_position(), None, None, board_changes[0][0]))
                        t.start()

                        moves_shown = True

                elif len(board_changes) == 0:
                    pass # do nothing

                else:

                    self.game_invalid()

            # update connection status
            self.check_connection()

            # check if board is still connected
            if not self.serial.is_open:
                self.continue_game = False

                # notify user why game was stopped
                prompt_queue.put((("[app.title]Not Connected", "", "[app.label]Game has been ended,", "[app.label]chess robot not connected..."), {"Ok": None}))



        # execution was terminated close the thread
        self.game_end()

    def game_moving(self, lastmove):
        global settings, board_visual

        try:
            # load settings file
            with open('settings.json') as json_file:
                settings = json.load(json_file)
        except:
            pass 
        
        try:
            # stop the alert sound if playing
            self.check_alert_thread.stop()
        except:
            pass

        # countdown timer to allow player to remove hand from board
        self.set_leds("countdown", custom_data={"index": 0}, suppress_errors=True)
        time.sleep(settings["game"]["countdown-duration"])

        # update leds
        self.set_leds("making-move")

        self.game_state = "moving"

        # use another library to get info about the game
        board = chess.Board(sf.get_fen_position())

        outcome = board.outcome()

        # detect checkmate, stalemate, etc
        if outcome != None:
            
            self.game_outcome(outcome)

        # detect check for bots side
        elif board.is_check():

            king_square = board.king(chess.BLACK)

            # show the king is in check on the board visual popout
            board_popout_window.update(sf.get_fen_position(), check=chess.square_name(king_square))

        self.capture = (False, "")

        # insult the player if they made a bad move
        if not lastmove in best_moves:
            self.speak(chatGPT.get_response(f"Your opponent has just made a bad move from {lastmove}"))

        # generate the best move using stockfish
        sf_move = sf.get_best_move()
            
        #check for capture
        if sf.get_what_is_on_square(sf_move[2:4]) != None:

            self.capture = (True, sf.get_what_is_on_square(sf_move[2:4]))

            self.remove_piece(sf_move[2:4])

        self.make_move(sf_move)
        
        # check for castling
        if (sf_move in self.castling_bishop_positions.keys()) and ("KING" in str(sf.get_what_is_on_square(sf_move[0:2]))):
            
            self.make_move(self.castling_bishop_positions[sf_move])

        # go back to waiting position
        position = settings["board-positions"]["home"]["position"]
        self.goto_position(x=position[0], y=position[1], grabber="closed", suppress_errors=True)

        # check for pawn promotion
        if len(sf_move) == 5:
            self.pawn_promotion = (True, [sf_move[0:2], sf_move[2:4]])
            
            prompt_queue.put((("[app.title]Pawn Promotion", "", "[app.label]Select promotion type,", "[app.label]then swap out piece."),
                {"♛  Queen": lambda *_: self.pawn_promotion[1].append("q"), "♝  Bishop": lambda *_: self.pawn_promotion[1].append("b"), "♞  Knight": lambda *_: self.pawn_promotion[1].append("n"), "♜  Rook": lambda *_: self.pawn_promotion[1].append("r")}))
            
            self.speak("Select what you want my promotion to be on the computer, then swap out the piece.")
            
            # wait until promotion type is specified
            while len(self.pawn_promotion[1]) != 3:

                time.sleep(0.5)

            prev_snapshot = self.get_board()

            board_changes = []

            # wait until piece is swapped out
            while self.pawn_promotion[0] and self.continue_game:
                # get board snapshot
                board_snapshot = self.get_board()

                # check if board is valid
                if board_snapshot != None:
                    
                    # store changes compared to previous snapshot
                    for row in board_snapshot.keys():
                        for square in board_snapshot[row].keys():

                            # if the snapshot squares are not the same save the changes
                            if board_snapshot[row][square] != prev_snapshot[row][square]:
                                board_changes.append((f"{square}{row}", board_snapshot[row][square])) # either True or False

                    if len(board_changes) > 1:
                    
                        # make sure no other moves are being made
                        for index in board_changes:
                            if (index[0] != self.pawn_promotion[1][1]):

                                self.game_invalid()

                        board_changes = []
                        
                        sf_move = "".join(self.pawn_promotion[1])
                        self.pawn_promotion = (False, "")

                    prev_snapshot = board_snapshot


        sf.make_moves_from_current_position([sf_move])

        board_visual = sf.get_board_visual()

        # update board visual popout
        board_popout_window.update(sf.get_fen_position())

        # update board popout window
        board_popout_window.update(sf.get_fen_position(), lastmove=sf_move)

        # play sound effects
        if self.capture[0]:
            play_sound.play_json_sound("capture")
        
        else:
            play_sound.play_json_sound("move")

        # use another library to get info about the game
        board = chess.Board(sf.get_fen_position())

        outcome = board.outcome()

        # detect checkmate, stalemate, etc
        if outcome != None:
            
            self.game_outcome(outcome)

        # detect check for bots side
        elif board.is_check():

            king_square = board.king(chess.WHITE)

            # show the king is in check on the board visual popout
            board_popout_window.update(sf.get_fen_position(), check=chess.square_name(king_square))

            # used to play an alert sound when in check
            self.check_alert_thread = continuous_threading.ContinuousThread(play_sound.play_json_sound, args=("check-alert", True,))
            
            self.check_alert_thread.start()
            
        # switch to waiting for move
        self.game_waiting()


    def game_invalid(self):
        self.game_state = "invalid"

        try:
            # stop the alert sound if playing
            self.check_alert_thread.stop()
        except:
            pass

        try:
            # load settings file
            with open('settings.json') as json_file:
                settings = json.load(json_file)
        except:
            pass 

        # do animations
        self.set_leds("invalid")
        play_sound.play_json_sound("invalid")
        self.speak(chatGPT.get_response("Your opponent has made an invalid move. You are about to clear the board."))

        #----------------------- clear the board

        # home z axis
        self.goto_position(z=0)

        time.sleep(1.5)

        # go to height
        self.goto_position(z=settings["board-positions"]["clear"]["height"], grabber="open")

        time.sleep(1)

        # go through clearing sequence
        for index in settings["board-positions"]["clear"]["sequence"]:
            self.goto_position(x=index[0], y=index[1])
            time.sleep(0.5)

        # go back up again
        self.goto_position(z=settings["board-positions"]["home"]["height"])
        time.sleep(1)

        # goto waiting position
        position = settings["board-positions"]["home"]["position"]
        self.goto_position(x=position[0], y=position[1], grabber="closed", suppress_errors=True)

        self.game_end()

    def game_outcome(self, outcome):
        
        # if white lost the game
        if outcome.winner:
            self.game_state = "win"

            self.set_leds("win")

            play_sound.play_json_sound("win")

            self.speak(chatGPT.get_response("Your opponent put you in check, you lost. Speak 4 sentences."))


        else:
            self.game_state = "lose"

            self.set_leds("lose")

            play_sound.play_json_sound("lose")

            self.speak(chatGPT.get_response("You put your opponent in check, you won. Speak 4 sentences."))

        self.game_end()


    def game_end(self, do_exit:bool = True):
        self.continue_game = False

        if do_exit:
            self.game_state = "inactive"

            self.set_leds("idle")

            exit()
    
