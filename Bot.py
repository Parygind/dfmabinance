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
markets = []
profit = 0

dict_book = dict()
dict_trail = dict()
dict_trail_step = dict()

order_price = 0

trade_on = False
trail_step = 0.005


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
                    dict_curr[tickers[pr]['symbol']] = float(tickers[pr]['quoteVolume'])
                    market = bin_bot.market(tickers[pr]['symbol'])
                    dict_prec[tickers[pr]['symbol']] = int(market['precision']['price'])
                    markets.append(tickers[pr]['symbol'].replace('/', ''))
                    dict_list[tickers[pr]['symbol']] = list()
            #b = bin_bot.fetch_open_orders(tickers[pr]['symbol'])
            #for i in b:
            #    dict_order[tickers[pr]['symbol']] = (i['info']['orderId'])
    symb_list = list(dict_curr.keys())
    #markets.append('BTCBUSD')
    #dict_list['BTCBUSD'] = list()

def alarm2(context):
    """Send the alarm message."""
    mesVol = ''
    mesOrd = ''
    mesShort = ''
    job = context.job
    global dict_prev, dict_curr, symb_list, c, tk, sl, dict_order, dict_pass, dict_prec, dict_start_price, dict_max_price, dict_min_price, dict_prev_vol, dict_prev_min, trade_on

    for i in range(0, int(len(symb_list))):
        inf = get_klines(symb_list[i])
        vol = float(inf[0][10])
        course = float(inf[0][4])

        prev_min = 0

        if symb_list[i] in dict_prev_min:
            prev_min = dict_prev_min[symb_list[i]]
        else:
            prev_min = float(inf[0][3])

        dict_last_price[symb_list[i]] = course

        if symb_list[i] in dict_start_price:
            dict_max_price[symb_list[i]] = max(dict_max_price[symb_list[i]], float(inf[0][2]))
            dict_min_price[symb_list[i]] = min(dict_min_price[symb_list[i]], float(inf[0][3]))

        if symb_list[i] in dict_pass:
            dict_pass[symb_list[i]] -= 1
            if dict_pass[symb_list[i]] < 1:
                del dict_pass[symb_list[i]]

        if symb_list[i] in dict_order:
            if dict_max_price[symb_list[i]] >= dict_order[symb_list[i]] * 1.01:
                tk = tk + 1
                mesOrd = mesOrd + 'Профит ' + symb_list[i] + ' ' + float_to_str(
                    dict_order[symb_list[i]]) + ' ' + float_to_str(course) + ' '
                del dict_order[symb_list[i]]
                dict_pass[symb_list[i]] = 60

            elif dict_min_price[symb_list[i]] <= dict_order[symb_list[i]] * 0.96:
                sl = sl + 1
                mesOrd = mesOrd + 'Убыток ' + symb_list[i] + ' ' + float_to_str(
                    dict_order[symb_list[i]]) + ' ' + float_to_str(course) + ' '
                del dict_order[symb_list[i]]
                dict_pass[symb_list[i]] = 60

        if vol >= dict_curr[symb_list[i]] * 0.0215 and float(inf[0][2]) / float(inf[0][1]) < 1.07 and float(
                inf[0][2]) / float(inf[0][1]) > 1 and float(inf[0][4]) / float(inf[0][1]) > 0.96 and float(
                inf[0][2]) / float(inf[0][3]) > 1.01 and float(inf[0][2]) / prev_min > 1.01 and float(
                inf[0][2]) / prev_min < 1.04 and len(dict_order) < 7:
            passPair = False
            if symb_list[i] in dict_max_price:
                if dict_max_price[symb_list[i]] <= course:
                    passPair = True
            if not symb_list[i] in dict_order and not symb_list[i] in dict_pass and not passPair:

                amount = int(order_price / course)
                type = 'market'  # or market
                side = 'buy'
                err = False

                if trade_on:
                    try:
                        order = bin_bot.create_order(symb_list[i], type, side, amount, None)

                        while order['status'] != 'closed':
                            order = bin_bot.fetch_order(order['id'], symb_list[i])

                            if order['status'] == 'rejected' or order['status'] == 'canceled':
                                break

                        if order['status'] != 'closed':
                            continue

                        price = float(order['price'])
                    except:
                        err = True
                        price = course
                else:
                    price = course

                dict_order[symb_list[i]] = price
                n = dict_prec[symb_list[i]]
                take_profit = float_to_str(round(price * 1.01, n))
                stop_loss = float_to_str(round(price * 0.96, n))
                type = 'limit'
                side = 'sell'

                if trade_on and not err:
                    order = bin_bot.create_order(symb_list[i], type, side, amount, take_profit)
                '''
                try:
                    order = bin_bot.private_post_order_oco(
                        {"symbol": symb_list[i].replace('/', ''), "side": "sell", "quantity": amount,
                         "price": take_profit, "stopPrice": stop_loss,
                         "stopLimitPrice": stop_loss, "stopLimitTimeInForce": "GTC"})
                except:
                    type = 'market'
                    order = bin_bot.create_order(symb_list[i], type, side, amount, take_profit)
                '''

                dict_start_price[symb_list[i]] = price
                dict_max_price[symb_list[i]] = price
                dict_min_price[symb_list[i]] = price

                if not trade_on or err:
                    mesVol += symb_list[i] + ' (F) (+' + str(round(vol, 2)) + ' / ' + str(
                        round((vol / dict_curr[symb_list[i]]) * 100, 2)) + '%, ' + str(price) + ' ' + str(
                        course) + ' ' + str(course / float(inf[0][1])) + ' ' + str(
                        float(inf[0][2]) / float(inf[0][1])) + ' ' + str(
                        float(inf[0][2]) / float(inf[0][3])) + ' ' + str(float(inf[0][2]) / prev_min) + ')\n'
                else:
                    mesVol += symb_list[i] + ' ($) (+' + str(round(vol, 2)) + ' / ' + str(
                        round((vol / dict_curr[symb_list[i]]) * 100, 2)) + '%, ' + str(price) + ' ' + str(
                        course) + ' ' + str(course / float(inf[0][1])) + ' ' + str(
                        float(inf[0][2]) / float(inf[0][1])) + ' ' + str(
                        float(inf[0][2]) / float(inf[0][3])) + ' ' + str(float(inf[0][2]) / prev_min) + ')\n'



        elif c > 0 and dict_prev_vol.get(symb_list[i]) != None:
            if vol + dict_prev_vol[symb_list[i]] >= dict_curr[symb_list[i]] * 0.022 and vol < dict_curr[
                symb_list[i]] * 0.0215 and float(inf[0][2]) / float(inf[0][1]) < 1.06 and float(inf[0][2]) / float(
                    inf[0][1]) > 1 and float(inf[0][4]) / float(inf[0][1]) > 0.96 and float(inf[0][2]) / float(
                    inf[0][3]) > 1.01 and float(inf[0][2]) / prev_min > 1.01 and float(
                    inf[0][2]) / prev_min < 1.04 and len(dict_order) < 7:
                passPair = False
                if symb_list[i] in dict_max_price:
                    if dict_max_price[symb_list[i]] <= course:
                        passPair = True
                if not symb_list[i] in dict_order and not symb_list[i] in dict_pass and not passPair:

                    amount = int(order_price / course)
                    type = 'market'  # or market
                    side = 'buy'
                    err = False

                    if trade_on:
                        try:
                            order = bin_bot.create_order(symb_list[i], type, side, amount, None)

                            while order['status'] != 'closed':
                                order = bin_bot.fetch_order(order['id'], symb_list[i])

                                if order['status'] == 'rejected' or order['status'] == 'canceled':
                                    break

                            if order['status'] != 'closed':
                                continue

                            price = float(order['price'])
                        except:
                            err = True
                            price = course
                    else:
                        price = course

                    dict_order[symb_list[i]] = price
                    n = dict_prec[symb_list[i]]
                    take_profit = float_to_str(round(price * 1.01, n))
                    stop_loss = float_to_str(round(price * 0.96, n))
                    type = 'limit'
                    side = 'sell'
                    if trade_on and not err:
                        order = bin_bot.create_order(symb_list[i], type, side, amount, take_profit)

                    dict_start_price[symb_list[i]] = price
                    dict_max_price[symb_list[i]] = price
                    dict_min_price[symb_list[i]] = price

                    if not trade_on or err:
                        mesVol += symb_list[i] + ' (F) TEST (+' + str(
                            round(vol + dict_prev_vol[symb_list[i]], 2)) + ' / ' + str(
                            round(((vol + dict_prev_vol[symb_list[i]]) / dict_curr[symb_list[i]]) * 100,
                                  2)) + '%, ' + str(float(inf[0][4])) + ' ' + str(course) + ' ' + str(
                            course / float(inf[0][1])) + ' ' + str(float(inf[0][2]) / float(inf[0][1])) + ' ' + str(
                            float(inf[0][2]) / float(inf[0][3])) + ' ' + str(float(inf[0][2]) / prev_min) + ')\n'
                    else:
                        mesVol += symb_list[i] + ' ($) TEST (+' + str(
                            round(vol + dict_prev_vol[symb_list[i]], 2)) + ' / ' + str(
                            round(((vol + dict_prev_vol[symb_list[i]]) / dict_curr[symb_list[i]]) * 100,
                                  2)) + '%, ' + str(float(inf[0][4])) + ' ' + str(course) + ' ' + str(
                            course / float(inf[0][1])) + ' ' + str(float(inf[0][2]) / float(inf[0][1])) + ' ' + str(
                            float(inf[0][2]) / float(inf[0][3])) + ' ' + str(float(inf[0][2]) / prev_min) + ')\n'
            elif vol >= dict_curr[symb_list[i]] * 0.02 and not symb_list[i] in dict_start_price:
                dict_start_price[symb_list[i]] = course
                dict_max_price[symb_list[i]] = course
                dict_min_price[symb_list[i]] = course
                dict_pass[symb_list[i]] = 60
                mesShort += symb_list[i] + '(+' + str(round(vol, 2)) + ' / ' + str(
                    round((vol / dict_curr[symb_list[i]]) * 100, 2)) + '%, ' + str(course) + ' ' + str(
                    course / float(inf[0][1])) + ' ' + str(float(inf[0][2]) / float(inf[0][1])) + ' ' + str(
                    float(inf[0][2]) / float(inf[0][3])) + ' ' + str(float(inf[0][2]) / prev_min) + ')\n'
            elif c > 0:
                if vol + dict_prev_vol[symb_list[i]] >= dict_curr[symb_list[i]] * 0.0215 and not symb_list[i] in dict_start_price:
                    dict_start_price[symb_list[i]] = course
                    dict_max_price[symb_list[i]] = course
                    dict_min_price[symb_list[i]] = course
                    dict_pass[symb_list[i]] = 60
                    mesShort += symb_list[i] + 'TEST (+' + str(
                        round(vol + dict_prev_vol[symb_list[i]], 2)) + ' / ' + str(
                        round(((vol + dict_prev_vol[symb_list[i]]) / dict_curr[symb_list[i]]) * 100, 2)) + '%, ' + str(
                        course) + ' ' + str(course / float(inf[0][1])) + ' ' + str(
                        float(inf[0][2]) / float(inf[0][1])) + ' ' + str(
                        float(inf[0][2]) / float(inf[0][3])) + ' ' + str(float(inf[0][2]) / prev_min) + ')\n'

        dict_prev_vol[symb_list[i]] = vol
        dict_prev_min[symb_list[i]] = float(inf[0][3])
    c += 1

    if len(mesVol) > 0:
        mes = 'Объемы выросли : ' + mesVol
        context.bot.send_message(chat_id='-1001242337520', text=mes)
    if len(mesOrd) > 0:
        mes = 'Сделки закрыты : ' + mesOrd
        context.bot.send_message(chat_id='-1001242337520', text=mes)
    if len(mesShort) > 0:
        mes = 'Можно шортануть : ' + mesShort
        context.bot.send_message(chat_id='-1001242337520', text=mes)

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
            'apiKey': os.environ['API_KEY'],
            'secret': os.environ['API_SECRET'],
            'enableRateLimit': True,
        })

        job = context.job_queue.run_repeating(updateData, due, first=0, context=chat_id)
        job = context.job_queue.run_repeating(alarm2, 60, first=20, context=chat_id)
        # job = context.job_queue.run_repeating(alarm2, 120, first=70, context=chat_id)
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
        if len(dict_list) == 0:
            update.message.reply_text('База данных пуста!')
            return

        update.message.reply_text(list(dict_list.keys())[0])
        update.message.reply_text(str(dict_list[list(dict_list.keys())[0]]))

    except (IndexError, ValueError):
        update.message.reply_text('COMMAND ERROR')


