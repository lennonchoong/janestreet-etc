#!/usr/bin/python
# ~~~~~==============   HOW TO RUN   ==============~~~~~
# 1) Configure things in CONFIGURATION section
# 2) Change permissions: chmod +x bot.py
# 3) Run in loop: while true; do ./bot.py; sleep 1; done

from __future__ import print_function

import sys
import socket
import json
from collections import deque

# ~~~~~============== CONFIGURATION  ==============~~~~~
# replace REPLACEME with your team name!
team_name = "HCHOONG"
# This variable dictates whether or not the bot is connecting to the prod
# or test exchange. Be careful with this switch!
test_mode = False

# This setting changes which test exchange is connected to.
# 0 is prod-like
# 1 is slower
# 2 is empty
test_exchange_index = 0
prod_exchange_hostname = "production"

port = 25000 + (test_exchange_index if test_mode else 0)
exchange_hostname = "test-exch-" + team_name if test_mode else prod_exchange_hostname

# ~~~~~============== NETWORKING CODE ==============~~~~~
def connect():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((exchange_hostname, port))
    return s.makefile("rw", 1)


def write_to_exchange(exchange, obj):
    json.dump(obj, exchange)
    exchange.write("\n")


def read_from_exchange(exchange):
    return json.loads(exchange.readline())


# ~~~~~============== MAIN LOOP ==============~~~~~

order_ids = set()
cur_id = 1

def bond():
    pass

def pair():
    pass

def etf():
    pass

def increment_id():
    global cur_id
    cur_id += 1

def buy_order(exchange, order_id, sym, price, size):
    return {"type": "add", "order_id": order_id, "symbol": sym.upper(), "dir": "BUY", "price": price, "size": size}

def sell_order(exchange, order_id, sym, price, size):
    return {"type": "add", "order_id": order_id, "symbol": sym.upper(), "dir": "SELL", "price": price, "size": size}

def convert_buy(exchange, order_id, sym, price, size):
    return {"type": "convert", "order_id": order_id, "symbol": sym.upper(), "dir": "BUY", "size": size}

def convert_sell(exchange, order_id, sym, price, size):
    return {"type": "convert", "order_id": order_id, "symbol": sym.upper(), "dir": "SELL", "size": size}

def cancel(exchange, order_id):
    return {"type": "cancel", "order_id": order_id}

def get_book(message):
    if message['type'] == 'book':
        print(message)

def buy_vol(message):
    total = 0
    for x in message["buy"]:
        total += x[-1]
    return total

def sell_vol(message):
    total = 0
    for x in message["sell"]:
        total += x[-1]
    return total

def ave_bid_sell(message):
    bid = float('-inf')
    ask = float('inf')
    for x in message['buy']:
        if x[0] > bid:
            bid = x[0]
    
    for y in message['sell']:
        if x[0] < ask:
            ask = x[0]

    return (bid + ask) / 2

def bid_price(message, symbol):
    bid = float('-inf') 

    if message['symbol'] != symbol:
        return

    for x in message['buy']:
        if x[0] > bid:
            bid = x[0]
    
    return bid

def offer_price(message, symbol):
    offer = float('inf')

    if message['symbol'] != symbol: 
        return

    for y in message['sell']:
        if y[0] < offer:
            offer = y[0]

    return offer

# buys the stock at the current offer price
def match_offer(exchange, order_id, sym, size, message):
    return buy_order(exchange, order_id, sym, bid_price(message, sym), size)

# sells the stock at the current bid price
def match_bid(exchange, order_id, sym, size, message):
    return sell_order(exchange, order_id, sym, offer_price(message, sym), size)

# buys the stock at the current offer price + offset
def match_offer_offset(exchange, order_id, sym, size, message, offset):
    return buy_order(exchange, order_id, sym, bid_price(message, sym) + offset, size)

# sells the stock at the current bid price + offset
def match_bid_offset(exchange, order_id, sym, size, message, offset):
    return sell_order(exchange, order_id, sym, offer_price(message, sym) + offset, size)


