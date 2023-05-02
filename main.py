import subprocess
import json
import chess_bot
import webbrowser
import time

try:
    import pyperclip
    import pytermgui as ptg
    import serial
    import serial.tools.list_ports
    import continuous_threading
except:
    subprocess.run(["pip", "install", "pytermgui", "pyserial", "pyperclip", "continuous-threading"])

    import pyperclip
    import pytermgui as ptg
    import serial
    import serial.tools.list_ports
    import continuous_threading

# define window manager
window_manager = ptg.WindowManager()

# load settings file
with open('settings.json') as json_file:
    settings = json.load(json_file)

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
    
    # Jog Machine page
    ptg.tim.define("!steps_z", lambda *_: str(get_steps(z_step_slider)))
    ptg.tim.define("!steps_xy", lambda *_: str(get_steps(xy_step_slider)))
    ptg.tim.define("!pos_x", lambda *_: str(round(chess_bot.pos_x, 1)))
    ptg.tim.define("!pos_y", lambda *_: str(round(chess_bot.pos_y, 1)))
    ptg.tim.define("!pos_z", lambda *_: str(round(chess_bot.pos_z, 1)))
    ptg.tim.define("!grabber_state", lambda *_: chess_bot.grabber_state)

    # Machine Settings page
    ptg.tim.define("!offset_joint1", lambda *_: str(get_joint_offset(joint_1_offset_slider)))
    ptg.tim.define("!offset_joint2", lambda *_: str(get_joint_offset(joint_2_offset_slider)))
    ptg.tim.define("!offset_joint3", lambda *_: str(get_joint_offset(joint_3_offset_slider)))

    # Status sidebar
    ptg.tim.define("!machine_status", get_status)
    ptg.tim.define("!machine_visuals", chess_bot.get_visuals)
    ptg.tim.define("!machine_wdl_stats", chess_bot.get_stats_visual)


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

# returns how much the joint should be offset by based on the slider input
def get_joint_offset(slider: float):
    offset = round((slider.value - 0.5) * 10)
    return offset

# returns if the chess_bot.py thread loop is active
def get_status(*_):
    try:
        if bot_mainloop.is_alive():
            return " 🟢 Connected"
        else:
            return " 🔴 Disconnected"

    except:
        return " 🔴 Disconnected"

# runs main function of chess bot after connecting to the board hardware
def toggle_connection(state: str):
    global bot_mainloop, ser
    
    if state == "Disconnect":
        try:
            ser = serial.Serial(port=settings["hardware"]["serial-port"], baudrate=settings["hardware"]["baud-rate"], timeout=1)

            bot_mainloop = continuous_threading.PeriodicThread(0.2, chess_bot.mainloop, args=(ser,))
            bot_mainloop.start()

        except:
            connect_toggle.toggle()

            # create an prompt notifying the user
            menu_prompt(("[app.title]Error", "", "[app.label]Failed to connect to chess bot...", "", f"[app.label]Port: [/][app.text]{settings['hardware']['serial-port']}"), {"Ok": None})

    else:
        try:
            bot_mainloop.join()
            ser.close()
        except:
            pass

# creates a custom alert menu
def menu_prompt(text: tuple, buttons: dict, _close=False, _function=None):
    global prompt_alert

    if _close:
        prompt_alert.close(animate=False)

        if _function != None:
            try: 
                _function()
            except Exception as e:
                menu_prompt(("[app.title]Error", "", f"[app.label]Failed to execute menu prompt function, [{e}]"), {"Ok": None})

    else:
        prompt = text
        
        for index in buttons.keys():
            if buttons[index] is None:
                new_button = ptg.Button(index, lambda *_: menu_prompt(text, buttons, _close=True))

            else:
                new_button = ptg.Button(index, lambda *_: menu_prompt(text, buttons, _close=True, _function=buttons[index]))

            # add a button
            prompt += ("" , new_button)

        prompt += ("",)

        prompt_alert = window_manager.alert(*prompt)

# runs in a seperate thread, checks to see if chess_bot.py has prompts available and then displays it
def get_prompts():
    if not chess_bot.prompt_queue.empty():
        try:
            text, buttons = chess_bot.prompt_queue.get()
            menu_prompt(text, buttons)
        except:
            menu_prompt(("[app.title]Error", "", "[app.label]Failed to create menu prompt..."), {"Ok": None})

