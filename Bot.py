# -*- coding: utf-8 -*-

from telegram.ext import Updater, CommandHandler
from binance_api import Binance
import os

bin_bot = None
dict_prev = dict()
dict_curr = dict()

dict_prev_pr = dict()
dict_curr_pr = dict()

def start(update, context):
    update.message.reply_text('Hi! Use /set <seconds> to set a timer')

def alarm(context):
    """Send the alarm message."""
    mesVol = ''
    mesPrc = ''
    job = context.job
    global dict_prev, dict_curr, dict_prev_pr, dict_curr_pr
    dict_prev = dict_curr
    dict_curr = dict()

    dict_prev_pr = dict_curr_pr
    dict_curr_pr = dict()

    for pr in bin_bot.ticker24hr():
        if pr['symbol'][-3:] == 'BTC': #and float(pr['quoteVolume']) >= 300.0:
            vol = dict_prev.get(pr['symbol'])

            price = dict_prev_pr.get(pr['symbol'])

            if vol != None and vol != 0:
                if float(pr['quoteVolume'])/vol >= 1.3:
                    mesVol += pr['symbol'] + '(+' + str(round(((float(pr['quoteVolume'])/vol)-1)*100, 2)) + '%) '

            if price != None and price != 0:
                if float(pr['lastPrice'])/price <= 0.95:
                    mesPrc += pr['symbol'] + '(-' + str(round((1-(float(pr['lastPrice'])/price))*100,2)) + '%) '

            dict_curr[pr['symbol']] = float(pr['quoteVolume'])
            dict_curr_pr[pr['symbol']] = float(pr['lastPrice'])

    if len(mesVol) > 0:
        mes = 'Объемы выросли : ' + mesVol
        context.bot.send_message(chat_id='@dfmatrade', text=mes)

    if len(mesPrc) > 0:
        mes = 'Цены упали : ' + mesPrc
        context.bot.send_message(chat_id='@dfmatrade', text=mes)

def set_timer(update, context):
    """Add a job to the queue."""
    chat_id = update.message.chat_id
    try:
        # args[0] should contain the time for the timer in seconds
        due = int(context.args[0])
        if due < 0:
            update.message.reply_text('Введите положительное время!')
            return

        global bin_bot

        bin_bot = Binance(
            API_KEY=os.environ['API_KEY'],
            API_SECRET=os.environ['API_SECRET']
        )

        job = context.job_queue.run_repeating(alarm, due, first=0, context=chat_id)
        context.chat_data['job'] = job

        update.message.reply_text('Таймер запущен!')

    except (IndexError, ValueError):
        update.message.reply_text('Usage: /start <seconds>')

def get_vol(update, context):
    try:
        # args[0] should contain the time for the timer in seconds
        pair = context.args[0]
        pair = pair.upper()
        if dict_curr.get(pair) == None or dict_prev.get(pair) == None:
            update.message.reply_text('В базе данных нет такой торговой пары!')
            return

        update.message.reply_text(str(round(dict_prev.get(pair), 2)))
        update.message.reply_text(str(round(dict_curr.get(pair) / dict_prev.get(pair), 2)))

    except (IndexError, ValueError):
        update.message.reply_text('Usage: /get <trade_pair>')

def unset(update, context):
    """Remove the job if the user changed their mind."""
    if 'job' not in context.chat_data:
        update.message.reply_text('У вас нет запущенного таймера')
        return

    job = context.chat_data['job']
    job.schedule_removal()
    del context.chat_data['job']

    update.message.reply_text('Таймер отключен!')

def hello(update, context):
    context.bot.send_message(chat_id='@dfmatrade', text='))')


def get_top(update, context):
    try:
        # args[0] should contain the time for the timer in seconds
        if len(dict_prev) == 0:
            update.message.reply_text('База данных пуста!')
            return

        update.message.reply_text(list(dict_prev.keys())[0])
        update.message.reply_text(str(dict_prev[list(dict_prev.keys())[0]]))

    except (IndexError, ValueError):
        update.message.reply_text('COMMAND ERROR')

URL = os.environ.get('URL')
PORT = int(os.environ.get('PORT', '5000'))
TOKEN = os.environ['TEL_TOKEN']

updater = Updater(TOKEN, use_context=True)

updater.dispatcher.add_handler(CommandHandler('hello', hello, pass_chat_data=True))
updater.dispatcher.add_handler(CommandHandler('start', start, pass_chat_data=True))
updater.dispatcher.add_handler(CommandHandler('set', set_timer, pass_args=True,
                                  pass_job_queue=True,
                                  pass_chat_data=True))
updater.dispatcher.add_handler(CommandHandler('get', get_vol, pass_args=True, pass_chat_data=True))
updater.dispatcher.add_handler(CommandHandler('gettop', get_top, pass_chat_data=True))
updater.dispatcher.add_handler(CommandHandler('unset', unset, pass_chat_data=True))

updater.start_webhook(listen='0.0.0.0', port=PORT, url_path=TOKEN)
updater.bot.set_webhook(URL + TOKEN)
#updater.start_polling()
updater.idle()
