import pandas as pd
import numpy as np


def _ema(series: pd.Series, span: int) -> pd.Series:
    return series.ewm(span=span, adjust=False).mean()


def calc_cci(df: pd.DataFrame, period: int = 20) -> pd.Series:
    """Commodity Channel Index."""
    tp = (df["High"] + df["Low"] + df["Close"]) / 3
    mean_tp = tp.rolling(period).mean()
    mean_dev = (tp - mean_tp).abs().rolling(period).mean()
    cci = (tp - mean_tp) / (0.015 * mean_dev)
    return cci


def calc_macd(df: pd.DataFrame, fast: int = 12, slow: int = 26, signal: int = 9) -> dict:
    """MACD line, signal line, histogram."""
    close = df["Close"]
    ema_fast = _ema(close, fast)
    ema_slow = _ema(close, slow)
    macd_line = ema_fast - ema_slow
    signal_line = _ema(macd_line, signal)
    histogram = macd_line - signal_line
    return {"macd": macd_line, "signal": signal_line, "histogram": histogram}


def calc_kdj(df: pd.DataFrame, period: int = 9, k_smooth: int = 3, d_smooth: int = 3) -> dict:
    """KDJ stochastic oscillator."""
    low = df["Low"]
    high = df["High"]
    close = df["Close"]
    lowest_low = low.rolling(period).min()
    highest_high = high.rolling(period).max()
    denom = highest_high - lowest_low
    rsv = (close - lowest_low) / denom.replace(0, np.nan) * 100
    rsv = rsv.fillna(50)
    K = rsv.ewm(span=k_smooth, adjust=False).mean()
    D = K.ewm(span=d_smooth, adjust=False).mean()
    J = 3 * K - 2 * D
    return {"K": K, "D": D, "J": J}