def print_stream_data_from_stream_buffer(binance_websocket_api_manager):
    global profit, sl, tk, trade_on, order_price
    while True:
        if binance_websocket_api_manager.is_manager_stopping():
            exit(0)
        data = binance_websocket_api_manager.pop_stream_data_from_stream_buffer()

        if data is not False:
            if not 'result' in data:
                # if 'depth' in data:
                if 1 == 2:
                    pass
                else:
                    data = eval(data.replace('false', 'False').replace('true', 'True'))

                    data = data['data']
                    t = data['E']

                    if (t / 1000) + 60 < time.time():
                        continue

                    if data['m']:
                        continue

                    symb = data['s'].replace('USDT', '/USDT')
                    price = float(data['p'])
                    if symb in dict_order and dict_order[symb][0] < t and not data['m']:
                        dict_max_price[symb] = max(dict_max_price[symb], price)
                        #trail

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
                                                         text='Профит ' + symb + ' ' + float_to_str(price / (dict_order[symb][1] * 1.0015) - 1) + ' баланс ' + float_to_str(
                                                             profit))
                                del dict_order[symb]
                                continue
                            else:
                                profit += (price / (dict_order[symb][1] * 1.0015) - 1)
                                sl += 1
                                tk = 0
                                dict_pass[symb] = t
                                updater.bot.send_message(chat_id='-1001242337520',
                                                         text='Убыток ' + symb + ' ' + float_to_str(price / (dict_order[symb][1] * 1.0015) - 1) + ' баланс ' + float_to_str(
                                                             profit))
                                del dict_order[symb]
                                continue
                        else:
                            if (t - dict_order[symb][0]) / 1000 > 300:
                                if price > dict_order[symb][1] * 1.0015 and dict_trail[symb] < dict_order[symb][1] * 1.0015:
                                    profit += (price / (dict_order[symb][1] * 1.0015) - 1)
                                    tk += 1
                                    dict_pass[symb] = t
                                    if trade_on:
                                        '''
                                        try:
                                            bin_bot.cancel_order(dict_order[symb][2], symb)
                                        except:
                                            pass
                                        '''
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

                                    updater.bot.send_message(chat_id='-1001242337520',
                                                             text='Профит ' + symb + ' ' + float_to_str(
                                                                 price / (dict_order[symb][
                                                                                         1] * 1.0015) - 1) + ' баланс ' + float_to_str(
                                                                 profit))
                                    del dict_order[symb]
                                    continue
                            if dict_trail_step[symb] == 0:
                                if price < dict_order[symb][1] * 1.008:
                                    if dict_order[symb][1] * ((price / dict_order[symb][1]) * 0.992) > dict_trail[symb] and ((dict_order[symb][1] * ((price / dict_order[symb][1]) * 0.992)) / dict_trail[symb]) - 1 > 0.001:
                                        dict_trail[symb] = dict_order[symb][1] * ((price / dict_order[symb][1]) * 0.992)
                                        '''
                                        if trade_on:
                                            try:
                                                bin_bot.cancel_order(dict_order[symb][2], symb)
                                            except:
                                                pass
                                            params = {'stopPrice': dict_trail[symb]}
                                            bb = dict_order[symb]
                                            order = bin_bot.createOrder(symb, 'STOP_LOSS', 'sell',
                                                                        dict_order[symb][3], None, params)
                                            bbb = (bb[0], bb[1], order['info']['orderId'], bb[3])
                                            dict_order[symb] = bbb
                                        '''
                                else:
                                    if dict_order[symb][1] * ((price / dict_order[symb][1]) * 0.995) > dict_trail[symb] and ((dict_order[symb][1] * ((price / dict_order[symb][1]) * 0.995)) / dict_trail[symb]) - 1 > 0.001:
                                        dict_trail[symb] = dict_order[symb][1] * ((price / dict_order[symb][1]) * 0.995)
                                        '''
                                        if trade_on:
                                            try:
                                                bin_bot.cancel_order(dict_order[symb][2], symb)
                                            except:
                                                pass
                                            params = {'stopPrice': dict_trail[symb]}
                                            bb = dict_order[symb]
                                            order = bin_bot.createOrder(symb, 'STOP_LOSS', 'sell',
                                                                        dict_order[symb][3], None, params)
                                            bbb = (bb[0], bb[1], order['info']['orderId'], bb[3])
                                            dict_order[symb] = bbb
                                        '''

                        #elif price > dict_trail[symb] * (1 + trail_step * 2):
                        #    dict_trail[symb] = dict_trail[symb] * (1 + trail_step)

                        if price > dict_order[symb][1] * 1.005 and 1 == 2:
                            profit += 0.0035
                            tk += 1
                            if not trade_on and tk > 2 and order_price > 0:
                                trade_on = True
                                sl = 0
                                tk = 0
                            del dict_order[symb]
                            dict_pass[symb] = t
                            updater.bot.send_message(chat_id='-1001242337520', text='Профит ' + symb + ' ' + str(price) + ' баланс ' + str(profit))
                        elif price < dict_order[symb][1] * 0.96 and 1 == 2:
                            profit -= 0.0415
                            sl += 1
                            tk = 0
                            if sl > 100:
                                trade_on = False
                                sl = 0
                            del dict_order[symb]
                            dict_pass[symb] = t
                            updater.bot.send_message(chat_id='-1001242337520',
                                                     text='Убыток ' + symb + ' ' + str(price) + ' баланс ' + str(profit))

                        elif (t - dict_order[symb][0]) / 1000 > 3600 and 1 == 2:
                            if trade_on:
                                try:
                                    bin_bot.cancel_order(dict_order[symb][2], symb)

                                    amount = 0
                                    for i in bin_bot.fetch_balance()['info']['balances']:
                                        if i['asset'] == symb.replace('/USDT', ''):
                                            amount = float(i['free'])

                                            type = 'market'  # or market
                                            side = 'sell'

                                            order = bin_bot.create_order(symb, type, side, amount, None)

                                            break
                                except Exception as e:
                                    updater.bot.send_message(chat_id='-1001242337520', text=str(e))

                            if price > dict_order[symb][1]:
                                profit += (price / dict_order[symb][1] - 1)
                                profit -= 0.0015
                                updater.bot.send_message(chat_id='-1001242337520', text='Профит! ' + symb + ' ' + str(price) + ' баланс ' + str(profit))
                            else:
                                profit -= (1 - price / dict_order[symb][1])
                                profit -= 0.0015
                                updater.bot.send_message(chat_id='-1001242337520',
                                                         text='Убыток! ' + symb + ' ' + str(price) + ' баланс ' + str(profit))

                            del dict_order[symb]
                            dict_pass[symb] = t

                    if symb in dict_pass:
                        if (t - dict_pass[symb]) / 1000 > 18000:
                            del dict_pass[symb]

                    if symb not in dict_min_price:
                        dict_min_price[symb] = price

                    if symb not in dict_order and symb not in dict_pass and symb != 'BTCBUSD':
                        q = float(data['q'])
                        vol = q * price
                        prevVol = vol
                        step = 2
                        for i, e in reversed(list(enumerate(dict_list[symb]))):
                            if (t - e[0]) / 1000 <= 30:
                                prevVol += e[1]
                            elif (t - e[0]) / 1000 <= 45:
                                if step == 2:
                                    if prevVol >= dict_curr[symb] * (0.011 * (30/60)) and price / dict_list[symb][0][2] > 1.005:
                                        inf = get_klines1(symb, '1m', int((time.time() - 300) * 1000), 5)
                                        min_price = 999
                                        max_price = 0

                                        for d in inf:
                                            max_price = max(max_price, float(d[2]))
                                            min_price = min(min_price, float(d[3]))

                                        if max(max_price, price) / min_price < 1.04 and max_price / min_price > 1.01 and price / float(
                                            inf[0][1]) > 1:

                                            inf = get_klines1(symb.replace('USDT', 'BTC'), '1m', None, 5)

                                            hour = get_klines1(symb, '1m', int((time.time() - 3600) * 1000), 1)
                                            if price / float(hour[0][1]) < 1.10 and price / float(hour[0][1]) > 1.01 and float(inf[4][4]) / float(inf[0][1]) > 1.01:
                                                print(inf)
                                                amount = int(order_price / price)
                                                type = 'market'  # or market
                                                side = 'buy'
                                                err = False

                                                mes = 'Объемы выросли : ' + symb + ' (F) ' + str(price)

                                                if trade_on and len(dict_order) < 3:
                                                    try:
                                                        order = bin_bot.create_order(symb, type, side, amount, None)

                                                        while order['status'] != 'closed':
                                                            order = bin_bot.fetch_order(order['id'], symb)

                                                            if order['status'] == 'rejected' or order[
                                                                'status'] == 'canceled':
                                                                break

                                                        if order['status'] != 'closed':
                                                            continue

                                                        price = float(order['price'])
                                                        mes = 'Объемы выросли : ' + symb + ' ($) ' + str(price)
                                                    except:
                                                        err = True
                                                        mes = 'Объемы выросли : ' + symb + ' (F) ' + str(price)

                                                dict_order[symb] = price
                                                n = dict_prec[symb]
                                                take_profit = float_to_str(round(price * 1.005, n))
                                                stop_loss = float_to_str(round(price * 0.96, n))
                                                type = 'limit'
                                                side = 'sell'

                                                dict_order[symb] = (t, price, None, amount)
                                                dict_trail[symb] = price * 0.99
                                                dict_trail_step[symb] = 0
                                                dict_max_price[symb] = price
                                                '''
                                                if trade_on and not err and len(dict_order) < 3:
                                                    try:
                                                        params = {'stopPrice': price * 0.99}
                                                        order = bin_bot.createOrder(symb, 'STOP_LOSS', 'sell',
                                                                                     amount, None, params)
                                                        print(str(order))
                                                        
                                                        order = bin_bot.private_post_order_oco(
                                                            {"symbol": symb.replace('/', ''), "side": "sell",
                                                             "quantity": amount,
                                                             "price": take_profit, "stopPrice": stop_loss,
                                                             "stopLimitPrice": stop_loss, "stopLimitTimeInForce": "GTC"})
                                                        
                                                        dict_order[symb] = (t, price, order['info']['orderId'], amount)
                                                    except:
                                                        type = 'market'
                                                        order = bin_bot.create_order(symb, type, side, amount,
                                                                                     take_profit)
                                                '''
                                                updater.bot.send_message(chat_id='-1001242337520', text=mes)
                                                print(mes + ' ' + datetime.today().strftime(
                                                '%Y-%m-%d-%H:%M:%S') + ' ' + str(t))
                                                print(hour)
                                                print(inf)
                                                print('30 ' +str(prevVol / (dict_curr[symb] * 0.021)))
                                                break
                                            elif price / float(hour[0][1]) < 1.10 and price / float(hour[0][1]) > 1.01:
                                                dict_pass[symb] = t - 17900 * 1000

                                step = 3
                                prevVol += e[1]
                            elif (t - e[0]) / 1000 <= 60:
                                if step == 3:
                                    if prevVol >= dict_curr[symb] * (0.011 * (45/60))  and price / dict_list[symb][0][2] > 1.005:
                                        inf = get_klines1(symb, '1m', int((time.time() - 300) * 1000), 5)
                                        min_price = 999
                                        max_price = 0

                                        for d in inf:
                                            max_price = max(max_price, float(d[2]))
                                            min_price = min(min_price, float(d[3]))

                                        if max(max_price,
                                               price) / min_price < 1.04 and max_price / min_price > 1.01 and price / float(
                                                inf[0][1]) > 1:
                                            inf = get_klines1(symb.replace('USDT', 'BTC'), '1m',
                                                              None, 5)

                                            hour = get_klines1(symb, '1m', int((time.time() - 3600) * 1000), 1)
                                            if price / float(hour[0][1]) < 1.10 and price / float(hour[0][1]) > 1.01 and float(inf[4][4]) / float(inf[0][1]) > 1.01:
                                                print(inf)
                                                amount = int(order_price / price)
                                                type = 'market'  # or market
                                                side = 'buy'
                                                err = False
                                                mes = 'Объемы выросли : ' + symb + ' (F) ' + str(price)
                                                if trade_on and len(dict_order) < 3:
                                                    try:
                                                        order = bin_bot.create_order(symb, type, side, amount, None)

                                                        while order['status'] != 'closed':
                                                            order = bin_bot.fetch_order(order['id'], symb)

                                                            if order['status'] == 'rejected' or order[
                                                                'status'] == 'canceled':
                                                                break

                                                        if order['status'] != 'closed':
                                                            continue

                                                        price = float(order['price'])
                                                        mes = 'Объемы выросли : ' + symb + ' ($) ' + str(price)
                                                    except:
                                                        err = True
                                                        mes = 'Объемы выросли : ' + symb + ' (F) ' + str(price)

                                                dict_order[symb] = price
                                                n = dict_prec[symb]
                                                take_profit = float_to_str(round(price * 1.005, n))
                                                stop_loss = float_to_str(round(price * 0.96, n))
                                                type = 'limit'
                                                side = 'sell'

                                                dict_order[symb] = (t, price, None, amount)
                                                dict_trail[symb] = price * 0.99
                                                dict_trail_step[symb] = 0
                                                dict_max_price[symb] = price
                                                '''
                                                if trade_on and not err and len(dict_order) < 3:
                                                    try:
                                                        
                                                        params = {'stopPrice': price * 0.99}
                                                        order = bin_bot.createOrder(symb, 'STOP_LOSS', 'sell',
                                                                                    amount, None, params)
                                                        print(str(order))
                                                        
                                                        order = bin_bot.private_post_order_oco(
                                                            {"symbol": symb.replace('/', ''), "side": "sell",
                                                             "quantity": amount,
                                                             "price": take_profit, "stopPrice": stop_loss,
                                                             "stopLimitPrice": stop_loss, "stopLimitTimeInForce": "GTC"})
                                                        
                                                        #dict_order[symb] = (t, price, order['info']['orderId'], amount)
                                                        dict_order[symb] = (t, price, None, amount)
                                                    except:
                                                        type = 'market'
                                                        order = bin_bot.create_order(symb, type, side, amount,
                                                                                     take_profit)'''

                                                updater.bot.send_message(chat_id='-1001242337520', text=mes)
                                                print(mes + ' ' + datetime.today().strftime(
                                                '%Y-%m-%d-%H:%M:%S') + ' ' + str(t))
                                                print(hour)
                                                print(inf)
                                                print('45 ' + str(prevVol / (dict_curr[symb] * 0.027)))
                                                break
                                            elif price / float(hour[0][1]) < 1.10 and price / float(hour[0][1]) > 1.01:
                                                dict_pass[symb] = t - 17900 * 1000
                                step = 4
                                prevVol += e[1]

                                if 1 == 2 and prevVol >= dict_curr[symb] * 0.011 and price / dict_list[symb][0][2] > 1.005:
                                    inf = get_klines1(symb, '1m', int((time.time() - 300) * 1000), 5)
                                    min_price = 999
                                    max_price = 0

                                    for d in inf:
                                        max_price = max(max_price, float(d[2]))
                                        min_price = min(min_price, float(d[3]))

                                    if max(max_price,
                                           price) / min_price < 1.04 and max_price / min_price > 1.01 and price / float(
                                            inf[0][1]) > 1:
                                        inf = get_klines1(symb.replace('USDT', 'BTC'), '1m',
                                                          None, 5)
                                        hour = get_klines1(symb, '1m', int((time.time() - 3600) * 1000), 1)

                                        if price / float(hour[0][1]) < 1.10 and price / float(hour[0][1]) > 1.01 and float(inf[4][4]) / float(inf[0][1]) > 1.01:
                                            print(inf)
                                            amount = int(order_price / price)
                                            type = 'market'  # or market
                                            side = 'buy'
                                            err = False
                                            mes = 'Объемы выросли : ' + symb + ' (F) ' + str(price)
                                            if trade_on and len(dict_order) < 3:
                                                try:
                                                    order = bin_bot.create_order(symb, type, side, amount, None)

                                                    while order['status'] != 'closed':
                                                        order = bin_bot.fetch_order(order['id'], symb)

                                                        if order['status'] == 'rejected' or order[
                                                            'status'] == 'canceled':
                                                            break

                                                    if order['status'] != 'closed':
                                                        continue

                                                    price = float(order['price'])
                                                    mes = 'Объемы выросли : ' + symb + ' ($) ' + str(price)
                                                except:
                                                    err = True
                                                    mes = 'Объемы выросли : ' + symb + ' (F) ' + str(price)

                                            dict_order[symb] = price
                                            n = dict_prec[symb]
                                            take_profit = float_to_str(round(price * 1.005, n))
                                            stop_loss = float_to_str(round(price * 0.96, n))
                                            type = 'limit'
                                            side = 'sell'

                                            dict_order[symb] = (t, price, None, amount)
                                            dict_trail[symb] = price * 0.99
                                            dict_trail_step[symb] = 0
                                            dict_max_price[symb] = price

                                            '''
                                            if trade_on and not err and len(dict_order) < 3:
                                                try:
                                                    params = {'stopPrice': price * 0.99}
                                                    order = bin_bot.createOrder(symb, 'STOP_LOSS', 'sell',
                                                                                amount, None, params)
                                                    print(str(order))
                                                    
                                                    order = bin_bot.private_post_order_oco(
                                                        {"symbol": symb.replace('/', ''), "side": "sell",
                                                         "quantity": amount,
                                                         "price": take_profit, "stopPrice": stop_loss,
                                                         "stopLimitPrice": stop_loss, "stopLimitTimeInForce": "GTC"})
                                                    
                                                    dict_order[symb] = (t, price, order['info']['orderId'], amount)
                                                except:
                                                    type = 'market'
                                                    order = bin_bot.create_order(symb, type, side, amount,
                                                                                 take_profit)
                                            '''

                                            updater.bot.send_message(chat_id='-1001242337520', text=mes)
                                            print(mes + ' ' + datetime.today().strftime(
                                                        '%Y-%m-%d-%H:%M:%S') + ' ' + str(t))
                                            print(hour)
                                            print(inf)
                                            print(str(prevVol / (dict_curr[symb] * 0.027)))
                                            break
                                        elif price / float(hour[0][1]) < 1.10 and price / float(hour[0][1]) > 1.01:
                                            dict_pass[symb] = t - 17900 * 1000
                            elif (t - e[0]) / 1000 > 300:
                                del dict_list[symb][0:i]
                                dict_min_price[symb] = price
                                break

                        dict_list[symb].append((t, vol, price))
                    elif symb == 'BTCBUSD':
                        q = float(data['q'])
                        vol = q * price
                        dict_list[symb].append((t, vol, price))

                        if (t - dict_list[symb][0][0]) / 1000 > 60:
                            del dict_list[symb][0]
                    dict_min_price[symb] = min(dict_min_price[symb], price)
        else:
            time.sleep(0.01)

