# -*- coding: utf-8 -*-

from telegram.ext import Updater, CommandHandler
from binance_api import Binance
import os
import decimal

# create a new context for this task
ctx = decimal.Context()

# 20 digits should be enough for everyone :D
ctx.prec = 20

def float_to_str(f):
    """
    Convert the given float to a string,
    without resorting to scientific notation
    """
    d1 = ctx.create_decimal(repr(f))
    return format(d1, 'f')

bin_bot = None
symb_list = None
dict_prev = dict()
dict_curr = dict()

dict_prev_pr = dict()
dict_curr_pr = dict()

limit = dict()

tk = 0
sl = 0
dict_order = dict()
dict_last_price = dict()

def start(update, context):
    update.message.reply_text('Hi! Use /set <seconds> to set a timer')

def count(update, context):
    update.message.reply_text('Кол-во пар : ' + str(len(symb_list)) + ', take profit : ' + str(tk) + ', stop loss : ' + str(sl))

def get_orders(update, context):
    mes = ''
    for k in dict_order.keys():
        mes = mes + k + ' : ' + float_to_str(dict_order[k]) + ' ' + float_to_str(dict_last_price[k]) + '\n'
    update.message.reply_text(mes)

def updateData(context):
    global dict_prev, dict_curr, symb_list
    dict_prev = dict_curr
    dict_curr = dict()

    for pr in bin_bot.ticker24hr():
        if pr['symbol'][-3:] == 'BTC' and float(pr['quoteVolume']) >= 0.00001 :#and float(pr['lastPrice']) >= 0.0001:
            dict_curr[pr['symbol']] = float(pr['quoteVolume'])

    symb_list = list(dict_curr.keys())

def alarm1(context):
    """Send the alarm message."""
    mesVol = ''
    mesOrd = ''
    job = context.job
    global dict_prev, dict_curr, symb_list, limit

    #for i in range(0, int(len(symb_list)/2)):
    for i in range(0, int(len(symb_list))):
        inf = bin_bot.klines(symbol=symb_list[i], interval='1m', limit=1)
        vol = float(inf[0][10])
        course = float(inf[0][4])

        if symb_list[i] in dict_order:
            dict_last_price[symb_list[i]] = max(course, dict_last_price[symb_list[i]])
            #if course - dict_order[symb_list[i]] >= 0.000003:
            if course >= dict_order[symb_list[i]] * 1.025:
                tk = tk + 1
                mesOrd = mesOrd + 'Профит ' + symb_list[i] + ' ' + float_to_str(course) + ' ' + float_to_str(dict_order[symb_list[i]]) + ' '
                del dict_order[symb_list[i]]
            #elif course - dict_order[symb_list[i]] <= -0.000003:
            if course <= dict_order[symb_list[i]] * 0.975:
                sl = sl + 1
                mesOrd = mesOrd + 'Убыток ' + symb_list[i] + ' ' + float_to_str(course) + ' ' + float_to_str(dict_order[symb_list[i]]) + ' '
                del dict_order[symb_list[i]]

        if vol >= dict_curr[symb_list[i]]*0.02:
            passMes = False
            lim = limit.get(symb_list[i])
            if lim != None:
                if vol >= dict_curr[symb_list[i]]*(pow(2,lim[0]+1)/100):
                    limit[symb_list[i]] = (30, (lim[1]+1))
                else:
                    passMes = True
                    if (lim[0]-1)%5 == 0:
                        l = lim[1] - 1
                        if l <= 1:
                            limit[symb_list[i]] = None
                        else:
                            limit[symb_list[i]] = (lim[0]-1, l)
                    else:
                        limit[symb_list[i]] = (lim[0] - 1, lim[1])

            else:
                limit[symb_list[i]] = (30, 1)
            if not passMes:
                mesVol += symb_list[i] + '(+' + str(round(vol, 2)) + ' / ' + str(round((vol/dict_curr[symb_list[i]])*100, 2)) + '%) Курс : ' + float_to_str(course) + " "
                if not symb_list[i] in dict_order:
                    dict_order[symb_list[i]] = course
                    dict_last_price[symb_list[i]] = course

    if len(mesVol) > 0:
        mes = 'Объемы выросли : ' + mesVol
        context.bot.send_message(chat_id='-1001242337520', text=mes)
    if len(mesOrd) > 0:
        mes = 'Сделки закрыты : ' + mesOrd
        context.bot.send_message(chat_id='-1001242337520', text=mes)

def alarm2(context):
    """Send the alarm message."""
    mesVol = ''
    job = context.job
    global dict_prev, dict_curr, symb_list

    for i in range(int(len(symb_list)/2), len(symb_list)):
        inf = bin_bot.klines(symbol=symb_list[i], interval='1m', limit=1)
        vol = float(inf[0][10])

        if vol >= dict_curr[symb_list[i]]*0.02:
            mesVol += symb_list[i] + '(+' + str(round(vol, 2)) + ' / ' + str(round((vol/dict_curr[symb_list[i]])*100, 2)) + '%) '

    if len(mesVol) > 0:
        mes = 'Объемы выросли : ' + mesVol
        context.bot.send_message(chat_id='-1001242337520', text=mes)

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

        job = context.job_queue.run_repeating(updateData, due, first=0, context=chat_id)
        job = context.job_queue.run_repeating(alarm1, 20, first=10, context=chat_id)
        #job = context.job_queue.run_repeating(alarm2, 120, first=70, context=chat_id)
        context.chat_data['job'] = job

        update.message.reply_text('Таймер запущен!')

    except (IndexError, ValueError):
        update.message.reply_text('Usage: /set <seconds>')

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
    context.bot.send_message(chat_id='-1001242337520', text='))')


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
updater.dispatcher.add_handler(CommandHandler('count', count, pass_chat_data=True))
updater.dispatcher.add_handler(CommandHandler('orders', get_orders, pass_chat_data=True))

updater.start_webhook(listen='0.0.0.0', port=PORT, url_path=TOKEN)
updater.bot.set_webhook(URL + TOKEN)

#updater.start_polling()
updater.idle()
