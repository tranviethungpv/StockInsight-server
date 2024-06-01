import eventlet
eventlet.monkey_patch()

from flask import Flask, request
from flask_socketio import SocketIO, emit
import yfinance as yf
import json
import threading
import time
from datetime import datetime, timedelta
from all_symbols import all_symbols
import requests

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

clients = {}

def get_stock_info(symbol, interval, period):
    ticker = yf.Ticker(symbol)
    quote_info = ticker.info

    historic_data = ticker.history(interval=interval, period=period)
    historic_data_json = json.loads(historic_data.to_json())

    # Determine comparison period
    if period == "1d":
        compare_period = "2d"
    elif period == "5d":
        compare_period = "10d"
    elif period == "1mo":
        compare_period = "2mo"
    elif period == "3mo":
        compare_period = "6mo"
    elif period == "6mo":
        compare_period = "1y"
    elif period == "ytd" or period == "1y":
        compare_period = "2y"
    elif period == "2y":
        compare_period = "4y"
    elif period == "5y":
        compare_period = "10y"
    elif period == "10y":
        compare_period = "20y"
    else:
        compare_period = "max"

    data = ticker.history(period=compare_period)
    data = data.to_json()
    data = json.loads(data)
    close_price = data["Close"]
    dates = list(close_price.keys())

    today_price = close_price[dates[-1]]

    today = datetime.now().date()
    yesterday_price = today_price  # Đặt giá trị mặc định là today_price

    def convert_date(date_string):
        try:
            return datetime.strptime(date_string.split(" ")[0], "%Y-%m-%d").date()
        except ValueError:
            return datetime.fromtimestamp(int(date_string) / 1000).date()

    # Add check to prevent IndexError
    if len(dates) > 1:
        if period == "1d":
            yesterday_price = close_price[dates[-2]]
        elif period == "5d":
            last_week = today - timedelta(days=7)
            last_week_dates = [d for d in dates if convert_date(d) <= last_week]
            if last_week_dates:
                yesterday_price = close_price[last_week_dates[-1]]
        elif period == "1mo":
            last_month = today - timedelta(days=30)
            last_month_dates = [d for d in dates if convert_date(d) <= last_month]
            if last_month_dates:
                yesterday_price = close_price[last_month_dates[-1]]
        elif period == "3mo":
            last_3months = today - timedelta(days=90)
            last_3months_dates = [d for d in dates if convert_date(d) <= last_3months]
            if last_3months_dates:
                yesterday_price = close_price[last_3months_dates[-1]]
        elif period == "6mo":
            last_6months = today - timedelta(days=180)
            last_6months_dates = [d for d in dates if convert_date(d) <= last_6months]
            if last_6months_dates:
                yesterday_price = close_price[last_6months_dates[-1]]
        elif period == "ytd" or period == "1y":
            last_year = today - timedelta(days=365)
            last_year_dates = [d for d in dates if convert_date(d) <= last_year]
            if last_year_dates:
                yesterday_price = close_price[last_year_dates[-1]]
        elif period == "2y":
            last_2years = today - timedelta(days=730)
            last_2years_dates = [d for d in dates if convert_date(d) <= last_2years]
            if last_2years_dates:
                yesterday_price = close_price[last_2years_dates[-1]]
        elif period == "5y":
            last_5years = today - timedelta(days=1825)
            last_5years_dates = [d for d in dates if convert_date(d) <= last_5years]
            if last_5years_dates:
                yesterday_price = close_price[last_5years_dates[-1]]
        elif period == "10y":
            last_10years = today - timedelta(days=3650)
            last_10years_dates = [d for d in dates if convert_date(d) <= last_10years]
            if last_10years_dates:
                yesterday_price = close_price[last_10years_dates[-1]]
        else:
            first_date = dates[0]
            yesterday_price = close_price[first_date]

    diff = today_price - yesterday_price
    percent_change = (diff / yesterday_price) * 100
    quote_info["diff"] = diff
    quote_info["percentChange"] = percent_change
    quote_info["today"] = today_price

    combined_data = {"quoteInfo": quote_info, "historicData": historic_data_json}
    return combined_data

@app.route('/')
def hello():
    return 'Hello, World!'

