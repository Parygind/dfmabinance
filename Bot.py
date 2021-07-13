# -*- coding: utf-8 -*-

from telegram.ext import Updater, CommandHandler
# from binance_api import Binance
import ccxt
import os
import decimal
import time
import asyncio
import sys
import ast
import unicorn_binance_websocket_api
import math
import threading
from datetime import datetime

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


def num_after_point(x):
    s = float_to_str(x)
    if not '.' in s:
        return 0
    return len(s) - s.index('.') - 1


bin_bot = None
symb_list = None
last_price = None
last_stop = None
dict_prev = dict()
dict_curr = dict()
dict_prev_vol = dict()
dict_list = dict()

binance_websocket_api_manager = None


dict_prev_pr = dict()
dict_curr_pr = dict()

limit = dict()

tk = 0
sl = 0
c = 0
dict_order = dict()
dict_pass = dict()
dict_last_price = dict()
dict_start_price = dict()
dict_max_price = dict()
dict_min_price = dict()
dict_wall_a = dict()
dict_wall_b = dict()
dict_prec = dict()
dict_prev_min = dict()
dict_price = dict()
dict_time = dict()
dict_kline = defaultdict(list)
markets = []
profit = 0

dict_book = dict()
dict_trail = dict()
dict_trail_step = dict()

order_price = 0

trade_on = False
trail_step = 0.005

channels = {'kline_1m'}
stream_id = None

def get_klines(symb):
    params = {}
    bin_bot.load_markets()
    market = bin_bot.market(symb)
    request = {'symbol': market['id'], 'interval': bin_bot.timeframes['5m'], }
    request['limit'] = 1  # default == max == 500
    method = 'publicGetKlines' if market['spot'] else 'fapiPublicGetKlines'

    return getattr(bin_bot, method)(bin_bot.extend(request, params))

def get_klines_hour(symb):
    params = {}
    bin_bot.load_markets()
    market = bin_bot.market(symb)
    request = {'symbol': market['id'], 'interval': bin_bot.timeframes['1h'], }
    request['limit'] = 1  # default == max == 500
    method = 'publicGetKlines' if market['spot'] else 'fapiPublicGetKlines'

    return getattr(bin_bot, method)(bin_bot.extend(request, params))

def get_klines1(symb, interval, start, limit):
    params = {}
    bin_bot.load_markets()
    market = bin_bot.market(symb)
    if start is None:
        request = {'symbol': market['id'], 'interval': bin_bot.timeframes[interval], }
    else:
        request = {'symbol': market['id'], 'interval': bin_bot.timeframes[interval], 'startTime': start, }
    request['limit'] = limit  # default == max == 500
    method = 'publicGetKlines' if market['spot'] else 'fapiPublicGetKlines'

    return getattr(bin_bot, method)(bin_bot.extend(request, params))



def start(update, context):
    update.message.reply_text('Hi! Use /set <seconds> to set a timer')


def get_balance(update, context):
    f = bin_bot.fetch_balance()
    for i in f['info']['balances']:
        if i['asset'] == 'USDT':
            update.message.reply_text('Баланс : ' + str(i['free']))


def count(update, context):
    update.message.reply_text(
        'Кол-во пар : ' + str(len(symb_list)) + ', take profit : ' + str(tk) + ', stop loss : ' + str(
            sl) + ', loops : ' + str(c))


def get_orders(update, context):
    mes = ''
    for k in dict_order.keys():
        mes = mes + k + ' : ' + float_to_str(dict_order[k]) + ' ' + float_to_str(
            dict_last_price[k]) + ' ' + float_to_str(round(dict_last_price[k] / dict_order[k] - 1, 4)) + '\n'
    update.message.reply_text(mes)


def set_trade_on(update, context):
    global trade_on
    trade_on = True
    update.message.reply_text('Торговля включена!')


def set_trade_off(update, context):
    global trade_on
    trade_on = False
    update.message.reply_text('Торговля выключена!')


