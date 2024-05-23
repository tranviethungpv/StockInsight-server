from flask import Flask
import yfinance as yf
import json

app = Flask(__name__)

@app.route('/')
def hello():
    return 'Hello, World!'

@app.route('/api/v1/quote-info/<symbol>/<interval>/<range>')
def get_stock_info(symbol, interval, range):
    # Create a ticker object
    ticker = yf.Ticker(symbol)

    # Get quote information
    quote_info = ticker.info

    # Get historic data
    historic_data = ticker.history(interval=interval, period=range)

    # Convert the historic data to JSON format
    historic_data_json = json.loads(historic_data.to_json())

    # Calculate the percent change in the stock price
    data = ticker.history(period='2d')
    data = data.to_json()
    data = json.loads(data)
    close_price = data['Close']
    dates = list(close_price.keys())
    today = close_price[dates[-1]]
    yesterday = close_price[dates[-2]]
    diff = today - yesterday
    percent_change = diff / yesterday * 100

    # Add diff and percent_change to quote_info
    quote_info['diff'] = diff
    quote_info['percentChange'] = percent_change
    quote_info['today'] = today

    # Combine quote information and historic data
    combined_data = {
        'quoteInfo': quote_info,
        'historicData': historic_data_json
    }

    return combined_data

if __name__ == '__main__':
    app.run()