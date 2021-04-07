# -*- coding: utf-8 -*-

from telegram.ext import Updater, CommandHandler
#from binance_api import Binance
import ccxt
import os
import decimal
import time
import asyncio
import sys
import ast

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

dict_book = dict()

order_price = 700

trade_on = True

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
        if i['asset'] == 'USDT':
            update.message.reply_text('Баланс : ' + str(i['free']))

def count(update, context):
    update.message.reply_text('Кол-во пар : ' + str(len(symb_list)) + ', take profit : ' + str(tk) + ', stop loss : ' + str(sl) + ', loops : ' + str(c))

def get_orders(update, context):
    mes = ''
    for k in dict_order.keys():
        mes = mes + k + ' : ' + float_to_str(dict_order[k]) + ' ' + float_to_str(dict_last_price[k]) + ' ' + float_to_str(round(dict_last_price[k] / dict_order[k] - 1, 4)) + '\n'
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
        mes = mes + k + ' : ' + float_to_str(dict_start_price[k]) + ' ' + float_to_str(dict_max_price[k]) + ' ' + float_to_str(round(dict_max_price[k] / dict_start_price[k] - 1, 4)) + '\n'
    update.message.reply_text(mes)

def get_min(update, context):
    mes = ''
    for k in dict_max_price.keys():
        mes = mes + k + ' : ' + float_to_str(dict_start_price[k]) + ' ' + float_to_str(dict_min_price[k]) + ' ' + float_to_str(round(dict_min_price[k] / dict_start_price[k] - 1, 4)) + '\n'
    update.message.reply_text(mes)