def get_max(update, context):
    mes = ''
    for k in dict_max_price.keys():
        mes = mes + k + ' : ' + float_to_str(dict_start_price[k]) + ' ' + float_to_str(
            dict_max_price[k]) + ' ' + float_to_str(round(dict_max_price[k] / dict_start_price[k] - 1, 4)) + '\n'
    update.message.reply_text(mes)


def get_min(update, context):
    mes = ''
    for k in dict_max_price.keys():
        mes = mes + k + ' : ' + float_to_str(dict_start_price[k]) + ' ' + float_to_str(
            dict_min_price[k]) + ' ' + float_to_str(round(dict_min_price[k] / dict_start_price[k] - 1, 4)) + '\n'
    update.message.reply_text(mes)


def updateData():
    global dict_prev, dict_curr, symb_list, dict_prec
    dict_prev = dict_curr
    dict_curr = dict()
    tickers = bin_bot.fetch_tickers()
    bin_bot.load_markets()
    # for pr in bin_bot.ticker24hr():
    for pr in tickers:
        if tickers[pr]['symbol'][-4:] == 'USDT' and float(tickers[pr]['quoteVolume']) >= 500000 and float(
                tickers[pr]['quoteVolume']) <= 15000000 and float(tickers[pr]['bidVolume']) > 0 and float(
                tickers[pr]['high']) < 20 \
                and tickers[pr]['symbol'] != 'SUSD/USDT' and tickers[pr]['symbol'] != 'LINK/BTC' and tickers[pr][
            'symbol'] != 'DCR/BTC' \
                and tickers[pr]['symbol'] != 'ENG/BTC' and tickers[pr]['symbol'] != 'LEND/BTC' and tickers[pr][
            'symbol'] != 'LUN/BTC' and tickers[pr]['symbol'] != 'PAX/USDT' \
                and tickers[pr]['symbol'].find('DOWN') == -1 and tickers[pr]['symbol'].find('UP') == -1 and tickers[pr][
            'symbol'] != 'PNT/USDT' \
                and tickers[pr]['symbol'] != 'ASR/USDT' and tickers[pr]['symbol'] != 'ATM/USDT' and tickers[pr][
            'symbol'] != 'ACM/USDT' and tickers[pr]['symbol'] != 'TUSD/BTC' and tickers[pr]['symbol'] != 'TUSD/USDT' and \
                tickers[pr]['symbol'] != 'PAX/BTC' and tickers[pr]['symbol'] != 'DAI/BTC' and tickers[pr][
            'symbol'] != 'SUN/USDT' and tickers[pr]['symbol'] != 'PUNDIX/USDT':
            for ppr in tickers:
                if tickers[ppr]['symbol'] == tickers[pr]['symbol'].replace('USDT', 'BTC'):
                    dict_curr[tickers[pr]['symbol']] = float(tickers[ppr]['quoteVolume'])
                    market = bin_bot.market(tickers[pr]['symbol'])
                    dict_prec[tickers[pr]['symbol']] = int(market['precision']['price'])
                    #markets.append(tickers[pr]['symbol'].replace('/', ''))
                    markets.append(tickers[pr]['symbol'].replace('/', ''))
                    dict_list[tickers[pr]['symbol']] = list()
            #b = bin_bot.fetch_open_orders(tickers[pr]['symbol'])
            #for i in b:
            #    dict_order[tickers[pr]['symbol']] = (i['info']['orderId'])
    symb_list = list(dict_curr.keys())
    #markets.append('BTCBUSD')
    #dict_list['BTCBUSD'] = list()

def set_price(update, context):
    """Add a job to the queue."""
    chat_id = update.message.chat_id
    try:
        # args[0] should contain the time for the timer in seconds
        due = int(context.args[0])
        if due < 0:
            update.message.reply_text('Введите положительное значение!')
            return

        global order_price

        order_price = due

        update.message.reply_text('Цена установлена!')

    except (IndexError, ValueError):
        update.message.reply_text('Usage: /set_price <value>')

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
        if len(dict_list) == 0:
            update.message.reply_text('База данных пуста!')
            return

        update.message.reply_text(list(dict_list.keys())[0])
        update.message.reply_text(str(dict_list[list(dict_list.keys())[0]]))

    except (IndexError, ValueError):
        update.message.reply_text('COMMAND ERROR')


