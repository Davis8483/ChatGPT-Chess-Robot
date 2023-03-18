import subprocess

try:
    import openai
except ImportError:
    subprocess.run(["pip", "install", "openai"])
    import openai

  
class ChatBot():
  def __init__(self, key):
    # initialize the API client with your API key
    openai.api_key = key

  # returns a response from the openai API
  def get_response(self, input):
    response = openai.Completion.create(
      model="text-davinci-003",
      prompt=input,
      temperature=0.5,
      max_tokens=60,
      top_p=0.3,
      frequency_penalty=0.5,
      presence_penalty=0
    )

    return response.choices[0].text