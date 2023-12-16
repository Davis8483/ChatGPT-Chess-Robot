import subprocess
import json
import chess_bot
import webbrowser
import atexit
import time
import platform

try:
    import pyperclip
    import pytermgui as ptg
    import serial
    import serial.tools.list_ports
    import continuous_threading
    from safe_cast import *

except:
    subprocess.run(["pip", "install", "pytermgui==7.3.0", "pyserial", "pyperclip", "continuous-threading", "safe-cast"])

    import pyperclip
    import pytermgui as ptg
    import serial
    import serial.tools.list_ports
    import continuous_threading
    from safe_cast import *

if platform.system() != "Windows":
    ptg.tim.print("[bold red]This program requires a windows machine to run...[/]")
    quit()

# define window manager
window_manager = ptg.WindowManager(framerate=20)

# load settings file
with open('settings.json') as json_file:
    settings = json.load(json_file)

# initialize communication with the chess robot
ser = serial.Serial(timeout=2)

serial_interface = chess_bot.SerialInterface(ser)

# create styles and macros
def _create_aliases():

    ptg.tim.alias("app.text", "#36b6fd")
    ptg.tim.alias("app.label", "bold #ffffff")

    ptg.tim.alias("app.header", "bold @#36b6fd #ffffff")
    ptg.tim.alias("app.header.fill", "@#36b6fd")

    ptg.tim.alias("app.title", "bold underline #36b6fd")

    ptg.tim.alias("app.button.label", "#ffffff")
    ptg.tim.alias("app.button.highlight", "bold inverse app.button.label")

    ptg.tim.alias("app.slider.filled", "bold #36b6fd")
    ptg.tim.alias("app.slider.filled_selected", "bold #ffffff")

    # define gui macros used in the status sidebar
    ptg.tim.define("!connection_status", lambda *_: get_connection_status())
    ptg.tim.define("!game_status", lambda *_: get_game_status())
    ptg.tim.define("!game_visuals", lambda *_: chess_bot.get_board_visual())
    ptg.tim.define("!game_wdl_stats", lambda *_: chess_bot.get_stats_visual())


# set default styles for different widget types
def _configure_widgets():
    """Defines all the global widget configurations.

    Some example lines you could use here:

        ptg.boxes.DOUBLE.set_chars_of(ptg.Window)
        ptg.Splitter.set_char("separator", " ")
        ptg.Button.styles.label = "myapp.button.label"
        ptg.Container.styles.border__corner = "myapp.border"
    """

    ptg.boxes.DOUBLE.set_chars_of(ptg.Window)
    ptg.boxes.ROUNDED.set_chars_of(ptg.Container)

    ptg.Button.styles.label = "app.button.label"
    ptg.Button.styles.highlight = "app.button.highlight"
    ptg.Button.set_char("delimiter", ["[ ", " ]"])

    ptg.Toggle.set_char("delimiter", ["[ ", " ]"])

    ptg.InputField.styles.prompt = "app.label"
    ptg.InputField.styles.value = "app.text"
    ptg.InputField.styles.cursor = "inverse app.text"

    ptg.Slider.styles.filled = "app.slider.filled"
    ptg.Slider.styles.filled_selected__cursor = "app.slider.filled_selected"

    ptg.Label.styles.value = "app.text"

    ptg.Window.styles.border__corner = "#b3b7ba"
    ptg.Container.styles.border__corner = "#36b6fd"

    ptg.Splitter.set_char("separator", "")

# defines ui elements that must retain the same value after a menu page is reloaded
def _define_widgets():
    global xy_step_slider, z_step_slider, connect_toggle

    # menu page
    connect_toggle = ptg.Toggle(("Connect", "Disconnect"),  toggle_connection)

    # jog machine page
    xy_step_slider = ptg.Slider()
    xy_step_slider.value = 0.3

    z_step_slider = ptg.Slider()
    z_step_slider.value = 0.3

# defines the window layout
def _define_layout():
    """Defines the application layout.

    Layouts work based on "slots" within them. Each slot can be given dimensions for
    both width and height. Integer values are interpreted to mean a static width, float
    values will be used to "scale" the relevant terminal dimension, and giving nothing
    will allow PTG to calculate the corrent dimension.
    """

    layout = ptg.Layout()

    # A header slot with a height of 1
    layout.add_slot("Header", height=1)
    layout.add_break()

    # A body slot that will fill the entire width, and the height is remaining
    layout.add_slot("Menu")

    # A slot in the same row as the menu, using the full non-occupied height and
    layout.add_slot("Status", width=0.5)

    return layout

# returns how much the machine should be jogged by in the x, y, or z direction based on slider input
def get_steps(slider: float):
    steps = round(2 ** ((slider.value * 10) - 3), 1)
    return steps

# returns a ui element indicating if the board is connected
def get_connection_status():

    if ser.is_open:
        return "🟢 Connected"
    else:
        return "🔴 Disconnected"
    
# returns a ui element indicating what stage the chess game is in
def get_game_status():

    if ser.is_open:
        if serial_interface.game_state == "inactive":
            return "Idle ⌛"
        
        elif serial_interface.game_state == "starting":
            return "Game Starting 🚩"
        
        elif serial_interface.game_state == "waiting":
            return "Waiting for Move 🕓"
        
        elif serial_interface.game_state == "moving":
            return "Making Move ♙🫲"
        
        elif serial_interface.game_state == "speaking":
            return "Speaking 🔊"
        
        elif serial_interface.game_state == "invalid":
            return "Invalid Move 🚫"
        
        elif serial_interface.game_state == "win":
            return "You Won 🏆"
        
        elif serial_interface.game_state == "lose":
            return "You Lost ❌"
        
        else:
            return serial_interface.game_state

    return "----"

