from core.data_fetcher import fetch_stock_data, get_stock_info
from core.indicators import calc_cci, calc_macd, calc_kdj, calc_generic_indicator


def run_alerts(stocks: list, indicators: list, on_progress=None) -> dict:
    """
    Run alert checks for all stocks against all enabled indicators.
    Returns:
        {
          "alerts": { ticker: [alert_dict, ...] },
          "stats":  { ticker: stat_dict }
        }
    """
    results_alerts = {}
    results_stats = {}

    enabled = [ind for ind in indicators if ind.get("enabled", True)]

    for i, ticker in enumerate(stocks):
        if on_progress:
            on_progress(ticker, i, len(stocks))
        try:
            df = fetch_stock_data(ticker)
            info = get_stock_info(ticker)
        except Exception as e:
            results_alerts[ticker] = [{"indicator": "ERROR", "signal": "error",
                                       "value": None, "reason": str(e)}]
            results_stats[ticker] = {}
            continue

        ticker_alerts = []
        stat = {
            "close": info["price"],
            "change_pct": info["change_pct"],
            "volume": info["volume"],
            "cci": None,
            "macd": None,
            "kdj_k": None,
        }

        for ind in enabled:
            itype = ind["type"]
            try:
                if itype == "CCI":
                    period = ind.get("period", 20)
                    buy_th = ind.get("buy_threshold", -100)
                    sell_th = ind.get("sell_threshold", 100)
                    cci = calc_cci(df, period)
                    val = float(cci.dropna().iloc[-1])
                    stat["cci"] = round(val, 2)
                    if val < buy_th:
                        ticker_alerts.append({
                            "indicator": "CCI",
                            "signal": "buy",
                            "value": round(val, 2),
                            "reason": f"CCI {val:.2f} below oversold threshold {buy_th}"
                        })
                    elif val > sell_th:
                        ticker_alerts.append({
                            "indicator": "CCI",
                            "signal": "sell",
                            "value": round(val, 2),
                            "reason": f"CCI {val:.2f} above overbought threshold {sell_th}"
                        })

                elif itype == "MACD":
                    fast = ind.get("fast", 12)
                    slow = ind.get("slow", 26)
                    signal = ind.get("signal", 9)
                    buy_th = ind.get("buy_threshold", None)
                    sell_th = ind.get("sell_threshold", None)
                    result = calc_macd(df, fast, slow, signal)
                    hist = result["histogram"].dropna()
                    macd_val = float(result["macd"].dropna().iloc[-1])
                    stat["macd"] = round(macd_val, 4)
                    if len(hist) >= 2:
                        prev_hist = float(hist.iloc[-2])
                        curr_hist = float(hist.iloc[-1])
                        # Crossover alerts (always active)
                        if prev_hist < 0 and curr_hist > 0:
                            ticker_alerts.append({
                                "indicator": "MACD",
                                "signal": "buy",
                                "value": round(curr_hist, 4),
                                "reason": f"MACD crossed above signal line (histogram {curr_hist:.4f})"
                            })
                        elif prev_hist > 0 and curr_hist < 0:
                            ticker_alerts.append({
                                "indicator": "MACD",
                                "signal": "sell",
                                "value": round(curr_hist, 4),
                                "reason": f"MACD crossed below signal line (histogram {curr_hist:.4f})"
                            })
                        # Range alert: histogram within [sell_th, buy_th] (convergence zone)
                        if buy_th is not None and sell_th is not None:
                            if sell_th < curr_hist < buy_th:
                                ticker_alerts.append({
                                    "indicator": "MACD",
                                    "signal": "alert",
                                    "value": round(curr_hist, 4),
                                    "reason": f"MACD histogram {curr_hist:.4f} within convergence range [{sell_th}, {buy_th}]"
                                })

                elif itype == "KDJ":
                    period = ind.get("period", 9)
                    k_smooth = ind.get("k_smooth", 3)
                    d_smooth = ind.get("d_smooth", 3)
                    buy_th = ind.get("buy_threshold", 20)
                    sell_th = ind.get("sell_threshold", 80)
                    result = calc_kdj(df, period, k_smooth, d_smooth)
                    K = result["K"].dropna()
                    D = result["D"].dropna()
                    J = result["J"].dropna()
                    k_val = float(K.iloc[-1])
                    stat["kdj_k"] = round(k_val, 2)
                    # J threshold alerts
                    if len(J) >= 1:
                        j_val = float(J.iloc[-1])
                        if j_val < buy_th:
                            ticker_alerts.append({
                                "indicator": "KDJ",
                                "signal": "buy",
                                "value": round(j_val, 2),
                                "reason": f"KDJ J={j_val:.2f} below oversold threshold {buy_th}"
                            })
                        elif j_val > sell_th:
                            ticker_alerts.append({
                                "indicator": "KDJ",
                                "signal": "sell",
                                "value": round(j_val, 2),
                                "reason": f"KDJ J={j_val:.2f} above overbought threshold {sell_th}"
                            })
                    # K/D crossover alerts
                    common = K.index.intersection(D.index)
                    if len(common) >= 2:
                        prev_k = float(K[common].iloc[-2])
                        prev_d = float(D[common].iloc[-2])
                        curr_k = float(K[common].iloc[-1])
                        curr_d = float(D[common].iloc[-1])
                        if prev_k <= prev_d and curr_k > curr_d:
                            ticker_alerts.append({
                                "indicator": "KDJ",
                                "signal": "buy",
                                "value": round(curr_k, 2),
                                "reason": f"KDJ K={curr_k:.2f} crossed above D={curr_d:.2f} (bullish crossover)"
                            })
                        elif prev_k >= prev_d and curr_k < curr_d:
                            ticker_alerts.append({
                                "indicator": "KDJ",
                                "signal": "sell",
                                "value": round(curr_k, 2),
                                "reason": f"KDJ K={curr_k:.2f} crossed below D={curr_d:.2f} (bearish crossover)"
                            })

                else:
                    # Generic TA-Lib indicator
                    buy_th = ind.get("buy_threshold", None)
                    sell_th = ind.get("sell_threshold", None)
                    # Pass all numeric params (except type, enabled, thresholds) to the function
                    SKIP = {"type", "enabled", "buy_threshold", "sell_threshold"}
                    ta_params = {k: v for k, v in ind.items() if k not in SKIP and isinstance(v, (int, float))}
                    series = calc_generic_indicator(df, itype, **ta_params)
                    val = float(series.dropna().iloc[-1])
                    if buy_th is not None and val < buy_th:
                        ticker_alerts.append({
                            "indicator": itype,
                            "signal": "buy",
                            "value": round(val, 4),
                            "reason": f"{itype} {val:.4f} below buy threshold {buy_th}"
                        })
                    elif sell_th is not None and val > sell_th:
                        ticker_alerts.append({
                            "indicator": itype,
                            "signal": "sell",
                            "value": round(val, 4),
                            "reason": f"{itype} {val:.4f} above sell threshold {sell_th}"
                        })

            except Exception as e:
                ticker_alerts.append({
                    "indicator": itype,
                    "signal": "error",
                    "value": None,
                    "reason": f"{itype} error: {e}"
                })

        results_alerts[ticker] = ticker_alerts
        results_stats[ticker] = stat

    return {"alerts": results_alerts, "stats": results_stats}