def print_stream_data_from_stream_buffer(binance_websocket_api_manager):
    global profit, sl, tk, trade_on, order_price, channels, stream_id, dict_time
    while True:
        if binance_websocket_api_manager.is_manager_stopping():
            exit(0)
        data = binance_websocket_api_manager.pop_stream_data_from_stream_buffer()

        if data is not False:
            if not 'result' in data:
                # if 'depth' in data:
                if 1 == 2:
                    pass
                elif 'kline' in data:
                    data = eval(data.replace('false', 'False').replace('true', 'True'))

                    if 'data' not in data:
                        continue
                    data = data['data']
                    symb = data['s'].replace('USDT', '/USDT')
                    kline = ata['k']
                    t = kline['t']
                    
                    if dict_time[symb] != t:
                        dict_time[symb] = t
                        dict_kline[symb].append(kline)
                        price = 0
                        
                        if len(dict_kline[symb]) > 5 and symb not in dict_order:
                            if len(dict_kline[symb]) > 7:
                                del dict_kline[symb][0]
                            c = 0
                            vol = 0
                            for i, e in reversed(list(enumerate(dict_kline[symb]))):
                                if e['o'] < e['c']:
                                    break
                                if price = 0:
                                    price = e['c']
                                vol += e['Q']
                                c += 1
                                if c == 5:
                                    if vol > dict_curr[symb] * 0.003 and vol < dict_curr[symb] * 0.03 and price / e['o'] < 1.02:
                                        markets_sub = []
                                        markets_sub.append(symb.replace('/', ''))
                                        inance_websocket_api_manager.subscribe_to_stream(stream_id, markets=markets_sub)
                                    break
                else:
                    data = eval(data.replace('false', 'False').replace('true', 'True'))

                    if 'data' not in data:
                        continue
                    data = data['data']
                    symb = data['s'].replace('USDT', '/USDT')
                    t = data['E']

                    if (t / 1000) + 60 < time.time():
                        continue

                    price = float(data['p'])
                    if symb not in dict_order;
                        dict_order[symb] = price
                        dict_trail[symb] = price * 0.99
                        mes = 'Объемы выросли : ' + symb_USDT + ' (F) ' + str(price)
                        updater.bot.send_message(chat_id='-1001242337520', text=mes)
                    if data['s'][-4:] == 'USDT':
                        if data['m']:
                            continue
                        symb = data['s'].replace('USDT', '/USDT')
                        dict_price[symb] = price
                        if symb in dict_order and dict_order[symb][0] < t and not data['m']:
                            dict_max_price[symb] = max(dict_max_price[symb], price)

                            if price < dict_trail[symb]:
                                if trade_on:
                                    try:
                                        order = bin_bot.create_order(symb, 'market', 'sell', dict_order[symb][3], None)

                                        while order['status'] != 'closed':
                                            order = bin_bot.fetch_order(order['id'], symb)

                                            if order['status'] == 'rejected' or order[
                                                'status'] == 'canceled':
                                                break

                                        if order['status'] != 'closed':
                                            continue

                                        price = float(order['price'])
                                    except:
                                        pass

                                if price > dict_order[symb][1] * 1.0015:
                                    profit += (price / (dict_order[symb][1] * 1.0015) - 1)
                                    tk += 1
                                    dict_pass[symb] = t
                                    updater.bot.send_message(chat_id='-1001242337520',
                                                             text='Профит ' + symb + ' ' + float_to_str(price / (
                                                                         dict_order[symb][
                                                                             1] * 1.0015) - 1) + ' баланс ' + float_to_str(
                                                                 profit) + ' ' + float_to_str(price) + ' ' + float_to_str(dict_trail[symb]))
                                    del dict_order[symb]

                                else:
                                    profit += (price / (dict_order[symb][1] * 1.0015) - 1)
                                    sl += 1
                                    tk = 0
                                    dict_pass[symb] = t
                                    updater.bot.send_message(chat_id='-1001242337520',
                                                             text='Убыток ' + symb + ' ' + float_to_str(price / (
                                                                         dict_order[symb][
                                                                             1] * 1.0015) - 1) + ' баланс ' + float_to_str(
                                                                 profit) + ' ' + float_to_str(price) + ' ' + float_to_str(dict_trail[symb]))
                                    del dict_order[symb]

                                markets_sub = []
                                markets_sub.append(symb.replace('/', ''))

                                binance_websocket_api_manager.unsubscribe_from_stream(stream_id, markets=markets_sub)
                            else:
                                if (t - dict_order[symb][0]) / 1000 > 300:
                                    if price > dict_order[symb][1] * 1.0015 and dict_trail[symb] < dict_order[symb][
                                        1] * 1.0015:
                                        profit += (price / (dict_order[symb][1] * 1.0015) - 1)
                                        tk += 1
                                        dict_pass[symb] = t
                                        if trade_on:
                                            try:
                                                order = bin_bot.create_order(symb, 'market', 'sell',
                                                                             dict_order[symb][3], None)

                                                while order['status'] != 'closed':
                                                    order = bin_bot.fetch_order(order['id'], symb)

                                                    if order['status'] == 'rejected' or order[
                                                        'status'] == 'canceled':
                                                        break

                                                if order['status'] != 'closed':
                                                    continue

                                                price = float(order['price'])
                                            except:
                                                pass

                                        updater.bot.send_message(chat_id='-1001242337520',
                                                                 text='Профит ' + symb + ' ' + float_to_str(
                                                                     price / (dict_order[symb][
                                                                                  1] * 1.0015) - 1) + ' баланс ' + float_to_str(
                                                                     profit) + ' ' + float_to_str(price) + ' ' + float_to_str(dict_trail[symb]))
                                        del dict_order[symb]
                                        dict_pass[symb] = t
                                        markets_sub = []
                                        markets_sub.append(symb.replace('/', ''))

                                        binance_websocket_api_manager.unsubscribe_from_stream(stream_id,
                                                                                          markets=markets_sub)
                                        continue
                                if 1 == 1:
                                    if price < dict_order[symb][1] * 1.008:
                                        if dict_order[symb][1] * ((price / dict_order[symb][1]) * 0.992) > dict_trail[
                                            symb] and ((dict_order[symb][1] * ((price / dict_order[symb][1]) * 0.992)) /
                                                       dict_trail[symb]) - 1 > 0.001:
                                            dict_trail[symb] = dict_order[symb][1] * (
                                                        (price / dict_order[symb][1]) * 0.992)
                                    else:
                                        if dict_order[symb][1] * ((price / dict_order[symb][1]) * 0.995) > dict_trail[
                                            symb] and ((dict_order[symb][1] * ((price / dict_order[symb][1]) * 0.995)) /
                                                       dict_trail[symb]) - 1 > 0.001:
                                            dict_trail[symb] = dict_order[symb][1] * (
                                                        (price / dict_order[symb][1]) * 0.995)

                        if symb in dict_pass:
                            if (t - dict_pass[symb]) / 1000 > 1800:
                                del dict_pass[symb]
                    elif 1 == 2:
                        symb = data['s'][:-3]
                        symb = symb + "/BTC"
                        symb_USDT = symb.replace('/BTC', '/USDT')
                        if symb_USDT not in dict_order and symb_USDT not in dict_pass:
                            q = float(data['q'])

                            vol = q * price

                            if data['m']:
                                vol = -vol

                            prevVol = vol
                            step = 2

                            for i, e in reversed(list(enumerate(dict_list[symb]))):
                                if (t - e[0]) / 1000 <= 30:
                                    prevVol += e[1]
                                elif (t - e[0]) / 1000 <= 45:
                                    if step == 2:
                                        if prevVol >= dict_curr[symb] * (0.015 * (30/60)) and price / e[2] > 1.001:
                                            inf = get_klines1(symb_USDT, '1m', None, 5)
                                            price = float(inf[4][4])
                                            min_price = 999
                                            max_price = 0

                                            for d in inf:
                                                max_price = max(max_price, float(d[2]))
                                                min_price = min(min_price, float(d[3]))

                                            if max(max_price, price) / min_price < 1.03 and max_price / min_price > 1.005:

                                                #hour = get_klines1(symb_USDT, '1m', int((time.time() - 3600) * 1000), 1)
                                                if 1 == 1:#price / float(hour[0][1]) < 1.10 and price / float(hour[0][1]) > 1.01:
                                                    print(inf)
                                                    amount = int(order_price / price)
                                                    type = 'market'  # or market
                                                    side = 'buy'
                                                    err = False

                                                    mes = 'Объемы выросли : ' + symb_USDT + ' (F) ' + str(price)

                                                    if trade_on:
                                                        try:
                                                            order = bin_bot.create_order(symb_USDT, type, side, amount, None)

                                                            while order['status'] != 'closed':
                                                                order = bin_bot.fetch_order(order['id'], symb_USDT)

                                                                if order['status'] == 'rejected' or order[
                                                                    'status'] == 'canceled':
                                                                    break

                                                            if order['status'] != 'closed':
                                                                continue

                                                            price = float(order['price'])
                                                            mes = 'Объемы выросли : ' + symb_USDT + ' ($) ' + str(price)
                                                        except:
                                                            err = True
                                                            mes = 'Объемы выросли : ' + symb_USDT + ' (F) ' + str(price)

                                                    dict_order[symb_USDT] = price
                                                    n = dict_prec[symb_USDT]

                                                    dict_order[symb_USDT] = (t, price, None, amount)
                                                    dict_trail[symb_USDT] = price * 0.99
                                                    dict_trail_step[symb_USDT] = 0
                                                    dict_max_price[symb_USDT] = price

                                                    markets_sub = []
                                                    markets_sub.append(symb_USDT.replace('/', ''))

                                                    binance_websocket_api_manager.subscribe_to_stream(stream_id, markets=markets_sub)

                                                    updater.bot.send_message(chat_id='-1001242337520', text=mes)
                                                    print(mes + ' ' + datetime.today().strftime(
                                                    '%Y-%m-%d-%H:%M:%S') + ' ' + str(t))
                                                    print('30 ' +str(prevVol / (dict_curr[symb] * 0.021)))
                                                    break

                                    step = 3
                                    prevVol += e[1]
                                elif (t - e[0]) / 1000 <= 60:
                                    if step == 3:
                                        if prevVol >= dict_curr[symb] * (0.015 * (45/60)) and price / e[2] > 1.001:
                                            inf = get_klines1(symb_USDT, '1m', None, 5)
                                            min_price = 999
                                            max_price = 0
                                            price = float(inf[4][4])

                                            for d in inf:
                                                max_price = max(max_price, float(d[2]))
                                                min_price = min(min_price, float(d[3]))

                                            if max(max_price,
                                                   price) / min_price < 1.03 and max_price / min_price > 1.005:

                                                #hour = get_klines1(symb_USDT, '1m', int((time.time() - 3600) * 1000), 1)
                                                if 1 == 1:#price / float(hour[0][1]) < 1.10 and price / float(hour[0][1]) > 1.01:
                                                    print(inf)
                                                    amount = int(order_price / price)
                                                    type = 'market'  # or market
                                                    side = 'buy'
                                                    err = False
                                                    mes = 'Объемы выросли : ' + symb_USDT + ' (F) ' + str(price)
                                                    if trade_on:
                                                        try:
                                                            order = bin_bot.create_order(symb_USDT, type, side, amount, None)

                                                            while order['status'] != 'closed':
                                                                order = bin_bot.fetch_order(order['id'], symb_USDT)

                                                                if order['status'] == 'rejected' or order[
                                                                    'status'] == 'canceled':
                                                                    break

                                                            if order['status'] != 'closed':
                                                                continue

                                                            price = float(order['price'])
                                                            mes = 'Объемы выросли : ' + symb_USDT + ' ($) ' + str(price)
                                                        except:
                                                            err = True
                                                            mes = 'Объемы выросли : ' + symb_USDT + ' (F) ' + str(price)

                                                    dict_order[symb_USDT] = price
                                                    n = dict_prec[symb_USDT]

                                                    dict_order[symb_USDT] = (t, price, None, amount)
                                                    dict_trail[symb_USDT] = price * 0.99
                                                    dict_trail_step[symb_USDT] = 0
                                                    dict_max_price[symb_USDT] = price

                                                    markets_sub = []
                                                    markets_sub.append(symb_USDT.replace('/', ''))

                                                    binance_websocket_api_manager.subscribe_to_stream(stream_id, markets=markets_sub)

                                                    updater.bot.send_message(chat_id='-1001242337520', text=mes)
                                                    print(mes + ' ' + datetime.today().strftime(
                                                    '%Y-%m-%d-%H:%M:%S') + ' ' + str(t))
                                                    print('45 ' + str(prevVol / (dict_curr[symb] * 0.027)))
                                                    break
                                    step = 4
                                    prevVol += e[1]

                                elif (t - e[0]) / 1000 > 300:
                                    del dict_list[symb][0:i]
                                    break

                            dict_list[symb].append((t, vol, price))

        else:
            time.sleep(0.01)

