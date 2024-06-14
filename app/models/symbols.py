import os
import pandas as pd

def load_symbols():
    # Define the directory where this script is located
    current_dir = os.path.dirname(__file__)

    # Construct the absolute path to each Excel file
    nasdaq_path = os.path.join(current_dir, 'nasdaq.xlsx')
    hose_path = os.path.join(current_dir, 'hose.xlsx')

    # Load NASDAQ symbols
    nasdaq_data = pd.read_excel(nasdaq_path)
    nasdaq_symbols = nasdaq_data.iloc[:, 0].tolist()
    
    # Load HOSE symbols and append '.VN' to each symbol
    hose_data = pd.read_excel(hose_path)
    hose_symbols = hose_data.iloc[:, 0].apply(lambda x: str(x) + '.VN').tolist()
    
    # Combine the lists
    all_symbols = nasdaq_symbols + hose_symbols
    return all_symbols

all_symbols = load_symbols()
