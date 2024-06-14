from flask import Blueprint, jsonify
from ..services.stock_service import get_stock_info, get_stock_info_history, get_list_symbol, get_stock_data

stock_blueprint = Blueprint('stock', __name__)

@stock_blueprint.route('/')
def hello():
    return 'Hello, World!'

@stock_blueprint.route('/get_stock/<symbol>/<period>')
def stock_info(symbol, period):
    return get_stock_info(symbol, period)

@stock_blueprint.route('/get_stock_info_history/<symbol>/<interval>/<period>')
def stock_history(symbol, interval, period):
    return get_stock_info_history(symbol, interval, period)

@stock_blueprint.route('/get_list_symbol')
def list_symbol():
    return get_list_symbol()

@stock_blueprint.route('/get_stock_data/<symbol>/<period>')
def stock_data(symbol, period):
    return get_stock_data(symbol, period)
