import pandas as pd

def load_symbols():
    # Load NASDAQ symbols
    nasdaq_data = pd.read_excel('nasdaq.xlsx')
    nasdaq_symbols = nasdaq_data.iloc[:, 0].tolist()
    
    # Load HOSE symbols and append '.VN' to each symbol
    hose_data = pd.read_excel('hose.xlsx')
    hose_symbols = hose_data.iloc[:, 0].apply(lambda x: str(x) + '.VN').tolist()
    
    # Combine the lists
    all_symbols = nasdaq_symbols + hose_symbols
    return all_symbols

all_symbols = load_symbols()