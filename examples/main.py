import chess_engine
import daniel_tts
import chat_bot
import json
import subprocess

try:
    import serial
except ImportError:
    subprocess.run(["pip", "install", "pyserial"])
    import serial

class ChessBot():
  def __init__(self):

    # Open the config file, if it does not exsist create a new one
    try:
      with open('config.json') as self.json_file:
        self.config = json.load(self.json_file)
    except:
      with open('config.json', 'w') as self.json_file:
        self.json_file.write('''{\n  "chat-bot":{\n    "api-key": "#add your api key here",\n    "personality": "Pretend to be a british chess player."\n  }\n}''')
        print('Config file created, please input information...')
        exit()

    # initialize objects
    self.engine = chess_engine.Engine()
    self.chat = chat_bot.ChatBot(self.config['chat-bot']['api-key'])
    self.tts = daniel_tts.TTS()
    self.serial = serial.Serial("COM3", baudrate=9600)

  def mainloop(self):
    # self.tts.say(self.chat.get_response(f"{self.config['chat-bot']['personality']} You claim a pawn."))
    # print(self.engine.get_move())
    # print(self.engine.last_captured)

    while True:
      self.serial_line = self.serial.readline()

      if 'fen' in self.serial_line:
        pass
      elif 'reset' in self.serial_line:
        pass
      elif 'invalid move' in self.serial_line:
        pass
    
if __name__ == "__main__":
  chess_bot = ChessBot()
  chess_bot.mainloop()
  