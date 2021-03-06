# -*- coding: utf-8 -*-

#  Licensed under the Apache License, Version 2.0 (the "License"); you may
#  not use this file except in compliance with the License. You may obtain
#  a copy of the License at
#
#       https://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#  WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#  License for the specific language governing permissions and limitations
#  under the License.

import os
import io
import sys
import json
from datetime import date
from argparse import ArgumentParser

from flask import Flask, request, abort
from google.cloud import speech
from google.cloud.speech import enums, types
from linebot import (
        LineBotApi, WebhookHandler
        )
from linebot.exceptions import (
        InvalidSignatureError
        )
from linebot.models import (
        MessageEvent, TextMessage, AudioMessage, TextSendMessage,
        FollowEvent, TemplateSendMessage, ButtonsTemplate,
        PostbackTemplateAction, MessageTemplateAction, StickerSendMessage,
        )


weekday = ["Monday", "Tuesday", "Wednesday",
        "Thursday", "Friday", "Saturday","Sunday"]


# Google Speech to text API
def transcribe_file(speech_file):
    client = speech.SpeechClient()

    with io.open(speech_file, 'rb') as audio_file:
        content = audio_file.read()

    audio = types.RecognitionAudio(content=content)
    config = types.RecognitionConfig(
            encoding=enums.RecognitionConfig.AudioEncoding.LINEAR16,
            sample_rate_hertz=16000,
            language_code='cmn-Hant-TW')

    response = client.recognize(config, audio)
    results = list(response.results)

    return(results[0].alternatives[0].transcript)


with open("message.json") as data_file:
    message_data = json.load(data_file)

app = Flask(__name__)

# get channel_secret and channel_access_token from your environment variable
channel_secret = os.getenv('LINE_CHANNEL_SECRET', None)
channel_access_token = os.getenv('LINE_CHANNEL_ACCESS_TOKEN', None)
if channel_secret is None:
    print('Specify LINE_CHANNEL_SECRET as environment variable.')
    sys.exit(1)
if channel_access_token is None:
    print('Specify LINE_CHANNEL_ACCESS_TOKEN as environment variable.')
    sys.exit(1)

line_bot_api = LineBotApi(channel_access_token)
handler = WebhookHandler(channel_secret)


@app.route("/callback", methods=['POST'])
def callback():
    # get X-Line-Signature header value
    signature = request.headers['X-Line-Signature']

    # get request body as text
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)

    # handle webhook body
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)

    return 'OK'


@handler.add(FollowEvent)
def follow_text(event):
    profile = line_bot_api.get_profile(event.source.user_id)

    line_bot_api.reply_message(
            event.reply_token, [
                TextSendMessage(
                    text=profile.display_name+message_data["follow_text"]
                    ),
                StickerSendMessage(
                    package_id='2',
                    sticker_id='22'
                    )
                ]
            )


@handler.add(MessageEvent, message=AudioMessage)
def audio(event):
    message_content = line_bot_api.get_message_content(event.message.id)

    with open("audio.m4a", 'wb') as fd:
        for chunk in message_content.iter_content():
            fd.write(chunk)
    os.system("avconv -i audio.m4a audio.wav -y")
    mess = transcribe_file('audio.wav')
    if not mess:
        line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text="你可能要在說一次")
                )
    else:
        line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text=f'你是說：{mess}')
                )


@handler.add(MessageEvent, message=TextMessage)
def message_text(event):
    text = event.message.text
    if text == 'About':
        today = date.today().weekday()
        if today != 5:
            line_bot_api.reply_message(
                    event.reply_token, [
                        TextSendMessage(
                            text=message_data['about'].format(weekday[today])
                            ),
                        StickerSendMessage(
                            package_id='1',
                            sticker_id='116'
                            )
                        ]
                    )
        else:
            line_bot_api.reply_message(
                    event.reply_token, [
                        TextSendMessage(
                            text=message_data['about_t'].format(weekday[today])
                            ),
                        StickerSendMessage(
                            package_id='1',
                            sticker_id='106'
                            )
                        ]
                    )

    elif text == 'Info':
        line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text=message_data['info'])
                )
    elif text == 'Help':
        line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text=message_data['help'])
                )
    elif text == 'Github':
        line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text=message_data['github'])
                )
    else:
        line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text=text)
                )


if __name__ == "__main__":
    arg_parser = ArgumentParser(
            usage='Usage: python ' + __file__ + ' [--port <port>] [--help]'
            )
    arg_parser.add_argument('-p', '--port', default=8080, help='port')
    arg_parser.add_argument('-d', '--debug', default=False, help='debug')
    options = arg_parser.parse_args()

    app.run(debug=options.debug, port=options.port)
