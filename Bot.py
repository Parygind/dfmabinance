# -*- coding: utf-8 -*-

from telegram.ext import Updater, CommandHandler
#from binance_api import Binance
import ccxt
import os
import decimal
import time
import asyncio

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
dict_wall_a = dict()
dict_wall_b = dict()

def get_klines(symb):
    params = {}
    bin_bot.load_markets()
    market = bin_bot.market(symb)
    request = {'symbol': market['id'], 'interval': bin_bot.timeframes['1m'], }
    request['limit'] = 1  # default == max == 500
    method = 'publicGetKlines' if market['spot'] else 'fapiPublicGetKlines'

    return getattr(bin_bot, method)(bin_bot.extend(request, params))

def start(update, context):
    update.message.reply_text('Hi! Use /set <seconds> to set a timer')

def get_balance(update, context):
    f = bin_bot.fetch_balance()
    for i in f['info']['balances']:
        if i['asset'] == 'BTC':
            update.message.reply_text('Баланс : ' + str(i['free']))

def count(update, context):
    update.message.reply_text('Кол-во пар : ' + str(len(symb_list)) + ', take profit : ' + str(tk) + ', stop loss : ' + str(sl))

def get_orders(update, context):
    mes = ''
    for k in dict_order.keys():
        mes = mes + k + ' : ' + float_to_str(dict_order[k]) + ' ' + float_to_str(dict_last_price[k]) + ' ' + float_to_str(round(dict_last_price[k] / dict_order[k] - 1, 4)) + '\n'
    update.message.reply_text(mes)

def updateData(context):
    global dict_prev, dict_curr, symb_list
    dict_prev = dict_curr
    dict_curr = dict()

    tickers = bin_bot.fetch_tickers()
    #for pr in bin_bot.ticker24hr():
    for pr in tickers:
        if tickers[pr]['symbol'][-3:] == 'BTC' and float(tickers[pr]['quoteVolume']) >= 0.01 and float(tickers[pr]['close']) >= 0.00001 and tickers[pr]['symbol'] != 'BNB/BTC':
            dict_curr[tickers[pr]['symbol']] = float(tickers[pr]['quoteVolume'])

    symb_list = list(dict_curr.keys())

def updateData1():
    global dict_prev, dict_curr, symb_list
    dict_prev = dict_curr
    dict_curr = dict()

    tickers = bin_bot.fetch_tickers()
    #for pr in bin_bot.ticker24hr():
    for pr in tickers:
        if tickers[pr]['symbol'][-3:] == 'BTC' and float(tickers[pr]['quoteVolume']) >= 5 and float(tickers[pr]['close']) >= 0.00001:
            dict_curr[tickers[pr]['symbol']] = float(tickers[pr]['quoteVolume'])

    symb_list = list(dict_curr.keys())

def alarm1(context):
    """Send the alarm message."""
    mesVol = ''
    mesOrd = ''
    job = context.job
    global dict_prev, dict_curr, symb_list, limit, tk, sl, dict_last_price, dict_order

    for i in range(0, int(len(symb_list))):
        #kline = get_klines(symb_list[i])
        #vol = float(kline[0][10])
        #course = float(kline[0][4])

        vol = 0
        tr = bin_bot.fetch_trades(symb_list[i], since=bin_bot.milliseconds() - 60000)
        if len(tr) == 0:
            continue

        for t in tr:
            if t['side'] == 'buy':
                vol += t['price'] * t['amount']
            else:
                vol -= t['price'] * t['amount']
        course = tr[len(tr) - 1]['price']


        if symb_list[i] in dict_order:
            dict_last_price[symb_list[i]] = course
            #if course - dict_order[symb_list[i]] >= 0.000003:
            if course >= dict_order[symb_list[i]] * 1.025:
                tk = tk + 1
                mesOrd = mesOrd + 'Профит ' + symb_list[i] + ' ' + float_to_str(dict_order[symb_list[i]]) + ' ' + float_to_str(course) + ' '
                del dict_order[symb_list[i]]
            #elif course - dict_order[symb_list[i]] <= -0.000003:
            elif course <= dict_order[symb_list[i]] * 0.965:
                sl = sl + 1
                mesOrd = mesOrd + 'Убыток ' + symb_list[i] + ' ' + float_to_str(dict_order[symb_list[i]]) + ' ' + float_to_str(course) + ' '
                del dict_order[symb_list[i]]

        if vol >= dict_curr[symb_list[i]]*0.02:
            passMes = False
            lim = limit.get(symb_list[i])
            if lim != None:
                if vol >= dict_curr[symb_list[i]]*(pow(2, lim[0]+1)/100):
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
                    '''
                    symbol = 'ETH/BTC'
                    type = 'market'  # or 'market'
                    side = 'sell'  # or 'buy'
                    amount = 1.0
                    price = None  # or None

                    # extra params and overrides if needed
                    params = {
                        'test': True,  # test if it's valid, but don't actually place it
                    }

                    order = bin_bot.create_order(symbol, type, side, amount, price, params)
                    context.bot.send_message(chat_id='-1001242337520', text=order)
                    '''

    if len(mesVol) > 0:
        mes = 'Объемы выросли : ' + mesVol
        context.bot.send_message(chat_id='-1001242337520', text=mes)
    if len(mesOrd) > 0:
        mes = 'Сделки закрыты : ' + mesOrd
        context.bot.send_message(chat_id='-1001242337520', text=mes)

