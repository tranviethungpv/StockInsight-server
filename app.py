from flask import Flask
import yfinance as yf

app = Flask(__name__)

@app.route('/')
def hello():
    return 'Hello, World!'

@app.route('/stock/<ticker>')
def stock(ticker):
    stock = yf.Ticker(ticker)
    return stock.history(period='1m').to_json()

if __name__ == '__main__':
    app.run()