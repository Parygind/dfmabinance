# -*- coding: utf-8 -*-

from telegram.ext import Updater, CommandHandler
from binance_api import Binance
import os

bot = None
dict_prev = dict()
dict_curr = dict()

def start(bot, update, context):
    update.message.reply_text('Hi! Use /set <seconds> to set a timer')

def alarm(context):
    """Send the alarm message."""
    mes = ''
    job = context.job
    global dict_prev, dict_curr
    dict_prev = dict_curr
    dict_curr = dict()
    for pr in bot.ticker24hr():
        if pr['symbol'][-3:] == 'BTC': #and float(pr['quoteVolume']) >= 300.0:
            vol = dict_prev.get(pr['symbol'])
            if vol != None:
                if float(pr['quoteVolume'])/vol >= 1.7:
                    mes += pr['symbol'] + ' '
            dict_curr[pr['symbol']] = pr['quoteVolume']
    context.bot.send_message(job.context, text=mes)

def set_timer(bot, update, context):
    """Add a job to the queue."""
    chat_id = update.message.chat_id
    try:
        # args[0] should contain the time for the timer in seconds
        due = int(context.args[0])
        if due < 0:
            update.message.reply_text('Введите положительное время!')
            return

        global bot

        bot = Binance(
            API_KEY=os.environ['API_KEY'],
            API_SECRET=os.environ['API_SECRET']
        )

        job = context.job_queue.run_repeating(alarm, due, context=chat_id)
        context.chat_data['job'] = job

        update.message.reply_text('Таймер запущен!')

    except (IndexError, ValueError):
        update.message.reply_text('Usage: /start <seconds>')

def get_vol(bot, update, context):
    try:
        # args[0] should contain the time for the timer in seconds
        pair = context.args[0]
        if dict_curr.get(pair) == None :
            update.message.reply_text('В базе данных нет такой торговой пары!')
            return

        update.message.reply_text(str(dict_curr.get(pair) / dict_prev.get(pair)))

    except (IndexError, ValueError):
        update.message.reply_text('Usage: /get <trade_pair>')

def unset(bot, update, context):
    """Remove the job if the user changed their mind."""
    if 'job' not in context.chat_data:
        update.message.reply_text('У вас нет запущенного таймера')
        return

    job = context.chat_data['job']
    job.schedule_removal()
    del context.chat_data['job']

    update.message.reply_text('Таймер отключен!')

def hello(bot, update):
    update.message.reply_text(
        'Hello {}'.format(update.message.from_user.first_name))


URL = os.environ.get('URL')
PORT = int(os.environ.get('PORT', '5000'))
TOKEN = os.environ['TEL_TOKEN']

updater = Updater(TOKEN)

updater.dispatcher.add_handler(CommandHandler('hello', hello))
updater.dispatcher.add_handler(CommandHandler('he', hello))
updater.dispatcher.add_handler(CommandHandler('start', start))
updater.dispatcher.add_handler(CommandHandler('set', set_timer))
updater.dispatcher.add_handler(CommandHandler('get', get_vol))
updater.dispatcher.add_handler(CommandHandler('unset', unset, pass_chat_data=True))

updater.start_webhook(listen='0.0.0.0', port=PORT, url_path=TOKEN)
updater.bot.set_webhook(URL + TOKEN)
#updater.start_polling()
updater.idle()