# Used by save_prompt() to merge save with settings
def _merge_dicts(dict1: dict, dict2: dict):
    """
    Merge two dictionaries recursively without overwriting sub-dictionaries.
    """
    for key, value in dict2.items():
        if isinstance(value, dict) and key in dict1:
            _merge_dicts(dict1[key], value)
        else:
            dict1[key] = value

    return dict1


# creates an alert window prompting to save changes
def save_prompt(page: str, save: dict, _dosave=None):
    global save_alert, settings

    if _dosave == None:
        save_alert = window_manager.alert(
            "[app.title]Save Changes?",
            "",
            ["Yes", lambda *_:save_prompt(page, save, _dosave=True)],
            "",
            ["No", lambda *_:save_prompt(page, save, _dosave=False)],
            "",
        )

    elif _dosave:
        # update settings dictionary using the save dictionary
        _merge_dicts(settings, save)

        # save settings to settings.json
        with open("settings.json", "w") as json_file:
            json_file.write(json.dumps(settings, indent=2))

        # close save prompt and navigate to specified window
        try:
            save_alert.close(animate=False)
        except:
            pass
        navigate_menu(page)

    else:
        # close save prompt and navigate to specified window
        try:
            save_alert.close(animate=False)
        except:
            pass
        navigate_menu(page)