async def alarm4(context):
    """Send the alarm message."""
    mesVol = ''
    mesOrd = ''
    job = context.job
    global dict_prev, dict_curr, symb_list, limit, tk, sl, dict_last_price, dict_order

    for i in range(0, int(len(symb_list))):
        #kline = get_klines(symb_list[i])
        #vol = float(kline[0][10])
        #course = float(kline[0][4])
        pass_val = False
        vol_a = 0
        vol_b = 0
        f = bin_bot.fetchOrderBook(symb_list[i])
        course = f['asks'][0][0]
        for item in f['asks']:
            vol_a += float(item[0]) * float(item[1])

        for item in f['bids']:
            vol_b += float(item[0]) * float(item[1])

        if not symb_list[i] in dict_wall_a:
            dict_wall_a[symb_list[i]] = vol_a
            dict_wall_b[symb_list[i]] = vol_b
            continue

        if symb_list[i] in dict_order:
            dict_last_price[symb_list[i]] = course
            if course >= dict_order[symb_list[i]] * 1.011:
                pass_val = True
                tk = tk + 1
                #mesOrd = mesOrd + 'Профит ' + symb_list[i] + ' ' + float_to_str(dict_order[symb_list[i]]) + ' ' + float_to_str(course) + ' '
                del dict_order[symb_list[i]]
            elif course <= dict_order[symb_list[i]] * 0.97:
                pass_val = True
                sl = sl + 1
                #mesOrd = mesOrd + 'Убыток ' + symb_list[i] + ' ' + float_to_str(dict_order[symb_list[i]]) + ' ' + float_to_str(course) + ' '
                del dict_order[symb_list[i]]

        if dict_wall_a[symb_list[i]] * 0.75 >= vol_a and dict_wall_b[symb_list[i]] * 1.25 < vol_b and not symb_list[i] in dict_order and not pass_val:
            amount = int(0.002 / course)
            type = 'market'  # or market
            side = 'buy'
            order = bin_bot.create_order(symb_list[i], type, side, amount, None)

            while order['status'] != 'FILLED':
                order = bin_bot.fetch_order(order['id'], symb_list[i])

                if order['status'] == 'REJECTED' or order['status'] == 'EXPIRED':
                    break

            if order['status'] != 'FILLED':
                continue

            limit_price = float(order['price']) * 0.97
            stop_price = float(order['price']) * 1.011

            await bin_bot.createOrder(symb_list[i], 'limit', 'sell', order['executedQty'], limit_price,
                                       {'stop': 'loss', 'stop_price': stop_price})

            mesVol += order + '\n'
            dict_order[symb_list[i]] = course
            dict_last_price[symb_list[i]] = course

        dict_wall_a[symb_list[i]] = vol_a
        dict_wall_b[symb_list[i]] = vol_b

    if len(mesVol) > 0:
        mes = 'Пробитие стены : ' + mesVol
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

        bin_bot = ccxt.binance({
            'apiKey' : os.environ['API_KEY'],
            'secret' : os.environ['API_SECRET'],
            'enableRateLimit': True,
        })

        job = context.job_queue.run_repeating(updateData, due, first=0, context=chat_id)
        job = context.job_queue.run_repeating(alarm4, 60, first=20, context=chat_id)
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
updater.dispatcher.add_handler(CommandHandler('balance', get_balance, pass_chat_data=True))

updater.start_webhook(listen='0.0.0.0', port=PORT, url_path=TOKEN)
updater.bot.set_webhook(URL + TOKEN)

#updater.start_polling()
updater.idle()