def main():
    counter = 0
    position = 0
    vale_pos = 0
    prev_buy_price = 0
    prev_sell_price = 0
    exchange = connect()
    write_to_exchange(exchange, {"type": "hello", "team": team_name.upper()})
    hello_from_exchange = read_from_exchange(exchange)
    orders = deque()
    buy_orders = 0
    sell_orders = 0
    vale_buys = vale_sells = 0
    prev_vale_buy = 0
    prev_vale_sell = sys.maxsize
    vale_bid = 0
    vale_mid = 0
    vale_ask = float('inf')
    # A common mistake people make is to call write_to_exchange() > 1
    # time for every read_from_exchange() response.
    # Since many write messages generate marketdata, this will cause an
    # exponential explosion in pending messages. Please, don't do that!
    print("The exchange replied:", hello_from_exchange, file=sys.stderr)
    while True:
        message = read_from_exchange(exchange)
        if message['type'] == "error":
            print(message)

        if message["type"] == "close":
            print("The round has ended")
            break

        if message['type'] == 'book' and message['symbol'] == "BOND":
            if position <= 100 and buy_orders <= 100 and bid_price(message, "BOND") < 1000:
                if bid_price(message, "BOND") <= prev_buy_price:
                    orders.append(match_offer_offset(exchange, counter, "BOND", 50, message, 0))
                else:
                    orders.append(match_offer_offset(exchange, counter, "BOND", 50, message, 1))
                buy_orders += 50
                counter += 1

            if position >= -100 and sell_orders <= 100 and offer_price(message, "BOND") > 1000:
                if offer_price(message, "BOND") >= prev_sell_price:
                    orders.append(match_bid_offset(exchange, counter, "BOND", 50, message, 0))
                else:
                    orders.append(match_bid_offset(exchange, counter, "BOND", 50, message, -1))
                sell_orders += 50
                counter += 1

        if message['type'] == 'fill' and message['symbol'] == "BOND":
            if message['dir'] == "BUY": # BUY executed
                position += message['size']
                if sell_orders <= 100:
                    orders.append(sell_order(exchange, counter, "BOND", (message['price'] + 1), message['size']))
                    sell_orders += message['size']
                    counter += 1
                prev_buy_price = max(prev_buy_price, message['price']) # buy
                buy_orders -= message['size']
            else:                       # SELL executed
                position -= message['size']
                if buy_orders <= 100:
                    orders.append(buy_order(exchange, counter, "BOND", (message['price'] - 1), message['size']))
                    buy_orders += message['size']
                    counter += 1
                prev_sell_price = min(prev_sell_price, message['price']) # buy
                sell_orders -= message['size']

        if message['type'] == 'book' and message['symbol'] == 'VALBZ':
            vale_bid = max(vale_bid, bid_price(message, "VALBZ"))
            vale_ask = min(vale_ask, offer_price(message,"VALBZ"))
            vale_mid = vale_bid + (vale_ask - vale_bid) / 2

        if message['type'] == 'book' and message['symbol'] == 'VALE':
            if vale_pos <= 10 and vale_buys <= 10 and vale_bid < vale_mid:
                if vale_bid <= prev_vale_buy:
                    orders.append(buy_order(exchange, counter, "VALE", vale_bid, 3))
                else:
                    orders.append(buy_order(exchange, counter, "VALE", vale_bid + 1, 3))
                vale_buys += 3
                counter += 1

            if vale_pos >= -10 and vale_sells <= 10 and vale_ask > vale_mid:
                if vale_ask >= prev_vale_sell:
                    orders.append(sell_order(exchange, counter, "VALE", vale_ask, 3))
                else:
                    orders.append(sell_order(exchange, counter, "VALE", vale_ask - 1, 3))
                vale_sells += 3
                counter += 1

        if message['type'] == 'fill' and message['symbol'] == "VALE":
            if message['dir'] == "BUY": # BUY executed
                vale_pos += message['size']
                if vale_sells <= 10:
                    orders.append(sell_order(exchange, counter, "VALE", (message['price'] + 1), message['size']))
                    vale_sells += message['size']
                    counter += 1
                prev_vale_buy = max(prev_vale_buy, message['price']) # buy
                vale_buys -= message['size']
            else:                       # SELL executed
                vale_pos -= message['size']
                if vale_buys <= 10:
                    orders.append(buy_order(exchange, counter, "VALE", (message['price'] - 1), message['size']))
                    vale_buys += message['size']
                    counter += 1
                prev_vale_sell = min(prev_vale_sell, message['price']) # buy
                vale_sells -= message['size']

        while orders:
            cur_order = orders.popleft()
            json.dump(cur_order, exchange)
            exchange.write("\n")


if __name__ == "__main__":
    main()