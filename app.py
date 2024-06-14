import eventlet
eventlet.monkey_patch()

from flask import Flask, request, jsonify
from flask_socketio import SocketIO, emit
import yfinance as yf
import json
import threading
import time
from datetime import datetime, timedelta
from symbols_reader import all_symbols
import requests

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

clients = {}


# @app.route('/get_stock/<symbol>/<interval>/<period>')
# def get_stock_info(symbol, interval, period):
#     ticker = yf.Ticker(symbol)
#     quote_info = ticker.info

#     # Fetch historical data
#     historic_data = ticker.history(interval=interval, period=period)
#     if historic_data.empty:
#         print(f"No historical data available for symbol: {symbol}, period: {period}, interval: {interval}")
#         return {
#             "quoteInfo": {"error": "No historical data available"},
#             "historicData": {}
#         }

#     historic_data_json = json.loads(historic_data.to_json())

#     today_price = historic_data['Close'][-1]
#     yesterday_price = None

#     if period == "1d":
#         # Use the closing price from ticker information for "1d" period
#         yesterday_price = quote_info.get("previousClose", today_price)
#     else:
#         # Adjust the comparison period for other periods
#         period_mapping = {
#             "5d": "10d",
#             "1mo": "2mo",
#             "3mo": "6mo",
#             "6mo": "1y",
#             "ytd": "2y",
#             "1y": "2y",
#             "2y": "5y",
#             "5y": "10y",
#             "10y": "max",
#         }
#         compare_period = period_mapping.get(period, "max")

#         # Fetch comparison data
#         data = ticker.history(period=compare_period)
#         if data.empty:
#             print(f"No comparison data available for symbol: {symbol}, compare period: {compare_period}")
#             return {
#                 "quoteInfo": {"error": "No comparison data available"},
#                 "historicData": historic_data_json
#             }

#         data_json = data.to_json()
#         data_dict = json.loads(data_json)
#         close_price = data_dict.get("Close", {})
#         dates = list(close_price.keys())

#         if not dates:
#             print(f"No dates found in comparison data for symbol: {symbol}")
#             return {
#                 "quoteInfo": {"error": "No dates found in comparison data"},
#                 "historicData": historic_data_json
#             }

#         today = datetime.now().date()

#         def convert_date(date_string):
#             try:
#                 return datetime.strptime(date_string.split(" ")[0], "%Y-%m-%d").date()
#             except ValueError:
#                 return datetime.fromtimestamp(int(date_string) / 1000).date()

#         if len(dates) > 1:
#             if period == "5d":
#                 last_week = today - timedelta(days=7)
#                 last_week_dates = [d for d in dates if convert_date(d) <= last_week]
#                 if last_week_dates:
#                     yesterday_price = close_price[last_week_dates[-1]]
#             elif period == "1mo":
#                 last_month = today - timedelta(days=30)
#                 last_month_dates = [d for d in dates if convert_date(d) <= last_month]
#                 if last_month_dates:
#                     yesterday_price = close_price[last_month_dates[-1]]
#             elif period == "3mo":
#                 last_3months = today - timedelta(days=90)
#                 last_3months_dates = [d for d in dates if convert_date(d) <= last_3months]
#                 if last_3months_dates:
#                     yesterday_price = close_price[last_3months_dates[-1]]
#             elif period == "6mo":
#                 last_6months = today - timedelta(days=180)
#                 last_6months_dates = [d for d in dates if convert_date(d) <= last_6months]
#                 if last_6months_dates:
#                     yesterday_price = close_price[last_6months_dates[-1]]
#             elif period in {"ytd", "1y"}:
#                 last_year = today - timedelta(days=365)
#                 last_year_dates = [d for d in dates if convert_date(d) <= last_year]
#                 if last_year_dates:
#                     yesterday_price = close_price[last_year_dates[-1]]
#             elif period == "2y":
#                 last_2years = today - timedelta(days=730)
#                 last_2years_dates = [d for d in dates if convert_date(d) <= last_2years]
#                 if last_2years_dates:
#                     yesterday_price = close_price[last_2years_dates[-1]]
#             elif period == "5y":
#                 last_5years = today - timedelta(days=1825)
#                 last_5years_dates = [d for d in dates if convert_date(d) <= last_5years]
#                 if last_5years_dates:
#                     yesterday_price = close_price[last_5years_dates[-1]]
#             elif period == "10y":
#                 last_10years = today - timedelta(days=3650)
#                 last_10years_dates = [d for d in dates if convert_date(d) <= last_10years]
#                 if last_10years_dates:
#                     yesterday_price = close_price[last_10years_dates[-1]]
#             else:
#                 first_date = dates[0]
#                 yesterday_price = close_price[first_date]

#     if yesterday_price is None:
#         print(f"Yesterday's price not found for symbol: {symbol}, period: {period}")
#         return {
#             "quoteInfo": {"error": "Yesterday's price not found"},
#             "historicData": historic_data_json
#         }

#     diff = today_price - yesterday_price
#     percent_change = (diff / yesterday_price) * 100
#     quote_info["diff"] = diff
#     quote_info["percentChange"] = percent_change
#     quote_info["today"] = today_price

#     combined_data = {"quoteInfo": quote_info, "historicData": historic_data_json}
#     return combined_data

