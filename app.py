import eventlet
eventlet.monkey_patch()


from flask import Flask, jsonify, request
from flask_socketio import SocketIO, emit
import yfinance as yf
import json
import threading
import time


app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

clients = {}

def get_stock_info(symbol, interval, range):
    ticker = yf.Ticker(symbol)
    quote_info = ticker.info
    historic_data = ticker.history(interval=interval, period=range)
    historic_data_json = json.loads(historic_data.to_json())
    data = ticker.history(period='2d')
    data = data.to_json()
    data = json.loads(data)
    close_price = data['Close']
    dates = list(close_price.keys())
    today = close_price[dates[-1]]
    yesterday = close_price[dates[-2]]
    diff = today - yesterday
    percent_change = diff / yesterday * 100
    quote_info['diff'] = diff
    quote_info['percentChange'] = percent_change
    quote_info['today'] = today
    combined_data = {
        'quoteInfo': quote_info,
        'historicData': historic_data_json
    }
    return combined_data

@app.route('/')
def hello():
    return 'Hello, World!'

@socketio.on('connect')
def handle_connect():
    print('Client connected')
    emit('message', {'data': 'Connected to server'})

@socketio.on('stock_request')
def handle_stock_request(json_data):
    client_id = request.sid

    symbol = json_data['symbol']
    interval = json_data['interval']
    range = json_data['range']

    if client_id in clients:
        clients[client_id]['stop_event'].set()
    
    stop_event = threading.Event()
    clients[client_id] = {
        'symbol': symbol,
        'interval': interval,
        'range': range,
        'stop_event': stop_event
    }

    def send_stock_updates(client_id):
        while not clients[client_id]['stop_event'].is_set():
            combined_data = get_stock_info(
                clients[client_id]['symbol'],
                clients[client_id]['interval'],
                clients[client_id]['range']
            )
            socketio.emit('stock_update', combined_data, to=client_id)
            time.sleep(10)
    
    thread = threading.Thread(target=send_stock_updates, args=(client_id,))
    thread.start()

@socketio.on('disconnect')
def handle_disconnect():
    client_id = request.sid
    if client_id in clients:
        clients[client_id]['stop_event'].set()
        del clients[client_id]
    print('Client disconnected')

if __name__ == '__main__':
    socketio.run(app, debug=True)