def updateData(context):
    global dict_prev, dict_curr, symb_list, dict_prec
    dict_prev = dict_curr
    dict_curr = dict()
    tickers = bin_bot.fetch_tickers()
    bin_bot.load_markets()
    #for pr in bin_bot.ticker24hr():
    for pr in tickers:
        if tickers[pr]['symbol'][-4:] == 'USDT' and float(tickers[pr]['quoteVolume']) >= 300000 and float(tickers[pr]['quoteVolume']) <= 25000000 and float(tickers[pr]['bidVolume']) > 0 and float(tickers[pr]['high']) < 20 \
                and tickers[pr]['symbol'] != 'SUSD/USDT' and tickers[pr]['symbol'] != 'LINK/BTC' and tickers[pr]['symbol'] != 'DCR/BTC'\
                and tickers[pr]['symbol'] != 'ENG/BTC' and tickers[pr]['symbol'] != 'LEND/BTC' and tickers[pr]['symbol'] != 'LUN/BTC' and tickers[pr]['symbol'] != 'PAX/USDT'\
                and tickers[pr]['symbol'].find('DOWN') == -1 and tickers[pr]['symbol'].find('UP') == -1 \
                and tickers[pr]['symbol'] != 'ASR/USDT' and tickers[pr]['symbol'] != 'TUSD/BTC' and tickers[pr]['symbol'] != 'TUSD/USDT' and tickers[pr]['symbol'] != 'PAX/BTC' and tickers[pr]['symbol'] != 'DAI/BTC' and tickers[pr]['symbol'] != 'SUN/USDT':
            dict_curr[tickers[pr]['symbol']] = float(tickers[pr]['quoteVolume'])
            market = bin_bot.market(tickers[pr]['symbol'])
            dict_prec[tickers[pr]['symbol']] = int(market['precision']['price'])
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
    mesShort = ''
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
            elif course <= dict_order[symb_list[i]] * 0.99:
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
                    dict_order[symb_list[i]][0] = course
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
    mesOrd = ''
    mesShort = ''
    job = context.job
    global dict_prev, dict_curr, symb_list, c, tk, sl, dict_order, dict_pass, dict_prec, dict_start_price, dict_max_price, dict_min_price, dict_prev_vol, dict_prev_min,trade_on

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
                mesOrd = mesOrd + 'Профит ' + symb_list[i] + ' ' + float_to_str(dict_order[symb_list[i]]) + ' ' + float_to_str(course) + ' '
                del dict_order[symb_list[i]]
                dict_pass[symb_list[i]] = 60

            elif dict_min_price[symb_list[i]] <= dict_order[symb_list[i]] * 0.96:
                sl = sl + 1
                mesOrd = mesOrd + 'Убыток ' + symb_list[i] + ' ' + float_to_str(dict_order[symb_list[i]]) + ' ' + float_to_str(course) + ' '
                del dict_order[symb_list[i]]
                dict_pass[symb_list[i]] = 60

        if vol >= dict_curr[symb_list[i]] * 0.0215 and float(inf[0][2]) / float(inf[0][1]) < 1.07 and float(inf[0][2]) / float(inf[0][1]) > 1 and float(inf[0][4]) / float(inf[0][1]) > 0.96 and float(inf[0][2]) / float(inf[0][3]) > 1.01 and len(dict_order) < 7:
            passPair = False
            if symb_list[i] in dict_max_price:
                if dict_max_price[symb_list[i]] <= course:
                    passPair = True
            if not symb_list[i] in dict_order and not symb_list[i] in dict_pass and not passPair:

                amount = int(order_price / course)
                type = 'market'  # or market
                side = 'buy'

                if trade_on:
                    order = bin_bot.create_order(symb_list[i], type, side, amount, None)

                    while order['status'] != 'closed':
                        order = bin_bot.fetch_order(order['id'], symb_list[i])

                        if order['status'] == 'rejected' or order['status'] == 'canceled':
                            break

                    if order['status'] != 'closed':
                        continue

                    price = float(order['price'])
                else:
                    price = course

                dict_order[symb_list[i]] = price
                n = dict_prec[symb_list[i]]
                take_profit = float_to_str(round(price * 1.01, n))
                stop_loss = float_to_str(round(price * 0.96, n))
                type = 'limit'
                side = 'sell'

                if trade_on:
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

                mesVol += symb_list[i] + '(+' + str(round(vol, 2)) + ' / ' + str(round((vol/dict_curr[symb_list[i]])*100, 2)) + '%, ' + str(price) + ' ' + str(course) + ' ' + str(course / float(inf[0][1])) + ' ' + str(float(inf[0][2]) / float(inf[0][1])) + ' ' + str(float(inf[0][2]) / float(inf[0][3])) + ' ' + str(float(inf[0][2]) / prev_min) +')\n'
        elif c > 0 and dict_prev_vol.get(symb_list[i]) != None:
            if vol + dict_prev_vol[symb_list[i]] >= dict_curr[symb_list[i]] * 0.023 and vol < dict_curr[symb_list[i]] * 0.0215 and float(inf[0][2]) / float(inf[0][1]) < 1.06 and float(inf[0][2]) / float(inf[0][1]) > 1 and float(inf[0][4]) / float(inf[0][1]) > 0.96 and float(inf[0][2]) / float(inf[0][3]) > 1.00 and len(dict_order) < 7:
                passPair = False
                if symb_list[i] in dict_max_price:
                    if dict_max_price[symb_list[i]] <= course:
                        passPair = True
                if not symb_list[i] in dict_order and not symb_list[i] in dict_pass and not passPair:

                    amount = int(order_price / course)
                    type = 'market'  # or market
                    side = 'buy'

                    if trade_on:
                        order = bin_bot.create_order(symb_list[i], type, side, amount, None)

                        while order['status'] != 'closed':
                            order = bin_bot.fetch_order(order['id'], symb_list[i])

                            if order['status'] == 'rejected' or order['status'] == 'canceled':
                                break

                        if order['status'] != 'closed':
                            continue

                        price = float(order['price'])
                    else:
                        price = course

                    dict_order[symb_list[i]] = price
                    n = dict_prec[symb_list[i]]
                    take_profit = float_to_str(round(price * 1.01, n))
                    stop_loss = float_to_str(round(price * 0.96, n))
                    type = 'limit'
                    side = 'sell'
                    if trade_on:
                        order = bin_bot.create_order(symb_list[i], type, side, amount, take_profit)

                    dict_start_price[symb_list[i]] = price
                    dict_max_price[symb_list[i]] = price
                    dict_min_price[symb_list[i]] = price

                    mesVol += symb_list[i] + ' TEST (+' + str(round(vol + dict_prev_vol[symb_list[i]], 2)) + ' / ' + str(round(((vol + dict_prev_vol[symb_list[i]])/dict_curr[symb_list[i]])*100, 2)) + '%, ' + str(float(inf[0][4])) + ' ' + str(course) + ' ' + str(course / float(inf[0][1])) + ' ' + str(float(inf[0][2]) / float(inf[0][1])) + ' ' + str(float(inf[0][2]) / float(inf[0][3])) + ' ' + str(float(inf[0][2]) / prev_min) +')\n'

            elif vol >= dict_curr[symb_list[i]] * 0.02 and not symb_list[i] in dict_start_price:
                dict_start_price[symb_list[i]] = course
                dict_max_price[symb_list[i]] = course
                dict_min_price[symb_list[i]] = course
                dict_pass[symb_list[i]] = 60
                mesShort += symb_list[i] + '(+' + str(round(vol, 2)) + ' / ' + str(round((vol/dict_curr[symb_list[i]])*100, 2)) + '%, ' + str(course) + ' ' + str(course / float(inf[0][1])) + ' ' + str(float(inf[0][2]) / float(inf[0][1])) + ' ' + str(float(inf[0][2]) / float(inf[0][3])) + ' ' + str(float(inf[0][2]) / prev_min) + ')\n'
            elif c > 0:
                if vol + dict_prev_vol[symb_list[i]] >= dict_curr[symb_list[i]] * 0.0215 and not symb_list[i] in dict_start_price:
                    dict_start_price[symb_list[i]] = course
                    dict_max_price[symb_list[i]] = course
                    dict_min_price[symb_list[i]] = course
                    dict_pass[symb_list[i]] = 60
                    mesShort += symb_list[i] + 'TEST (+' + str(round(vol + dict_prev_vol[symb_list[i]], 2)) + ' / ' + str(round(((vol+dict_prev_vol[symb_list[i]])/dict_curr[symb_list[i]])*100, 2)) + '%, ' + str(course) + ' ' + str(course / float(inf[0][1])) + ' ' + str(float(inf[0][2]) / float(inf[0][1])) + ' ' + str(float(inf[0][2]) / float(inf[0][3])) + ' ' + str(float(inf[0][2]) / prev_min) + ')\n'

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

