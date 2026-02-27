"""Configuration: ticker mappings, indices list, constants."""

# Google Sheet ticker → Yahoo Finance ticker mapping
TICKER_MAP = {
    # London Stock Exchange
    "LON:VUSA": "VUSA.L",
    "LON:BARC": "BARC.L",
    "LON:BT.A": "BT-A.L",
    "LON:CNA": "CNA.L",
    "LON:ANTO": "ANTO.L",
    "LON:HSBA": "HSBA.L",
    # US - NASDAQ
    "NASDAQ:TSLA": "TSLA",
    "NASDAQ:MSFT": "MSFT",
    "NASDAQ:AAPL": "AAPL",
    "NASDAQ:NVDA": "NVDA",
    "NASDAQ:GOOGL": "GOOGL",
    "NASDAQ:AMD": "AMD",
    "NASDAQ:AMZN": "AMZN",
    "NASDAQ:META": "META",
    "NASDAQ:NFLX": "NFLX",
    "NASDAQ:INTC": "INTC",
    "NASDAQ:AVGO": "AVGO",
    "NASDAQ:ADBE": "ADBE",
    "NASDAQ:IREN": "IREN",
    "NASDAQ:MU": "MU",
    # US - NYSE
    "NYSE:HDB": "HDB",
    "NYSE:V": "V",
    "NYSE:MCO": "MCO",
    "NYSE:SPGI": "SPGI",
    "NYSE:BRK.B": "BRK-B",
    "NYSE:MA": "MA",
    "NYSE:AXP": "AXP",
    "NYSE:UNH": "UNH",
    "NYSE:IONQ": "IONQ",
    "NYSE:ORCL": "ORCL",
    # Other
    "NYSEARCA:VOO": "VOO",
    "NYSEARCA:COPX": "COPX",
    "OTCMKTS:BYDDY": "BYDDY",
    "NSE:TATAPOWER": "TATAPOWER.NS",
}

# World indices for the dashboard
INDICES = [
    {"ticker": "^GSPC", "display_name": "S&P 500", "sort_order": 1},
    {"ticker": "^DJI", "display_name": "Dow Jones", "sort_order": 2},
    {"ticker": "^IXIC", "display_name": "NASDAQ", "sort_order": 3},
    {"ticker": "^FTSE", "display_name": "FTSE 100", "sort_order": 4},
    {"ticker": "^AXJO", "display_name": "ASX 200", "sort_order": 5},
    {"ticker": "^STOXX50E", "display_name": "STOXX Europe 600", "sort_order": 6},
    {"ticker": "^NSEI", "display_name": "Nifty 50", "sort_order": 7},
    {"ticker": "^BSESN", "display_name": "Sensex", "sort_order": 8},
    {"ticker": "^HSI", "display_name": "Hang Seng", "sort_order": 9},
    {"ticker": "000001.SS", "display_name": "Shanghai Composite", "sort_order": 10},
    {"ticker": "^N225", "display_name": "Nikkei 225", "sort_order": 11},
]

# Currency pairs to track
FX_PAIRS = [
    {"ticker": "GBPUSD=X", "display_name": "GBP/USD"},
    {"ticker": "GBPEUR=X", "display_name": "GBP/EUR"},
    {"ticker": "GBPINR=X", "display_name": "GBP/INR"},
]

# Watchlist order matching Google Sheet (left to right)
WATCHLIST_ORDER = [
    "VUSA.L", "BARC.L", "BT-A.L", "TSLA", "HDB", "MSFT", "AAPL", "NVDA",
    "GOOGL", "AMD", "VOO", "V", "MCO", "SPGI", "BYDDY", "AMZN", "CNA.L",
    "META", "BRK-B", "NFLX", "MA", "TATAPOWER.NS", "AXP", "ANTO.L", "UNH",
    "HSBA.L", "INTC", "AVGO", "ADBE", "IREN", "IONQ", "MU", "COPX",
    "XAUUSD=X", "XAGUSD=X", "ORCL", "TATAPOWER.NS",
]

# Brokers
BROKERS = ["JB", "DBS"]

# Base currency for the portfolio
BASE_CURRENCY = "GBP"
