# -*- coding: utf-8 -*-

from telegram.ext import Updater, CommandHandler
import os

def start(update, context):
    update.message.reply_text('Hi! Use /set <seconds> to set a timer')

def hello(bot, update):
    update.message.reply_text(
        'Hello {}'.format(update.message.from_user.first_name))


updater = Updater(os.environ['TEL_TOKEN'])

updater.dispatcher.add_handler(CommandHandler('hello', hello))

dp = updater.dispatcher

dp.add_handler(CommandHandler("start", start))
dp.add_handler(CommandHandler("help", start))

updater.start_polling()
updater.idle()