@socketio.on('connect')
def handle_connect():
    print('Client connected')
    emit('message', {'data': 'Connected to server'})

@socketio.on('stock_request_homepage')
def handle_stock_request_info(json_data):
    handle_stock_request_generic(json_data, 'homepage')

@socketio.on('stock_request_watchlist')
def handle_stock_request_watchlist(json_data):
    handle_stock_request_generic(json_data, 'watchlist')

@socketio.on('stock_request_specific')
def handle_stock_request_specific(json_data):
    client_id = request.sid

    symbol = json_data['symbol']
    interval = json_data['interval']
    range = json_data['range']

    if client_id not in clients:
        clients[client_id] = {}

    if 'specific' in clients[client_id]:
        clients[client_id]['specific']['stop_event'].set()

    stop_event = threading.Event()
    clients[client_id]['specific'] = {
        'symbol': symbol,
        'interval': interval,
        'range': range,
        'stop_event': stop_event
    }

    def send_specific_stock_update(client_id):
        while not clients[client_id]['specific']['stop_event'].is_set():
            stock_data = get_stock_info(
                clients[client_id]['specific']['symbol'],
                clients[client_id]['specific']['interval'],
                clients[client_id]['specific']['range']
            )
            socketio.emit('stock_update_specific', stock_data, to=client_id)
            time.sleep(3)
    
    thread = threading.Thread(target=send_specific_stock_update, args=(client_id,))
    thread.start()

def handle_stock_request_generic(json_data, request_type):
    client_id = request.sid

    symbols = json_data['symbols']
    interval = json_data['interval']
    range = json_data['range']

    if client_id not in clients:
        clients[client_id] = {}

    if request_type in clients[client_id]:
        clients[client_id][request_type]['stop_event'].set()
    
    stop_event = threading.Event()
    clients[client_id][request_type] = {
        'symbols': symbols,
        'interval': interval,
        'range': range,
        'stop_event': stop_event
    }

    def send_stock_updates(client_id, request_type):
        while not clients[client_id][request_type]['stop_event'].is_set():
            combined_data = []
            for symbol in clients[client_id][request_type]['symbols']:
                stock_data = get_stock_info(
                    symbol,
                    clients[client_id][request_type]['interval'],
                    clients[client_id][request_type]['range']
                )
                combined_data.append(stock_data)
            socketio.emit(f'stock_update_{request_type}', combined_data, to=client_id)
            time.sleep(3)
    
    thread = threading.Thread(target=send_stock_updates, args=(client_id, request_type))
    thread.start()

@socketio.on('disconnect')
def handle_disconnect():
    client_id = request.sid
    if client_id in clients:
        for request_type in clients[client_id]:
            clients[client_id][request_type]['stop_event'].set()
        del clients[client_id]
    print('Client disconnected')


@socketio.on('stock_request_search')
def handle_stock_request_search(json_data):
    client_id = request.sid
    keyword = json_data['keyword'].upper()  # Assuming keyword is passed and should be case-insensitive
    interval = json_data['interval']
    range = json_data['range']

    # Filter symbols based on the keyword
    matched_symbols = [symbol for symbol in all_symbols if keyword in symbol]

    if client_id not in clients:
        clients[client_id] = {}

    if 'search' in clients[client_id]:
        clients[client_id]['search']['stop_event'].set()  # Stop any previous requests
    
    stop_event = threading.Event()
    clients[client_id]['search'] = {
        'symbols': matched_symbols,
        'interval': interval,
        'range': range,
        'stop_event': stop_event
    }

    def send_stock_updates(client_id, request_type):
        while not clients[client_id][request_type]['stop_event'].is_set():
            combined_data = []
            for symbol in clients[client_id][request_type]['symbols']:
                stock_data = get_stock_info(
                    symbol,
                    clients[client_id][request_type]['interval'],
                    clients[client_id][request_type]['range']
                )
                combined_data.append(stock_data)
            socketio.emit(f'stock_update_{request_type}', combined_data, to=client_id)
            time.sleep(3)
    
    thread = threading.Thread(target=send_stock_updates, args=(client_id, 'search'))
    thread.start()


if __name__ == '__main__':
    socketio.run(app, debug=True)