def alarm4(context):
    """Send the alarm message."""
    try:
        mesVol = ''
        mesOrd = ''
        job = context.job
        global dict_prev, dict_curr, symb_list, limit, tk, sl, dict_last_price, dict_order, c, last_price, last_stop, dict_prec
        c += 1
        for i in range(0, int(len(symb_list))):
            #kline = get_klines(symb_list[i])
            #vol = float(kline[0][10])
            #course = float(kline[0][4])
            pass_val = False
            vol_a = 0
            vol_b = 0
            course = 0
            f = bin_bot.fetchOrderBook(symb_list[i])

            try:
                course = f['asks'][0][0]
            except Exception:
                continue

            for item in f['asks']:
                vol_a += float(item[0]) * float(item[1])

            for item in f['bids']:
                vol_b += float(item[0]) * float(item[1])

            if not symb_list[i] in dict_wall_a:
                dict_wall_a[symb_list[i]] = vol_a
                dict_wall_b[symb_list[i]] = vol_b
                dict_last_price[symb_list[i]] = course
                dict_book[symb_list[i]] = f
                continue

            if symb_list[i] in dict_order:
                if course >= dict_order[symb_list[i]] * 1.005:
                    pass_val = True
                    tk = tk + 1
                    dict_order[symb_list[i]] = course
                    #mesOrd = mesOrd + 'Профит ' + symb_list[i] + ' ' + float_to_str(dict_order[symb_list[i]]) + ' ' + float_to_str(course) + ' '
                    del dict_order[symb_list[i]]
                elif course <= dict_order[symb_list[i]] * 0.993:
                    pass_val = True
                    sl = sl + 1

                    #mesOrd = mesOrd + 'Убыток ' + symb_list[i] + ' ' + float_to_str(dict_order[symb_list[i]][0]) + ' ' + float_to_str(order['amount']) + ' '

                    del dict_order[symb_list[i]]

            if dict_wall_a[symb_list[i]] * 0.65 >= vol_a and dict_wall_b[symb_list[i]] * 1.25 < vol_b and not symb_list[i] in dict_order and not pass_val:
                amount = int(0.001 / course)
                type = 'market'  # or market
                side = 'buy'
                order = bin_bot.create_order(symb_list[i], type, side, amount, None)

                while order['status'] != 'closed':
                    order = bin_bot.fetch_order(order['id'], symb_list[i])

                    if order['status'] == 'rejected' or order['status'] == 'canceled':
                        break

                if order['status'] != 'closed':
                    continue

                price = float(order['price'])
                n = dict_prec[symb_list[i]]
                take_profit = float_to_str(round(price * 1.005, n))
                stop_loss = float_to_str(round(price * 0.993, n))

                if last_price == None:
                    last_price = take_profit
                    last_stop = stop_loss

                order = bin_bot.private_post_order_oco(
                    {"symbol": symb_list[i].replace('/', ''), "side": "sell", "quantity": order['amount'], "price": take_profit, "stopPrice": stop_loss,
                     "stopLimitPrice": stop_loss, "stopLimitTimeInForce": "GTC"})

                last_price = None
                last_stop = None
                '''
                order = bin_bot.createOrder(symb_list[i], 'TAKE_PROFIT_LIMIT', 'sell', order['amount'], take_profit,
                                    {'stopPrice': take_profit})

                
                bin_bot.createOrder(symb_list[i], 'STOP_LOSS', 'sell', order['amount'], stop_loss,
                                           { 'stopPrice': stop_loss})
                '''
                mesVol += symb_list[i] + '(' + str(round((vol_a/dict_wall_a[symb_list[i]])*100, 2)) + '% / ' + str(round((vol_b/dict_wall_b[symb_list[i]])*100, 2)) + '%) Курс : ' + float_to_str(price) + ' ' + float_to_str(dict_last_price[symb_list[i]] - course) +'\n'
                #mesVol += str(dict_book[symb_list[i]]) +'\n'
                #mesVol += str(f) + '\n'
                dict_order[symb_list[i]] = price

            dict_book[symb_list[i]] = f
            dict_wall_a[symb_list[i]] = vol_a
            dict_wall_b[symb_list[i]] = vol_b
            dict_last_price[symb_list[i]] = course

        if len(mesVol) > 0:
            mes = 'Пробитие стены : ' + mesVol
            if len(mes) > 4096:
                for x in range(0, len(mes), 4096):
                    context.bot.send_message(chat_id='-1001242337520', text=mes[x:x + 4096])
            else:
                context.bot.send_message(chat_id='-1001242337520', text=mes)
        if len(mesOrd) > 0:
            mes = 'Сделки закрыты : ' + mesOrd
            context.bot.send_message(chat_id='-1001242337520', text=mes)
    except Exception:
        context.bot.send_message(chat_id='-1001242337520', text=sys.exc_info()[0])
        
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
            'apiKey' : os.environ['API_KEY'],
            'secret' : os.environ['API_SECRET'],
            'enableRateLimit': True,
        })

        job = context.job_queue.run_repeating(updateData, due, first=0, context=chat_id)
        job = context.job_queue.run_repeating(alarm2, 60, first=20, context=chat_id)
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
            'apiKey' : os.environ['API_KEY'],
            'secret' : os.environ['API_SECRET'],
            'enableRateLimit': True,
        })

job = updater.job_queue.run_repeating(updateData, 3600, first=0, context=None)
job = updater.job_queue.run_repeating(alarm2, 60, first=20, context=None)

updater.idle()
