import yfinance as yf
import pandas as pd


def fetch_stock_data(ticker: str, period: str = "3mo", interval: str = "1d") -> pd.DataFrame:
    """Download OHLCV data for a ticker. Returns a DataFrame."""
    df = yf.download(ticker, period=period, interval=interval, auto_adjust=True, progress=False)
    if df.empty:
        raise ValueError(f"No data returned for ticker '{ticker}'")
    # Flatten multi-level columns if present
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df.index = pd.to_datetime(df.index)
    return df


def get_stock_info(ticker: str) -> dict:
    """Return basic info: name, current price, % change, volume."""
    try:
        t = yf.Ticker(ticker)
        info = t.info
        name = info.get("shortName") or info.get("longName") or ticker
        price = info.get("currentPrice") or info.get("regularMarketPrice") or 0.0
        prev_close = info.get("regularMarketPreviousClose") or info.get("previousClose") or price
        change_pct = ((price - prev_close) / prev_close * 100) if prev_close else 0.0
        volume = info.get("regularMarketVolume") or info.get("volume") or 0
        return {
            "ticker": ticker,
            "name": name,
            "price": round(price, 2),
            "change_pct": round(change_pct, 2),
            "volume": volume,
        }
    except Exception:
        return {"ticker": ticker, "name": ticker, "price": 0.0, "change_pct": 0.0, "volume": 0}