URL = os.environ.get('URL')
PORT = int(os.environ.get('PORT', '5000'))
TOKEN = os.environ['TEL_TOKEN']

updater = Updater(TOKEN, use_context=True)

updater.dispatcher.add_handler(CommandHandler('hello', hello, pass_chat_data=True))
'''
updater.dispatcher.add_handler(CommandHandler('start', start, pass_chat_data=True))

updater.dispatcher.add_handler(CommandHandler('set', set_timer, pass_args=True,
                              pass_job_queue=True,
                              pass_chat_data=True))'''
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
channels = {'trade'}
divisor = math.ceil(len(markets) / binance_websocket_api_manager.get_limit_of_subscriptions_per_stream())
max_subscriptions = math.ceil(len(markets) / divisor)
print(max_subscriptions)
for channel in channels:
    if len(markets) <= max_subscriptions:
        binance_websocket_api_manager.create_stream(channel, markets, stream_label=channel)
    else:
        loops = 1
        i = 1
        markets_sub = []
        for market in markets:
            markets_sub.append(market)
            if i == max_subscriptions or loops*max_subscriptions + i == len(markets):
                binance_websocket_api_manager.create_stream(channel, markets_sub, stream_label=str(channel+"_"+str(i)),
                                                            ping_interval=10, ping_timeout=10, close_timeout=5)
                markets_sub = []
                i = 1
                loops += 1
            i += 1
updater.bot.send_message(chat_id='-1001242337520', text='Запуск!')

updater.idle()
