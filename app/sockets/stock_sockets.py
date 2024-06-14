from flask_socketio import emit
from flask import request
import threading
import time
from ..services.stock_service import get_stock_info
from ..models.symbols import all_symbols

clients = {}

def register_sockets(socketio):
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
