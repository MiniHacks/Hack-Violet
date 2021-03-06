from flask import Flask
from slack import WebClient
from slackeventsapi import SlackEventAdapter
import requests
import sentence_splitter
from twilio.rest import Client
import json

app = Flask(__name__)
BOT_USER_TOKEN = "xoxb-3062362679586-3062373690386-VVqLHe6283JdxAH7cGMAuVCi"
swc = WebClient(token=BOT_USER_TOKEN)
EVENT_TOKEN = "15c23c1f9950849f957f05567d354750"
sea = SlackEventAdapter(EVENT_TOKEN, "/slack/events", app)

ACCOUNT_SID = "AC321c86468de6829c768203a8b42cc1e6"
AUTH_TOKEN = "bf6aa3288273ee4b398e26fc0e8a2270"
MSG_SID = "MG272157a072f76d6b7e52467b302eedfc"
twilio_client = Client(ACCOUNT_SID, AUTH_TOKEN)

MESSAGE_BLOCK = {
    "type": "section",
    "text": {
        "type": "mrkdwn",
        "text": "",
    },
}

ML_ENDPOINT = "http://34.67.45.8/process_segments"
THRESHOLD = 0.4
ADMIN_ID = "U031UB8QE3V"
ADMIN_PN = "+19526669929"

def get_real_name(user_id):
    response = swc.users_profile_get(user=user_id)
    return response.data.get("profile").get("real_name")

def text_admin(message):
    message = twilio_client.messages.create(messaging_service_sid=MSG_SID, body=message, to=ADMIN_PN)
    return message

def alert_admin(name, segment, certainty):
    MESSAGE_BLOCK["text"]["text"] = "We've flagger {name}'s message for sexual harassment with {certainty}% certainty: \n`\"{segment}\"`\n If you deem this to be a case of sexual harassment, look to www.rainn.org/, www.womenagainstabuse.org/, leanin.org/ for resources.".format(name=name, segment=segment.strip(), certainty=round(certainty * 100, 2))
    to_send = {"channel": ADMIN_ID, "blocks": [MESSAGE_BLOCK]}
    text_admin(MESSAGE_BLOCK["text"]["text"])
    result = swc.chat_postMessage(**to_send)
    return result

@sea.on("message")
def message(payload):
    event = payload.get("event")
    if event.get("bot_id") != None:
        return

    text = event.get("text")

    sentences = sentence_splitter.split_into_sentences(text)
    data = json.dumps(sentences if "." in text else [text])
    response = requests.get(ML_ENDPOINT, data=data)
    print(response)

    response = response.json()
    for cur in response["result"]:
        certainty = cur["rating"]
        segment = cur["segment"]
        if certainty > THRESHOLD:
            name = get_real_name(event.get("user"))
            alert_admin(name, segment, certainty)
    return

if __name__ == "__main__":
    print("Lets go")
    app.run(host="0.0.0.0", port=8080, debug=True)