# runs main function of chess bot after connecting to the board hardware
def toggle_connection(state: str):
    global connection_checking_thread, ser, serial_interface
    
    if state == "Disconnect":
        try:
            ser.port = settings["hardware"]["serial-port"]
            ser.baudrate = settings["hardware"]["baud-rate"]

            ser.open()

            time.sleep(0.5)

            connection_checking_thread = continuous_threading.PeriodicThread(3, lambda *_: serial_interface.check_connection())
            connection_checking_thread.start()

            if ser.is_open:
                # push idle led animation to indicate connection success
                serial_interface.set_leds("idle")
        
        except:
            connect_toggle.toggle()
        
            # create an prompt notifying the user
            menu_prompt(("[app.title]Error", "", "[app.label]Failed to connect to chess bot...", "", f"[app.label]Port: [/][app.text]{settings['hardware']['serial-port']}"), {"Edit": (lambda *_: navigate_menu("hardware_settings")), "Ok": None})

    else:

        if ser.is_open:
            # push disconnected led animation
            serial_interface.set_leds("disconnected")

            ser.close()

        try:
            connection_checking_thread.close()
        except:
            pass

# starts the chess game
def new_game():
    global chess_game_thread

    # check if board is connected
    if ser.is_open:

        # if a game is already running, ask user if they want to restart
        if serial_interface.game_state != "inactive":

            menu_prompt(("[app.title]Restart Game?", "", "[app.label]A chess game is in progress,", "[app.label]do you want to restart?"), {"Yes": restart_game, "No": None})
        
        else:
            chess_game_thread = continuous_threading.Thread(serial_interface.game_start)
            chess_game_thread.start()
    else:
        menu_prompt(("[app.title]Not Connected", "", "[app.label]Unable to start game,", "[app.label]chess robot not connected...", "", connect_toggle), {"Ok": None})

# restarts the chess game
def restart_game():
    global chess_game_thread

    serial_interface.game_end(do_exit=False)

    chess_game_thread = continuous_threading.Thread(serial_interface.game_start)
    chess_game_thread.start()

# stops the chess game
def end_game():
    if serial_interface.game_state != "inactive":
        menu_prompt(("[app.title]End Game?",), {"Yes": lambda *_: serial_interface.game_end(do_exit=False), "No": None})
    
    else:
        menu_prompt(("[app.title]Cannot End", "", "[app.label]You cannot end a non-existent", "[app.label]chess game..."), {"Ok": None})

def popout_board():

    if chess_bot.board_popout_window.is_open:
        menu_prompt(("[app.title]Can't Open Window", "", "[app.label]A board pop-out window,", "[app.label]already exists..."), {"Ok": None})

    else:

        chess_bot.board_popout_window.show()

    
# creates a custom alert menu
# example call: menu_prompt(("[app.title]Test Prompt", ""), {"Ok": my_function})
prompt_alerts = []
def menu_prompt(text: tuple, buttons: dict, _close=False, _function=None):
    global prompt_alerts

    if _close:
        prompt_alerts[len(prompt_alerts) - 1].close(animate=False)
        prompt_alerts.pop()

        if _function is not None:
            try:
                _function()
            except Exception as e:
                menu_prompt(
                    ("[app.title]Error", "", "[app.label]Failed to execute menu prompt function,", f"[app.label][{e}]"), 
                    {"Ok": None}
                )
        return

    prompt = text

    for index in buttons.keys():
        if buttons[index] is None:
            new_button = ptg.Button(
                index,
                lambda *_: menu_prompt(text, buttons, _close=True)
            )
        else:
            new_button = ptg.Button(
                index,
                lambda *_, f=buttons[index]: menu_prompt(text, buttons, _close=True, _function=f)
            )

        prompt += ("", new_button)

    prompt_alerts.append(window_manager.alert(*prompt, ""))


# runs in a seperate thread, checks to see if chess_bot.py has prompts available and then displays it
def get_prompts():
    if not chess_bot.prompt_queue.empty():
        try:
            menu_prompt(*chess_bot.prompt_queue.get())
        except:
            menu_prompt(("[app.title]Error", "", "[app.label]Failed to create menu prompt..."), {"Ok": None})

# runs in a seperate thread, used by the gui to live update joint positions while editing
prev_joint_offsets = {"hardware":{}}
def update_joint_offset(joint_num, value):

    joint_offsets = {"joint-offsets": {}}
    joint_offsets["joint-offsets"][str(joint_num)] = value

    merge_dicts(settings, joint_offsets)

    # save settings to settings.json
    with open("settings.json", "w") as json_file:
        json_file.write(json.dumps(settings, indent=2))

    serial_interface.goto_position(x=chess_bot.pos_x, y=chess_bot.pos_y, grabber="calibrate", retract=False)

# runs in a separate thread, used to update the matrix on the sensor test page
def update_sensor_matrix(matrix):
    letter_columns = ["a", "b", "c", "d", "e", "f", "g", "h"]

    try:
        board = serial_interface.get_board()

        # iterate through the entire board dictionary
        for row in reversed(range(8)):
            for column in range(8):

                # we are using 3x3 pixels as one square
                for i in range(3):
                    for j in range(3):
                        y = str((7 - row) * 3 + i)
                        x = str(column * 3 + j)

                        if board[str(row + 1)][letter_columns[column]]:
                            matrix[(7 - row) * 3 + i, column * 3 + j] = "green"
                        else:
                            matrix[(7 - row) * 3 + i, column * 3 + j] = "red"

        # update the matrix
        matrix.build()
        
    except:
        pass

# fills the entirety of a ptg matrix to the desired color
def fill_matrix(matrix, color):

    for y in range(matrix.rows):
        for x in range(matrix.columns):
            matrix[y, x] = color
    
    matrix.build()

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

# compares dictionary stored values, returns false if stored values are different
def compare_dicts(large_dict: dict, smaller_dict: dict):
    for key, value in smaller_dict.items():
        if key in large_dict:
            if isinstance(value, dict) and isinstance(large_dict[key], dict):
                if not compare_dicts(large_dict[key], value):
                    return False
            elif value != large_dict[key]:
                return False
        else:
            return False
    return True

