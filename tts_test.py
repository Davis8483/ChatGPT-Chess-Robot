import pyttsx3 # library is stored localy because of a bug with the original
import time
import json
import nltk
import serial
    
ser = serial.Serial(port="COM4", baudrate=9600)

# initialize engine
engine = pyttsx3.init()

def speak(text: str):
    
    # load arpabet, maps words to mouth shapes
    try:
        arpabet = nltk.corpus.cmudict.dict()
    except:
        nltk.download("cmudict")
        arpabet = nltk.corpus.cmudict.dict()


    # load settings file
    with open('settings.json') as json_file:
        settings = json.load(json_file)

    # executed every time a word is said if talking animation is enabled
    def onWord(name, location, length):
        
        # find word using positioning info
        word = "".join(filter(str.isalpha, text[location:(location + length)])).lower()
        
        # check if word is valid
        if word in arpabet.keys():

            # select the first arpabet sequence for the word
            arpabet_letters = arpabet[word][0]

            # iterate through arpabet sequence
            for letter in arpabet_letters:

                # remove numbers from the letter
                clean_letter = "".join(filter(str.isalpha, letter))

                # check if letter is in servo positions dictionary
                if  clean_letter in settings["tts"]["arpabet-servo-positions"].keys():
                    
                    # send positions to servo
                    angle = settings["tts"]["arpabet-servo-positions"][clean_letter]
                    ser.write(f'{{"data": {{"angle-joint3": {angle + 5}}}}}\n'.encode())

                    time.sleep(settings["tts"]["arpabet-delay"])

        # close the mouth
        angle = settings["hardware"]["grabber-closed-angle"]
        ser.write(f'{{"data": {{"angle-joint3": {angle + 5}}}}}\n'.encode())

    # connect talking animation
    if settings["tts"]["talking-animation"]:
        engine.connect('started-word', onWord)

    # set voice
    voices = engine.getProperty('voices')
    for index in voices:
        if index.name == settings["tts"]["voice"]:
            engine.setProperty('voice', index.id)

    engine.say(text, text)
    engine.runAndWait()

while True:
    speak(input("Speak Text: "))