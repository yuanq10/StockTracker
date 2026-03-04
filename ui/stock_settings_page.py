import threading
import customtkinter as ctk
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from storage.settings_manager import load_settings, save_settings, load_alerts

INDICATOR_STAT_KEYS = {"CCI": "CCI", "MACD": "MACD", "KDJ K": "KDJ"}


class StockSettingsPage(ctk.CTkFrame):
    def __init__(self, parent, app):
        super().__init__(parent, corner_radius=0, fg_color="transparent")
        self._app = app
        self._fig = None
        self._current_df = None
        self._current_ticker = None
        self._active_indicator = None
        self._stat_key_btns = {}
        self._build_ui()

    # ------------------------------------------------------------------
    # Layout
    # ------------------------------------------------------------------
    def _build_ui(self):
        # ── Top bar ──────────────────────────────────────────────────
        top = ctk.CTkFrame(self, fg_color="transparent")
        top.pack(fill="x", padx=16, pady=(12, 0))

        ctk.CTkLabel(top, text="Stock Settings", font=ctk.CTkFont(size=20, weight="bold")).pack(side="left")

        search_frame = ctk.CTkFrame(top, fg_color="transparent")
        search_frame.pack(side="right")

        self._entry_ticker = ctk.CTkEntry(search_frame, placeholder_text="Enter ticker (e.g. AAPL)", width=220)
        self._entry_ticker.pack(side="left", padx=(0, 8))
        self._entry_ticker.bind("<Return>", lambda _: self._on_add())

        ctk.CTkButton(search_frame, text="Add", width=80, command=self._on_add).pack(side="left")

        self._lbl_msg = ctk.CTkLabel(top, text="", text_color="gray")
        self._lbl_msg.pack(side="left", padx=16)

        # ── Middle row ───────────────────────────────────────────────
        mid = ctk.CTkFrame(self, fg_color="transparent")
        mid.pack(fill="both", expand=True, padx=16, pady=12)

        # Right: my stocks list
        right_panel = ctk.CTkFrame(mid, width=160)
        right_panel.pack(side="right", fill="y", padx=(8, 0))
        right_panel.pack_propagate(False)

        ctk.CTkLabel(right_panel, text="My Stocks", font=ctk.CTkFont(weight="bold")).pack(pady=(10, 4), padx=8)
        self._stocks_list = ctk.CTkScrollableFrame(right_panel)
        self._stocks_list.pack(fill="both", expand=True, padx=4, pady=4)

        # Left: chart + stats
        left_panel = ctk.CTkFrame(mid, fg_color="transparent")
        left_panel.pack(side="left", fill="both", expand=True)

        bottom = ctk.CTkFrame(left_panel, fg_color="transparent")
        bottom.pack(fill="both", expand=True)
        bottom.columnconfigure(0, weight=5)   # Chart (dominant)
        bottom.columnconfigure(1, weight=2)   # Stats
        bottom.rowconfigure(0, weight=1)

        # Chart
        chart_frame = ctk.CTkFrame(bottom)
        chart_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 4))
        ctk.CTkLabel(chart_frame, text="Price Chart", font=ctk.CTkFont(weight="bold")).pack(pady=(10, 4), padx=8, anchor="w")
        self._chart_container = ctk.CTkFrame(chart_frame, fg_color="transparent")
        self._chart_container.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        # Stats
        stats_frame = ctk.CTkFrame(bottom)
        stats_frame.grid(row=0, column=1, sticky="nsew", padx=(4, 0))
        ctk.CTkLabel(stats_frame, text="Stock Stats", font=ctk.CTkFont(weight="bold")).pack(pady=(10, 4), padx=8, anchor="w")
        ctk.CTkLabel(stats_frame, text="Click CCI/MACD/KDJ to plot",
                     text_color="gray", font=ctk.CTkFont(size=10)).pack(padx=8, anchor="w")

        self._stats_inner = ctk.CTkFrame(stats_frame, fg_color="transparent")
        self._stats_inner.pack(fill="both", expand=True, padx=8, pady=(4, 8))

        self._stat_labels = {}

        # Non-clickable stats
        for key, display in [("Close", "Close"), ("Change % (1d)", "Change (1d)"), ("Volume", "Volume")]:
            row = ctk.CTkFrame(self._stats_inner, fg_color="transparent")
            row.pack(fill="x", pady=2)
            ctk.CTkLabel(row, text=f"{display}:", width=80, anchor="w").pack(side="left")
            lbl = ctk.CTkLabel(row, text="—", anchor="w")
            lbl.pack(side="left")
            self._stat_labels[key] = lbl

        # Separator
        ctk.CTkLabel(self._stats_inner, text="─── Indicators (click to plot) ───",
                     text_color="gray", font=ctk.CTkFont(size=10)).pack(pady=(6, 2), anchor="w")

        # Clickable indicator stats
        for stat_key, ind_type in INDICATOR_STAT_KEYS.items():
            row = ctk.CTkFrame(self._stats_inner, fg_color="transparent")
            row.pack(fill="x", pady=2)
            key_btn = ctk.CTkButton(
                row, text=f"{stat_key}:", width=72, anchor="w",
                fg_color="transparent", hover_color=("gray70", "gray35"),
                text_color=("gray30", "gray70"),
                font=ctk.CTkFont(size=12),
                command=lambda k=stat_key, t=ind_type: self._toggle_indicator_plot(k, t)
            )
            key_btn.pack(side="left")
            lbl = ctk.CTkLabel(row, text="—", anchor="w")
            lbl.pack(side="left")
            self._stat_labels[stat_key] = lbl
            self._stat_key_btns[stat_key] = key_btn

        self._refresh_stocks_list()

    # ------------------------------------------------------------------
    # Stocks list
    # ------------------------------------------------------------------
    def on_show(self):
        self._refresh_stocks_list()

    def _refresh_stocks_list(self):
        for w in self._stocks_list.winfo_children():
            w.destroy()
        settings = load_settings()
        stocks = settings.get("stocks", [])
        if not stocks:
            ctk.CTkLabel(self._stocks_list, text="No stocks added", text_color="gray").pack(pady=8)
        for ticker in stocks:
            row = ctk.CTkFrame(self._stocks_list, fg_color="transparent")
            row.pack(fill="x", pady=2)
            btn = ctk.CTkButton(
                row, text=ticker, anchor="w", fg_color="transparent",
                hover_color=("gray70", "gray40"),
                command=lambda t=ticker: self._select_ticker(t)
            )
            btn.pack(side="left", fill="x", expand=True)
            del_btn = ctk.CTkButton(
                row, text="X", width=30, fg_color="transparent",
                text_color="red", hover_color=("gray70", "gray40"),
                command=lambda t=ticker: self._on_remove(t)
            )
            del_btn.pack(side="right")

    def _on_add(self):
        ticker = self._entry_ticker.get().strip().upper()
        if not ticker:
            return
        settings = load_settings()
        stocks = settings.get("stocks", [])
        if ticker in stocks:
            self._lbl_msg.configure(text=f"{ticker} already added.", text_color="orange")
            return
        stocks.append(ticker)
        settings["stocks"] = stocks
        save_settings(settings)
        self._entry_ticker.delete(0, "end")
        self._lbl_msg.configure(text=f"Added {ticker}.", text_color="green")
        self._refresh_stocks_list()

    def _on_remove(self, ticker: str):
        settings = load_settings()
        stocks = settings.get("stocks", [])
        if ticker in stocks:
            stocks.remove(ticker)
        settings["stocks"] = stocks
        save_settings(settings)
        self._lbl_msg.configure(text=f"Removed {ticker}.", text_color="gray")
        self._refresh_stocks_list()

    # ------------------------------------------------------------------
    # Ticker selection
    # ------------------------------------------------------------------
    def _select_ticker(self, ticker: str):
        self._current_ticker = ticker
        self._active_indicator = None
        self._reset_indicator_btn_highlights()
        threading.Thread(target=self._load_ticker_data, args=(ticker,), daemon=True).start()

    def _load_ticker_data(self, ticker: str):
        try:
            from core.data_fetcher import fetch_stock_data, get_stock_info
            df = fetch_stock_data(ticker)
            info = get_stock_info(ticker)
            alerts_data = load_alerts()
            stat = alerts_data.get("stats", {}).get(ticker, {})
            self.after(0, lambda: self._show_ticker_detail(df, ticker, info, stat))
        except Exception as e:
            self.after(0, lambda: self._show_error(str(e)))

    def _show_ticker_detail(self, df, ticker, info, stat):
        self._current_df = df
        self._render_chart(df, ticker, self._active_indicator)

        def fmt(val, suffix=""):
            return f"{val}{suffix}" if val is not None else "—"

        self._stat_labels["Close"].configure(text=fmt(info.get("price")))
        change = info.get("change_pct")
        color = "green" if (change or 0) >= 0 else "red"
        self._stat_labels["Change % (1d)"].configure(text=fmt(change, "%"), text_color=color)
        vol = info.get("volume")
        self._stat_labels["Volume"].configure(text=f"{vol:,}" if vol else "—")
        self._stat_labels["CCI"].configure(text=fmt(stat.get("cci")))
        self._stat_labels["MACD"].configure(text=fmt(stat.get("macd")))
        self._stat_labels["KDJ K"].configure(text=fmt(stat.get("kdj_k")))

    def _show_error(self, msg: str):
        for w in self._chart_container.winfo_children():
            w.destroy()
        ctk.CTkLabel(self._chart_container, text=f"Error: {msg}", text_color="red").pack(expand=True)

    # ------------------------------------------------------------------
    # Indicator subplot toggle
    # ------------------------------------------------------------------
    def _toggle_indicator_plot(self, stat_key: str, ind_type: str):
        if self._current_df is None or self._current_ticker is None:
            return
        if self._active_indicator == ind_type:
            self._active_indicator = None
            self._reset_indicator_btn_highlights()
        else:
            self._active_indicator = ind_type
            self._reset_indicator_btn_highlights()
            self._stat_key_btns[stat_key].configure(
                text_color=("#1a7fd4", "#4a9eff"),
                fg_color=("gray80", "gray25")
            )
        self._render_chart(self._current_df, self._current_ticker, self._active_indicator)

    def _reset_indicator_btn_highlights(self):
        for btn in self._stat_key_btns.values():
            btn.configure(text_color=("gray30", "gray70"), fg_color="transparent")

    # ------------------------------------------------------------------
    # Chart rendering
    # ------------------------------------------------------------------
    def _render_chart(self, df, ticker: str, indicator: str = None):
        for w in self._chart_container.winfo_children():
            w.destroy()
        if self._fig:
            plt.close(self._fig)

        bg = "#2b2b2b"
        fg = "white"

        if indicator:
            self._fig, (ax_price, ax_ind) = plt.subplots(
                2, 1, figsize=(5, 4), facecolor=bg,
                gridspec_kw={"height_ratios": [3, 2]}, sharex=False
            )
        else:
            self._fig, ax_price = plt.subplots(figsize=(5, 3), facecolor=bg)
            ax_ind = None

        # Price subplot
        ax_price.set_facecolor(bg)
        ax_price.plot(df.index, df["Close"], color="#4a9eff", linewidth=1.5)
        ax_price.set_title(ticker, color=fg, fontsize=10)
        ax_price.tick_params(colors=fg, labelsize=7)
        ax_price.spines[:].set_color("gray")
        if ax_ind is None:
            ax_price.xaxis.set_major_locator(matplotlib.dates.AutoDateLocator())
            ax_price.xaxis.set_major_formatter(matplotlib.dates.DateFormatter("%m/%d"))
            plt.setp(ax_price.get_xticklabels(), rotation=30, ha="right")
        else:
            plt.setp(ax_price.get_xticklabels(), visible=False)

        # Indicator subplot
        if ax_ind is not None:
            ax_ind.set_facecolor(bg)
            ax_ind.tick_params(colors=fg, labelsize=7)
            ax_ind.spines[:].set_color("gray")
            ax_ind.xaxis.set_major_locator(matplotlib.dates.AutoDateLocator())
            ax_ind.xaxis.set_major_formatter(matplotlib.dates.DateFormatter("%m/%d"))
            plt.setp(ax_ind.get_xticklabels(), rotation=30, ha="right")

            settings = load_settings()
            ind_cfg = next((i for i in settings.get("indicators", []) if i["type"] == indicator), {})
            self._plot_indicator(ax_ind, df, indicator, ind_cfg, fg, bg)

        self._fig.tight_layout(pad=0.5)
        canvas = FigureCanvasTkAgg(self._fig, master=self._chart_container)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)

    def _plot_indicator(self, ax, df, indicator: str, ind_cfg: dict, fg: str, bg: str):
        from core.indicators import calc_cci, calc_macd, calc_kdj

        if indicator == "CCI":
            period = ind_cfg.get("period", 20)
            cci = calc_cci(df, period).dropna()
            ax.plot(cci.index, cci.values, color="#ff9f40", linewidth=1.2)
            buy_th = ind_cfg.get("buy_threshold", -100)
            sell_th = ind_cfg.get("sell_threshold", 100)
            ax.axhline(buy_th, color="lime", linestyle="--", linewidth=0.8, alpha=0.8)
            ax.axhline(sell_th, color="tomato", linestyle="--", linewidth=0.8, alpha=0.8)
            ax.axhline(0, color="gray", linewidth=0.5, alpha=0.5)
            ax.set_ylabel("CCI", color=fg, fontsize=7)

        elif indicator == "MACD":
            fast = ind_cfg.get("fast", 12)
            slow = ind_cfg.get("slow", 26)
            signal = ind_cfg.get("signal", 9)
            result = calc_macd(df, fast, slow, signal)
            macd_s = result["macd"].dropna()
            sig_s = result["signal"].dropna()
            hist_s = result["histogram"].dropna()
            idx = macd_s.index.intersection(sig_s.index).intersection(hist_s.index)
            ax.plot(macd_s[idx].index, macd_s[idx].values, color="#4a9eff", linewidth=1.2, label="MACD")
            ax.plot(sig_s[idx].index, sig_s[idx].values, color="#ff6b6b", linewidth=1.2, label="Signal")
            pos = hist_s[idx][hist_s[idx] >= 0]
            neg = hist_s[idx][hist_s[idx] < 0]
            if not pos.empty:
                ax.bar(pos.index, pos.values, color="lime", alpha=0.45, width=0.8)
            if not neg.empty:
                ax.bar(neg.index, neg.values, color="tomato", alpha=0.45, width=0.8)
            buy_th = ind_cfg.get("buy_threshold")
            sell_th = ind_cfg.get("sell_threshold")
            if buy_th is not None and buy_th != 0:
                ax.axhline(buy_th, color="lime", linestyle="--", linewidth=0.8, alpha=0.8)
            if sell_th is not None and sell_th != 0:
                ax.axhline(sell_th, color="tomato", linestyle="--", linewidth=0.8, alpha=0.8)
            ax.axhline(0, color="gray", linewidth=0.5, alpha=0.5)
            ax.set_ylabel("MACD", color=fg, fontsize=7)
            ax.legend(fontsize=6, facecolor=bg, labelcolor=fg, loc="upper left")

        elif indicator == "KDJ":
            period = ind_cfg.get("period", 9)
            k_smooth = ind_cfg.get("k_smooth", 3)
            d_smooth = ind_cfg.get("d_smooth", 3)
            result = calc_kdj(df, period, k_smooth, d_smooth)
            K = result["K"].dropna()
            D = result["D"].dropna()
            J = result["J"].dropna()
            ax.plot(K.index, K.values, color="#4a9eff", linewidth=1.2, label="K")
            ax.plot(D.index, D.values, color="#ff9f40", linewidth=1.2, label="D")
            ax.plot(J.index, J.values, color="#ff6b6b", linewidth=1.2, label="J")
            buy_th = ind_cfg.get("buy_threshold", 20)
            sell_th = ind_cfg.get("sell_threshold", 80)
            ax.axhline(buy_th, color="lime", linestyle="--", linewidth=0.8, alpha=0.8)
            ax.axhline(sell_th, color="tomato", linestyle="--", linewidth=0.8, alpha=0.8)
            ax.set_ylabel("KDJ", color=fg, fontsize=7)
            ax.legend(fontsize=6, facecolor=bg, labelcolor=fg, loc="upper left")
