from slack_bolt import App
import os, logging
from pathlib import Path 
from dotenv import load_dotenv
import string
from datetime import datetime, timedelta

import pprint

printer = pprint.PrettyPrinter()

env_path = Path('.') / '.env'
load_dotenv(dotenv_path=env_path)

logging.basicConfig(level=logging.DEBUG)


app = App(
    token=os.environ.get("SLACK_TOKEN"),
    signing_secret=os.environ.get("SIGNING_SECRET"),
)

# {
#   '123': {
#     'username': 'remykartzman',
#     'messages': {
#       'timestamp': 'val'
#     }
#   }
# }
user_messages = {}

@app.middleware  # or app.use(log_request)
def log_request(logger, body, next):
    logger.debug(body)
    next()

# Step 5: Payload is sent to this endpoint, we extract the `trigger_id` and call views.open
@app.command("/brag")
def handle_command(body, ack, client, logger, context):  
    ack()
    printer.pprint('handle_command +++++++++++++++++++++++++')
    printer.pprint(context['channel_id'])
    channel_id = context['channel_id']
    res = client.views_open(
        trigger_id=body["trigger_id"],
        view={
            "type": "modal",
            "callback_id": "brag-modal",
            "title": {"type": "plain_text", "text": "Brag Box"},
            "submit": {"type": "plain_text", "text": "Submit"},
            "close": {"type": "plain_text", "text": "Cancel"},
            "private_metadata": channel_id,
            "blocks": [
                {
                    "type": "input",
                    "block_id": "my_block",
                    "element": {"type": "plain_text_input", "action_id": "my_action"},
                    "label": {"type": "plain_text", "text": "What have you accomplished this week?"},
                }
            ],
        },
    )
    


@app.view("brag-modal")
def view_submission(ack, body, client, logger, request, say, context, payload):
  ack()
  printer.pprint('view submission======================================')
  printer.pprint(payload)
  channel_id = payload['private_metadata']
  timestamp = int(datetime.now().timestamp())    
  user_id = body["user"]["id"]
  user_name = body["user"]["username"]
  brag_text = body["view"]["state"]["values"]["my_block"]["my_action"]["value"]
  
  if user_id != None: 
    if user_id in user_messages:
      user_messages[user_id]['messages'][timestamp] = brag_text
      # push on to array
    else:
      # initialize it with data
      user_messages[user_id] = {}
      user_messages[user_id]['messages'] = {}
      user_messages[user_id]['username'] = user_name
      user_messages[user_id]['messages'][timestamp] = brag_text

  say(channel=channel_id, text=brag_text)
  
  
  # printer.pprint(user_messages)


if __name__ == "__main__":
    app.start(5000)