import json
import random
import sounddevice as sd
import soundfile as sf

def play_sound_file(file_path, volume):
    data, sample_rate = sf.read(file_path)
    adjusted_data = data * volume
    sd.play(adjusted_data, sample_rate)

def play_json_sound(name, blocking:bool=False):

    # load settings file
    with open('settings.json') as json_file:
        settings = json.load(json_file)

    # check if sound exsists
    if name in settings["sounds"].keys():

        # pick a random sound variant
        sound_data = random.choice(settings["sounds"][name])

        # play the sound
        play_sound_file(sound_data['path'], sound_data["volume"])

        if blocking:
            sd.wait()
    
