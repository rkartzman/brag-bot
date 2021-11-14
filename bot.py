import slack
import os, logging

from pathlib import Path 
from dotenv import load_dotenv
from flask import Flask, request, Response
from slackeventsapi import SlackEventAdapter
import string
from datetime import datetime, timedelta

import pprint




printer = pprint.PrettyPrinter()

env_path = Path('.') / '.env'
load_dotenv(dotenv_path=env_path)

app = Flask(__name__) # represents the name of the file 
slack_event_adapter = SlackEventAdapter(os.environ['SIGNING_SECRET'],'/slack/events',app) #handle different events from slack api

client = slack.WebClient(token=os.environ['SLACK_TOKEN'])

printer.pprint(client.api_call("auth.test"))
BOT_ID = client.api_call("auth.test")['user_id']

BAD_WORDS = ['bad_word', 'fack']

# list of messages we want to schedule 


SCHEDULED_MESSAGES = [
  {'text': 'first message' ,'post_at': int((datetime.now() + timedelta(seconds=20)).timestamp()), 'channel': 'C02KP2N930C' },
  {'text': 'second message' ,'post_at': int((datetime.now() + timedelta(seconds=30)).timestamp()), 'channel':  'C02KP2N930C'}
]

user_message_counts = {}

# store all of the welcome messages we send to each user
welcome_messages = {}


class WelcomeMessage:
  START_TEXT = {
    'type': 'section',
    'text': {
      'type': 'mrkdwn',
      'text': (
        'Welcome to this channel \n\n'
        '*Get started by completing this task!*'
      )
    }
  }

  DIVIDER = { 'type': 'divider' }

  def __init__(self, channel, user):
      self.channel = channel
      self.user = user
      self.icon_emoji = ':robot_face:'
      self.timestamp = ''
      self.completed = False
  
  def get_message(self):
      return {
        'ts': self.timestamp,
        'channel': self.channel,
        'username': 'Welcome Robot',
        'icon_emoji': self.icon_emoji,
        'blocks': [self.START_TEXT, self.DIVIDER, self._get_reaction_task()]
      }
  
  def _get_reaction_task(self):
    checkmark = ':white_check_mark:'
    if not self.completed:
      checkmark = ':white_large_square:'
    
    text = f'{checkmark} *React to this message!*'

    return {'type': 'section', 'text': {'type': 'mrkdwn', 'text': text}}


def check_if_bad_words(message_str):
  msg = message_str.lower()
  msg = msg.translate(str.maketrans('', '', string.punctuation))
  # creates a translation table that maps a character to a new character. whenever i see 'a', => map it to 'b'
  # we essentially want to replace any punctuation with nothing
  return any(word in msg for word in BAD_WORDS)

def send_welcome_message(channel, user): 
  if channel not in welcome_messages:
        welcome_messages[channel] = {}

  if user in welcome_messages[channel]: #we've already sent them a welcome message 
      return

  welcome = WelcomeMessage(channel, user)
  message = welcome.get_message()
  response = client.chat_postMessage(**message)
  welcome.timestamp = response['ts']

  
  welcome_messages[channel][user] = welcome

def list_scheduled_messages(channel):
    response = client.chat_scheduledMessages_list(channel=channel)
    messages = response.data.get('scheduled_messages')  
    ids = []
    for msg in messages:
        ids.append(msg.get('id'))

    return ids

def schedule_messages(messages):
    ids = []
    for msg in messages:
        response = client.chat_scheduleMessage(channel=msg['channel'], text=msg['text'], post_at=msg['post_at']).data
        id_ = response.get('scheduled_message_id')
        ids.append(id_)
    return ids

def delete_scheduled_messages(ids, channel):
    for _id in ids:
        try:
            client.chat_deleteScheduledMessage(channel=channel, scheduled_message_id=id)
        except Exception as e:
          print(e)

@slack_event_adapter.on('message')
def message(payload): 
    # print(payLoad)
    event = payload.get('event', {})
    channel_id = event.get('channel')
    user_id = event.get('user')
    text = event.get('text')
    #only send a message if it's not from a bot, otherwise will become infinite loop 
    if user_id != None and BOT_ID != user_id:
      if user_id in user_message_counts: 
          user_message_counts[user_id] += 1
      else: 
          user_message_counts[user_id] = 1
      if text.lower() == 'start':
          send_welcome_message(f'@{user_id}', user_id)
      elif check_if_bad_words(text):
          ts = event.get('ts')
          client.chat_postMessage(channel=channel_id, thread_ts=ts, text="THAT IS A BAD WORD")
      

@slack_event_adapter.on('reaction_added')
def reaction(payload):
  event = payload.get('event', {})
  channel_id = event.get('item', {}).get('channel')
  user_id = event.get('user')

  if f'@{user_id}' not in welcome_messages:
    return

  welcome = welcome_messages[f'@{user_id}'][user_id]
  welcome.completed = True
  welcome.channel = channel_id
  message = welcome.get_message()
  updated_message = client.chat_update(**message)
  welcome.timestamp = updated_message['ts']

@app.route('/message-count', methods=['POST'])
def message_count(): 
    print('hey this route')
    data = request.form
    user_id = data.get('user_id')
    channel_id = data.get('channel_id')
    message_count = user_message_counts.get(user_id, 0)
    client.chat_postMessage(channel=channel_id, text=f'Message count: {message_count}')    
    return Response(), 200



if __name__ == '__main__': 
  # schedule_messages(SCHEDULED_MESSAGES)
  # ids = list_scheduled_messages('C02KP2N930C')
  # delete_scheduled_messages(ids, 'C02KP2N930C')
  app.run(debug=True)