# creates an alert window prompting to save changes
def save_prompt(command: object, save: dict, _dosave=None):
    global save_alert, settings

    # check if a prompt needs to be created
    if (_dosave == None) and not compare_dicts(settings, save):

        save_alert = window_manager.alert(
            "[app.title]Save Changes?",
            "",
            ["Yes", lambda *_:save_prompt(command, save, _dosave=True)],
            "",
            ["No", lambda *_:save_prompt(command, save, _dosave=False)],
            "",
        )

    elif _dosave:
        # update settings dictionary using the save dictionary
        merge_dicts(settings, save)

        # save settings to settings.json
        with open("settings.json", "w") as json_file:
            json_file.write(json.dumps(settings, indent=2))

        # close save prompt and navigate to specified window
        save_prompt(command, save, _dosave=False)

    else:
        # close save prompt and navigate to specified window
        try:
            save_alert.close(animate=False)
        except:
            pass
        
        # execute the set command
        command()

# switches which menu page is displayed
def navigate_menu(page: str, *args):
    global menu, settings, joint_1_offset_slider, joint_2_offset_slider, joint_3_offset_slider, sensor_matrix_thread, brightness_slider

    # open new widow based on preset
    if page == "main":
        new_menu = ptg.Window(
            "[app.title]Menu",
            "",
            ["Settings »", lambda *_: navigate_menu("settings")],
            "",
            ["Calibrate »", lambda *_: navigate_menu("calibrate")],
            "",
            ["Jog Machine »", lambda *_: navigate_menu("jog")],
            "",
            ["New Game", lambda *_: new_game()],
            "",
            ["End Game", lambda *_: end_game()],
            "",
            ["Pop-out Board", lambda *_: popout_board()],
            "",
            connect_toggle,
            vertical_align=0,
            is_static=True,
            is_noresize=True,
            title="Menu"
        )

    if page == "settings":

        # make sure a game isn't in progress
        if serial_interface.game_state == "inactive":
            pass

        else:
            menu_prompt(("[app.title]Game Running", "", "[app.label]Unable to access page,", "[app.label]a chess game is in progress..."), {"Ok": None})
            return
        
        new_menu = ptg.Window(
            "[app.title]Settings",
            "",
            ["ChatGPT »", lambda *_: navigate_menu("gpt_settings")],
            "",
            ["Hardware »", lambda *_: navigate_menu("hardware_settings")],
            "",
            ["LED Strip »", lambda *_: navigate_menu("led_settings")],
            "",
            ["Game »", lambda *_: navigate_menu("game_settings")],
            "",
            ["TTS »", lambda *_: navigate_menu("tts_settings")],
            "",
            ["Open File", lambda *_: webbrowser.open("settings.json")],
            "",
            ["« Back", lambda *_: navigate_menu("main")],
            is_static=True,
            is_noresize=True,
            vertical_align=0,
            title="Menu » Settings"
        )

    if page == "gpt_settings":
        api_key_input = ptg.InputField(
            value=settings["gpt"]["api-key"], prompt="API key: "
        )

        prompt_input = ptg.InputField(
            value=settings["gpt"]["prompt"],
            prompt="Prompt: "
        )
        
        temperature_slider = ptg.Slider()
        temperature_slider.value = settings["gpt"]["temperature"] / 2
        ptg.tim.define("!temperature", lambda *_: str(round((temperature_slider.value * 2), 1)))

        presence_penalty_slider = ptg.Slider()
        presence_penalty_slider.value = (settings["gpt"]["presence-penalty"] / 4) + 0.5
        ptg.tim.define("!presence-penalty", lambda *_: str(round(((presence_penalty_slider.value - 0.5) * 4), 1)))

        frequency_penalty_slider = ptg.Slider()
        frequency_penalty_slider.value = (settings["gpt"]["frequency-penalty"] / 4) + 0.5
        ptg.tim.define("!frequency-penalty", lambda *_: str(round(((frequency_penalty_slider.value - 0.5) * 4), 1)))

        request_timeout_input = ptg.InputField(
            value=str(settings["gpt"]["request-timeout"]), 
            prompt="Request Timeout (sec): "
        )

        new_menu = ptg.Window(
            "[app.title]ChatGPT Settings",
            "",
            ptg.Container(
                api_key_input,
                "",
                ["Get Key", lambda *_: webbrowser.open_new_tab('https://platform.openai.com/account/api-keys')],
                "",
                ["Paste Key", lambda *_: api_key_input.insert_text(pyperclip.paste())],
                "",
                ptg.Splitter(
                    ptg.Label("[app.label]Temperature:", parent_align=0),
                    ptg.Label("[!temperature] [/!]",parent_align=2)
                ),
                temperature_slider,
                "",
                ptg.Splitter(
                    ptg.Label("[app.label]Presence Penalty:", parent_align=0),
                    ptg.Label("[!presence-penalty] [/!]",parent_align=2)
                ),
                presence_penalty_slider,
                "",
                ptg.Splitter(
                    ptg.Label("[app.label]Frequency Penalty:", parent_align=0),
                    ptg.Label("[!frequency-penalty] [/!]",parent_align=2)
                ),
                frequency_penalty_slider,
                "",
                request_timeout_input,
                "",
                prompt_input,
                relative_width=0.6
            ),
            "",
            ["« Back", lambda *_: save_prompt(lambda *_: navigate_menu("settings"),
                                              save={
                                                  "gpt": {
                                                      "api-key": safe_str(api_key_input.value, ""),
                                                      "prompt": safe_str(prompt_input.value, ""),
                                                      "temperature": round((temperature_slider.value * 2), 1),
                                                      "presence-penalty": round(((presence_penalty_slider.value - 0.5) * 4), 1),
                                                      "frequency-penalty": round(((frequency_penalty_slider.value - 0.5) * 4), 1),
                                                      "request-timeout": safe_float(request_timeout_input.value, 1, 10)
                                                      }})],
            is_static=True,
            is_noresize=True,
            vertical_align=0,
            title="Menu » Settings » ChatGPT"
        )

    if page == "hardware_settings":
        serial_port_input = ptg.InputField(
            value=str(settings["hardware"]["serial-port"]),
            prompt="Serial Port: "
        )
        
        baud_rate_input = ptg.InputField(
            value=str(settings["hardware"]["baud-rate"]),
            prompt="Baud Rate: "
        )

        arm1_length_input = ptg.InputField(
            value=str(settings["hardware"]["length-arm-1"]),
            rompt="Arm 1 Length (mm): "
        )

        arm2_length_input = ptg.InputField(
            value=str(settings["hardware"]["length-arm-2"]),
            prompt="Arm 2 Length (mm): "
        )

        grabber_open_input = ptg.InputField(
            value=str(settings["hardware"]["grabber-open-angle"]),
            prompt="Grabber Open Angle: "
        )

        grabber_closed_input = ptg.InputField(
            value=str(settings["hardware"]["grabber-closed-angle"]),
            prompt="Grabber Closed Angle: "
        )

        servo_speed_input = ptg.InputField(
            value=str(settings["hardware"]["servo-speed-deg/sec"]),
            prompt="Servo Speed (deg/sec): "
        )

        retraction_angle_input = ptg.InputField(
            value=str(settings["hardware"]["retraction-angle"]),
            prompt="Arm Retract Angle: "
        )

        ports = ""
        for port, desc, hwid in sorted(serial.tools.list_ports.comports()):
            ports += f"\n[app.label]{port}:[/][app.text] {desc} [{hwid}]\n"
    
        if ports == "":
            ports = "\nNone\n"

        new_menu = ptg.Window(
            "[app.title]Hardware Settings",
            "",
            ptg.Container(
                serial_port_input,
                "",
                baud_rate_input,
                "",
                ptg.Collapsible(
                    "Available Ports",
                    ptg.Container(
                    ports
                    )
                ),
                relative_width=0.6
            ),
            "",
            ptg.Container(
                arm1_length_input,
                "",
                arm2_length_input,
                "",
                grabber_open_input,
                "",
                grabber_closed_input,
                "",
                servo_speed_input,
                "",
                retraction_angle_input,
                relative_width=0.6
            ),
            "",
            ["« Back", lambda *_: save_prompt(lambda *_: navigate_menu("settings"),
                                              save={"hardware": {
                                                    "serial-port": safe_str(serial_port_input.value, ""),
                                                    "baud-rate": safe_int(baud_rate_input.value, 0),
                                                    "length-arm-1": safe_float(arm1_length_input.value, 2, 10),
                                                    "length-arm-2": safe_float(arm2_length_input.value, 2, 10),
                                                    "grabber-open-angle": safe_int(grabber_open_input.value, 90),
                                                    "grabber-closed-angle": safe_int(grabber_closed_input.value, 90),
                                                    "servo-speed-deg/sec": safe_int(servo_speed_input.value, 150),
                                                    "retraction-angle": safe_int(retraction_angle_input.value, 130)
                                                    }})],
            is_static=True,
            is_noresize=True,
            vertical_align=0,
            title="Menu » Settings » Hardware"
        )

    if page == "led_settings":

        brightness_slider = ptg.Slider()
        brightness_slider.value = settings["led-strip"]["brightness"] / 255
        ptg.tim.define("!brightness", lambda *_: str(round(brightness_slider.value * 255)))

        macro_buttons = []
        for macro in settings["led-strip"]["macros"].keys():
            
            macro_buttons.append([f"{settings['led-strip']['macros'][macro]['label']} »", lambda x, led_macro=macro: save_prompt(lambda *_: navigate_menu("led_macro_settings", led_macro),
                                              save={"led-strip": {
                                                  "brightness": round(brightness_slider.value * 255)
                                                  }})])
            macro_buttons.append("")

        # create the page
        new_menu = ptg.Window(
            "[app.title]LED Settings",
            "",
            ptg.Container(
                ptg.Splitter(
                    ptg.Label("[app.label]Brightness:", parent_align=0),
                    ptg.Label("[!brightness] [/!]",parent_align=2)
                ),
                brightness_slider,
                "",
                ["Preview", lambda *_: serial_interface.push_data({"data": {
                                                                    "leds": {
                                                                        "brightness": round(brightness_slider.value * 255)}}})],
                relative_width=0.6
            ),
            "",
            *macro_buttons,
            ["« Back", lambda *_: save_prompt(lambda *_: navigate_menu("settings"),
                                              save={"led-strip": {
                                                  "brightness": round(brightness_slider.value * 255)
                                                  }})],
            is_static=True,
            is_noresize=True,
            vertical_align=0,
            title="Menu » Settings » LED Strip"
        )

    if page == "led_macro_settings":
        
        effect_input = ptg.InputField(value=settings["led-strip"]["macros"][args[0]]["effect"],
                                       prompt="Effect: ")

        speed_slider = ptg.Slider()
        speed_slider.value = (settings["led-strip"]["macros"][args[0]]["speed"] / 255)
        ptg.tim.define("!effect_speed", lambda *_: str(round(speed_slider.value * 255)))

        intensity_slider = ptg.Slider()
        intensity_slider.value = (settings["led-strip"]["macros"][args[0]]["intensity"] / 255)
        ptg.tim.define("!effect_intensity", lambda *_: str(round(intensity_slider.value * 255)))

        reverse_toggle = ptg.Toggle(("Reversed: True", "Reversed: False"))
        if not settings["led-strip"]["macros"][args[0]]["reversed"]:
            reverse_toggle.toggle()

        pallet1_matrix = ptg.PixelMatrix(4, 3, default=f"{settings['led-strip']['macros'][args[0]]['pallet']['1'][0]};{settings['led-strip']['macros'][args[0]]['pallet']['1'][1]};{settings['led-strip']['macros'][args[0]]['pallet']['1'][2]}")
        
        pallet2_matrix = ptg.PixelMatrix(4, 3, default=f"{settings['led-strip']['macros'][args[0]]['pallet']['2'][0]};{settings['led-strip']['macros'][args[0]]['pallet']['2'][1]};{settings['led-strip']['macros'][args[0]]['pallet']['2'][2]}")

        pallet1_red_slider = ptg.Slider()
        pallet1_red_slider.value = (settings["led-strip"]["macros"][args[0]]["pallet"]["1"][0] / 255)
        pallet1_red_slider.styles.unfilled = "80;0;0"
        pallet1_red_slider.styles.filled = "255;0;0"
        ptg.tim.define("!pallet_1r", lambda *_: str(round(pallet1_red_slider.value * 255)))

        pallet1_green_slider = ptg.Slider()
        pallet1_green_slider.value = (settings["led-strip"]["macros"][args[0]]["pallet"]["1"][1] / 255)
        pallet1_green_slider.styles.unfilled = "0;80;0"
        pallet1_green_slider.styles.filled = "0;255;0"
        ptg.tim.define("!pallet_1g", lambda *_: str(round(pallet1_green_slider.value * 255)))

        pallet1_blue_slider = ptg.Slider()
        pallet1_blue_slider.value = (settings["led-strip"]["macros"][args[0]]["pallet"]["1"][2] / 255)
        pallet1_blue_slider.styles.unfilled = "0;0;80"
        pallet1_blue_slider.styles.filled = "0;0;255"
        ptg.tim.define("!pallet_1b", lambda *_: str(round(pallet1_blue_slider.value * 255)))

        pallet2_red_slider = ptg.Slider()
        pallet2_red_slider.value = (settings["led-strip"]["macros"][args[0]]["pallet"]["2"][0] / 255)
        pallet2_red_slider.styles.unfilled = "80;0;0"
        pallet2_red_slider.styles.filled = "255;0;0"
        ptg.tim.define("!pallet_2r", lambda *_: str(round(pallet2_red_slider.value * 255)))

        pallet2_green_slider = ptg.Slider()
        pallet2_green_slider.value = (settings["led-strip"]["macros"][args[0]]["pallet"]["2"][1] / 255)
        pallet2_green_slider.styles.unfilled = "0;80;0"
        pallet2_green_slider.styles.filled = "0;255;0"
        ptg.tim.define("!pallet_2g", lambda *_: str(round(pallet2_green_slider.value * 255)))

        pallet2_blue_slider = ptg.Slider()
        pallet2_blue_slider.value = (settings["led-strip"]["macros"][args[0]]["pallet"]["2"][2] / 255)
        pallet2_blue_slider.styles.unfilled = "0;0;80"
        pallet2_blue_slider.styles.filled = "0;0;255"
        ptg.tim.define("!pallet_2b", lambda *_: str(round(pallet2_blue_slider.value * 255)))
        
        # when sliders are changed update the color matrix
        update_matrix1 = lambda *_: fill_matrix(pallet1_matrix, f"{round(pallet1_red_slider.value * 255)};{round(pallet1_green_slider.value * 255)};{round(pallet1_blue_slider.value * 255)}")
        update_matrix2 = lambda *_: fill_matrix(pallet2_matrix, f"{round(pallet2_red_slider.value * 255)};{round(pallet2_green_slider.value * 255)};{round(pallet2_blue_slider.value * 255)}")

        pallet1_red_slider.onchange = update_matrix1
        pallet1_green_slider.onchange = update_matrix1
        pallet1_blue_slider.onchange = update_matrix1

        pallet2_red_slider.onchange = update_matrix2
        pallet2_green_slider.onchange = update_matrix2
        pallet2_blue_slider.onchange = update_matrix2


        # create the text list of led effects
        effects = ""
        if ser.is_open:
            for index in sorted(serial_interface.get_effects()):
                effects += f"\n{index}\n"
        
            if effects == "":
                effects = "\nNone\n"

        else:
            effects = "\nNot Connected\n"

        # create the page
        new_menu = ptg.Window(
            f"[app.title]{settings['led-strip']['macros'][args[0]]['label']}",
            "",
            ptg.Container(
                effect_input,
                "",
                ptg.Collapsible(
                    "Available Effects",
                    ptg.Container(
                        effects
                    )
                ),
                "",
                reverse_toggle,
                "",
                ptg.Splitter(
                    ptg.Label("[app.label]Speed:", parent_align=0),
                    ptg.Label("[!effect_speed] [/!]",parent_align=2)
                ),
                speed_slider,
                "",
                ptg.Splitter(
                    ptg.Label("[app.label]Intensity:", parent_align=0),
                    ptg.Label("[!effect_intensity] [/!]",parent_align=2)
                ),
                intensity_slider,
                "",
                ptg.Splitter(
                    ptg.Label("[app.label]Color 1:", parent_align=0),
                    ptg.Label("([!pallet_1r] [/!], [!pallet_1g] [/!], [!pallet_1b] [/!])",parent_align=2)
                ),
                ptg.Splitter(
                    pallet1_matrix,
                    ptg.Container(
                        pallet1_red_slider,
                        pallet1_green_slider,
                        pallet1_blue_slider,
                        box="EMPTY"
                    ),
                ),
                "",
                ptg.Splitter(
                    ptg.Label("[app.label]Color 2:", parent_align=0),
                    ptg.Label("([!pallet_2r] [/!], [!pallet_2g] [/!], [!pallet_2b] [/!])",parent_align=2)
                ),
                ptg.Splitter(
                    pallet2_matrix,
                    ptg.Container(
                        pallet2_red_slider,
                        pallet2_green_slider,
                        pallet2_blue_slider,
                        box="EMPTY"
                    ),
                ),
                "",
                ["Preview", lambda *_: serial_interface.push_data({"data": {
                                                                    "leds": {
                                                                        "effect": safe_str(effect_input.value, "blink"),
                                                                        "speed": round(speed_slider.value * 255),
                                                                        "intensity": round(intensity_slider.value * 255),
                                                                        "reversed": reverse_toggle.checked,
                                                                        "pallet":{
                                                                            "1": [
                                                                                round(pallet1_red_slider.value * 255),
                                                                                round(pallet1_green_slider.value * 255),
                                                                                round(pallet1_blue_slider.value * 255)
                                                                            ],
                                                                            "2": [
                                                                                round(pallet2_red_slider.value * 255),
                                                                                round(pallet2_green_slider.value * 255),
                                                                                round(pallet2_blue_slider.value * 255)
                                                                            ]
                                                                        }}}})],
                relative_width = 0.6
            ),
            "",
            ["« Back", lambda *_: save_prompt(lambda *_: navigate_menu("led_settings"),
                                              save={"led-strip":{
                                                    "macros": {
                                                        args[0]:{
                                                            "effect": safe_str(effect_input.value, "blink"),
                                                            "speed": round(speed_slider.value * 255),
                                                            "intensity": round(intensity_slider.value * 255),
                                                            "reversed": reverse_toggle.checked,
                                                            "pallet":{
                                                                "1": [
                                                                    round(pallet1_red_slider.value * 255),
                                                                    round(pallet1_green_slider.value * 255),
                                                                    round(pallet1_blue_slider.value * 255)
                                                                ],
                                                                "2": [
                                                                    round(pallet2_red_slider.value * 255),
                                                                    round(pallet2_green_slider.value * 255),
                                                                    round(pallet2_blue_slider.value * 255)
                                                                ]
                                                            }}}}})],
            is_static=True,
            is_noresize=True,
            vertical_align=0,
            title=f"Menu » Settings » LED Strip » {args[0]}"
        )

    if page == "game_settings":

        countdown_duration_input = ptg.InputField(
            value=str(settings["game"]["countdown-duration"]),
            prompt="Countdown Duration: "
        )

        bot_elo_slider = ptg.Slider()
        bot_elo_slider.value = (settings["game"]["bot-elo"] / 3000)
        ptg.tim.define("!bot-elo", lambda *_: str(round(bot_elo_slider.value * 3000)))

        top_move_count_slider = ptg.Slider()
        top_move_count_slider.value = (settings["game"]["top-move-count"] / 10)
        ptg.tim.define("!top_move_count", lambda *_: str(round(top_move_count_slider.value * 10)))

        starting_fen_input = ptg.InputField(
            value=str(settings["game"]["starting-fen"]),
            prompt="Starting Fen: "
        )

        new_menu = ptg.Window(
            "[app.title]Game Settings",
            "",
            ptg.Container(
                countdown_duration_input,
                "",
                ptg.Splitter(
                    ptg.Label("[app.label]Bot Elo:", parent_align=0),
                    ptg.Label("[!bot-elo] [/!]",parent_align=2)
                ),
                bot_elo_slider,
                "",
                ptg.Splitter(
                    ptg.Label("[app.label]Top Move Count Before Insult:", parent_align=0),
                    ptg.Label("[!top_move_count] [/!]",parent_align=2)
                ),
                top_move_count_slider,
                "",
                starting_fen_input,
                "",
                ["Paste Fen", lambda *_: starting_fen_input.insert_text(pyperclip.paste())],
                "",

                relative_width=0.6
            ),
            "",
            ["« Back", lambda *_: save_prompt(lambda *_: navigate_menu("settings"),
                                              save={
                                                  "game": {
                                                        "countdown-duration": safe_float(countdown_duration_input.value, 1, 5),
                                                        "bot-elo": round(bot_elo_slider.value * 3000),
                                                        "starting-fen": safe_str(starting_fen_input.value, "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w"),
                                                        "top-move-count": safe_int(top_move_count_slider.value * 10)
                                                  }
                                              })],
            is_static=True,
            is_noresize=True,
            vertical_align=0,
            title="Menu » Settings » Game"
        )

    if page == "tts_settings":

        voice_input = ptg.InputField(
            value=settings["tts"]["voice"],
            prompt="Voice: "
        )

        voices = ""
        for voice in serial_interface.get_voices():
            voices += f"\n[app.label]{voice}\n"
    
        if voices == "":
            voices = "\nNone\n"

        tts_volume_slider = ptg.Slider()
        tts_volume_slider.value = settings["tts"]["volume"]
        ptg.tim.define("!tts-volume", lambda *_: str(round(tts_volume_slider.value, 1)))

        speech_rate_input = ptg.InputField(
            value=str(settings["tts"]["rate-wpm"]),
            prompt="Rate (WPM): "
        )

        speaking_animation_toggle = ptg.Toggle(("Animation: True", "Animation: False"))
        if not settings["tts"]["talking-animation"]:
            speaking_animation_toggle.toggle()

        new_menu = ptg.Window(
            "[app.title]TTS Settings",
            "",
            ptg.Container(
                voice_input,
                "",
                ptg.Collapsible(
                    "Available Voices",
                    ptg.Container(
                        voices
                    )
                ),
                "",
                ptg.Splitter(
                    ptg.Label("[app.label]Volume:", parent_align=0),
                    ptg.Label("[!tts-volume] [/!]",parent_align=2)
                ),
                tts_volume_slider,
                "",
                speech_rate_input,
                "",
                speaking_animation_toggle,
                "",
                relative_width=0.6
            ),
            "",
            ["« Back", lambda *_: save_prompt(lambda *_: navigate_menu("settings"),
                                              save={
                                                  "tts": {
                                                      "voice": safe_str(voice_input.value),
                                                      "volume": round(tts_volume_slider.value, 1),
                                                      "rate-wpm": safe_int(speech_rate_input.value, 130),
                                                      "talking-animation": speaking_animation_toggle.checked
                                                  }
                                              })],
            is_static=True,
            is_noresize=True,
            vertical_align=0,
            title="Menu » Settings » TTS"
        )


    if page == "jog":
        
        # make sure a game isn't in progress
        if serial_interface.game_state == "inactive":
            pass

        else:
            menu_prompt(("[app.title]Game Running", "", "[app.label]Unable to access page,", "[app.label]a chess game is in progress..."), {"Ok": None})
            return
        
        # check to see if the hardware is connected
        if ser.is_open:
            pass

        else:
            menu_prompt(("[app.title]Not Connected", "", "[app.label]Unable to access page,", "[app.label]chess robot not connected...", "", connect_toggle), {"Ok": None})
            return

        x_input = ptg.InputField(value="0", prompt="X: ")
        y_input = ptg.InputField(value="0", prompt="Y: ")

        # define macros used in this page
        ptg.tim.define("!steps_z", lambda *_: str(get_steps(z_step_slider)))
        ptg.tim.define("!steps_xy", lambda *_: str(get_steps(xy_step_slider)))
        ptg.tim.define("!pos_x", lambda *_: str(round(chess_bot.pos_x, 1)))
        ptg.tim.define("!pos_y", lambda *_: str(round(chess_bot.pos_y, 1)))
        ptg.tim.define("!pos_z", lambda *_: str(round(chess_bot.pos_z, 1)))
        ptg.tim.define("!grabber_state", lambda *_: chess_bot.grabber_state)

        new_menu = ptg.Window(
            "[app.title]Jog Machine",
            "",
            ptg.Container(
                ptg.Splitter(
                    ptg.Label("[app.label]Jog X/Y:", parent_align=0),
                    ptg.Label("([!pos_x] [/!], [!pos_y] [/!]) mm",
                              parent_align=2)
                ),
                ptg.KeyboardButton("w ↑", lambda *_: serial_interface.goto_position(y=(chess_bot.pos_y + get_steps(xy_step_slider)), retract=False), bound="w"),
                ptg.KeyboardButton("a ←", lambda *_: serial_interface.goto_position(x=(chess_bot.pos_x - get_steps(xy_step_slider)), retract=False), bound="a"),
                ptg.KeyboardButton("s ↓", lambda *_: serial_interface.goto_position(y=(chess_bot.pos_y - get_steps(xy_step_slider)), retract=False), bound="s"),
                ptg.KeyboardButton("d →", lambda *_: serial_interface.goto_position(x=(chess_bot.pos_x + get_steps(xy_step_slider)), retract=False), bound="d"),
                "",
                ptg.Splitter(
                    ptg.Label("[app.label]Step:", parent_align=0),
                    ptg.Label("[!steps_xy] [/!] mm", parent_align=2)
                ),
                xy_step_slider,
                "",
                x_input,
                y_input,
                ["GoTo", lambda *_: serial_interface.goto_position(x=safe_int(x_input.value, None), y=safe_int(y_input.value, None))],
                relative_width=0.6
            ),
            "",
            ptg.Container(
                ptg.Splitter(
                    ptg.Label("[app.label]Jog Z:", parent_align=0),
                    ptg.Label("[!pos_z] [/!] mm", parent_align=2)
                ),
                ptg.KeyboardButton("e Up", lambda *_: serial_interface.goto_position(z=(chess_bot.pos_z + get_steps(z_step_slider))), bound="e"),
                ptg.KeyboardButton("q Down", lambda *_: serial_interface.goto_position(z=(chess_bot.pos_z - get_steps(z_step_slider))), bound="q"),
                ptg.Button("Home", lambda *_: serial_interface.goto_position(z=0)),
                "",
                ptg.Splitter(
                    ptg.Label("[app.label]Step:", parent_align=0),
                    ptg.Label("[!steps_z] [/!] mm", parent_align=2)
                ),
                z_step_slider,
                relative_width=0.6
            ),
            "",
            ptg.Container(
                ptg.Splitter(
                    ptg.Label("[app.label]Grabber State:", parent_align=0),
                    ptg.Label("[!grabber_state] [/!]", parent_align=2),
                ),
                ptg.KeyboardButton(
                    "r Open", lambda *_: serial_interface.goto_position(grabber="open"), bound="r"),
                ptg.KeyboardButton(
                    "f Close", lambda *_: serial_interface.goto_position(grabber="closed"), bound="f"),
                relative_width=0.6
            ),
            "",
            ["« Back", lambda *_: navigate_menu("main")],
            is_static=True,
            is_noresize=True,
            vertical_align=0,
            horizontal_align=0,
            title="Menu » Jog Machine"
        )
    
    if page == "calibrate":

        # check to see if the hardware is connected

        if ser.is_open:
            pass

        else:
            menu_prompt(("[app.title]Not Connected", "", "[app.label]Unable to access page,", "[app.label]chess robot not connected...", "", connect_toggle), {"Ok": None})
            return

        new_menu = ptg.Window(
            "[app.title]Calibrate",
            "",
            ["Sensor Test »", lambda *_: navigate_menu("sensor_test")],
            "",
            ["Joint Offsets »", lambda *_: navigate_menu("joint_offsets")],
            "",
            ["Speak Message »", lambda *_: navigate_menu("speak_message")],
            "",
            ["« Back", lambda *_: navigate_menu("main")],
            is_static=True,
            is_noresie=True,
            vertical_align=0,
            horizontal_align=0,
            title="Menu » Calibrate"
        )

    if page == "sensor_test":

        matrix = ptg.PixelMatrix(24, 24, default="red")

        sensor_matrix_thread = continuous_threading.PeriodicThread(0.1, lambda *_: update_sensor_matrix(matrix))
        sensor_matrix_thread.start()

        new_menu = ptg.Window(
            "[app.title]Sensor Test",
            "",
            ptg.Container(
                matrix,
                relative_width=0
            ),
            "",
            ["« Back", lambda *_: navigate_menu("calibrate")],
            is_static=True,
            is_noresie=True,
            vertical_align=0,
            horizontal_align=0,
            title="Menu » Calibrate » Sensor Test"
        )

    else:
        try:
            sensor_matrix_thread.close()
        except:
            pass

    if page == "joint_offsets":

        joint_1_offset_slider = ptg.Slider()
        joint_1_offset_slider.value = round((round(settings["joint-offsets"]["1"]) / 20) + 0.5, 1)
        joint_1_offset_slider.onchange = lambda *_: update_joint_offset(1, round((joint_1_offset_slider.value - 0.5) * 20))
        ptg.tim.define("!offset_joint1", lambda *_: str(round((joint_1_offset_slider.value - 0.5) * 20)))

        joint_2_offset_slider = ptg.Slider()
        joint_2_offset_slider.value = round((round(settings["joint-offsets"]["2"]) / 20) + 0.5, 1)
        joint_2_offset_slider.onchange = lambda *_: update_joint_offset(2, round((joint_2_offset_slider.value - 0.5) * 20))
        ptg.tim.define("!offset_joint2", lambda *_: str(round((joint_2_offset_slider.value - 0.5) * 20)))

        joint_3_offset_slider = ptg.Slider()
        joint_3_offset_slider.value = round((round(settings["joint-offsets"]["3"]) / 20) + 0.5, 1)
        joint_3_offset_slider.onchange = lambda *_: update_joint_offset(3, round((joint_3_offset_slider.value - 0.5) * 20))
        ptg.tim.define("!offset_joint3", lambda *_: str(round((joint_3_offset_slider.value - 0.5) * 20)))

        new_menu = ptg.Window(
            "[app.title]Joint Offsets",
            "",
            ptg.Container(
                ptg.Splitter(
                    ptg.Label("[app.label]Joint 1 Offset:", parent_align=0),
                    ptg.Label("[!offset_joint1] [/!]°", parent_align=2)
                ),
                joint_1_offset_slider,
                "",
                ptg.Splitter(
                    ptg.Label("[app.label]Joint 2 Offset:", parent_align=0),
                    ptg.Label("[!offset_joint2] [/!]°", parent_align=2)
                ),
                joint_2_offset_slider,
                "",
                ptg.Splitter(
                    ptg.Label("[app.label]Grabber Offset:", parent_align=0),
                    ptg.Label("[!offset_joint3] [/!]°", parent_align=2)
                ),
                joint_3_offset_slider,
                "",
                ["Right Angle Joints", lambda *_: serial_interface.goto_position(x=-settings["hardware"]["length-arm-1"], y=-settings["hardware"]["length-arm-2"], grabber="calibrate")],
                relative_width=0.6
            ),
            "",
            ["« Back", lambda *_: navigate_menu("calibrate")],
            is_static=True,
            is_noresie=True,
            vertical_align=0,
            horizontal_align=0,
            title="Menu » Calibrate » Joint Offsets"
        )

    
    if page == "speak_message":

        message_input = ptg.InputField(
            prompt="Message: "
        )

        new_menu = ptg.Window(
            "[app.title]Speak Message",
            "",
            ptg.Container(
                message_input,
                "",
                ["Paste Message", lambda *_: message_input.insert_text(pyperclip.paste())],
                "",
                ["Speak", lambda *_: serial_interface.speak(message_input.value)],
                relative_width=0.6
            ),
            "",
            ["« Back", lambda *_: navigate_menu("calibrate")],
            is_static=True,
            is_noresie=True,
            vertical_align=0,
            horizontal_align=0,
            title="Menu » Calibrate » Speak Message"
        )
    
    # close the old menu window if open
    try:
        menu.close(animate=False)
    except:
        pass

    menu = new_menu

    # now open the new window
    window_manager.add(menu, assign="menu", animate=False)

