import subprocess
import json
import threading

try:
    import openai

except:
    subprocess.run(["pip", "install", "openai"])

    import openai

# resets chat history to default
def reset_history():
    global message_history

    try:
        # load settings file
        with open('settings.json') as json_file:
            settings = json.load(json_file)
    except:
        pass

    message_history = [
        {"role": "system", "content": "You are a chess robot that plays a role."},
        {"role": "user", "content": settings["gpt"]["prompt"]}
    ]

def get_response(message):
    global message_history, api_response

    try:
        # load settings file
        with open('settings.json') as json_file:
            settings = json.load(json_file)
    except:
        pass

    # set api key
    openai.api_key = settings["gpt"]["api-key"]
    
    my_message = {"role": "user", "content": message}

    message_history.append(my_message)

    api_response = None
    
    def timed_response():
        global api_response

        try:
            api_response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=message_history,
                temperature=settings["gpt"]["temperature"],
                presence_penalty=settings["gpt"]["presence-penalty"],
                frequency_penalty=settings["gpt"]["frequency-penalty"]
                )["choices"][0]["message"]
            
        except Exception as e:
            api_response = e

    timed_thread = threading.Thread(target=timed_response)
    timed_thread.start()

    # wait until thread is done or timout occours
    timed_thread.join(timeout=settings["gpt"]["request-timeout"])

    if isinstance(api_response, Exception):
        return f"Error: {api_response}"
    
    elif api_response != None:
        message_history.append(api_response)

        return api_response["content"]
    
    else:
        return "Error: failed to contact ChatGPT API"
    
# initialize history
reset_history()