URL = os.environ.get('URL')
PORT = int(os.environ.get('PORT', '5000'))
TOKEN = os.environ['TEL_TOKEN']

updater = Updater(TOKEN, use_context=True)

updater.dispatcher.add_handler(CommandHandler('hello', hello, pass_chat_data=True))
updater.dispatcher.add_handler(CommandHandler('get', get_vol, pass_args=True, pass_chat_data=True))
updater.dispatcher.add_handler(CommandHandler('set_price', set_price, pass_args=True, pass_chat_data=True))
updater.dispatcher.add_handler(CommandHandler('gettop', get_top, pass_chat_data=True))
updater.dispatcher.add_handler(CommandHandler('unset', unset, pass_chat_data=True))
updater.dispatcher.add_handler(CommandHandler('count', count, pass_chat_data=True))
updater.dispatcher.add_handler(CommandHandler('orders', get_orders, pass_chat_data=True))
updater.dispatcher.add_handler(CommandHandler('max', get_max, pass_chat_data=True))
updater.dispatcher.add_handler(CommandHandler('min', get_min, pass_chat_data=True))
updater.dispatcher.add_handler(CommandHandler('trade_on', set_trade_on, pass_chat_data=True))
updater.dispatcher.add_handler(CommandHandler('trade_off', set_trade_off, pass_chat_data=True))
updater.dispatcher.add_handler(CommandHandler('balance', get_balance, pass_chat_data=True))