# runs the gui
def main():

    _create_aliases()
    _configure_widgets()
    _define_widgets()

    window_manager.layout = _define_layout()
    header = ptg.Window(
        "[app.header]♙ ♖ ♘ ♗ ♕ ♔  ChatGPT Chess Bot  ♚ ♛ ♝ ♞ ♜ ♟",
        box="EMPTY",
        is_static=True,
        is_noresize=True
    )

    header.styles.fill = "app.header.fill"

    # Since header is the first defined slot, this will assign to the correct place
    window_manager.add(header)

    status_sidebar = ptg.Window(
        ptg.Container(
            ptg.Container(
                "",
                ptg.Splitter(
                    ptg.Container(
                    ptg.Label("[app.label][/bold][!game_visuals] [/!]", parent_align=0, padding=2),
                    static_width=37,
                    box="EMPTY"
                    ),
                    ptg.Container(
                        ptg.Label("[app.label][/bold][!game_wdl_stats] [/!]"),
                        box="EMPTY"
                    )
                )
            ),
            ptg.Splitter(
                ptg.Label("[app.label] [!connection_status] [/!]", parent_align=0),
                ptg.Label("[app.label][!game_status] [/!]   ", parent_align=2),
            ),
            box="EMPTY",
            static_width=52
        ),
        title="Machine Status",
        is_static=True,
        is_noresize=True
    )

    window_manager.add(status_sidebar, assign="status")

    # Menu
    navigate_menu("main")
    
    # runs the prompt handling popup in a seperate thread
    notification_thread = continuous_threading.PeriodicThread(0.5, get_prompts)
    notification_thread.start()

    window_manager.run()

# code to run after the program has finnished
def on_exit():
    if ser.is_open:
        # push disconnected led animation
        serial_interface.set_leds("disconnected")

        ser.close()

if __name__ == "__main__":
    atexit.register(on_exit)
    main()
