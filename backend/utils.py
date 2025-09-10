# utils.py
import pandas as pd
import numpy as np
import yfinance as yf
import os
from typing import Tuple
import datetime

def get_nse100_tickers(csv_path='ind_nifty100list.csv'):
    """
    Returns Nifty100 tickers in yfinance format (with .NS suffix).
    Assumes CSV has a column 'Symbol'.
    """
    nse_tickers = [
    'ASIANPAINT.NS', 'AXISBANK.NS', 'BAJFINANCE.NS', 'BAJAJFINSV.NS', 'BHARTIARTL.NS',
    'HCLTECH.NS', 'HDFCBANK.NS', 'HINDUNILVR.NS', 'ICICIBANK.NS', 'INDUSINDBK.NS',
    'INFY.NS', 'ITC.NS', 'JSWSTEEL.NS', 'KOTAKBANK.NS', 'LT.NS',
    'M&M.NS', 'MARUTI.NS', 'NESTLEIND.NS', 'NTPC.NS', 'POWERGRID.NS',
    'RELIANCE.NS', 'SBIN.NS', 'SUNPHARMA.NS', 'TCS.NS', 'TATAMOTORS.NS',
    'TATASTEEL.NS', 'TECHM.NS', 'TITAN.NS', 'ULTRACEMCO.NS', 'WIPRO.NS']
    return nse_tickers

def get_yfinance_news_summary(ticker: str, max_items: int = 10) -> str:
    """
    Use yfinance .news (best-effort). Returns simple aggregated text.
    """
    try:
        stock = yf.Ticker(ticker)
        news_list = getattr(stock, "news", []) or []
        if not news_list:
            return "No recent news found."
        news_summary_text = ""
        for news_item in news_list[:max_items]:
            title = news_item.get('title') or news_item.get('providerPublishTime') or "<headline>"
            summary = ""
            for k in ['summary', 'publisher', 'link']:
                if news_item.get('content').get(k):
                    summary += f"{news_item.get(k)} "
            news_summary_text += f"- {title.strip()}: {summary.strip()}\n"
        return news_summary_text.strip()
    except Exception as e:
        return f"Could not fetch news via yfinance API: {e}"

def get_stock_data_summary(ticker: str) -> Tuple[dict, str]:
    """
    Gathers quantitative data for a single stock, including price pattern analysis.
    Returns (data_dict, status)
    """
    try:
        stock = yf.Ticker(ticker)
        info = getattr(stock, "info", {}) or {}

        hist = stock.history(period="1y")
        if hist is None or hist.empty:
            return None, "Could not fetch history."

        hist = hist.copy()
        hist['daily_return'] = hist['Close'].pct_change()
        volatility = float(hist['daily_return'].std() * np.sqrt(252))

        x = np.arange(len(hist))
        y = hist['Close'].values
        if len(y) >= 2:
            slope, _ = np.polyfit(x, y, 1)
            normalized_slope = float(slope / y.mean()) if y.mean() != 0 else 0.0
        else:
            normalized_slope = 0.0

        high_52w = float(hist['High'].max())
        low_52w = float(hist['Low'].min())
        current_price = float(hist['Close'].iloc[-1])
        position_in_52w_range = float((current_price - low_52w) / (high_52w - low_52w)) if (high_52w - low_52w) != 0 else 0.5

        delta = hist['Close'].diff()
        gain = delta.clip(lower=0).rolling(window=14).mean()
        loss = -delta.clip(upper=0).rolling(window=14).mean()
        rsi = float(100 - (100 / (1 + (gain.iloc[-1] / loss.iloc[-1])))) if loss.iloc[-1] != 0 else 100.0

        sma_50 = float(hist['Close'].rolling(window=50).mean().iloc[-1]) if len(hist) >= 50 else float(np.nan)
        sma_200 = float(hist['Close'].rolling(window=200).mean().iloc[-1]) if len(hist) >= 200 else float(np.nan)

        info_map = {
            'Ticker': ticker.replace(".NS", ""),
            'longName': info.get('longName', ticker.replace(".NS","")),
            'currentPrice': current_price,
            'marketCap': info.get('marketCap', 0),
            'averageVolume': info.get('averageVolume', 0),
            'beta': info.get('beta', 0),
            '52WeekChange': info.get('52WeekChange', 0),
            'trailingEps': info.get('trailingEps', 0),
            'forwardEps': info.get('forwardEps', 0),
            'priceToBook': info.get('priceToBook', 0),
            'trailingPE': info.get('trailingPE', 0),
            'profitMargins': info.get('profitMargins', 0),
            'grossMargins': info.get('grossMargins', 0),
            'ebitdaMargins': info.get('ebitdaMargins', 0),
            'returnOnEquity': info.get('returnOnEquity', 0),
            'debtToEquity': info.get('debtToEquity', 0),
            'revenuePerShare': info.get('revenuePerShare', 0),
            'earningsGrowth': info.get('earningsGrowth', 0),
            'revenueGrowth': info.get('revenueGrowth', 0),
            'dividendYield': info.get('dividendYield', 0),
            'earningsQuarterlyGrowth': info.get('earningsQuarterlyGrowth', 0),
            'RSI': rsi,
            'sma_50': sma_50,
            'sma_200': sma_200,
            'volatility': volatility,
            'trend_slope': normalized_slope,
            'position_in_52w_range': position_in_52w_range,
            'fetched_at': datetime.datetime.utcnow().isoformat() + 'Z'
        }
        return info_map, "Success"
    except Exception as e:
        return None, f"An error occurred in get_stock_data_summary: {e}"