def determine_interval(period):
    if period in ["1d", "5d"]:
        return "1m"  # Dữ liệu phút cho những khoảng thời gian ngắn
    elif period in ["3mo", "6mo", "1y"]:
        return "1h"  # Dữ liệu nửa giờ cho nửa năm đến một năm
    elif period in ["ytd", "max"]:
        return "1d"  # Dữ liệu hàng ngày cho những khoảng thời gian rất dài
    else:
        return "1d"  # Trường hợp mặc định


@app.route('/get_stock/<symbol>/<period>')
def get_stock_info(symbol, period):
    interval = determine_interval(period)
    ticker = yf.Ticker(symbol)
    historic_data = ticker.history(period=period, interval=interval)
    historic_data_json = json.loads(historic_data.to_json())
    
    # Kiểm tra liệu DataFrame có dữ liệu không
    if historic_data.empty:
        return {"error": "No data available"}, 404
    
    quote_info = ticker.info

    # Thêm kiểm tra trước khi truy cập vào DataFrame
    try:
        current_price = quote_info.get('currentPrice')
        if quote_info.get('currentPrice') is None:
            current_price = quote_info.get('regularMarketPreviousClose')
        previous_close = historic_data['Close'].iloc[0] if period != '1d' else quote_info.get('previousClose')
        diff = current_price - previous_close
    except IndexError:
        return {"error": "Insufficient data to calculate price difference"}, 404
    
    percent_change = (diff / previous_close) * 100
    quote_info["diff"] = diff
    quote_info["percentChange"] = percent_change
    quote_info["today"] = current_price

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
    range = json_data['range']

    if client_id not in clients:
        clients[client_id] = {}

    if 'specific' in clients[client_id]:
        clients[client_id]['specific']['stop_event'].set()

    stop_event = threading.Event()
    clients[client_id]['specific'] = {
        'symbol': symbol,
        'range': range,
        'stop_event': stop_event
    }

    def send_specific_stock_update(client_id):
        while not clients[client_id]['specific']['stop_event'].is_set():
            stock_data = get_stock_info(
                clients[client_id]['specific']['symbol'],
                clients[client_id]['specific']['range']
            )
            socketio.emit('stock_update_specific', stock_data, to=client_id)
            time.sleep(3)
    
    thread = threading.Thread(target=send_specific_stock_update, args=(client_id,))
    thread.start()

@socketio.on('stock_request_notification')
def handle_stock_request_notification(json_data):
    handle_stock_request_generic(json_data, 'notification')

def handle_stock_request_generic(json_data, request_type):
    client_id = request.sid

    symbols = json_data['symbols']
    range = json_data['range']

    if client_id not in clients:
        clients[client_id] = {}

    if request_type in clients[client_id]:
        clients[client_id][request_type]['stop_event'].set()
    
    stop_event = threading.Event()
    clients[client_id][request_type] = {
        'symbols': symbols,
        'range': range,
        'stop_event': stop_event
    }

    def send_stock_updates(client_id, request_type):
        while not clients[client_id][request_type]['stop_event'].is_set():
            combined_data = []
            for symbol in clients[client_id][request_type]['symbols']:
                stock_data = get_stock_info(
                    symbol,
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
    range = json_data['range']

    matched_symbols = [symbol for symbol in all_symbols if keyword in str(symbol)]

    if client_id not in clients:
        clients[client_id] = {}

    if 'search' in clients[client_id]:
        clients[client_id]['search']['stop_event'].set()  # Stop any previous requests
    
    stop_event = threading.Event()
    clients[client_id]['search'] = {
        'symbols': matched_symbols,
        'range': range,
        'stop_event': stop_event
    }

    def send_stock_updates(client_id, request_type):
        while not clients[client_id][request_type]['stop_event'].is_set():
            combined_data = []
            for symbol in clients[client_id][request_type]['symbols']:
                stock_data = get_stock_info(
                    symbol,
                    clients[client_id][request_type]['range']
                )
                combined_data.append(stock_data)
            socketio.emit(f'stock_update_{request_type}', combined_data, to=client_id)
            time.sleep(3)
    
    thread = threading.Thread(target=send_stock_updates, args=(client_id, 'search'))
    thread.start()


@app.route('/get_list_symbol')
def get_list_symbol():
    return all_symbols

@app.route('/get_stock_info_history/<symbol>/<interval>/<period>')
def get_stock_info_history(symbol, interval, period):
    ticker = yf.Ticker(symbol)
    history = ticker.history(period=period, interval = interval)
    return {
        "history": json.loads(history.to_json()),
        "info": ticker.info
    }
    
@app.route('/get_stock_data/<symbol>/<period>')
def get_stock_data(symbol, period):
    interval = determine_interval(period)
    ticker = yf.Ticker(symbol)
    historic_data = ticker.history(period=period, interval=interval)
    historic_data_json = json.loads(historic_data.to_json())
    
    # Kiểm tra liệu DataFrame có dữ liệu không
    if historic_data.empty:
        return {"error": "No data available"}, 404
    
    quote_info = ticker.info
    
    # Thêm kiểm tra trước khi truy cập vào DataFrame
    try:
        current_price = quote_info.get('currentPrice')
        previous_close = historic_data['Close'].iloc[0] if period != '1d' else quote_info.get('previousClose')
        diff = current_price - previous_close
    except IndexError:
        return {"error": "Insufficient data to calculate price difference"}, 404
    
    return {
        "Historic Data": historic_data_json,
        "Quote Info": quote_info,
        "Price Difference (diff)": diff
    }

if __name__ == '__main__':
    socketio.run(app, debug=True)