updater.start_webhook(listen='0.0.0.0', port=PORT, url_path=TOKEN)
updater.bot.set_webhook(URL + TOKEN)

bin_bot = ccxt.binance({
    'apiKey': os.environ['API_KEY'],
    'secret': os.environ['API_SECRET'],
    'enableRateLimit': True,
})

updateData()

binance_websocket_api_manager = unicorn_binance_websocket_api.BinanceWebSocketApiManager()

# start a worker process to move the received stream_data from the stream_buffer to a print function
worker_thread = threading.Thread(target=print_stream_data_from_stream_buffer, args=(binance_websocket_api_manager,))
worker_thread.start()
divisor = math.ceil(len(markets) / binance_websocket_api_manager.get_limit_of_subscriptions_per_stream())
max_subscriptions = math.ceil(len(markets) / divisor)
print(max_subscriptions)
for channel in channels:
    if len(markets) <= max_subscriptions:
        stream_id = binance_websocket_api_manager.create_stream(channel, markets, stream_label=channel)
    else:
        loops = 1
        i = 1
        markets_sub = []
        for market in markets:
            markets_sub.append(market)
            if i == max_subscriptions or loops*max_subscriptions + i == len(markets):
                stream_id = binance_websocket_api_manager.create_stream(channel, markets_sub, stream_label=str(channel+"_"+str(i)),
                                                            ping_interval=10, ping_timeout=10, close_timeout=5)
                markets_sub = []
                i = 1
                loops += 1
            i += 1
updater.bot.send_message(chat_id='-1001242337520', text='Запуск!')

updater.idle()
