import subprocess
import os

def say(text):

    # balcon.exe, tts aplication directory
    balcon_directory = fr"{os.path.dirname(os.path.abspath(__file__))}\balcon.exe"
    voice = "ScanSoft Daniel_Full_22kHz"

    subprocess.run([balcon_directory, "-n", voice, "-t", str(text)])