# switches which menu page is displayed
def navigate_menu(page: str,):
    global menu, settings, joint_1_offset_slider, joint_2_offset_slider, joint_3_offset_slider

    # close the old menu window if open
    try:
        menu.close(animate=False)
    except:
        pass

    # open new widow based on preset
    if page == "main":
        menu = ptg.Window(
            "[app.title]Menu",
            "",
            ["Settings", lambda *_: navigate_menu("settings")],
            "",
            ["Jog Machine", lambda *_: navigate_menu("jog")],
            "",
            connect_toggle,
            vertical_align=0,
            is_static=True,
            is_noresize=True,
            title="Menu"
        )

    if page == "settings":
        menu = ptg.Window(
            "[app.title]Settings",
            "",
            ["GPT", lambda *_: navigate_menu("gpt_settings")],
            "",
            ["Hardware", lambda *_: navigate_menu("hardware_settings")],
            "",
            ["Back", lambda *_: navigate_menu("main")],
            is_static=True,
            is_noresize=True,
            vertical_align=0,
            title="Menu » Settings"
        )

    if page == "gpt_settings":
        api_key_input = ptg.InputField(
            value=settings["gpt"]["api-key"], prompt="API key: ")
        prompt_input = ptg.InputField(
            value=settings["gpt"]["prompt"], prompt="Prompt: ")
        menu = ptg.Window(
            "[app.title]GPT Settings",
            "",
            ptg.Container(
                api_key_input,
                "",
                ["Get Key", lambda *_: webbrowser.open_new_tab('https://platform.openai.com/account/api-keys')],
                "",
                ["Paste Key", lambda *_: api_key_input.insert_text(pyperclip.paste())],
                "",
                prompt_input,
                relative_width=0.6
            ),
            "",
            ["Back", lambda *_: save_prompt("settings", save={
                "gpt": {"api-key": api_key_input.value, "prompt": prompt_input.value}})],
            is_static=True,
            is_noresize=True,
            vertical_align=0,
            title="Menu » Settings » GPT"
        )

    if page == "hardware_settings":
        serial_port_input = ptg.InputField(value=str(settings["hardware"]["serial-port"]), prompt="Serial Port: ")
        baud_rate_input = ptg.InputField(value=str(settings["hardware"]["baud-rate"]), prompt="Baud Rate: ")

        joint_1_offset_slider = ptg.Slider()
        joint_1_offset_slider.value = round((int(settings["hardware"]["offset-joint-1"]) / 10) + 0.5, 1)

        joint_2_offset_slider = ptg.Slider()
        joint_2_offset_slider.value = round((int(settings["hardware"]["offset-joint-2"]) / 10) + 0.5, 1)

        joint_3_offset_slider = ptg.Slider()
        joint_3_offset_slider.value = round((int(settings["hardware"]["offset-joint-3"]) / 10) + 0.5, 1)

        ports = ""
        for port, desc, hwid in sorted(serial.tools.list_ports.comports()):
            ports += f"\n[app.label]{port}:[/][app.text] {desc} [{hwid}]\n"
    
        if ports == "":
            ports = "\nNone\n"

        menu = ptg.Window(
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
                relative_width=0.6
            ),
            "",
            ["Back", lambda *_: save_prompt("settings", save={"hardware": {"serial-port": serial_port_input.value, "baud-rate": int(baud_rate_input.value), "offset-joint-1": get_joint_offset(joint_1_offset_slider), "offset-joint-2": get_joint_offset(joint_2_offset_slider), "offset-joint-3": get_joint_offset(joint_3_offset_slider)}})],
            is_static=True,
            is_noresize=True,
            vertical_align=0,
            title="Menu » Settings » Hardware"
        )

    if page == "jog":
        menu = ptg.Window(
            "[app.title]Jog Machine",
            "",
            ptg.Container(
                ptg.Splitter(
                    ptg.Label("[app.label]Jog X/Y:", parent_align=0),
                    ptg.Label("([!pos_x] [/!], [!pos_y] [/!]) mm",
                              parent_align=2)
                ),
                ptg.KeyboardButton("w ↑", lambda *_: chess_bot.goto_position(
                    chess_bot.pos_x, (chess_bot.pos_y + get_steps(xy_step_slider)), chess_bot.pos_z), bound="w"),
                ptg.KeyboardButton("a ←", lambda *_: chess_bot.goto_position(
                    (chess_bot.pos_x - get_steps(xy_step_slider)), chess_bot.pos_y, chess_bot.pos_z), bound="a"),
                ptg.KeyboardButton("s ↓", lambda *_: chess_bot.goto_position(
                    chess_bot.pos_x, (chess_bot.pos_y - get_steps(xy_step_slider)), chess_bot.pos_z), bound="s"),
                ptg.KeyboardButton("d →", lambda *_: chess_bot.goto_position(
                    (chess_bot.pos_x + get_steps(xy_step_slider)), chess_bot.pos_y, chess_bot.pos_z), bound="d"),
                "",
                ptg.Splitter(
                    ptg.Label("[app.label]Step:", parent_align=0),
                    ptg.Label("[!steps_xy] [/!] mm", parent_align=2)
                ),
                xy_step_slider,
                relative_width=0.6
            ),
            "",
            ptg.Container(
                ptg.Splitter(
                    ptg.Label("[app.label]Jog Z:", parent_align=0),
                    ptg.Label("[!pos_z] [/!] mm", parent_align=2)
                ),
                ptg.KeyboardButton("e Up", lambda *_: chess_bot.goto_position(
                    chess_bot.pos_x, chess_bot.pos_y, (chess_bot.pos_z + get_steps(z_step_slider))), bound="e"),
                ptg.KeyboardButton("q Down", lambda *_: chess_bot.goto_position(
                    chess_bot.pos_x, chess_bot.pos_y, (chess_bot.pos_z - get_steps(z_step_slider))), bound="q"),
                ptg.Button(
                    "Home", lambda *_: chess_bot.goto_position(chess_bot.pos_x, chess_bot.pos_y, 0)),
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
                    "r Open", lambda *_: chess_bot.set_grabber('open'), bound="r"),
                ptg.KeyboardButton(
                    "f Close", lambda *_: chess_bot.set_grabber('closed'), bound="f"),
                "",
                relative_width=0.6
            ),
            "",
            ["Back", lambda *_: navigate_menu("main")],
            is_static=True,
            is_noresize=True,
            vertical_align=0,
            horizontal_align=0,
            title="Menu » Jog Machine"
        )

    window_manager.add(menu, assign="menu", animate=True)

# runs the gui
def main():

    _create_aliases()
    _configure_widgets()
    _define_widgets()

    window_manager.layout = _define_layout()
    header = ptg.Window(
        "[app.header]♘ ♗ ♖ ♕ ♔  Chess Bot  ♚ ♛ ♜ ♝ ♞",
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
                    ptg.Label("[app.label][/bold][!machine_visuals] [/!]", parent_align=0, padding=2),
                    static_width=37,
                    box="EMPTY"
                    ),
                    ptg.Container(
                        ptg.Label("[app.label][/bold][!machine_wdl_stats] [/!]"),
                        box="EMPTY"
                    )
                )
            ),
            ptg.Label("[app.label][!machine_status] [/!]", parent_align=0),
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


if __name__ == "__main__":
    main()
