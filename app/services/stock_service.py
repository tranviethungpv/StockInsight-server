import yfinance as yf
import json
from ..models.symbols import all_symbols

def determine_interval(period):
    if period in ["1d", "5d"]:
        return "1m"
    elif period in ["3mo", "6mo", "1y"]:
        return "1h"
    elif period in ["ytd", "max"]:
        return "1d"
    else:
        return "1d"

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

def get_stock_info_history(symbol, interval, period):
    ticker = yf.Ticker(symbol)
    history = ticker.history(period=period, interval=interval)
    return {
        "history": json.loads(history.to_json()),
        "info": ticker.info
    }

def get_list_symbol():
    return all_symbols

def get_stock_data(symbol, period):
    return get_stock_info(symbol, period)
